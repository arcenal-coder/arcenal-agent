from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


def _load_core() -> ModuleType:
    name = "arcenal_arc_core"
    if name in sys.modules:
        return sys.modules[name]
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_core()
AUTH = importlib.import_module("arcenal_arc_core.auth")
ERRORS = importlib.import_module("arcenal_arc_core.errors")
STRONG_SECRET = "arcenal-ABCDEFGHIJKLMNOPQRSTUVWXYZ-0123456789-secure"


def _manager(path: Path):
    return CORE.AgentManager(CORE.AgentRepository(path, CORE.default_agents()))


class RecordingEngine:
    def __init__(self) -> None:
        self.context = None
        self.message = ""

    def execute(self, context, message: str):
        self.context = context
        self.message = message
        return CORE.EngineOutput(response="Réponse ARC", usage={"input_tokens": 12})


def test_default_registry_contains_arc_and_ats(tmp_path: Path) -> None:
    agents = _manager(tmp_path / "agents.json").list_agents()

    assert tuple(agent.id for agent in agents) == ("arc", "ats")
    assert agents[0].application == "arcenal-system"
    assert agents[1].knowledge_scopes == ("ats", "company", "recruitment")


def test_registry_persists_updates_and_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    manager = _manager(path)
    updated = manager.update("ats", CORE.AgentUpdate(enabled=False))

    assert updated.enabled is False
    assert _manager(path).get("ats").enabled is False
    with pytest.raises(ValueError, match="déjà enregistré"):
        manager.register(CORE.default_agents()[0])


