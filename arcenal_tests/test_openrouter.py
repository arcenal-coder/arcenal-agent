"""Tests isolés de la connexion OpenRouter du panneau ARCenal."""

import asyncio
import importlib.util
from pathlib import Path
from typing import Any


MODULE = Path(__file__).parents[1] / "plugins/arcenal-supervisor/dashboard/plugin_api.py"
SPEC = importlib.util.spec_from_file_location("arcenal_openrouter_test", MODULE)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


async def _async_result(value: Any) -> Any:
    return value


def test_openrouter_reports_a_missing_key(monkeypatch) -> None:
    monkeypatch.setattr(supervisor, "_configured_openrouter_key", lambda: "")

    result = asyncio.run(supervisor.test_openrouter(supervisor.OpenRouterProbeRequest()))

    assert result.connection == "missing"
    assert result.configured is False


def test_openrouter_accepts_a_configured_key(monkeypatch) -> None:
    monkeypatch.setattr(supervisor, "_configured_openrouter_key", lambda: "stored-key")
    monkeypatch.setattr(
        supervisor,
        "_probe_openrouter",
        lambda _key: _async_result(supervisor._openrouter_probe_result(200)),
    )

    result = asyncio.run(supervisor.test_openrouter(supervisor.OpenRouterProbeRequest()))

    assert result.connection == "connected"


def test_openrouter_rejects_an_invalid_key(monkeypatch) -> None:
    monkeypatch.setattr(
        supervisor,
        "_probe_openrouter",
        lambda _key: _async_result(supervisor._openrouter_probe_result(401)),
    )

    request = supervisor.OpenRouterProbeRequest(api_key="bad-key")
    result = asyncio.run(supervisor.test_openrouter(request))

    assert result.connection == "invalid"
    assert "refusé" in result.message
