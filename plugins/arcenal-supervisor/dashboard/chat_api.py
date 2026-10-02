"""Conversations ARC persistées et exécutées par le runtime natif."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from types import ModuleType
from typing import Annotated, Literal, Protocol, cast
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(prefix="/chat")
_LOCK = RLock()


class ChatStorageError(RuntimeError):
    """Signale un stockage de conversation ARC illisible ou indisponible."""


class AgentQueryLike(Protocol):
    response: str
    sources: tuple[dict[str, str], ...]
    actions: tuple[dict[str, str], ...]
    usage: dict[str, bool | int | float | str]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=100_000)
    created_at: datetime


class ChatSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str
    title: str = Field(min_length=1, max_length=120)
    messages: tuple[ChatMessage, ...] = ()
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class ChatStore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    sessions: tuple[ChatSession, ...] = ()


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=20_000)


class ChatArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    archived: bool


class ChatQueryResponse(BaseModel):
    session: ChatSession
    sources: tuple[dict[str, str], ...] = ()
    actions: tuple[dict[str, str], ...] = ()
    usage: dict[str, bool | int | float | str] = Field(default_factory=dict)


def _agents() -> ModuleType:
    module = sys.modules.get("arcenal_agents_api")
    if not isinstance(module, ModuleType):
        raise ChatStorageError("Le runtime des agents ARC est indisponible.")
    return module


def _store_path() -> Path:
    from hermes_constants import get_hermes_home

    root = get_hermes_home() / "arcenal"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root / "chat-sessions.json"


def _read_sessions() -> tuple[ChatSession, ...]:
    path = _store_path()
    if not path.is_file():
        return ()
    try:
        return ChatStore.model_validate_json(path.read_text(encoding="utf-8")).sessions
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ChatStorageError("L’historique des conversations ARC est illisible.") from exc


def _write_sessions(sessions: tuple[ChatSession, ...]) -> None:
    path = _store_path()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".chat-sessions.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            payload = {"sessions": [item.model_dump(mode="json") for item in sessions]}
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ChatStorageError("L’historique ARC ne peut pas être enregistré.") from exc


def _find_session(session_id: str, sessions: tuple[ChatSession, ...]) -> ChatSession:
    session = next((item for item in sessions if item.id == session_id), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation ARC introuvable.")
    return session


def _replace_session(current: ChatSession, sessions: tuple[ChatSession, ...]) -> tuple[ChatSession, ...]:
    return tuple(current if item.id == current.id else item for item in sessions)


def _append_message(session: ChatSession, role: Literal["user", "assistant"], text: str) -> ChatSession:
    now = datetime.now(timezone.utc)
    message = ChatMessage(id=uuid4().hex, role=role, text=text, created_at=now)
    title = text.strip().replace("\n", " ")[:120] if not session.messages else session.title
    return session.model_copy(update={"title": title or session.title, "messages": (*session.messages, message), "updated_at": now})


def _persist_message(session_id: str, role: Literal["user", "assistant"], text: str) -> ChatSession:
    with _LOCK:
        sessions = _read_sessions()
        current = _find_session(session_id, sessions)
        if current.archived:
            raise HTTPException(status_code=409, detail="Cette conversation est archivée.")
        updated = _append_message(current, role, text)
        _write_sessions(_replace_session(updated, sessions))
        return updated


def _query_agent(session: ChatSession, message: str, user_id: str) -> AgentQueryLike:
    query = getattr(_agents(), "query_dashboard_agent", None)
    if not callable(query):
        raise ChatStorageError("Le point d’entrée conversationnel ARC est absent.")
    return cast(AgentQueryLike, query("arc", message, session.id, user_id))


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    translator = getattr(_agents(), "_translate_error", None)
    if callable(translator):
        return cast(HTTPException, translator(exc))
    return HTTPException(status_code=500, detail="La conversation ARC a échoué.")


def _identity(remote_user: str | None, x_remote_user: str | None) -> str:
    user_id = (remote_user or x_remote_user or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Session administrateur YunoHost requise.")
    return user_id


@router.get("/sessions", response_model=list[ChatSession])
def list_sessions() -> list[ChatSession]:
    with _LOCK:
        sessions = tuple(item for item in _read_sessions() if not item.archived)
    return sorted(sessions, key=lambda item: item.updated_at, reverse=True)


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
def create_session() -> ChatSession:
    now = datetime.now(timezone.utc)
    session = ChatSession(id=uuid4().hex, title="Nouvelle conversation", created_at=now, updated_at=now)
    with _LOCK:
        _write_sessions((*_read_sessions(), session))
    return session


@router.get("/sessions/{session_id}", response_model=ChatSession)
def get_session(session_id: str) -> ChatSession:
    with _LOCK:
        return _find_session(session_id, _read_sessions())


@router.patch("/sessions/{session_id}", response_model=ChatSession)
def archive_session(session_id: str, request: ChatArchiveRequest) -> ChatSession:
    with _LOCK:
        sessions = _read_sessions()
        current = _find_session(session_id, sessions)
        updated = current.model_copy(update={"archived": request.archived, "updated_at": datetime.now(timezone.utc)})
        _write_sessions(_replace_session(updated, sessions))
    return updated


@router.post("/sessions/{session_id}/messages", response_model=ChatQueryResponse)
def send_message(
    session_id: str,
    request: ChatMessageRequest,
    remote_user: Annotated[str | None, Header(alias="Remote-User")] = None,
    x_remote_user: Annotated[str | None, Header(alias="X-Remote-User")] = None,
) -> ChatQueryResponse:
    user_id = _identity(remote_user, x_remote_user)
    user_session = _persist_message(session_id, "user", request.text)
    try:
        result = _query_agent(user_session, request.text, user_id)
        completed = _persist_message(session_id, "assistant", result.response)
        return ChatQueryResponse(session=completed, sources=result.sources, actions=result.actions, usage=result.usage)
    except Exception as exc:
        raise _http_error(exc) from exc
