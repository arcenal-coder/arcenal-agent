from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import NoReturn, Protocol, cast

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


class ProviderLike(Protocol):
    id: str
    health: object
    secret_reference: str


class ProviderRegistryLike(Protocol):
    def upsert(self, provider: object) -> ProviderLike: ...

    def get(self, provider_id: str) -> ProviderLike | None: ...


class ModelRegistryLike(Protocol):
    def upsert(self, model: object) -> object: ...


class FakeAdapter:
    def __init__(self, failing: tuple[str, ...] = (), empty: tuple[str, ...] = (), unavailable: tuple[str, ...] = ()) -> None:
        self.failing = failing
        self.empty = empty
        self.unavailable = unavailable
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> object:
        provider_id = provider.id
        self.calls.append(provider_id)
        if provider_id in self.unavailable:
            raise RuntimeError("HTTP 503 (UNAVAILABLE): high demand")
        if provider_id in self.failing:
            raise RuntimeError("panne simulée")
        response = "" if provider_id in self.empty else f"{provider_id}:{message}"
        return CORE.EngineOutput(response=response, usage={"input_tokens": 4, "output_tokens": 2, "cost": 0.001})


def _provider(identifier: str, location: str, enabled: bool = True, health: str = "healthy", tools: bool = True) -> ProviderLike:
    capabilities = [CORE.ProviderCapability.CHAT, CORE.ProviderCapability.TOKEN_USAGE]
    if tools:
        capabilities.append(CORE.ProviderCapability.TOOL_CALLING)
    provider = CORE.ProviderDescriptor(id=identifier, name=identifier.title(), type=identifier, enabled=enabled, base_url=f"https://{identifier}.example.test/v1", authentication_type=CORE.AuthenticationType.BEARER, secret_reference=f"{identifier.upper()}_API_KEY", location=CORE.ModelLocation(location), jurisdiction="test", capabilities=tuple(capabilities), priority=10, health=CORE.ProviderHealth(health))
    return cast(ProviderLike, provider)


def _model(identifier: str, provider: str, location: str, priority: int = 10) -> object:
    return CORE.ModelDescriptor(id=identifier, provider=provider, model_name=f"model-{identifier}", capabilities=(CORE.CapabilityProfile.STANDARD,), context_window=32_000, supports_tools=True, supports_structured_output=False, privacy_class=CORE.ConfidentialityLevel.ADMIN, location=CORE.ModelLocation(location), priority=priority)


def _need(**updates: object) -> object:
    values = {"agent_id": "arc", "task_type": CORE.TaskType.GENERATION, "required_capability": CORE.CapabilityProfile.STANDARD, "confidentiality": CORE.ConfidentialityLevel.INTERNAL}
    return CORE.RoutingNeed(**{**values, **updates})


def _registries(tmp_path: Path) -> tuple[ProviderRegistryLike, ModelRegistryLike]:
    providers = CORE.ProviderRegistry(tmp_path / "providers.json")
    models = CORE.ModelRegistry(tmp_path / "models.json")
    return cast(ProviderRegistryLike, providers), cast(ModelRegistryLike, models)


def test_provider_registry_keeps_secrets_as_references(tmp_path: Path) -> None:
    providers, _models = _registries(tmp_path)
    saved = providers.upsert(_provider("openrouter", "remote"))

    content = (tmp_path / "providers.json").read_text(encoding="utf-8")
    assert saved.secret_reference == "OPENROUTER_API_KEY"
    assert "sk-" not in content
    assert "OPENROUTER_API_KEY" in content


def test_router_excludes_disabled_unavailable_and_incapable_providers(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("disabled", "remote", enabled=False))
    providers.upsert(_provider("down", "remote", health="unavailable"))
    providers.upsert(_provider("safe", "remote"))
    for identifier in ("disabled", "down", "safe"):
        models.upsert(_model(identifier, identifier, "remote"))

    decision = CORE.ModelRouter(models, providers=providers).route(_need())
    with pytest.raises(Exception, match="Aucun modèle activé"):
        CORE.ModelRouter(models, providers=providers).route(_need(tools_required=True, allowed_providers=("down",)))
    assert decision.provider == "safe"


def test_local_only_never_calls_remote_provider(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("remote", "openrouter", "remote"))

    with pytest.raises(Exception, match="Aucun modèle activé"):
        CORE.ModelRouter(models, providers=providers).route(_need(local_only=True))


