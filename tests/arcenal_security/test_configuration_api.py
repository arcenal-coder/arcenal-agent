from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


def _load_core() -> ModuleType:
    existing = sys.modules.get("arcenal_arc_core")
    if existing is not None:
        return existing
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location("arcenal_arc_core", source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_api() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "configuration_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_configuration_api_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("L’API de configuration ARC est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_core()
API = _load_api()


def _runtime(tmp_path: Path):
    config = CORE.ArcNativeConfigStore(tmp_path / "arcenal" / "config.json")
    vault = CORE.ArcFileVault(tmp_path / ".env")
    return CORE.ArcRuntimeConfiguration(config, vault)


def _client(runtime, monkeypatch) -> TestClient:
    monkeypatch.setattr(API, "_runtime", lambda: runtime)
    app = FastAPI()
    app.include_router(API.router)
    return TestClient(app)


def test_configuration_round_trip_uses_native_namespaces(tmp_path: Path, monkeypatch) -> None:
    runtime = _runtime(tmp_path)
    client = _client(runtime, monkeypatch)
    payload = {
        "approvals": {"mode": "smart"},
        "arcenal": {"general": {"agent_name": "ARC", "language": "fr", "notification_email": "arc@example.test", "organization_name": "ARCenal", "timezone": "Europe/Paris"}},
        "providers": {"openrouter": {"enabled": True}},
    }

    assert client.put("/configuration/v1", json=payload).status_code == 200
    response = client.get("/configuration/v1")

    assert response.status_code == 200
    assert response.json()["backend"] == "arc"
    assert response.json()["config"]["approvals"] == {"mode": "smart"}
    assert response.json()["config"]["providers"]["openrouter"] == {"enabled": True}


def test_secret_rotation_and_deletion_never_return_values(tmp_path: Path, monkeypatch) -> None:
    client = _client(_runtime(tmp_path), monkeypatch)

    first = client.put("/configuration/v1/secrets/OPENROUTER_API_KEY", json={"value": "secret-a"})
    second = client.put("/configuration/v1/secrets/OPENROUTER_API_KEY", json={"value": "secret-b"})
    status = client.get("/configuration/v1")
    deleted = client.delete("/configuration/v1/secrets/OPENROUTER_API_KEY")

    assert first.json() == {"configured": True}
    assert second.json() == {"configured": True}
    assert status.json()["secrets"]["OPENROUTER_API_KEY"] is True
    assert "secret-a" not in status.text and "secret-b" not in status.text
    assert deleted.json() == {"configured": False}


def test_invalid_provider_and_secret_are_rejected(tmp_path: Path, monkeypatch) -> None:
    client = _client(_runtime(tmp_path), monkeypatch)

    provider = client.put("/configuration/v1", json={"providers": {"../bad": {"enabled": True}}})
    secret = client.put("/configuration/v1/secrets/bad-key", json={"value": "secret"})

    assert provider.status_code == 422
    assert secret.status_code == 422


def test_brand_asset_under_a_yunohost_subpath_is_accepted(tmp_path: Path, monkeypatch) -> None:
    client = _client(_runtime(tmp_path), monkeypatch)
    appearance = {"accent_color": "#9F3434", "button_color": "#D95A35", "favicon_url": "", "link_color": "#174D70", "logo_url": "/arcenal/api/plugins/arcenal-supervisor/branding/assets/logo?v=2", "text_color": "#1D2733"}

    response = client.put("/configuration/v1", json={"arcenal": {"appearance": appearance}})

    assert response.status_code == 200


def test_model_change_invalidates_only_previous_model(tmp_path: Path, monkeypatch) -> None:
    runtime = _runtime(tmp_path)
    runtime.config.set("models", "default", "old-model")
    invalidated: list[str] = []
    monkeypatch.setattr(API, "_invalidate_model", invalidated.append)
    client = _client(runtime, monkeypatch)

    response = client.put("/configuration/v1", json={"models": {"default": "new-model", "provider": "openrouter"}})

    assert response.status_code == 200
    assert invalidated == ["hermes-current"]
    assert runtime.config.get("models", "default") == "new-model"


@pytest.mark.parametrize("model", ["auto", " AUTO "])
def test_literal_auto_model_is_rejected(model: str, tmp_path: Path, monkeypatch) -> None:
    client = _client(_runtime(tmp_path), monkeypatch)

    response = client.put("/configuration/v1", json={"models": {"default": model, "provider": "gemini"}})

    assert response.status_code == 422
    assert "modèle précis" in response.text


def test_legacy_mode_rejects_configuration_writes(tmp_path: Path, monkeypatch) -> None:
    legacy = CORE.HermesConfigAdapter(lambda: {"model": {"default": "legacy"}})
    runtime = CORE.ArcRuntimeConfiguration(legacy, CORE.ArcFileVault(tmp_path / ".env"), backend="hermes", migration_state="legacy")
    client = _client(runtime, monkeypatch)

    response = client.put("/configuration/v1", json={"approvals": {"mode": "manual"}})

    assert response.status_code == 409
    assert "lecture seule" in response.json()["detail"]


@pytest.mark.parametrize("provider", ["openrouter", "openai", "gemini", "anthropic", "mistral", "ollama", "vllm", "compatible"])
def test_supported_provider_configuration_round_trip(provider: str, tmp_path: Path, monkeypatch) -> None:
    runtime = _runtime(tmp_path)
    client = _client(runtime, monkeypatch)

    response = client.put("/configuration/v1", json={"providers": {provider: {"base_url": "http://127.0.0.1:8000/v1", "enabled": True}}})

    assert response.status_code == 200
    assert runtime.config.get("providers", provider) == {"base_url": "http://127.0.0.1:8000/v1", "enabled": True}