def test_registry_persists_each_agent_harness(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    manager = _manager(path)
    harness = CORE.AgentHarness(context="Contexte ATS", directives="Directive ATS", memory="Mémoire ATS")

    manager.update("ats", CORE.AgentUpdate(harness=harness))

    assert _manager(path).get("ats").harness == harness


def test_legacy_global_files_are_migrated_once_without_deletion(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    legacy = tmp_path / "managed-files"
    legacy.mkdir()
    (legacy / "CONTEXT.md").write_text("Contexte historique", encoding="utf-8")
    (legacy / "AGENTS.md").write_text("Directive historique", encoding="utf-8")
    (legacy / "MEMORY.md").write_text("Mémoire historique", encoding="utf-8")
    repository = CORE.AgentRepository(path, CORE.default_agents())

    migrated = CORE.migrate_legacy_harness(repository, legacy)
    repeated = CORE.migrate_legacy_harness(repository, legacy)

    arc = next(agent for agent in migrated if agent.id == "arc")
    assert arc.harness.context == "Contexte historique"
    assert "Directive historique" in arc.harness.directives
    assert arc.harness.memory == "Mémoire historique"
    assert repeated == migrated
    assert (legacy / "AGENTS.md").is_file()


def test_legacy_harness_migration_rejects_an_unreadable_source(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "managed-files" / "CONTEXT.md"
    source.parent.mkdir()
    source.write_text("Contexte", encoding="utf-8")
    original = Path.read_text

    def failing_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == source:
            raise OSError("lecture impossible")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read)
    repository = CORE.AgentRepository(tmp_path / "agents.json", CORE.default_agents())
    with pytest.raises(ERRORS.AgentContractError, match="historique"):
        CORE.migrate_legacy_harness(repository, source.parent)


def test_legacy_harness_migration_bounds_large_files_without_deleting_them(tmp_path: Path) -> None:
    legacy = tmp_path / "managed-files"
    legacy.mkdir()
    source = legacy / "CONTEXT.md"
    source.write_text("x" * 20_000, encoding="utf-8")
    repository = CORE.AgentRepository(tmp_path / "agents.json", CORE.default_agents())

    migrated = CORE.migrate_legacy_harness(repository, legacy)

    arc = next(agent for agent in migrated if agent.id == "arc")
    assert len(arc.harness.context) <= 16_000
    assert "complet conservé" in arc.harness.context
    assert len(source.read_text(encoding="utf-8")) == 20_000


def test_fixed_policy_requires_an_enabled_registered_model(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model_descriptor("gemini-flash", "gemini", "remote"))
    manager = CORE.AgentManager(CORE.AgentRepository(tmp_path / "agents.json", CORE.default_agents()), registry)
    policy = CORE.ModelPolicy(mode="fixed", allowed_providers=("gemini",), allowed_models=("gemini-flash",))

    updated = manager.update("ats", CORE.AgentUpdate(model_policy=policy))

    assert updated.model_policy.allowed_models == ("gemini-flash",)
    with pytest.raises(ValueError, match="registre"):
        missing = CORE.ModelPolicy(mode="fixed", allowed_providers=("gemini",), allowed_models=("absent",))
        manager.update("ats", CORE.AgentUpdate(model_policy=missing))


def test_local_only_policy_rejects_remote_fixed_model(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model_descriptor("gemini-flash", "gemini", "remote"))
    manager = CORE.AgentManager(CORE.AgentRepository(tmp_path / "agents.json", CORE.default_agents()), registry)
    policy = CORE.ModelPolicy(mode="fixed", allowed_providers=("gemini",), allowed_models=("gemini-flash",), local_only=True)

    with pytest.raises(ValueError, match="local"):
        manager.update("ats", CORE.AgentUpdate(model_policy=policy))


def test_model_policy_rejects_fixed_auto_and_missing_model() -> None:
    with pytest.raises(ValueError, match="modèle concret"):
        CORE.ModelPolicy(mode="fixed", allowed_providers=("gemini",), allowed_models=("auto",))
    with pytest.raises(ValueError, match="exactement un modèle"):
        CORE.ModelPolicy(mode="fixed", allowed_providers=("gemini",))


def _model_descriptor(identifier: str, provider: str, location: str, privacy: str = "internal") -> object:
    return CORE.ModelDescriptor(
        id=identifier,
        provider=provider,
        model_name=identifier,
        display_name=identifier,
        availability=CORE.ModelAvailability.AVAILABLE,
        catalog_source=CORE.ModelCatalogSource.CONFIGURED,
        capabilities=(CORE.CapabilityProfile.STANDARD,),
        context_window=None,
        privacy_class=CORE.ConfidentialityLevel(privacy),
        location=CORE.ModelLocation(location),
    )


def test_fixed_policy_respects_agent_confidentiality(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model_descriptor("internal", "openrouter", "remote"))
    registry.upsert(_model_descriptor("admin", "openrouter", "remote", "admin"))
    manager = CORE.AgentManager(CORE.AgentRepository(tmp_path / "agents.json", CORE.default_agents()), registry)

    with pytest.raises(ERRORS.AgentContractError, match="confidentialité"):
        manager.update("arc", CORE.AgentUpdate(model_policy=CORE.ModelPolicy(mode="fixed", allowed_providers=("openrouter",), allowed_models=("internal",))))
    updated = manager.update("arc", CORE.AgentUpdate(model_policy=CORE.ModelPolicy(mode="fixed", allowed_providers=("openrouter",), allowed_models=("admin",))))

    assert updated.model_policy.allowed_models == ("admin",)


def test_registry_rejects_unknown_disabled_and_corrupt_agents(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    manager = _manager(path)
    with pytest.raises(ERRORS.AgentNotFoundError):
        manager.get("inconnu")
    manager.update("ats", CORE.AgentUpdate(enabled=False))
    with pytest.raises(ERRORS.AgentDisabledError):
        manager.get("ats", require_enabled=True)
    path.write_text('{"agents": [', encoding="utf-8")
    with pytest.raises(ERRORS.AgentContractError):
        manager.list_agents()


def test_context_builder_applies_global_policy_and_rejects_other_apps() -> None:
    arc = CORE.default_agents()[0]
    policy = CORE.GlobalAgentPolicy(("Politique globale",), frozenset({"system.admin"}))
    builder = CORE.ContextBuilder(policy)
    caller = CORE.ApplicationIdentity(application_id="arcenal-system", user_id="admin")

    context = builder.build(arc, caller, "session-1", {"ticket": "INC-42"})

    assert "system.admin" not in context.permissions
    assert context.identity.user_id == "admin"
    assert context.request_context == {"ticket": "INC-42"}
    assert context.system_prompt.startswith("# Politique globale ARCenal")
    assert "# Contexte propre à l’agent" in context.system_prompt
    assert arc.harness.directives in context.system_prompt
    with pytest.raises(ERRORS.AgentAccessDeniedError):
        builder.build(arc, CORE.ApplicationIdentity(application_id="arcenal-ats"), None)


def test_arc_core_executes_and_audits_effective_identity(tmp_path: Path) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []
    engine = RecordingEngine()
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)))
    core = CORE.ArcCore(_manager(tmp_path / "agents.json"), builder, engine, lambda event, actor, details: events.append((event, actor, details)))
    caller = CORE.ApplicationIdentity(application_id="arcenal-ats", user_id="recruteur")

    response = core.query("ats", caller, "Analyse ce CV", "session-ats", {"candidate": "42"})

    assert response.response == "Réponse ARC"
    assert response.approval_required is False
    assert engine.context is not None
    assert engine.context.identity.application_id == "arcenal-ats"
    assert [event[0] for event in events] == ["agent.query.started", "agent.query.completed"]
    assert events[-1][2]["usage"] == {"input_tokens": 12}