def test_local_preference_and_secure_multi_provider_fallback(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("ollama", "local"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("qwen-local", "ollama", "local", priority=50))
    models.upsert(_model("qwen-remote", "openrouter", "remote", priority=1))
    decision = CORE.ModelRouter(models, providers=providers).route(_need(local_preferred=True))

    adapter = FakeAdapter(unavailable=("ollama",))
    executor = CORE.ProviderExecutor(adapter, retries=0, registry=providers)
    store = CORE.AutomationStore(tmp_path)
    engine = CORE.FrugalAgentEngine(adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, executor)
    output = engine.execute(_context(), "Rédige une réponse courte")

    assert decision.provider == "ollama"
    assert output.response == "openrouter:Rédige une réponse courte"
    assert output.usage["provider"] == "openrouter"
    assert output.usage["provider_failures"] == 1
    assert adapter.calls == ["ollama", "openrouter"]


def test_provider_executor_retries_once_and_rejects_empty_response(tmp_path: Path) -> None:
    providers, _models = _registries(tmp_path)
    provider = providers.upsert(_provider("openrouter", "remote"))
    adapter = FakeAdapter(empty=("openrouter",))

    with pytest.raises(Exception, match="indisponible"):
        CORE.ProviderExecutor(adapter, retries=1, registry=providers, retry_delay_seconds=0).execute(_context(), "bonjour", provider, "small")
    assert adapter.calls == ["openrouter", "openrouter"]
    current_provider = providers.get("openrouter")
    assert current_provider is not None
    assert current_provider.health is CORE.ProviderHealth.DEGRADED


def test_provider_executor_observes_rate_limit_and_stops_after_retry(tmp_path: Path) -> None:
    providers, _models = _registries(tmp_path)
    provider = providers.upsert(_provider("openrouter", "remote"))

    with pytest.raises(CORE.ProviderExecutionError) as captured:
        CORE.ProviderExecutor(RateLimitedAdapter(), retries=1, registry=providers, retry_delay_seconds=0).execute(_context(), "bonjour", provider, "small")
    assert [attempt.status for attempt in captured.value.attempts] == ["rate_limited", "rate_limited"]


def test_provider_executor_classifies_gemini_503_as_unavailable(tmp_path: Path) -> None:
    providers, _models = _registries(tmp_path)
    provider = providers.upsert(_provider("gemini", "remote"))

    with pytest.raises(CORE.ProviderExecutionError) as captured:
        CORE.ProviderExecutor(UnavailableAdapter(), retries=0, registry=providers).execute(_context(), "bonjour", provider, "gemini-flash")

    assert captured.value.attempts[0].status == "unavailable"
    assert "high demand" not in str(captured.value)


def test_auto_mode_falls_back_after_gemini_503(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("gemini", "remote"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("gemini-fast", "gemini", "remote", priority=1))
    models.upsert(_model("openrouter-fast", "openrouter", "remote", priority=2))
    adapter = FakeAdapter(unavailable=("gemini",))
    store = CORE.AutomationStore(tmp_path)
    engine = CORE.FrugalAgentEngine(adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, CORE.ProviderExecutor(adapter, retries=0, registry=providers))

    output = engine.execute(_context(), "Rédige une réponse courte")

    assert output.usage["provider"] == "openrouter"
    assert adapter.calls == ["gemini", "openrouter"]


def test_auto_mode_falls_back_after_gemini_textual_429(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("gemini", "remote"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("gemini-fast", "gemini", "remote", priority=1))
    models.upsert(_model("openrouter-fast", "openrouter", "remote", priority=2))
    adapter = TextualRateLimitThenSuccessAdapter()
    store = CORE.AutomationStore(tmp_path)
    executor = CORE.ProviderExecutor(adapter, retries=0, registry=providers)
    engine = CORE.FrugalAgentEngine(adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, executor)

    output = engine.execute(_context(), "Rédige une réponse courte")

    assert output.usage["provider"] == "openrouter"
    assert adapter.calls == ["gemini", "openrouter"]


@pytest.mark.parametrize("adapter", ["authentication", "configuration"])
def test_auto_mode_never_falls_back_on_non_temporary_provider_errors(tmp_path: Path, adapter: str) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("gemini", "remote"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("gemini-fast", "gemini", "remote", priority=1))
    models.upsert(_model("openrouter-fast", "openrouter", "remote", priority=2))
    selected_adapter = AuthenticationAdapter() if adapter == "authentication" else ConfigurationAdapter()
    store = CORE.AutomationStore(tmp_path)
    executor = CORE.ProviderExecutor(selected_adapter, retries=1, registry=providers, retry_delay_seconds=0)
    engine = CORE.FrugalAgentEngine(selected_adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, executor)

    with pytest.raises(CORE.ProviderExecutionError) as captured:
        engine.execute(_context(), "Rédige une réponse courte")

    assert captured.value.code == adapter
    assert selected_adapter.calls == ["gemini"]


def test_wrapped_authentication_error_takes_priority_over_unavailable_message(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("gemini", "remote"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("gemini-fast", "gemini", "remote", priority=1))
    models.upsert(_model("openrouter-fast", "openrouter", "remote", priority=2))
    adapter = WrappedAuthenticationAdapter()
    store = CORE.AutomationStore(tmp_path)
    executor = CORE.ProviderExecutor(adapter, retries=0, registry=providers)
    engine = CORE.FrugalAgentEngine(adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, executor)

    with pytest.raises(CORE.ProviderExecutionError) as captured:
        engine.execute(_context(), "Rédige une réponse courte")

    assert captured.value.code == "authentication"
    assert adapter.calls == ["gemini"]


def test_auto_mode_falls_back_after_provider_timeout(tmp_path: Path) -> None:
    providers, models = _registries(tmp_path)
    providers.upsert(_provider("gemini", "remote"))
    providers.upsert(_provider("openrouter", "remote"))
    models.upsert(_model("gemini-fast", "gemini", "remote", priority=1))
    models.upsert(_model("openrouter-fast", "openrouter", "remote", priority=2))
    adapter = TimeoutThenSuccessAdapter()
    store = CORE.AutomationStore(tmp_path)
    executor = CORE.ProviderExecutor(adapter, retries=0, registry=providers)
    engine = CORE.FrugalAgentEngine(adapter, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(models, providers=providers), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store), providers, executor)

    output = engine.execute(_context(), "Rédige une réponse courte")

    assert output.usage["provider"] == "openrouter"
    assert adapter.calls == ["gemini", "openrouter"]


def test_runtime_enables_provider_from_process_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret-never-persisted")
    runtime = CORE.FrugalRuntime(tmp_path)
    runtime.ensure_providers()

    assert runtime.providers.get("openrouter").enabled is True
    assert "test-secret-never-persisted" not in (tmp_path / "provider-registry.json").read_text(encoding="utf-8")


def test_runtime_exposes_groq_without_persisting_its_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "groq-secret-never-persisted")
    runtime = CORE.FrugalRuntime(tmp_path)
    runtime.ensure_providers()

    provider = runtime.providers.get("groq")
    assert provider is not None
    assert provider.enabled is True
    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.secret_reference == "GROQ_API_KEY"
    assert "groq-secret-never-persisted" not in (tmp_path / "provider-registry.json").read_text(encoding="utf-8")


def test_runtime_reconciles_provider_after_native_configuration_changes(tmp_path: Path) -> None:
    config = CORE.ArcNativeConfigStore(tmp_path / "config.json")
    vault = CORE.ArcFileVault(tmp_path / ".env")
    runtime = CORE.FrugalRuntime(tmp_path / "frugal", CORE.ArcRuntimeConfiguration(config, vault))
    runtime.ensure_providers()
    config.set("providers", "openrouter", {"enabled": True, "base_url": "https://router.example.test/v1"})
    vault.set_secret("OPENROUTER_API_KEY", "secret-test")

    runtime.ensure_providers()

    provider = runtime.providers.get("openrouter")
    assert provider is not None
    assert provider.enabled is True
    assert provider.base_url == "https://router.example.test/v1"


class RateLimitedAdapter:
    def execute(self, context: object, message: str, provider: object, model: str) -> NoReturn:
        raise CORE.ProviderExecutionError("limite simulée", "rate_limited")


class UnavailableAdapter:
    def execute(self, context: object, message: str, provider: object, model: str) -> NoReturn:
        raise RuntimeError("Gemini HTTP 503 (UNAVAILABLE): high demand api_key=secret-test")


class ProviderHttpError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> NoReturn:
        self.calls.append(provider.id)
        raise ProviderHttpError("HTTP 401: invalid API key secret-test", 401)


class ConfigurationAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> NoReturn:
        self.calls.append(provider.id)
        raise ProviderHttpError("HTTP 404: model missing", 404)


class TextualRateLimitThenSuccessAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> object:
        self.calls.append(provider.id)
        if provider.id == "gemini":
            raise RuntimeError("Gemini HTTP 429 (RESOURCE_EXHAUSTED): quota exceeded")
        return CORE.EngineOutput(response="Réponse de repli", usage={})


class WrappedAuthenticationAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> NoReturn:
        self.calls.append(provider.id)
        cause = ProviderHttpError("HTTP 401: invalid API key secret-test", 401)
        raise RuntimeError("temporarily unavailable wrapper") from cause


class TimeoutThenSuccessAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context: object, message: str, provider: ProviderLike, model: str) -> object:
        self.calls.append(provider.id)
        if provider.id == "gemini":
            raise TimeoutError("provider timeout")
        return CORE.EngineOutput(response="Réponse de repli", usage={})


def _context() -> object:
    agent = CORE.default_agents()[0]
    caller = CORE.ApplicationIdentity(application_id=agent.application, user_id="admin", user_source=CORE.UserIdentitySource.YUNOHOST)
    return CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",))).build(agent, caller, None, {}, "demande")
