"""API d'administration séparée du processus agentique Hermes."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from security import ACTION_CATALOG, ActionRequest, Actor, evaluate_action
from security.approvals import ApprovalError, consume_approval, issue_approval, pending_approvals
from security.audit import AuditWriteError, append_event, read_events
from security.broker_client import BrokerUnavailableError, execute
from security.identity import AdministratorDeniedError, AdministratorLookupError, administrator_actor
from security.models import SecurityContractError


app = FastAPI(title="ARCenal Control API", docs_url=None, redoc_url=None)


class ActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=3, max_length=80)
    target: str | None = Field(default=None, max_length=80)


class PrepareRequest(ActionPayload):
    human_confirmed: bool = False


class ExecuteRequest(ActionPayload):
    approval_id: str | None = Field(default=None, min_length=32, max_length=128)


def _actor(remote_user: str | None) -> Actor:
    if remote_user is None:
        raise HTTPException(status_code=401, detail="Identité YunoHost absente.")
    try:
        primary = os.environ.get("ARCENAL_PRIMARY_ADMIN", "").strip()
        return administrator_actor(remote_user, primary)
    except AdministratorDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdministratorLookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SecurityContractError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _public_action(action_id: str) -> dict[str, object]:
    action = ACTION_CATALOG[action_id]
    return {
        "id": action.action_id,
        "authorization": int(action.authorization),
        "risk": action.risk.value,
        "description": action.description,
        "consequence": action.consequence,
        "rollback": action.rollback,
        "allowed_targets": action.allowed_targets,
    }


@app.get("/health")
def health(remote_user: str | None = Header(default=None, alias="Remote-User")) -> dict[str, str]:
    actor = _actor(remote_user)
    return {"status": "ok", "actor": actor.username}


@app.get("/actions")
def actions(remote_user: str | None = Header(default=None, alias="Remote-User")) -> dict[str, object]:
    _actor(remote_user)
    return {"actions": [_public_action(key) for key in ACTION_CATALOG]}


@app.get("/security/overview")
def security_overview(remote_user: str | None = Header(default=None, alias="Remote-User")) -> dict[str, object]:
    actor = _actor(remote_user)
    try:
        events = read_events(100)
        approvals = pending_approvals(100)
    except (AuditWriteError, ApprovalError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "actor": {"username": actor.username, "roles": list(actor.roles)},
        "actions": [_public_action(key) for key in ACTION_CATALOG],
        "approvals": approvals,
        "audit": {"events": events, "integrity": True},
        "gateways": {
            "control": Path("/run/arcenal-control/privileged.sock").exists(),
            "readonly": Path("/run/arcenal-readonly/query.sock").exists(),
        },
    }


@app.post("/actions/prepare")
def prepare_action(
    request: PrepareRequest,
    remote_user: str | None = Header(default=None, alias="Remote-User"),
) -> dict[str, object]:
    actor = _actor(remote_user)
    security_request = ActionRequest(request.action_id, actor, request.target)
    try:
        decision = evaluate_action(security_request)
    except SecurityContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if decision.allowed:
        return {"status": "ready", "action": _public_action(request.action_id)}
    if not decision.confirmation_required:
        raise HTTPException(status_code=403, detail=decision.reason)
    if not request.human_confirmed:
        return {"status": "confirmation_required", "action": _public_action(request.action_id)}
    approval_id = issue_approval(actor.username, request.action_id, request.target)
    append_event("approval.requested", actor.username, {"action_id": request.action_id, "target": request.target})
    return {"status": "confirmation_required", "approval_id": approval_id, "action": _public_action(request.action_id)}


def _confirmed(request: ExecuteRequest, actor: Actor) -> bool:
    action = ACTION_CATALOG.get(request.action_id)
    if action is None or int(action.authorization) < 3:
        return False
    if request.approval_id is None:
        raise HTTPException(status_code=409, detail="Une confirmation humaine est obligatoire.")
    try:
        consume_approval(request.approval_id, actor.username, request.action_id, request.target)
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return True


def _execute_authorized(request: ExecuteRequest, actor: Actor) -> dict[str, object]:
    append_event("action.requested", actor.username, {"action_id": request.action_id, "target": request.target})
    try:
        result = execute({"action_id": request.action_id, "target": request.target})
    except BrokerUnavailableError as exc:
        append_event("action.failed", actor.username, {"action_id": request.action_id, "reason": str(exc)})
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    event = "action.completed" if result["ok"] else "action.failed"
    append_event(event, actor.username, {"action_id": request.action_id, "target": request.target})
    if not result["ok"]:
        raise HTTPException(status_code=500, detail=str(result.get("error") or "L'action a échoué."))
    return {"status": "completed", "action": _public_action(request.action_id), "result": result}


@app.post("/actions/execute")
def run_action(
    request: ExecuteRequest,
    remote_user: str | None = Header(default=None, alias="Remote-User"),
) -> dict[str, object]:
    actor = _actor(remote_user)
    try:
        confirmed = _confirmed(request, actor)
        decision = evaluate_action(ActionRequest(request.action_id, actor, request.target, confirmed))
    except SecurityContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not decision.allowed:
        append_event("action.refused", actor.username, {"action_id": request.action_id, "reason": decision.reason})
        status = 409 if decision.confirmation_required else 403
        raise HTTPException(status_code=status, detail=decision.reason)
    return _execute_authorized(request, actor)