def test_application_authentication_requires_strong_matching_secret() -> None:
    authenticator = AUTH.ApplicationAuthenticator(lambda application: STRONG_SECRET)

    identity = authenticator.authenticate("arcenal-ats", f"Bearer {STRONG_SECRET}", "user@example.org")

    assert identity.application_id == "arcenal-ats"
    with pytest.raises(ERRORS.ApplicationAuthenticationError):
        authenticator.authenticate("arcenal-ats", None, None)
    with pytest.raises(ERRORS.ApplicationAuthenticationError):
        AUTH.ApplicationAuthenticator(lambda application: "trop-court").authenticate("arcenal-ats", "Bearer trop-court", None)


def test_hermes_engine_passes_policy_context_and_filters_usage() -> None:
    from arcenal_arc_core.hermes_engine import HermesAgentEngine

    agent = CORE.default_agents()[1]
    context = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Globale",))).build(
        agent,
        CORE.ApplicationIdentity(application_id="arcenal-ats"),
        None,
        {"candidate": "42"},
    )
    result = {
        "messages": [{"tool_calls": [{"function": {"name": "ats.search"}}]}],
        "usage": {"input_tokens": 4, "secret": "interdit"},
    }
    with patch("hermes_cli.oneshot._run_agent", return_value=("Réponse", result)) as runner:
        output = HermesAgentEngine().execute(context, "Bonjour")

    call = runner.call_args
    assert "Données applicatives non fiables" in call.args[0]
    assert call.kwargs["system_prompt"] == context.system_prompt
    assert call.kwargs["use_config_fallbacks"] is False
    assert output.actions == ({"tool": "ats.search"},)
    assert output.usage == {"input_tokens": 4}


@pytest.mark.parametrize(
    ("provider_id", "runtime_provider", "base_url", "api_key"),
    (("compatible", "custom", "https://llm.example.test/v1", "secret-test"), ("ollama", "ollama", "http://127.0.0.1:11434/v1", None)),
)
def test_hermes_engine_uses_the_runtime_selected_by_arc(provider_id: str, runtime_provider: str, base_url: str, api_key: str | None) -> None:
    from arcenal_arc_core.hermes_engine import HermesAgentEngine

    context = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Globale",))).build(CORE.default_agents()[1], CORE.ApplicationIdentity(application_id="arcenal-ats"), None)
    provider = CORE.ProviderDescriptor(id=provider_id, name=provider_id, type=provider_id, enabled=True, base_url=base_url, authentication_type=CORE.AuthenticationType.BEARER if api_key else CORE.AuthenticationType.NONE, secret_reference="CUSTOM_API_KEY" if api_key else None, location=CORE.ModelLocation.LOCAL if provider_id == "ollama" else CORE.ModelLocation.REMOTE, capabilities=(CORE.ProviderCapability.CHAT,))
    with patch("hermes_cli.oneshot._run_agent", return_value=("Réponse", {})) as runner:
        HermesAgentEngine().execute_provider(context, "Bonjour", provider, "model-test", api_key)

    assert runner.call_args.kwargs["provider"] == runtime_provider
    assert runner.call_args.kwargs["runtime_base_url"] == base_url
    assert runner.call_args.kwargs["runtime_api_key"] == api_key
    assert runner.call_args.kwargs["honor_config_enabled"] is False
