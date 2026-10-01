from __future__ import annotations

import importlib.util
import sys
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
        self.assertEqual(MODULE._models({"models": [{"name": "models/gemini-test"}]}), ["gemini-test"])


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
        ):
            response = await MODULE.test_provider(request)
        self.assertEqual(response.models, ["mistral-small"])
        probe.assert_awaited_once()
        write_status.assert_called_once_with(expected)
