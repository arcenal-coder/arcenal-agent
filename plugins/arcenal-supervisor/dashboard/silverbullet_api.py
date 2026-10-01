"""Connexion administrateur entre ARC et un coffre SilverBullet."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge/silverbullet")


class SilverBulletStatusResponse(BaseModel):
    configured: bool
    connection: str = Field(pattern="^(connected|error|missing|never)$")
    documents: int = Field(ge=0)
    last_error: str
    last_sync_at: str | None
    service_url: str


class SilverBulletSyncResponse(BaseModel):
    downloaded: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    removed: int = Field(ge=0)
    synchronized_at: str


class SilverBulletStateView(BaseModel):
    etags: dict[str, str] = Field(default_factory=dict)
    last_error: str = ""
    last_sync_at: datetime | None = None


def _core() -> ModuleType:
    knowledge = sys.modules.get("arcenal_knowledge_api")
    loader = getattr(knowledge, "_load_arc_core", None)
    if not callable(loader):
        raise RuntimeError("Le cœur documentaire ARCenal est indisponible.")
    module = loader()
    if not isinstance(module, ModuleType):
        raise RuntimeError("Le cœur documentaire ARCenal est invalide.")
    return module


def _home() -> Path:
    from hermes_constants import get_hermes_home

    return get_hermes_home()


def _credential() -> tuple[str, str] | None:
    runtime = _core().runtime_configuration()
    credentials = runtime.access_credentials()
    match = next((item for item in credentials if _is_silverbullet(item)), None)
    item = _record(match)
    if item is None:
        return None
    secret_env = item.get("secretEnv")
    service_url = item.get("serviceUrl")
    if not isinstance(secret_env, str) or not isinstance(service_url, str):
        return None
    token = runtime.vault.get_secret(secret_env)
    token = token.strip() if isinstance(token, str) else ""
    return (service_url, token) if token else None


def _is_silverbullet(value: object) -> bool:
    item = _record(value)
    if item is None or item.get("enabled") is False or item.get("kind") != "api":
        return False
    identity = f"{item.get('id', '')} {item.get('label', '')}".casefold()
    return "silverbullet" in identity or "silver bullet" in identity


def _actor(request: Request) -> str:
    actor = request.headers.get("remote-user") or request.headers.get("x-remote-user")
    if not actor or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}", actor):
        raise HTTPException(status_code=401, detail="Administrateur YunoHost non identifié.")
    return actor


def _state() -> SilverBulletStateView:
    path = _home() / "arcenal" / "silverbullet-sync.json"
    if not path.is_file():
        return SilverBulletStateView()
    try:
        return SilverBulletStateView.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="L’état SilverBullet est invalide.") from exc


def _record(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    return {str(key): item for key, item in value.items()}


@router.get("/status", response_model=SilverBulletStatusResponse)
def silverbullet_status() -> SilverBulletStatusResponse:
    credential = _credential()
    state = _state()
    service_url = credential[0] if credential else ""
    connection = _connection(credential is not None, state)
    return SilverBulletStatusResponse(
        configured=credential is not None,
        connection=connection,
        documents=len(state.etags),
        last_error=state.last_error,
        last_sync_at=state.last_sync_at.isoformat() if state.last_sync_at else None,
        service_url=service_url,
    )


def _connection(configured: bool, state: SilverBulletStateView) -> str:
    if not configured:
        return "missing"
    if state.last_error:
        return "error"
    return "connected" if state.last_sync_at else "never"


@router.post("/sync", response_model=SilverBulletSyncResponse)
async def synchronize_silverbullet(request: Request) -> SilverBulletSyncResponse:
    _actor(request)
    credential = _credential()
    if credential is None:
        raise HTTPException(status_code=409, detail="Ajoutez d’abord un accès API nommé SilverBullet dans Paramètres > Accès.")
    core = _core()
    settings = core.SilverBulletSettings(base_url=credential[0], token=credential[1])
    synchronizer = core.SilverBulletSynchronizer(settings, _home(), core.HttpxSilverBulletTransport())
    try:
        result = await synchronizer.sync()
    except core.SilverBulletError as exc:
        core.SilverBulletStateRepository(_home() / "arcenal" / "silverbullet-sync.json").record_error(str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    core.rebuild_index(_home())
    return SilverBulletSyncResponse(**result.model_dump(mode="json"))
