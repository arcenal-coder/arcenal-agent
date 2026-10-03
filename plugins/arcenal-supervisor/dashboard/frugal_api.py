"""API administrateur d'ARC Frugal et des automatisations gouvernées."""

from __future__ import annotations

import re
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from arc_core.frugal_models import AutomationWorkflow, WorkflowStatus


router = APIRouter(prefix="/frugal/v1")
ACTOR_RE = re.compile(r"[^\w@.+\- ]", re.UNICODE)


def _core() -> ModuleType:
    core = sys.modules.get("arcenal_arc_core")
    if core is None:
        raise RuntimeError("ARC Core doit être chargé avant l'API ARC Frugal.")
    return core


CORE = _core()


class WorkflowTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: str = Field(pattern=r"^(testing|active|disabled|archived)$")


class CacheInvalidation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    identifier: str = Field(min_length=1, max_length=240)


def _runtime():
    from hermes_constants import get_hermes_home

    runtime = CORE.FrugalRuntime(get_hermes_home() / "arcenal" / "frugal")
    runtime.ensure_configured_model()
    return runtime


def _actor(request: Request) -> str:
    raw = next((request.headers.get(name, "") for name in ("x-remote-user", "remote-user", "x-auth-user") if request.headers.get(name)), "")
    actor = ACTOR_RE.sub("", raw).strip()[:120]
    if not actor:
        raise HTTPException(status_code=401, detail="Authentification administrateur requise.")
    return actor


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (ValueError, ValidationError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="ARC Frugal est indisponible.")


@router.get("/overview")
def overview(request: Request) -> dict[str, object]:
    _actor(request)
    runtime = _runtime()
    return {"metrics": runtime.metrics.metrics().model_dump(mode="json"), "models": [item.model_dump(mode="json") for item in runtime.registry.list()], "providers": [item.model_dump(mode="json") for item in runtime.providers.list()], "traces": [item.model_dump(mode="json") for item in runtime.metrics.recent()]}


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    _actor(request)
    runtime = _runtime()
    providers = runtime.providers.list()
    configuration = CORE.runtime_configuration()
    return {
        "status": "healthy",
        "components": {"backend": "healthy", "storage": "healthy", "provider_registry": "healthy"},
        "config_backend": configuration.backend,
        "migration_status": configuration.migration_state,
        "providers": {item.id: item.health.value for item in providers},
        "remote_provider_required": False,
        "vault_status": "ready",
    }


@router.put("/providers/{provider_id}")
def save_provider(provider_id: str, request: Request, payload: dict[str, object]) -> dict[str, object]:
    actor = _actor(request)
    try:
        provider = CORE.ProviderDescriptor.model_validate_json(json.dumps({**payload, "id": provider_id}))
        saved = _runtime().providers.upsert(provider)
        CORE.append_agent_event("frugal.provider.saved", actor, {"provider_id": provider_id, "enabled": provider.enabled})
        return saved.model_dump(mode="json")
    except Exception as exc:
        raise _translate(exc) from exc


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str, request: Request) -> dict[str, bool]:
    actor = _actor(request)
    runtime = _runtime()
    if any(item.provider == provider_id for item in runtime.registry.list()):
        raise HTTPException(status_code=409, detail="Ce fournisseur est encore utilisé par un modèle.")
    runtime.providers.remove(provider_id)
    CORE.append_agent_event("frugal.provider.removed", actor, {"provider_id": provider_id})
    return {"deleted": True}


@router.put("/models/{model_id}")
def save_model(model_id: str, request: Request, payload: dict[str, object]) -> dict[str, object]:
    actor = _actor(request)
    try:
        model = CORE.ModelDescriptor.model_validate_json(json.dumps({**payload, "id": model_id}))
        runtime = _runtime()
        saved = runtime.registry.upsert(model)
        if not model.enabled:
            runtime.cache.invalidate("model", model_id)
        CORE.append_agent_event("frugal.model.saved", actor, {"model_id": model_id})
        return saved.model_dump(mode="json")
    except Exception as exc:
        raise _translate(exc) from exc


