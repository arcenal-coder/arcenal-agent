from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "provider_connections_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_provider_connections_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des fournisseurs est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_core() -> ModuleType:
    existing = sys.modules.get("arcenal_arc_core")
    if isinstance(existing, ModuleType):
        return existing
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location("arcenal_arc_core", source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("Le cœur ARC est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class ProviderConnectionTests(TestCase):
    def test_compatible_url_targets_the_models_endpoint(self) -> None:
        self.assertEqual(MODULE._compatible_models_url("https://llm.example.test/v1"), "https://llm.example.test/v1/models")
        self.assertEqual(MODULE._compatible_models_url("http://ollama.test"), "http://ollama.test/v1/models")
        self.assertEqual(MODULE._probe_url("vllm", None), "http://127.0.0.1:8000/v1/models")

    def test_provider_url_rejects_credentials(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE._probe_url("internal", "https://admin:secret@llm.example.test/v1")
        self.assertEqual(raised.exception.status_code, 422)

    def test_model_parser_accepts_openai_and_gemini_formats(self) -> None:
        self.assertEqual(MODULE._models({"data": [{"id": "gpt-test"}]}), ["gpt-test"])
        payload = {"models": [
            {"name": "models/gemini-chat", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-embed", "supportedGenerationMethods": ["embedContent"]},
        ]}
        self.assertEqual(MODULE._models(payload), ["gemini-chat"])

    def test_gemini_key_is_not_sent_as_an_oauth_bearer(self) -> None:
        self.assertEqual(MODULE._headers("gemini", "secret"), {"accept": "application/json"})
        self.assertEqual(
            MODULE._headers("openai", "secret"),
            {"accept": "application/json", "authorization": "Bearer secret"},
        )

    def test_codex_sync_requires_an_active_device_connection(self) -> None:
        with patch("hermes_cli.auth.get_codex_auth_status", return_value={"logged_in": False}):
            with self.assertRaises(HTTPException) as raised:
                MODULE.sync_codex_provider()

        self.assertEqual(raised.exception.status_code, 409)

    def test_codex_sync_rejects_an_empty_catalog(self) -> None:
        with (
            patch("hermes_cli.auth.get_codex_auth_status", return_value={"logged_in": True}),
            patch.object(MODULE, "_codex_models", return_value=[]),
        ):
            with self.assertRaises(HTTPException) as raised:
                MODULE.sync_codex_provider()

        self.assertEqual(raised.exception.status_code, 503)

    def test_codex_sync_populates_the_arc_model_registry(self) -> None:
        with (
            patch("hermes_cli.auth.get_codex_auth_status", return_value={"logged_in": True}),
            patch.object(MODULE, "_codex_models", return_value=["gpt-codex-test"]),
            patch.object(MODULE, "_sync_models") as sync_models,
        ):
            response = MODULE.sync_codex_provider()

        self.assertTrue(response.configured)
        self.assertEqual(response.models, ["gpt-codex-test"])
        sync_models.assert_called_once_with("openai-codex", ["gpt-codex-test"])


class ProviderProbeTests(IsolatedAsyncioTestCase):
    async def test_missing_key_is_reported_without_network_call(self) -> None:
        request = MODULE.ProviderProbeRequest(provider="openai")
        with (
            patch.object(MODULE, "_configured_key", return_value=""),
            patch.object(MODULE, "_probe", new_callable=AsyncMock) as probe,
            patch.object(MODULE, "_write_status") as write_status,
        ):
            response = await MODULE.test_provider(request)
        self.assertEqual(response.connection, "missing")
        probe.assert_not_awaited()
        write_status.assert_called_once()

    async def test_configured_provider_is_probed_and_status_is_saved(self) -> None:
        request = MODULE.ProviderProbeRequest(provider="mistral", api_key="secret")
        expected = MODULE._result("mistral", 200, ["mistral-small"])
        with (
            patch.object(MODULE, "_probe", new=AsyncMock(return_value=expected)) as probe,
            patch.object(MODULE, "_write_status") as write_status,
            patch.object(MODULE, "_sync_models"),
        ):
            response = await MODULE.test_provider(request)
        self.assertEqual(response.models, ["mistral-small"])
        probe.assert_awaited_once()
        write_status.assert_called_once_with(expected)

    async def test_discovered_models_feed_the_existing_registry(self) -> None:
        request = MODULE.ProviderProbeRequest(provider="gemini", api_key="secret")
        expected = MODULE._result("gemini", 200, ["gemini-flash"])
        with (
            patch.object(MODULE, "_probe", new=AsyncMock(return_value=expected)),
            patch.object(MODULE, "_write_status"),
            patch.object(MODULE, "_sync_models") as sync_models,
        ):
            await MODULE.test_provider(request)
        sync_models.assert_called_once_with("gemini", ["gemini-flash"])

    async def test_quota_limit_is_not_reported_as_invalid_credentials(self) -> None:
        result = MODULE._result("gemini", 429, [])

        self.assertEqual(result.connection, "quota_limited")
        self.assertIn("quota", result.message.lower())
        self.assertNotIn("clé", result.message.lower())

    async def test_discovery_persists_models_and_marks_missing_entries(self) -> None:
        _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}):
            MODULE._sync_models("gemini", ["gemini-flash", "gemini-pro"])
            MODULE._sync_models("gemini", ["gemini-flash"])
            runtime = MODULE._core().FrugalRuntime(Path(directory) / "arcenal" / "frugal")
            models = {model.model_name: model for model in runtime.registry.list() if model.provider == "gemini"}

        self.assertEqual(models["gemini-flash"].availability.value, "available")
        self.assertEqual(models["gemini-pro"].availability.value, "unavailable")
        self.assertEqual(models["gemini-flash"].catalog_source.value, "discovered")
