"""API administrateur versionnée de la mémoire d’entreprise ARCenal."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError


router = APIRouter(prefix="/memory/v1")
ACTOR_RE = re.compile(r"[^\w@.+\- ]", re.UNICODE)


def _core() -> ModuleType:
    core = sys.modules.get("arcenal_arc_core")
    if core is None:
        raise RuntimeError("ARC Core doit être chargé avant l’API mémoire.")
    return core


CORE = _core()


class MemoryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=16_000)
    source_type: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=240)
    source_recorded_at: datetime | None = None
    source_author: str | None = Field(default=None, max_length=160)
    request_id: str | None = Field(default=None, max_length=160)
    agent_id: str | None = Field(default=None, max_length=64)
    application_id: str | None = Field(default=None, max_length=64)
    confidence: float = Field(default=1.0, ge=0, le=1)
    status: str = Field(default="active", max_length=40)
    retention_mode: str = Field(default="permanent", max_length=40)
    expires_at: datetime | None = None
    knowledge_scopes: list[str] = Field(default_factory=lambda: ["company"], min_length=1, max_length=30)
    confidentiality: str = Field(default="internal", max_length=40)
    allowed_applications: list[str] = Field(default_factory=list, max_length=30)
    allowed_agents: list[str] = Field(default_factory=list, max_length=30)
    allowed_users: list[str] = Field(default_factory=list, max_length=30)
    project: str | None = Field(default=None, max_length=240)
    person: str | None = Field(default=None, max_length=240)
    decision_context: str | None = Field(default=None, max_length=2_000)
    decision_reason: str | None = Field(default=None, max_length=2_000)
    decision_maker: str | None = Field(default=None, max_length=240)
    review_date: datetime | None = None
    person_service: str | None = Field(default=None, max_length=240)
    person_role: str | None = Field(default=None, max_length=240)
    responsibilities: list[str] = Field(default_factory=list, max_length=50)
    project_status: str | None = Field(default=None, max_length=120)
    rule_kind: str | None = Field(default=None, max_length=40)
    official_reference: str | None = Field(default=None, max_length=240)
    preference_owner: str | None = Field(default=None, max_length=240)
    preference_scope: str | None = Field(default=None, max_length=240)
    preference_context: str | None = Field(default=None, max_length=500)
    relations: list[dict[str, str]] = Field(default_factory=list, max_length=50)


class MemoryCorrection(MemoryWrite):
    reason: str = Field(min_length=1, max_length=500)


class MemoryTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern=r"^(active|archived|expired|deleted|pending_review)$")
    reason: str = Field(min_length=1, max_length=500)


class MemoryDelete(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirmed: bool
    physical: bool = False
    reason: str = Field(min_length=1, max_length=500)


def _repository() -> CORE.EnterpriseMemoryRepository:
    from hermes_constants import get_hermes_home

    return CORE.EnterpriseMemoryRepository(CORE.memory_database_path(get_hermes_home()))


def _actor(request: Request) -> str:
    raw = next((request.headers.get(name, "") for name in ("x-remote-user", "remote-user", "x-auth-user") if request.headers.get(name)), "")
    cleaned = ACTOR_RE.sub("", raw).strip()[:120]
    if not cleaned:
        raise HTTPException(status_code=401, detail="Authentification administrateur requise.")
    return cleaned


def _provenance(payload: MemoryWrite, actor: str) -> CORE.MemoryProvenance:
    return CORE.MemoryProvenance(
        source_type=CORE.MemorySourceType(payload.source_type), source_id=payload.source_id.strip(),
        recorded_at=payload.source_recorded_at or datetime.now(timezone.utc), author=payload.source_author or actor,
        request_id=payload.request_id, agent_id=payload.agent_id, application_id=payload.application_id,
    )


def _draft(payload: MemoryWrite, actor: str) -> CORE.MemoryDraft:
    status = CORE.MemoryStatus(payload.status)
    if payload.source_type in {"agent", "conversation"} and status is CORE.MemoryStatus.ACTIVE:
        status = CORE.MemoryStatus.PENDING_REVIEW
    relations = tuple(CORE.MemoryRelation.model_validate(item) for item in payload.relations)
    return CORE.MemoryDraft(
        memory_type=CORE.MemoryType(payload.memory_type), summary=payload.summary.strip(), content=payload.content.strip(),
        provenance=_provenance(payload, actor), confidence=payload.confidence, status=status,
        retention_mode=CORE.RetentionMode(payload.retention_mode), expires_at=payload.expires_at,
        knowledge_scopes=_normalized(payload.knowledge_scopes), confidentiality=CORE.ConfidentialityLevel(payload.confidentiality),
        allowed_applications=_normalized(payload.allowed_applications), allowed_agents=_normalized(payload.allowed_agents),
        allowed_users=_normalized(payload.allowed_users), required_permissions=("memory.read",),
        project=_clean(payload.project), person=_clean(payload.person), rule_kind=CORE.RuleKind(payload.rule_kind) if payload.rule_kind else None,
        decision_context=_clean(payload.decision_context), decision_reason=_clean(payload.decision_reason),
        decision_maker=_clean(payload.decision_maker), review_date=payload.review_date,
        person_service=_clean(payload.person_service), person_role=_clean(payload.person_role),
        responsibilities=_normalized(payload.responsibilities), project_status=_clean(payload.project_status),
        official_reference=_clean(payload.official_reference), preference_owner=_clean(payload.preference_owner),
        preference_scope=_clean(payload.preference_scope), preference_context=_clean(payload.preference_context), relations=relations,
    )


def _normalized(values: list[str]) -> tuple[str, ...]:
    cleaned = (value.strip().casefold() for value in values)
    return tuple(dict.fromkeys(value for value in cleaned if value))


def _clean(value: str | None) -> str | None:
    cleaned = value.strip() if value else ""
    return cleaned or None


def _audit(action: str, actor: str, memory_id: str, details: dict[str, object] | None = None) -> None:
    CORE.append_agent_event(f"memory.{action}", actor, {"memory_id": memory_id, **(details or {})})


def _refresh_index() -> None:
    from hermes_constants import get_hermes_home

    CORE.rebuild_index(get_hermes_home())


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, CORE.MemoryNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CORE.MemoryConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (ValueError, ValidationError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="La mémoire d’entreprise est indisponible.")


def _serialize(memory: CORE.EnterpriseMemory) -> dict[str, object]:
    return memory.model_dump(mode="json")


def _filters(query: str, memory_type: str | None, status: str | None, source_type: str | None, scope: str | None, confidentiality: str | None, project: str | None, person: str | None, created_from: datetime | None, created_to: datetime | None) -> CORE.MemorySearchFilters:
    return CORE.MemorySearchFilters(
        query=query, memory_type=CORE.MemoryType(memory_type) if memory_type else None,
        status=CORE.MemoryStatus(status) if status else None,
        source_type=CORE.MemorySourceType(source_type) if source_type else None, scope=scope,
        confidentiality=CORE.ConfidentialityLevel(confidentiality) if confidentiality else None,
        project=project, person=person, created_from=created_from, created_to=created_to,
    )


@router.get("")
def list_memories(
    request: Request, query: str = Query(default="", max_length=300),
    memory_type: str | None = None, status: str | None = None,
    source_type: str | None = None, scope: str | None = None,
    confidentiality: str | None = None, project: str | None = None,
    person: str | None = None, created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict[str, object]:
    _actor(request)
    try:
        filters = _filters(query, memory_type, status, source_type, scope, confidentiality, project, person, created_from, created_to)
        return {"entries": [_serialize(item) for item in _repository().search(filters)]}
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("", status_code=201)
def create_memory(payload: MemoryWrite, request: Request) -> dict[str, object]:
    actor = _actor(request)
    try:
        memory = _repository().create(_draft(payload, actor), actor)
        _refresh_index()
        _audit("create", actor, memory.id, {"type": memory.memory_type.value, "source": memory.provenance.source_type.value})
        return {"entry": _serialize(memory)}
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/metrics")
def memory_metrics(request: Request) -> dict[str, object]:
    _actor(request)
    from hermes_constants import get_hermes_home

    used = CORE.index_status(get_hermes_home()).memories
    return _repository().metrics(used).model_dump(mode="json")


@router.get("/{memory_id}")
def get_memory(memory_id: str, request: Request) -> dict[str, object]:
    actor = _actor(request)
    try:
        entry = _repository().get(memory_id)
        _audit("retrieve", actor, memory_id)
        return {"entry": _serialize(entry), "history": [item.model_dump(mode="json") for item in _repository().history(memory_id)]}
    except Exception as exc:
        raise _translate(exc) from exc


@router.patch("/{memory_id}")
def correct_memory(memory_id: str, payload: MemoryCorrection, request: Request) -> dict[str, object]:
    actor = _actor(request)
    try:
        memory = _repository().correct(memory_id, _draft(payload, actor), actor, payload.reason)
        _refresh_index()
        _audit("update", actor, memory.id, {"version": memory.version, "reason": payload.reason})
        return {"entry": _serialize(memory)}
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/{memory_id}/status")
def transition_memory(memory_id: str, payload: MemoryTransition, request: Request) -> dict[str, object]:
    actor = _actor(request)
    try:
        memory = _repository().set_status(memory_id, CORE.MemoryStatus(payload.status), actor, payload.reason)
        _refresh_index()
        action = {"active": "restore", "archived": "archive", "expired": "expire", "deleted": "delete"}.get(payload.status, "update")
        _audit(action, actor, memory.id, {"status": payload.status, "reason": payload.reason})
        return {"entry": _serialize(memory)}
    except Exception as exc:
        raise _translate(exc) from exc


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, payload: MemoryDelete, request: Request) -> dict[str, object]:
    actor = _actor(request)
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="La suppression doit être confirmée.")
    try:
        if payload.physical:
            _repository().delete_physical(memory_id)
        else:
            _repository().set_status(memory_id, CORE.MemoryStatus.DELETED, actor, payload.reason)
        _refresh_index()
        _audit("delete", actor, memory_id, {"physical": payload.physical, "reason": payload.reason})
        return {"deleted": True, "physical": payload.physical}
    except Exception as exc:
        raise _translate(exc) from exc
