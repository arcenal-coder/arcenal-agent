"""Tests bornés des fournisseurs IA configurés pour ARC."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/providers")

PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {"env": "OPENROUTER_API_KEY", "url": "https://openrouter.ai/api/v1/models"},
    "openai": {"env": "OPENAI_API_KEY", "url": "https://api.openai.com/v1/models"},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "url": "https://api.anthropic.com/v1/models"},
    "mistral": {"env": "MISTRAL_API_KEY", "url": "https://api.mistral.ai/v1/models"},
    "gemini": {"env": "GEMINI_API_KEY", "url": "https://generativelanguage.googleapis.com/v1beta/models"},
    "ollama": {"env": "", "url": "http://127.0.0.1:11434/v1/models"},
    "compatible": {"env": "OPENAI_COMPATIBLE_API_KEY", "url": ""},
    "internal": {"env": "ARCENAL_INTERNAL_LLM_API_KEY", "url": ""},
}


class ProviderProbeRequest(BaseModel):
    """Paramètres temporaires utilisés sans persister le secret."""

    provider: str = Field(min_length=2, max_length=40)
    api_key: str | None = Field(default=None, max_length=2048)
    base_url: str | None = Field(default=None, max_length=2048)


class ProviderProbeResponse(BaseModel):
    """Résultat expurgé d’un test de connexion."""

    configured: bool
    connection: str = Field(pattern="^(connected|invalid|missing|unreachable)$")
    message: str
    models: list[str]
    provider: str
    tested_at: str


class JsonResponse(Protocol):
    """Contrat minimal requis pour décoder une réponse HTTP."""

    def json(self) -> object: ...


def _definition(provider: str) -> dict[str, str]:
    definition = PROVIDERS.get(provider)
    if definition is None:
        raise HTTPException(status_code=404, detail="Fournisseur IA inconnu.")
    return definition


def _configured_key(env_name: str) -> str:
    if not env_name:
        return ""
    from hermes_cli.config import load_env

    return load_env().get(env_name, "").strip()


def _probe_url(provider: str, requested: str | None) -> str:
    definition = _definition(provider)
    raw = (requested or definition["url"]).strip()
    if not raw:
        raise HTTPException(status_code=422, detail="L’adresse du fournisseur est obligatoire.")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="L’adresse du fournisseur est invalide.")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="L’adresse ne doit pas contenir d’identifiants.")
    if provider in {"compatible", "internal", "ollama"}:
        return _compatible_models_url(raw)
    return definition["url"]


def _compatible_models_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/models"):
        return normalized
    return f"{normalized}/models" if normalized.endswith("/v1") else f"{normalized}/v1/models"


def _headers(provider: str, api_key: str) -> dict[str, str]:
    if provider == "anthropic":
        return {"accept": "application/json", "anthropic-version": "2023-06-01", "x-api-key": api_key}
    if api_key:
        return {"accept": "application/json", "authorization": f"Bearer {api_key}"}
    return {"accept": "application/json"}


def _models(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return _gemini_models(payload)
    identifiers = [item.get("id") for item in payload["data"] if isinstance(item, dict)]
    return sorted({str(identifier) for identifier in identifiers if identifier})[:100]


def _gemini_models(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return []
    names = [item.get("name") for item in payload["models"] if isinstance(item, dict)]
    return sorted({str(name).removeprefix("models/") for name in names if name})[:100]


def _status_root() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = home / "arcenal"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _status_path() -> Path:
    return _status_root() / "provider-status.json"


def _read_statuses() -> dict[str, dict[str, object]]:
    path = _status_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="État des fournisseurs illisible.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="État des fournisseurs invalide.")
    return {str(key): value for key, value in payload.items() if key in PROVIDERS and isinstance(value, dict)}


def _write_status(response: ProviderProbeResponse) -> None:
    statuses = {**_read_statuses(), response.provider: response.model_dump()}
    descriptor, temporary_name = tempfile.mkstemp(prefix=".providers.", dir=_status_root())
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(statuses, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, _status_path())
        _status_path().chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="État des fournisseurs impossible à enregistrer.") from exc


def _result(provider: str, status: int, models: list[str]) -> ProviderProbeResponse:
    tested_at = datetime.now(timezone.utc).isoformat()
    if status in {200, 429}:
        return ProviderProbeResponse(provider=provider, configured=True, connection="connected", message="Connexion opérationnelle.", models=models, tested_at=tested_at)
    if status in {401, 403}:
        return ProviderProbeResponse(provider=provider, configured=True, connection="invalid", message="Le fournisseur a refusé l’authentification.", models=[], tested_at=tested_at)
    return ProviderProbeResponse(provider=provider, configured=True, connection="unreachable", message=f"Le fournisseur répond avec le code HTTP {status}.", models=[], tested_at=tested_at)


def _missing(provider: str) -> ProviderProbeResponse:
    return ProviderProbeResponse(provider=provider, configured=False, connection="missing", message="La clé ou l’adresse requise est absente.", models=[], tested_at=datetime.now(timezone.utc).isoformat())


async def _probe(provider: str, url: str, api_key: str) -> ProviderProbeResponse:
    import httpx

    params = {"key": api_key} if provider == "gemini" else None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.get(url, headers=_headers(provider, api_key), params=params)
    except httpx.HTTPError:
        return _result(provider, 503, [])
    payload = _response_payload(response) if response.status_code in {200, 429} else {}
    return _result(provider, response.status_code, _models(payload))


def _response_payload(response: JsonResponse) -> object:
    try:
        return response.json()
    except (TypeError, ValueError):
        return {}


@router.get("/status")
def provider_statuses() -> dict[str, object]:
    return {"providers": _read_statuses()}


@router.post("/test", response_model=ProviderProbeResponse)
async def test_provider(request: ProviderProbeRequest) -> ProviderProbeResponse:
    definition = _definition(request.provider)
    api_key = (request.api_key or "").strip() or _configured_key(definition["env"])
    url = _probe_url(request.provider, request.base_url)
    if definition["env"] and not api_key:
        response = _missing(request.provider)
    else:
        response = await _probe(request.provider, url, api_key)
    _write_status(response)
    return response
