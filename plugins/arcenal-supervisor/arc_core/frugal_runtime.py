"""Assemblage persistant d'ARC Frugal pour l'application YunoHost."""

from __future__ import annotations

from pathlib import Path

from .automation_engine import AutomationStore, ProcessObserver, WorkflowEngine
from .deterministic_engine import DeterministicEngine
from .frugal_cache import FrugalCache
from .frugal_engine import FrugalAgentEngine
from .frugal_metrics import FrugalMetricsRepository
from .frugal_models import ModelLocation
from .hermes_engine import HermesAgentEngine
from .model_router import ModelRegistry, ModelRouter
from .provider_adapter import HermesProviderAdapter, ProviderExecutor
from .provider_models import AuthenticationType, ProviderCapability, ProviderDescriptor, ProviderHealth
from .provider_registry import ProviderRegistry
from .configuration_runtime import ArcRuntimeConfiguration, runtime_configuration


class FrugalRuntime:
    def __init__(self, root: Path, configuration: ArcRuntimeConfiguration | None = None) -> None:
        self.configuration = configuration or runtime_configuration()
        self.registry = ModelRegistry(root / "model-registry.json")
        self.providers = ProviderRegistry(root / "provider-registry.json")
        self.cache = FrugalCache(root / "frugal-cache.json")
        self.metrics = FrugalMetricsRepository(root / "frugal-measurements.json")
        self.automations = AutomationStore(root)
        hermes = HermesAgentEngine()
        router = ModelRouter(self.registry, providers=self.providers)
        adapter = HermesProviderAdapter(hermes, self.configuration.vault.get_secret)
        executor = ProviderExecutor(adapter, registry=self.providers)
        self.engine = FrugalAgentEngine(hermes, DeterministicEngine(), self.cache, WorkflowEngine(self.automations), router, self.metrics, ProcessObserver(self.automations), self.providers, executor)

    def ensure_configured_model(self) -> None:
        self.ensure_providers()

    def ensure_providers(self) -> None:
        existing = {item.id: item for item in self.providers.list()}
        for configured in _default_providers(self.configuration):
            current = existing.get(configured.id)
            self.providers.upsert(_reconciled_provider(configured, current))


def _reconciled_provider(configured: ProviderDescriptor, current: ProviderDescriptor | None) -> ProviderDescriptor:
    if current is None:
        return configured
    return configured.model_copy(update={
        "health": current.health,
        "jurisdiction": current.jurisdiction,
        "priority": current.priority,
    })


def _default_providers(configuration: ArcRuntimeConfiguration) -> tuple[ProviderDescriptor, ...]:
    common = (ProviderCapability.CHAT, ProviderCapability.STREAMING, ProviderCapability.STRUCTURED_OUTPUT, ProviderCapability.TOOL_CALLING, ProviderCapability.VISION, ProviderCapability.TOKEN_USAGE)
    return (
        _provider(configuration, "openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", ModelLocation.REMOTE, common + (ProviderCapability.COST_REPORTING,), 100),
        _codex_provider(configuration, common, 150),
        _provider(configuration, "openai", "OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY", ModelLocation.REMOTE, common + (ProviderCapability.EMBEDDINGS, ProviderCapability.COST_REPORTING), 200),
        _provider(configuration, "gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", ModelLocation.REMOTE, common + (ProviderCapability.EMBEDDINGS,), 300),
        _provider(configuration, "anthropic", "Anthropic", "https://api.anthropic.com", "ANTHROPIC_API_KEY", ModelLocation.REMOTE, common, 400),
        _provider(configuration, "mistral", "Mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", ModelLocation.REMOTE, common, 450),
        _provider(configuration, "groq", "Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", ModelLocation.REMOTE, common, 475),
        _provider(configuration, "ollama", "Ollama", "http://127.0.0.1:11434/v1", None, ModelLocation.LOCAL, common + (ProviderCapability.EMBEDDINGS,), 10),
        _provider(configuration, "vllm", "vLLM", "http://127.0.0.1:8000/v1", None, ModelLocation.LOCAL, common, 20),
        _provider(configuration, "compatible", "Endpoint compatible OpenAI", "", "OPENAI_COMPATIBLE_API_KEY", ModelLocation.REMOTE, common, 500),
        _provider(configuration, "internal", "Fournisseur interne", "", "ARCENAL_INTERNAL_LLM_API_KEY", ModelLocation.LOCAL, common, 550),
    )


def _codex_provider(configuration: ArcRuntimeConfiguration, capabilities: tuple[ProviderCapability, ...], priority: int) -> ProviderDescriptor:
    return ProviderDescriptor(
        id="openai-codex", name="OpenAI Codex", type="openai-codex",
        enabled=_codex_enabled(configuration), base_url="https://chatgpt.com/backend-api/codex",
        authentication_type=AuthenticationType.OAUTH, secret_reference=None,
        location=ModelLocation.REMOTE, jurisdiction=None,
        capabilities=capabilities, priority=priority, health=ProviderHealth.UNKNOWN,
    )


def _codex_enabled(configuration: ArcRuntimeConfiguration) -> bool:
    configured = configuration.config.get("providers", "openai-codex", {})
    if isinstance(configured, dict) and configured.get("enabled") is False:
        return False
    from hermes_cli.auth import get_codex_auth_status

    return bool(get_codex_auth_status().get("logged_in"))


def _provider(configuration: ArcRuntimeConfiguration, provider_id: str, name: str, base_url: str, secret: str | None, location: ModelLocation, capabilities: tuple[ProviderCapability, ...], priority: int) -> ProviderDescriptor:
    configured = _provider_enabled(configuration, provider_id, secret)
    authentication = AuthenticationType.BEARER if secret else AuthenticationType.NONE
    resolved_url = _provider_url(configuration, provider_id, base_url)
    return ProviderDescriptor(id=provider_id, name=name, type=provider_id, enabled=configured, base_url=resolved_url, authentication_type=authentication, secret_reference=secret, location=location, jurisdiction=None, capabilities=capabilities, priority=priority, health=ProviderHealth.UNKNOWN)


def _provider_url(configuration: ArcRuntimeConfiguration, provider_id: str, default: str) -> str:
    configured = configuration.config.get("providers", provider_id, {})
    if not isinstance(configured, dict):
        return default
    value = configured.get("base_url")
    return value if isinstance(value, str) else default


def _provider_enabled(configuration: ArcRuntimeConfiguration, provider_id: str, secret: str | None) -> bool:
    configured = configuration.config.get("providers", provider_id, {})
    if isinstance(configured, dict) and isinstance(configured.get("enabled"), bool):
        return configured["enabled"] and configuration.provider_enabled(provider_id, secret)
    if secret is not None:
        return configuration.provider_enabled(provider_id, secret)
    return provider_id == "ollama"
