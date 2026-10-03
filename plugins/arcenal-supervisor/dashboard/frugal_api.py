"""API administrateur d'ARC Frugal et des automatisations gouvernées."""

from __future__ import annotations

import re
import sys
import json
import fcntl
import logging
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, AsyncIterator, Iterator, cast

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from arc_core.automation_engine import AutomationStore
    from arc_core.frugal_models import AutomationWorkflow, WorkflowStatus


ACTOR_RE = re.compile(r"[^\w@.+\- ]", re.UNICODE)
LOGGER = logging.getLogger(__name__)
WORKFLOW_TRANSITION_LOCK = threading.RLock()
MANAGED_CRON_PREFIX = "ARC-WORKFLOW:"
DORMANT_CRON_SCHEDULE = "2099-12-31T23:59:00+00:00"


@asynccontextmanager
async def _automation_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        with _workflow_transition_lock():
            _reconcile_scheduled_workflows(_runtime().automations)
    except Exception:
        LOGGER.exception("La réconciliation des automatisations ARC a échoué au démarrage.")
    yield


router = APIRouter(prefix="/frugal/v1", lifespan=_automation_lifespan)


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


class WorkflowConsistencyError(RuntimeError):
    """Signale une compensation incomplète nécessitant une réconciliation."""


def _runtime():
    from hermes_constants import get_hermes_home

    runtime = CORE.FrugalRuntime(get_hermes_home() / "arcenal" / "frugal")
    runtime.ensure_configured_model()
    return runtime


