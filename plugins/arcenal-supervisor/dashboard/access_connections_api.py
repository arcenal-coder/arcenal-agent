"""Tests de disponibilité des accès métier confiés à ARC."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/access")
SECRET_ENV_RE = re.compile(r"^ARCENAL_ACCESS_[A-Z0-9_]+_(?:API_KEY|PASSWORD)$")


class AccessProbeResponse(BaseModel):
    """Résultat expurgé du test d’un accès métier."""

    access_id: str
    connection: str = Field(pattern="^(connected|invalid|missing|unreachable|disabled)$")
    message: str
    tested_at: str


def _credentials() -> tuple[list[object], Mapping[str, str]]:
    from hermes_cli.config import load_config_readonly, load_env

    config = load_config_readonly()
    arcenal = config.get("arcenal")
    credentials = arcenal.get("access_credentials") if isinstance(arcenal, Mapping) else []
    return (credentials if isinstance(credentials, list) else []), load_env()


def _credential(access_id: str) -> tuple[Mapping[str, object], str]:
    credentials, environment = _credentials()
    item = next((value for value in credentials if isinstance(value, Mapping) and value.get("id") == access_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Accès métier introuvable.")
    secret_env = item.get("secretEnv")
    if not isinstance(secret_env, str) or not SECRET_ENV_RE.fullmatch(secret_env):
        raise HTTPException(status_code=422, detail="Référence de secret invalide.")
    return item, environment.get(secret_env, "").strip()


def _service_url(item: Mapping[str, object]) -> str:
    raw = item.get("serviceUrl")
    if not isinstance(raw, str):
        raise HTTPException(status_code=422, detail="Adresse de service absente.")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Adresse de service invalide.")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="L’adresse ne doit pas contenir d’identifiants.")
    return raw


def _status(access_id: str, connection: str, message: str) -> AccessProbeResponse:
    return AccessProbeResponse(access_id=access_id, connection=connection, message=message, tested_at=datetime.now(timezone.utc).isoformat())


def _headers(item: Mapping[str, object], secret: str) -> dict[str, str]:
    return {"accept": "application/json", "authorization": f"Bearer {secret}"} if item.get("kind") == "api" else {"accept": "application/json"}


def _auth(item: Mapping[str, object], secret: str) -> tuple[str, str] | None:
    login = item.get("login")
    if item.get("kind") != "account" or not isinstance(login, str):
        return None
    return login, secret


async def _probe_access(access_id: str, item: Mapping[str, object], secret: str) -> AccessProbeResponse:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=False) as client:
            response = await client.get(_service_url(item), headers=_headers(item, secret), auth=_auth(item, secret))
    except httpx.HTTPError:
        return _status(access_id, "unreachable", "Le service est temporairement inaccessible.")
    if response.status_code in {401, 403}:
        return _status(access_id, "invalid", "Le service a refusé l’authentification.")
    if response.status_code < 500:
        return _status(access_id, "connected", "Le service est joignable.")
    return _status(access_id, "unreachable", f"Le service répond avec le code HTTP {response.status_code}.")


def _status_path() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = home / "arcenal"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "access-status.json"


def _read_statuses() -> dict[str, dict[str, object]]:
    path = _status_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="État des accès illisible.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="État des accès invalide.")
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _write_status(response: AccessProbeResponse) -> None:
    statuses = {**_read_statuses(), response.access_id: response.model_dump()}
    path = _status_path()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".access.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(statuses, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="État des accès impossible à enregistrer.") from exc


@router.get("/status")
def access_statuses() -> dict[str, object]:
    return {"accesses": _read_statuses()}


@router.post("/{access_id}/test", response_model=AccessProbeResponse)
async def test_access(access_id: str) -> AccessProbeResponse:
    item, secret = _credential(access_id)
    if item.get("enabled") is False:
        response = _status(access_id, "disabled", "Cet accès est désactivé.")
    elif not secret:
        response = _status(access_id, "missing", "Le secret associé est absent.")
    else:
        response = await _probe_access(access_id, item, secret)
    _write_status(response)
    return response
