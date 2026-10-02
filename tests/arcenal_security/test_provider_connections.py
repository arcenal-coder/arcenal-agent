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
        openai = {"data": [
            {"id": "gpt-test"},
            {
                "id": "reasoning-test",
                "supported_parameters": ["reasoning", "tools", "structured_outputs"],
                "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            },
            {"id": "text-embedding-test"},
            {"id": "image-test", "architecture": {"output_modalities": ["image"]}},
            {"id": "gpt-realtime"},
            {"id": "gpt-audio-preview"},
            {"id": "gpt-3.5-turbo-instruct"},
        ]}
        self.assertEqual(MODULE._models(openai), ["gpt-test", "reasoning-test"])
        capabilities = MODULE._model_capabilities(openai)["reasoning-test"]
        self.assertTrue(capabilities.reasoning)
        self.assertTrue(capabilities.tools)
        self.assertTrue(capabilities.structured_output)
        self.assertTrue(capabilities.vision)
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

    def test_openrouter_discovery_routes_advanced_arc_requests(self) -> None:
        core = _load_core()
        metadata = MODULE.ModelProbeCapabilities(reasoning=True, tools=True)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory, "ARCENAL_CONFIG_BACKEND": "arc"}, clear=False):
            configuration = core.runtime_configuration()
            configuration.vault.set_secret("OPENROUTER_API_KEY", "secret")
            MODULE._sync_models("openrouter", ["openrouter-model"], {"openrouter-model": metadata})
            runtime = MODULE._frugal_runtime()
            model = next(item for item in runtime.registry.list() if item.provider == "openrouter")
            runtime.registry.upsert(model.model_copy(update={"privacy_class": core.ConfidentialityLevel.ADMIN}))
            decision = core.ModelRouter(runtime.registry, providers=runtime.providers).route(core.RoutingNeed(
                agent_id="arc", task_type=core.TaskType.REASONING,
                required_capability=core.CapabilityProfile.ADVANCED,
                confidentiality=core.ConfidentialityLevel.ADMIN,
                tools_required=True,
            ))

        self.assertEqual(decision.provider, "openrouter")
        self.assertEqual(decision.model, "openrouter-model")
        self.assertNotIn("repli standard", decision.reason)

    def test_standard_model_can_explicitly_replace_an_advanced_model(self) -> None:
        core = _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}, clear=False):
            core.runtime_configuration().vault.set_secret("OPENROUTER_API_KEY", "secret")
            MODULE._sync_models("openrouter", ["openrouter-model"])
            runtime = MODULE._frugal_runtime()
            model = next(item for item in runtime.registry.list() if item.provider == "openrouter")
            runtime.registry.upsert(model.model_copy(update={"privacy_class": core.ConfidentialityLevel.ADMIN}))
            decision = core.ModelRouter(runtime.registry, providers=runtime.providers).route(core.RoutingNeed(
                agent_id="arc", task_type=core.TaskType.REASONING,
                required_capability=core.CapabilityProfile.ADVANCED,
                confidentiality=core.ConfidentialityLevel.ADMIN,
            ))

        self.assertIn("repli standard", decision.reason)

    def test_unproven_tool_support_is_rejected(self) -> None:
        core = _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}, clear=False):
            core.runtime_configuration().vault.set_secret("OPENROUTER_API_KEY", "secret")
            MODULE._sync_models("openrouter", ["openrouter-model"])
            runtime = MODULE._frugal_runtime()
            model = next(item for item in runtime.registry.list() if item.provider == "openrouter")
            runtime.registry.upsert(model.model_copy(update={"privacy_class": core.ConfidentialityLevel.ADMIN}))
            need = core.RoutingNeed(
                agent_id="arc", task_type=core.TaskType.REASONING,
                required_capability=core.CapabilityProfile.STANDARD,
                confidentiality=core.ConfidentialityLevel.ADMIN,
                tools_required=True,
            )

            with self.assertRaises(core.ModelRoutingError):
                core.ModelRouter(runtime.registry, providers=runtime.providers).route(need)

    def test_provider_contracts_enable_only_known_tool_models(self) -> None:
        core = _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}, clear=False):
            MODULE._sync_models("gemini", ["gemini-flash"])
            MODULE._sync_models("anthropic", ["claude-sonnet"])
            MODULE._sync_models("openai", ["gpt-5", "babbage-002", "gpt-realtime", "gpt-audio-preview", "gpt-3.5-turbo-instruct"])
            MODULE._sync_models("compatible", ["private-model"])
            models = {item.model_name: item for item in MODULE._frugal_runtime().registry.list()}

        self.assertTrue(models["gemini-flash"].supports_tools)
        self.assertTrue(models["claude-sonnet"].supports_tools)
        self.assertTrue(models["gpt-5"].supports_tools)
        self.assertFalse(models["babbage-002"].supports_tools)
        self.assertFalse(models["gpt-realtime"].supports_tools)
        self.assertFalse(models["gpt-audio-preview"].supports_tools)
        self.assertFalse(models["gpt-3.5-turbo-instruct"].supports_tools)
        self.assertFalse(models["private-model"].supports_tools)
        self.assertFalse(models["gemini-flash"].supports_structured_output)
        self.assertEqual(models["gpt-5"].location, core.ModelLocation.REMOTE)

    def test_codex_contract_does_not_invent_structured_output(self) -> None:
        core = _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}, clear=False):
            MODULE._sync_models("openai-codex", ["gpt-codex-test"])
            model = next(item for item in MODULE._frugal_runtime().registry.list() if item.provider == "openai-codex")

        self.assertTrue(model.supports_tools)
        self.assertFalse(model.supports_structured_output)
        self.assertEqual(model.location, core.ModelLocation.REMOTE)


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
            patch.object(MODULE, "_sync_models") as sync_models,
        ):
            response = await MODULE.test_provider(request)
        self.assertEqual(response.models, ["mistral-small"])
        probe.assert_awaited_once()
        write_status.assert_called_once_with(expected)
        sync_models.assert_not_called()

    async def test_connection_persists_secret_configuration_and_models(self) -> None:
        _load_core()
        request = MODULE.ProviderConnectRequest(provider="gemini", api_key="secret", enabled=True)
        expected = MODULE._result("gemini", 200, ["gemini-flash"])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory, "ARCENAL_CONFIG_BACKEND": "arc"}, clear=False):
            os.environ["GEMINI_API_KEY"] = "old-secret"
            with patch.object(MODULE, "_probe", new=AsyncMock(return_value=expected)):
                response = await MODULE.connect_provider(request)
            configuration = MODULE._core().runtime_configuration()
            persisted_secret = configuration.vault.get_secret("GEMINI_API_KEY")
            persisted_provider = configuration.config.get("providers", "gemini")
            persisted_status = MODULE._read_statuses()["gemini"]
            models = MODULE._frugal_runtime().registry.list()
            runtime_secret = os.environ.get("GEMINI_API_KEY")

        self.assertEqual(response.models, ["gemini-flash"])
        self.assertEqual(persisted_secret, "secret")
        self.assertEqual(runtime_secret, "secret")
        self.assertIsNone(os.environ.get("GEMINI_API_KEY"))
        self.assertEqual(persisted_provider, {"enabled": True})
        self.assertEqual(persisted_status["connection"], "connected")
        self.assertTrue(any(model.model_name == "gemini-flash" for model in models))

    async def test_failed_probe_preserves_existing_provider(self) -> None:
        _load_core()
        request = MODULE.ProviderConnectRequest(provider="gemini", api_key="new-secret")
        rejected = MODULE._result("gemini", 429, [])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory, "ARCENAL_CONFIG_BACKEND": "arc"}, clear=False):
            configuration = MODULE._core().runtime_configuration()
            configuration.vault.set_secret("GEMINI_API_KEY", "old-secret")
            configuration.config.set("providers", "gemini", {"enabled": False})
            with patch.object(MODULE, "_probe", new=AsyncMock(return_value=rejected)), patch.object(MODULE, "_write_status"):
                with self.assertRaises(HTTPException):
                    await MODULE.connect_provider(request)
            persisted_secret = configuration.vault.get_secret("GEMINI_API_KEY")
            persisted_provider = configuration.config.get("providers", "gemini")

        self.assertEqual(persisted_secret, "old-secret")
        self.assertEqual(persisted_provider, {"enabled": False})

    async def test_empty_catalog_is_not_persisted(self) -> None:
        request = MODULE.ProviderConnectRequest(provider="openrouter", api_key="secret")
        empty = MODULE._result("openrouter", 200, [])
        with (
            patch.object(MODULE, "_probe", new=AsyncMock(return_value=empty)),
            patch.object(MODULE, "_write_status"),
            patch.object(MODULE, "_provider_snapshot") as snapshot,
        ):
            with self.assertRaises(HTTPException) as raised:
                await MODULE.connect_provider(request)

        self.assertEqual(raised.exception.status_code, 503)
        snapshot.assert_not_called()

    async def test_synchronization_failure_restores_previous_state(self) -> None:
        _load_core()
        request = MODULE.ProviderConnectRequest(provider="mistral", api_key="new-secret")
        expected = MODULE._result("mistral", 200, ["new-model"])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory, "ARCENAL_CONFIG_BACKEND": "arc"}, clear=False):
            configuration = MODULE._core().runtime_configuration()
            configuration.vault.set_secret("MISTRAL_API_KEY", "old-secret")
            os.environ["MISTRAL_API_KEY"] = "old-secret"
            configuration.config.set("providers", "mistral", {"enabled": False})
            MODULE._sync_models("mistral", ["old-model"])
            MODULE._write_status(MODULE._result("mistral", 401, []))
            with patch.object(MODULE, "_probe", new=AsyncMock(return_value=expected)), patch.object(MODULE, "_sync_models", side_effect=RuntimeError("sync")):
                with self.assertRaises(HTTPException) as raised:
                    await MODULE.connect_provider(request)
            persisted_secret = configuration.vault.get_secret("MISTRAL_API_KEY")
            persisted_provider = configuration.config.get("providers", "mistral")
            persisted_status = MODULE._read_statuses()["mistral"]
            models = MODULE._frugal_runtime().registry.list()
            runtime_secret = os.environ.get("MISTRAL_API_KEY")

        self.assertEqual(persisted_secret, "old-secret")
        self.assertEqual(runtime_secret, "old-secret")
        self.assertEqual(persisted_provider, {"enabled": False})
        self.assertEqual([model.model_name for model in models if model.provider == "mistral"], ["old-model"])
        self.assertEqual(persisted_status["connection"], "invalid")
        self.assertEqual(raised.exception.status_code, 500)
        self.assertIn("restauré", raised.exception.detail)

    async def test_quota_limit_is_not_reported_as_invalid_credentials(self) -> None:
        result = MODULE._result("gemini", 429, [])

        self.assertEqual(result.connection, "quota_limited")
        self.assertIn("quota", result.message.lower())
        self.assertNotIn("clé", result.message.lower())

    async def test_discovery_persists_models_and_marks_missing_entries(self) -> None:
        _load_core()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}):
            MODULE._sync_models("gemini", ["gemini-flash", "gemini-pro"])
            runtime = MODULE._core().FrugalRuntime(Path(directory) / "arcenal" / "frugal")
            original = next(model for model in runtime.registry.list() if model.model_name == "gemini-flash")
            runtime.registry.upsert(original.model_copy(update={
                "context_window": 64_000,
                "display_name": "Gemini interne",
                "enabled": False,
                "privacy_class": MODULE._core().ConfidentialityLevel.ADMIN,
            }))
            MODULE._sync_models("gemini", ["gemini-flash"])
            runtime = MODULE._core().FrugalRuntime(Path(directory) / "arcenal" / "frugal")
            models = {model.model_name: model for model in runtime.registry.list() if model.provider == "gemini"}

        self.assertEqual(models["gemini-flash"].availability.value, "available")
        self.assertEqual(models["gemini-pro"].availability.value, "unavailable")
        self.assertEqual(models["gemini-flash"].catalog_source.value, "discovered")
        self.assertFalse(models["gemini-flash"].enabled)
        self.assertEqual(models["gemini-flash"].privacy_class.value, "admin")
        self.assertEqual(models["gemini-flash"].context_window, 64_000)
        self.assertEqual(models["gemini-flash"].display_name, "Gemini interne")
        self.assertEqual(
            {capability.value for capability in models["gemini-flash"].capabilities},
            {"standard"},
        )

    async def test_discovery_uses_proven_model_capabilities(self) -> None:
        _load_core()
        metadata = MODULE.ModelProbeCapabilities(
            reasoning=True,
            structured_output=True,
            tools=True,
            vision=True,
        )
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ARCENAL_HOME": directory}):
            MODULE._sync_models("openrouter", ["reasoning-model"], {"reasoning-model": metadata})
            runtime = MODULE._frugal_runtime()
            model = next(item for item in runtime.registry.list() if item.model_name == "reasoning-model")

        self.assertEqual({item.value for item in model.capabilities}, {"standard", "advanced"})
        self.assertTrue(model.supports_tools)
        self.assertTrue(model.supports_structured_output)
        self.assertTrue(model.supports_vision)