@contextmanager
def _workflow_transition_lock() -> Iterator[None]:
    from hermes_constants import get_hermes_home

    lock_path = get_hermes_home() / "arcenal" / "frugal" / ".workflow-transition.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with WORKFLOW_TRANSITION_LOCK, lock_path.open("a+b") as handle:
        lock_path.chmod(0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
    with _workflow_transition_lock():
        store = _runtime().automations
        _reconcile_scheduled_workflows(store)
    return {"workflows": [item.model_dump(mode="json") for item in store.workflows()], "candidates": [item.model_dump(mode="json") for item in store.candidates()]}


@router.post("/workflows")
def create_workflow(request: Request, payload: dict[str, object]) -> dict[str, object]:
    actor = _actor(request)
    now = datetime.now(timezone.utc)
    try:
        values = {**payload, "status": "draft", "created_at": now.isoformat(), "updated_at": now.isoformat(), "approved_by": None}
        workflow = CORE.AutomationWorkflow.model_validate_json(json.dumps(values))
        with _workflow_transition_lock():
            store = _runtime().automations
            if any(item.id == workflow.id for item in store.workflows()):
                raise HTTPException(status_code=409, detail="Cet identifiant d’automatisation existe déjà.")
            saved = store.save_workflow(workflow)
        CORE.append_agent_event("frugal.workflow.created", actor, {"workflow_id": workflow.id})
        return saved.model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as exc:
        raise _translate(exc) from exc


def _cron_dashboard() -> ModuleType:
    from hermes_cli import web_server

    return web_server


def _create_cron_job(workflow: AutomationWorkflow) -> str:
    from hermes_cli.web_models import CronJobCreate

    if workflow.schedule is None:
        raise CORE.AutomationPolicyError("Une planification est requise pour créer la tâche exécutable.")
    profile = workflow.profile_name or "default"
    name = f"{MANAGED_CRON_PREFIX}{workflow.id}:{workflow.name}"
    body = CronJobCreate(prompt=workflow.description, schedule=DORMANT_CRON_SCHEDULE, name=name, deliver="local")
    dashboard = _cron_dashboard()
    job = dashboard._create_cron_job_sync(body, profile)
    job_id = str(job["id"])
    try:
        dashboard._pause_cron_job_sync(job_id, profile)
    except Exception:
        dashboard._delete_cron_job_sync(job_id, profile)
        raise
    return job_id


def _activate_cron_job(workflow: AutomationWorkflow) -> None:
    from hermes_cli.web_models import CronJobUpdate

    if workflow.cron_job_id is None or workflow.schedule is None:
        raise CORE.AutomationPolicyError("La planification approuvée est incomplète.")
    dashboard = _cron_dashboard()
    profile = workflow.profile_name or "default"
    dashboard._update_cron_job_sync(workflow.cron_job_id, CronJobUpdate(updates={"schedule": workflow.schedule}), profile)
    dashboard._resume_cron_job_sync(workflow.cron_job_id, profile)


def _update_cron_state(workflow: AutomationWorkflow, status: WorkflowStatus) -> None:
    if workflow.cron_job_id is None:
        return
    dashboard = _cron_dashboard()
    profile = workflow.profile_name or "default"
    if status is CORE.WorkflowStatus.ACTIVE:
        _activate_cron_job(workflow)
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
    if updated.status is CORE.WorkflowStatus.ACTIVE:
        return updated
    if current.cron_job_id is not None:
        _cron_dashboard()._pause_cron_job_sync(current.cron_job_id, current.profile_name or "default")
    return updated


def _finalize_scheduled_workflow(updated: AutomationWorkflow) -> None:
    if updated.cron_job_id is None:
        return
    if updated.status is CORE.WorkflowStatus.ACTIVE:
        _activate_cron_job(updated)
        return
    if updated.status is CORE.WorkflowStatus.ARCHIVED:
        _cron_dashboard()._delete_cron_job_sync(updated.cron_job_id, updated.profile_name or "default")


def _restore_archived_workflow(current: AutomationWorkflow) -> AutomationWorkflow:
    if _cron_job_exists(current):
        _update_cron_state(current, current.status)
        return current
    cron_job_id = _create_cron_job(current)
    restored = current.model_copy(update={"cron_job_id": cron_job_id})
    _update_cron_state(restored, current.status)
    return restored


def _cron_inventory() -> tuple[dict[str, dict[str, object]], set[str]]:
    jobs = _cron_dashboard()._list_cron_jobs_sync("all")
    existing = {str(job["id"]): job for job in jobs}
    managed = {str(job["id"]) for job in jobs if str(job.get("name", "")).startswith(MANAGED_CRON_PREFIX)}
    return existing, managed


def _schedule_matches(workflow: AutomationWorkflow, job: dict[str, object]) -> bool:
    if workflow.schedule is None:
        return False
    from cron.jobs import parse_schedule

    expected = {key: value for key, value in parse_schedule(workflow.schedule).items() if key != "display"}
    actual = job.get("schedule")
    if not isinstance(actual, dict):
        return False
    return {key: value for key, value in actual.items() if key != "display"} == expected


def _is_relative_one_shot(schedule: str | None) -> bool:
    return schedule is not None and schedule.strip().casefold().startswith("in ")


def _materialize_relative_schedule(workflow: AutomationWorkflow) -> AutomationWorkflow:
    if workflow.status is not CORE.WorkflowStatus.ACTIVE or not _is_relative_one_shot(workflow.schedule):
        return workflow
    from cron.jobs import parse_schedule

    parsed = parse_schedule(str(workflow.schedule))
    return workflow.model_copy(update={"schedule": str(parsed["run_at"])})


def _materialize_existing_one_shot(
    store: AutomationStore, workflow: AutomationWorkflow, job: dict[str, object]
) -> AutomationWorkflow:
    schedule = job.get("schedule")
    if not _is_relative_one_shot(workflow.schedule) or not isinstance(schedule, dict):
        return workflow
    normalized = cast(dict[str, object], schedule)
    run_at = normalized.get("run_at")
    if normalized.get("kind") != "once" or not isinstance(run_at, str):
        return workflow
    materialized = workflow.model_copy(update={"schedule": run_at})
    store.save_workflow(materialized)
    return materialized


def _repair_active_cron(workflow: AutomationWorkflow, job: dict[str, object]) -> None:
    if not _schedule_matches(workflow, job):
        _activate_cron_job(workflow)
        return
    if not bool(job.get("enabled", True)) or job.get("state") == "paused":
        _cron_dashboard()._resume_cron_job_sync(workflow.cron_job_id, workflow.profile_name or "default")


def _one_shot_is_expired(schedule: str | None) -> bool:
    if schedule is None:
        return False
    from cron.jobs import parse_schedule

    parsed = parse_schedule(schedule)
    if parsed.get("kind") != "once":
        return False
    run_at = datetime.fromisoformat(str(parsed["run_at"]).replace("Z", "+00:00"))
    return run_at <= datetime.now(timezone.utc)


def _disable_completed_workflow(store: AutomationStore, workflow: AutomationWorkflow) -> None:
    disabled = workflow.model_copy(update={"status": CORE.WorkflowStatus.DISABLED, "updated_at": datetime.now(timezone.utc)})
    store.save_workflow(disabled)


def _reconcile_workflow(
    store: AutomationStore, workflow: AutomationWorkflow, existing: dict[str, dict[str, object]]
) -> None:
    if workflow.cron_job_id not in existing:
        if workflow.status is not CORE.WorkflowStatus.ACTIVE or workflow.schedule is None:
            return
        if _is_relative_one_shot(workflow.schedule):
            _disable_completed_workflow(store, workflow)
            return
        if _one_shot_is_expired(workflow.schedule):
            _disable_completed_workflow(store, workflow)
            return
        restored = workflow.model_copy(update={"cron_job_id": _create_cron_job(workflow)})
        store.save_workflow(restored)
        _activate_cron_job(restored)
        return
    job = existing[str(workflow.cron_job_id)]
    if job.get("state") == "completed":
        if workflow.status is CORE.WorkflowStatus.ACTIVE:
            _disable_completed_workflow(store, workflow)
        return
    if workflow.status is CORE.WorkflowStatus.ACTIVE:
        workflow = _materialize_existing_one_shot(store, workflow, job)
        _repair_active_cron(workflow, job)
        return
    _update_cron_state(workflow, workflow.status)


def _delete_orphan_crons(workflows: tuple[AutomationWorkflow, ...], managed: set[str]) -> None:
    linked = {str(item.cron_job_id) for item in workflows if item.cron_job_id is not None}
    dashboard = _cron_dashboard()
    for job_id in managed - linked:
        dashboard._delete_cron_job_sync(job_id, None)


def _reconcile_scheduled_workflows(store: AutomationStore) -> None:
    workflows = store.workflows()
    existing, managed = _cron_inventory()
    for workflow in workflows:
        _reconcile_workflow(store, workflow, existing)
    _delete_orphan_crons(workflows, managed)


def _rollback_scheduled_workflow(current: AutomationWorkflow, updated: AutomationWorkflow) -> AutomationWorkflow:
    if updated.status is CORE.WorkflowStatus.ARCHIVED and current.cron_job_id is not None:
        return _restore_archived_workflow(current)
    dashboard = _cron_dashboard()
    profile = current.profile_name or "default"
    if updated.cron_job_id != current.cron_job_id and updated.cron_job_id is not None:
        dashboard._delete_cron_job_sync(updated.cron_job_id, profile)
        return current
    if current.cron_job_id is None:
        return current
    if current.status is CORE.WorkflowStatus.ACTIVE:
        dashboard._resume_cron_job_sync(current.cron_job_id, profile)
    else:
        dashboard._pause_cron_job_sync(current.cron_job_id, profile)
    return current


def _transition_details(current: AutomationWorkflow, updated: AutomationWorkflow, result: str) -> dict[str, str]:
    return {
        "workflow_id": current.id,
        "previous_state": current.status.value,
        "new_state": updated.status.value,
        "operation": "transition",
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _audit_failed_transition(actor: str, current: AutomationWorkflow, updated: AutomationWorkflow) -> None:
    try:
        CORE.append_agent_event("frugal.workflow.transition.failed", actor, _transition_details(current, updated, "failed"))
    except Exception as exc:
        LOGGER.error("Échec de l’audit d’une transition de workflow refusée.", exc_info=exc)


def _compensate_failed_transition(
    store: AutomationStore, current: AutomationWorkflow, updated: AutomationWorkflow, persisted: bool
) -> None:
    restored = _rollback_scheduled_workflow(current, updated)
    if persisted or restored.cron_job_id != current.cron_job_id:
        store.save_workflow(restored)


def _requested_transition(current: AutomationWorkflow, status: WorkflowStatus, actor: str) -> AutomationWorkflow:
    if current.status is status:
        return current
    return CORE.transition_workflow(current, status, actor)


def _commit_workflow_transition(
    store: AutomationStore, current: AutomationWorkflow, status: WorkflowStatus, actor: str
) -> AutomationWorkflow:
    persisted = False
    updated = current
    try:
        updated = _requested_transition(current, status, actor)
        updated = _materialize_relative_schedule(updated)
        updated = _synchronize_scheduled_workflow(current, updated)
        store.save_workflow(updated)
        persisted = True
        _finalize_scheduled_workflow(updated)
        CORE.append_agent_event("frugal.workflow.transition", actor, _transition_details(current, updated, "success"))
        return updated
    except Exception as original:
        try:
            _compensate_failed_transition(store, current, updated, persisted)
        except Exception as compensation_error:
            LOGGER.critical("La compensation du workflow ARC a échoué.", exc_info=compensation_error)
            _audit_failed_transition(actor, current, updated)
            raise WorkflowConsistencyError("La transition nécessite une réconciliation automatique.") from original
        _audit_failed_transition(actor, current, updated)
        raise


@router.post("/workflows/{workflow_id}/transition")
def change_workflow(workflow_id: str, payload: WorkflowTransition, request: Request) -> dict[str, object]:
    actor = _actor(request)
    with _workflow_transition_lock():
        store = _runtime().automations
        current = next((item for item in store.workflows() if item.id == workflow_id), None)
        if current is None:
            raise HTTPException(status_code=404, detail="Workflow introuvable.")
        try:
            updated = _commit_workflow_transition(store, current, CORE.WorkflowStatus(payload.status), actor)
            return updated.model_dump(mode="json")
        except Exception as exc:
            raise _translate(exc) from exc


@router.post("/cache/invalidate")
def invalidate_cache(payload: CacheInvalidation, request: Request) -> dict[str, int]:
    actor = _actor(request)
    count = _runtime().cache.invalidate(payload.kind, payload.identifier)
    CORE.append_agent_event("frugal.cache.invalidated", actor, {"kind": payload.kind, "identifier": payload.identifier, "count": count})
    return {"invalidated": count}
