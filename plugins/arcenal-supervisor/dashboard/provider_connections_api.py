"""Tests bornés des fournisseurs IA configurés pour ARC."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/providers")

PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {"env": "OPENROUTER_API_KEY", "url": "https://openrouter.ai/api/v1/models"},
    "openai": {"env": "OPENAI_API_KEY", "url": "https://api.openai.com/v1/models"},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "url": "https://api.anthropic.com/v1/models"},
    "mistral": {"env": "MISTRAL_API_KEY", "url": "https://api.mistral.ai/v1/models"},
    "gemini": {"env": "GEMINI_API_KEY", "url": "https://generativelanguage.googleapis.com/v1beta/models"},
    "ollama": {"env": "", "url": "http://127.0.0.1:11434/v1/models"},
    "vllm": {"env": "", "url": "http://127.0.0.1:8000/v1/models"},
    "compatible": {"env": "OPENAI_COMPATIBLE_API_KEY", "url": ""},
    "internal": {"env": "ARCENAL_INTERNAL_LLM_API_KEY", "url": ""},
}


class ProviderProbeRequest(BaseModel):
    """Paramètres temporaires utilisés sans persister le secret."""

    provider: str = Field(min_length=2, max_length=40)
    api_key: str | None = Field(default=None, max_length=2048)
    base_url: str | None = Field(default=None, max_length=2048)


class ProviderConnectRequest(ProviderProbeRequest):
    """Connexion validée puis persistée de manière atomique."""

    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = True


class ProviderProbeResponse(BaseModel):
    """Résultat expurgé d’un test de connexion."""

    configured: bool
    connection: str = Field(pattern="^(connected|invalid|missing|quota_limited|unreachable)$")
    message: str
    models: list[str]
    provider: str
    tested_at: str


class CodexSyncResponse(BaseModel):
    configured: bool
    models: list[str]
    provider: str = "openai-codex"


class JsonResponse(Protocol):
    """Contrat minimal requis pour décoder une réponse HTTP."""

    def json(self) -> object: ...


class ProviderDescriptorLike(Protocol):
    id: str
    capabilities: tuple[object, ...]
    location: object
    priority: int


class ModelDescriptorLike(Protocol):
    id: str
    provider: str
    catalog_source: object

    def model_copy(self, *, update: dict[str, object]) -> ModelDescriptorLike: ...


class ModelRegistryLike(Protocol):
    def list(self) -> tuple[ModelDescriptorLike, ...]: ...

    def upsert(self, model: ModelDescriptorLike) -> ModelDescriptorLike: ...

    def remove(self, model_id: str) -> None: ...


class FrugalRuntimeLike(Protocol):
    registry: ModelRegistryLike

    def ensure_configured_model(self) -> None: ...


@dataclass(frozen=True)
class ProviderSnapshot:
    """État minimal permettant d'annuler une activation incomplète."""

    config_exists: bool
    config_value: object
    models: tuple[ModelDescriptorLike, ...]
    secret_value: str | None


class ProviderActivationError(RuntimeError):
    """Échec d'activation après validation distante du fournisseur."""


def _definition(provider: str) -> dict[str, str]:
    definition = PROVIDERS.get(provider)
    if definition is None:
        raise HTTPException(status_code=404, detail="Fournisseur IA inconnu.")
    return definition


def _configured_key(env_name: str) -> str:
    if not env_name:
        return ""
    value = _core().runtime_configuration().vault.get_secret(env_name)
    return value.strip() if isinstance(value, str) else ""


def _core() -> ModuleType:
    module = sys.modules.get("arcenal_arc_core")
    if not isinstance(module, ModuleType):
        raise RuntimeError("Le cœur de configuration ARC est indisponible.")
    return module


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
    if provider in {"compatible", "internal", "ollama", "vllm"}:
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
    if provider == "gemini":
        return {"accept": "application/json"}
    if api_key:
        return {"accept": "application/json", "authorization": f"Bearer {api_key}"}
    return {"accept": "application/json"}


def _models(payload: object) -> list[str]:
    record = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    data = record.get("data")
    if not isinstance(data, list):
        return _gemini_models(payload)
    identifiers = [cast(dict[str, object], item).get("id") for item in data if isinstance(item, dict)]
    return sorted({str(identifier) for identifier in identifiers if identifier})[:100]


