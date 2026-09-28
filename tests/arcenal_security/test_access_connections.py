from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "access_connections_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_access_connections_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des accès est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class AccessConnectionTests(TestCase):
    def test_service_url_rejects_embedded_credentials(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE._service_url({"serviceUrl": "https://admin:secret@example.test"})
        self.assertEqual(raised.exception.status_code, 422)

    def test_api_secret_is_sent_only_as_an_authorization_header(self) -> None:
        headers = MODULE._headers({"kind": "api"}, "secret")
        self.assertEqual(headers, {"accept": "application/json", "authorization": "Bearer secret"})


class AccessProbeTests(IsolatedAsyncioTestCase):
    async def test_disabled_access_never_reaches_the_network(self) -> None:
        item = {"enabled": False}
        with (
            patch.object(MODULE, "_credential", return_value=(item, "secret")),
            patch.object(MODULE, "_probe_access", new_callable=AsyncMock) as probe,
            patch.object(MODULE, "_write_status"),
        ):
            response = await MODULE.test_access("crm")
        self.assertEqual(response.connection, "disabled")
        probe.assert_not_awaited()

    async def test_missing_secret_is_reported_without_network(self) -> None:
        with (
            patch.object(MODULE, "_credential", return_value=({}, "")),
            patch.object(MODULE, "_probe_access", new_callable=AsyncMock) as probe,
            patch.object(MODULE, "_write_status"),
        ):
            response = await MODULE.test_access("crm")
        self.assertEqual(response.connection, "missing")
        probe.assert_not_awaited()