@router.delete("/models/{model_id}")
def delete_model(model_id: str, request: Request) -> dict[str, bool]:
    actor = _actor(request)
    runtime = _runtime()
    runtime.registry.remove(model_id)
    runtime.cache.invalidate("model", model_id)
    CORE.append_agent_event("frugal.model.removed", actor, {"model_id": model_id})
    return {"deleted": True}


@router.get("/automations")
def automations(request: Request) -> dict[str, object]:
    _actor(request)
    store = _runtime().automations
    return {"workflows": [item.model_dump(mode="json") for item in store.workflows()], "candidates": [item.model_dump(mode="json") for item in store.candidates()]}


@router.post("/workflows")
def create_workflow(request: Request, payload: dict[str, object]) -> dict[str, object]:
    actor = _actor(request)
    now = datetime.now(timezone.utc)
    try:
        values = {**payload, "status": "draft", "created_at": now.isoformat(), "updated_at": now.isoformat(), "approved_by": None}
        workflow = CORE.AutomationWorkflow.model_validate_json(json.dumps(values))
        saved = _runtime().automations.save_workflow(workflow)
        CORE.append_agent_event("frugal.workflow.created", actor, {"workflow_id": workflow.id})
        return saved.model_dump(mode="json")
    except Exception as exc:
        raise _translate(exc) from exc


def _cron_dashboard() -> ModuleType:
    from hermes_cli import web_server

    return web_server


def _create_cron_job(workflow: AutomationWorkflow) -> str:
    from hermes_cli.web_models import CronJobCreate

    schedule = workflow.schedule
    if schedule is None:
        raise CORE.AutomationPolicyError("Une planification est requise pour créer la tâche exécutable.")
    body = CronJobCreate(prompt=workflow.description, schedule=schedule, name=workflow.name, deliver="local")
    job = _cron_dashboard()._create_cron_job_sync(body, workflow.profile_name or "default")
    return str(job["id"])


def _update_cron_state(workflow: AutomationWorkflow, status: WorkflowStatus) -> None:
    if workflow.cron_job_id is None:
        return
    dashboard = _cron_dashboard()
    profile = workflow.profile_name or "default"
    if status is CORE.WorkflowStatus.ACTIVE:
        dashboard._resume_cron_job_sync(workflow.cron_job_id, profile)
        return
    if status is CORE.WorkflowStatus.ARCHIVED:
        dashboard._delete_cron_job_sync(workflow.cron_job_id, profile)
        return
    dashboard._pause_cron_job_sync(workflow.cron_job_id, profile)


def _cron_job_exists(workflow: AutomationWorkflow) -> bool:
    if workflow.cron_job_id is None:
        return False
    try:
        _cron_dashboard()._get_cron_job_sync(workflow.cron_job_id, workflow.profile_name or "default")
    except HTTPException as exc:
        if exc.status_code == 404:
            return False
        raise
    return True


def _synchronize_scheduled_workflow(current: AutomationWorkflow, updated: AutomationWorkflow) -> AutomationWorkflow:
    if updated.schedule is None:
        return updated
    if updated.status is CORE.WorkflowStatus.ACTIVE and not _cron_job_exists(current):
        return updated.model_copy(update={"cron_job_id": _create_cron_job(updated)})
    _update_cron_state(current, updated.status)
    return updated


@router.post("/workflows/{workflow_id}/transition")
def change_workflow(workflow_id: str, payload: WorkflowTransition, request: Request) -> dict[str, object]:
    actor = _actor(request)
    store = _runtime().automations
    current = next((item for item in store.workflows() if item.id == workflow_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable.")
    try:
        updated = CORE.transition_workflow(current, CORE.WorkflowStatus(payload.status), actor)
        updated = _synchronize_scheduled_workflow(current, updated)
        store.save_workflow(updated)
        CORE.append_agent_event("frugal.workflow.transition", actor, {"workflow_id": workflow_id, "status": payload.status})
        return updated.model_dump(mode="json")
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/cache/invalidate")
def invalidate_cache(payload: CacheInvalidation, request: Request) -> dict[str, int]:
    actor = _actor(request)
    count = _runtime().cache.invalidate(payload.kind, payload.identifier)
    CORE.append_agent_event("frugal.cache.invalidated", actor, {"kind": payload.kind, "identifier": payload.identifier, "count": count})
    return {"invalidated": count}
