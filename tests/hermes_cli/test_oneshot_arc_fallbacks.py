"""Non-régression des replis Hermes lorsqu’ARC gouverne le routage."""

from __future__ import annotations

from unittest.mock import ANY
from unittest.mock import patch

import pytest

from hermes_cli import oneshot


class FakeAgent:
    created_kwargs: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        type(self).created_kwargs = kwargs

    def run_conversation(self, prompt: str) -> dict[str, object]:
        return {"final_response": f"Réponse à {prompt}"}

    def shutdown_memory_provider(self, *messages: object) -> None:
        return None

    def close(self) -> None:
        return None


def _run_with_fallback_policy(enabled: bool) -> dict[str, object]:
    config = {"fallback_providers": [{"provider": "gemini", "model": "gemini-test"}]}
    runtime = {"provider": "openrouter", "requested_provider": "openrouter", "api_mode": "chat_completions", "api_key": "secret-test", "base_url": "https://openrouter.ai/api/v1", "credential_pool": None}
    with (
        patch("hermes_cli.config.load_config", return_value=config),
        patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=runtime),
        patch("hermes_cli.mcp_startup.ensure_mcp_discovery_before_agent_build"),
        patch("run_agent.AIAgent", FakeAgent),
        patch.object(oneshot, "_create_session_db_for_oneshot", return_value=None),
        patch("tools.process_registry.process_registry.wait_for_pending_completions"),
    ):
        oneshot._run_agent("Bonjour", model="openrouter/test", provider="openrouter", use_config_toolsets=False, use_config_fallbacks=enabled)
    return FakeAgent.created_kwargs


def _run_arc(
    config: dict[str, object],
    *,
    provider: str,
    model: str,
    base_url: str,
    api_key: str | None,
) -> dict[str, object]:
    with (
        patch("hermes_cli.config.load_config", return_value=config),
        patch("hermes_cli.mcp_startup.ensure_mcp_discovery_before_agent_build"),
        patch("run_agent.AIAgent", FakeAgent),
        patch.object(oneshot, "_create_session_db_for_oneshot", return_value=None),
        patch("tools.process_registry.process_registry.wait_for_pending_completions"),
    ):
        oneshot._run_agent(
            "Bonjour", model=model, provider=provider, use_config_toolsets=False,
            use_config_fallbacks=False, runtime_base_url=base_url,
            runtime_api_key=api_key, platform="arcenal", honor_config_enabled=False,
        )
    return FakeAgent.created_kwargs


def test_arc_disables_the_global_hermes_fallback_chain() -> None:
    assert _run_with_fallback_policy(False)["fallback_model"] is None


def test_regular_oneshot_keeps_the_global_hermes_fallback_chain() -> None:
    assert _run_with_fallback_policy(True)["fallback_model"] == [{"provider": "gemini", "model": "gemini-test"}]


def test_arc_custom_runtime_reaches_the_agent_without_hermes_configuration() -> None:
    with (
        patch("hermes_cli.config.load_config", return_value={}),
        patch("hermes_cli.mcp_startup.ensure_mcp_discovery_before_agent_build"),
        patch("run_agent.AIAgent", FakeAgent),
        patch.object(oneshot, "_create_session_db_for_oneshot", return_value=None),
        patch("tools.process_registry.process_registry.wait_for_pending_completions"),
    ):
        oneshot._run_agent("Bonjour", model="model-test", provider="custom", use_config_toolsets=False, use_config_fallbacks=False, runtime_base_url="https://llm.example.test/v1", runtime_api_key="secret-test")

    assert FakeAgent.created_kwargs["provider"] == "custom"
    assert FakeAgent.created_kwargs["base_url"] == "https://llm.example.test/v1"
    assert FakeAgent.created_kwargs["api_key"] == "secret-test"


def test_arc_openrouter_ignores_a_global_gemini_configuration() -> None:
    config = {
        "model": {"default": "gemini-old", "provider": "gemini"},
        "providers": {"openrouter": {"enabled": False}},
    }
    created = _run_arc(
        config, provider="openrouter", model="openrouter/model-test",
        base_url="https://openrouter.ai/api/v1", api_key="openrouter-secret",
    )
    assert created == {
        "api_key": "openrouter-secret",
        "api_mode": ANY,
        "base_url": "https://openrouter.ai/api/v1",
        "clarify_callback": ANY,
        "credential_pool": ANY,
        "enabled_toolsets": None,
        "ephemeral_system_prompt": None,
        "fallback_model": None,
        "model": "openrouter/model-test",
        "platform": "arcenal",
        "provider": "openrouter",
        "quiet_mode": True,
        "requested_provider": "openrouter",
        "session_db": None,
    }


def test_arc_codex_ignores_a_stale_disabled_hermes_provider() -> None:
    config = {"providers": {"openai-codex": {"enabled": False}}}
    credentials = {"api_key": "codex-access", "base_url": "https://chatgpt.com/backend-api/codex"}
    with patch("hermes_cli.runtime_provider.resolve_codex_runtime_credentials", return_value=credentials) as resolver:
        created = _run_arc(
            config, provider="openai-codex", model="gpt-codex-test",
            base_url=credentials["base_url"], api_key=None,
        )

    resolver.assert_called_once_with()
    assert created["provider"] == "openai-codex"
    assert created["api_key"] == "codex-access"
    assert created["platform"] == "arcenal"


def test_regular_runtime_still_rejects_a_disabled_provider() -> None:
    config = {"providers": {"openrouter": {"enabled": False}}}
    with patch("hermes_cli.config.load_config", return_value=config):
        with pytest.raises(ValueError, match="disabled in config"):
            oneshot._run_agent(
                "Bonjour", model="openrouter/model-test", provider="openrouter",
                use_config_toolsets=False, runtime_api_key="openrouter-secret",
            )