def _gemini_models(payload: object) -> list[str]:
    record = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    models = record.get("models")
    if not isinstance(models, list):
        return []
    usable = [cast(dict[str, object], item) for item in models if _supports_generation(item)]
    names = [item.get("name") for item in usable]
    return sorted({str(name).removeprefix("models/") for name in names if name})[:100]


def _supports_generation(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    methods = cast(dict[str, object], value).get("supportedGenerationMethods")
    return isinstance(methods, list) and "generateContent" in methods


def _status_root() -> Path:
    home = Path(os.environ.get("ARCENAL_HOME") or os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
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
    if status == 200:
        return ProviderProbeResponse(provider=provider, configured=True, connection="connected", message="Connexion opérationnelle.", models=models, tested_at=tested_at)
    if status == 429:
        return ProviderProbeResponse(provider=provider, configured=True, connection="quota_limited", message="Le quota disponible du fournisseur est épuisé.", models=[], tested_at=tested_at)
    if status in {401, 403}:
        return ProviderProbeResponse(provider=provider, configured=True, connection="invalid", message="Le fournisseur a refusé l’authentification.", models=[], tested_at=tested_at)
    return ProviderProbeResponse(provider=provider, configured=True, connection="unreachable", message=f"Le fournisseur répond avec le code HTTP {status}.", models=[], tested_at=tested_at)


def _missing(provider: str) -> ProviderProbeResponse:
    return ProviderProbeResponse(provider=provider, configured=False, connection="missing", message="La clé ou l’adresse requise est absente.", models=[], tested_at=datetime.now(timezone.utc).isoformat())


def _model_id(provider: str, model_name: str) -> str:
    digest = sha256(model_name.encode("utf-8")).hexdigest()[:16]
    return f"{provider}-{digest}"


def _discovered_model(provider: ProviderDescriptorLike, model_name: str) -> ModelDescriptorLike:
    core = _core()
    capabilities = (core.CapabilityProfile.STANDARD,)
    return cast(ModelDescriptorLike, core.ModelDescriptor(
        id=_model_id(provider.id, model_name), provider=provider.id,
        model_name=model_name, display_name=model_name,
        availability=core.ModelAvailability.AVAILABLE,
        catalog_source=core.ModelCatalogSource.DISCOVERED,
        capabilities=capabilities, context_window=None,
        supports_tools=core.ProviderCapability.TOOL_CALLING in provider.capabilities,
        supports_structured_output=core.ProviderCapability.STRUCTURED_OUTPUT in provider.capabilities,
        supports_vision=core.ProviderCapability.VISION in provider.capabilities,
        location=provider.location, priority=provider.priority,
    ))


def _mark_missing_models(registry: ModelRegistryLike, provider_id: str, active_ids: frozenset[str]) -> None:
    core = _core()
    for model in registry.list():
        if model.provider != provider_id or model.catalog_source is not core.ModelCatalogSource.DISCOVERED:
            continue
        availability = core.ModelAvailability.AVAILABLE if model.id in active_ids else core.ModelAvailability.UNAVAILABLE
        registry.upsert(model.model_copy(update={"availability": availability}))


def _sync_models(provider_id: str, model_names: list[str]) -> None:
    core = _core()
    runtime = core.FrugalRuntime(_status_root() / "frugal")
    runtime.ensure_configured_model()
    provider = cast(ProviderDescriptorLike | None, runtime.providers.get(provider_id))
    if provider is None:
        raise HTTPException(status_code=422, detail="Fournisseur absent du registre ARC.")
    models = tuple(_discovered_model(provider, name) for name in model_names)
    for model in models:
        runtime.registry.upsert(model)
    registry = cast(ModelRegistryLike, runtime.registry)
    _mark_missing_models(registry, provider_id, frozenset(model.id for model in models))


def _provider_snapshot(provider_id: str, env_name: str) -> ProviderSnapshot:
    configuration = _core().runtime_configuration()
    runtime = _frugal_runtime()
    models = tuple(model for model in runtime.registry.list() if model.provider == provider_id)
    return ProviderSnapshot(
        config_exists=configuration.config.exists("providers", provider_id),
        config_value=configuration.config.get("providers", provider_id),
        models=models,
        secret_value=configuration.vault.get_secret(env_name) if env_name else None,
    )


def _frugal_runtime() -> FrugalRuntimeLike:
    core = _core()
    runtime = core.FrugalRuntime(_status_root() / "frugal")
    runtime.ensure_configured_model()
    return cast(FrugalRuntimeLike, runtime)


def _restore_models(provider_id: str, models: tuple[ModelDescriptorLike, ...]) -> None:
    registry = cast(ModelRegistryLike, _frugal_runtime().registry)
    for model in tuple(registry.list()):
        if model.provider == provider_id:
            registry.remove(model.id)
    for model in models:
        registry.upsert(model)


def _restore_provider(provider_id: str, env_name: str, snapshot: ProviderSnapshot) -> None:
    runtime = _core().runtime_configuration()
    if snapshot.config_exists:
        runtime.config.set("providers", provider_id, snapshot.config_value)
    else:
        runtime.config.delete("providers", provider_id)
    if env_name and snapshot.secret_value is not None:
        runtime.vault.set_secret(env_name, snapshot.secret_value)
    elif env_name:
        runtime.vault.delete_secret(env_name)
    _restore_models(provider_id, snapshot.models)


def _activate_provider(request: ProviderConnectRequest, response: ProviderProbeResponse, env_name: str) -> None:
    runtime = _core().runtime_configuration()
    base_url = request.base_url.strip() if request.base_url else None
    api_key = request.api_key.strip() if request.api_key else ""
    value = {"enabled": request.enabled, **({"base_url": base_url} if base_url else {})}
    runtime.config.set("providers", request.provider, value)
    if env_name and api_key:
        runtime.vault.set_secret(env_name, api_key)
    _sync_models(request.provider, response.models)


def _require_connectable(response: ProviderProbeResponse) -> None:
    if response.connection != "connected":
        status = 503 if response.connection in {"quota_limited", "unreachable"} else 422
        raise HTTPException(status_code=status, detail=response.message)
    if not response.models:
        raise HTTPException(status_code=503, detail="Le fournisseur ne publie aucun modèle compatible.")


def _abort_activation(provider_id: str, env_name: str, snapshot: ProviderSnapshot, cause: Exception) -> None:
    try:
        _restore_provider(provider_id, env_name, snapshot)
    except Exception as rollback_error:
        error = ProviderActivationError("Activation échouée et état antérieur impossible à restaurer.")
        raise HTTPException(status_code=500, detail=str(error)) from rollback_error
    error = ProviderActivationError("Activation annulée et état antérieur restauré.")
    raise HTTPException(status_code=500, detail=str(error)) from cause


def _codex_models() -> list[str]:
    from hermes_cli.inventory import build_models_payload, load_picker_context

    payload = build_models_payload(load_picker_context(), explicit_only=True, for_picker=True, probe_custom_providers=False, max_models=100)
    providers = payload.get("providers", [])
    row = next((item for item in providers if isinstance(item, dict) and item.get("slug") == "openai-codex"), {})
    models = row.get("models", []) if isinstance(row, dict) else []
    return [item for item in models if isinstance(item, str) and item.strip()][:100]


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


async def _evaluate_provider(request: ProviderProbeRequest) -> ProviderProbeResponse:
    definition = _definition(request.provider)
    api_key = (request.api_key or "").strip() or _configured_key(definition["env"])
    url = _probe_url(request.provider, request.base_url)
    if definition["env"] and not api_key:
        return _missing(request.provider)
    return await _probe(request.provider, url, api_key)


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
    response = await _evaluate_provider(request)
    _write_status(response)
    return response


@router.post("/connect", response_model=ProviderProbeResponse)
async def connect_provider(request: ProviderConnectRequest) -> ProviderProbeResponse:
    definition = _definition(request.provider)
    response = await _evaluate_provider(request)
    try:
        _require_connectable(response)
    except HTTPException:
        _write_status(response)
        raise
    snapshot = _provider_snapshot(request.provider, definition["env"])
    try:
        _activate_provider(request, response, definition["env"])
    except Exception as exc:
        _abort_activation(request.provider, definition["env"], snapshot, exc)
    _write_status(response)
    return response


@router.post("/codex/sync", response_model=CodexSyncResponse)
def sync_codex_provider() -> CodexSyncResponse:
    from hermes_cli.auth import get_codex_auth_status

    if not get_codex_auth_status().get("logged_in"):
        raise HTTPException(status_code=409, detail="La connexion Codex n’est pas active.")
    models = _codex_models()
    if not models:
        raise HTTPException(status_code=503, detail="Le catalogue Codex est temporairement indisponible.")
    _sync_models("openai-codex", models)
    return CodexSyncResponse(configured=True, models=models)
