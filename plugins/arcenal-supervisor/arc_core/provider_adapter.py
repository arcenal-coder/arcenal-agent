"""Adaptation générique entre ARC et la couche d’inférence Hermes."""

from __future__ import annotations

from time import perf_counter, sleep
from typing import Protocol

from .errors import ProviderExecutionError
from .models import EffectiveContext, EngineOutput
from .provider_models import ProviderAttempt, ProviderDescriptor, ProviderHealth
from .provider_registry import ProviderRegistry
from .service import AgentEngine


class ProviderAdapter(Protocol):
    def execute(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str) -> EngineOutput: ...


class HermesProviderAdapter:
    """Traduit un choix ARC en paramètres Hermes, sans décision métier."""

    def __init__(self, engine: AgentEngine) -> None:
        self._engine = engine

    def execute(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str) -> EngineOutput:
        policy = context.model_policy.model_copy(update={"allowed_providers": (provider.id,), "allowed_models": (model,)})
        routed = context.model_copy(update={"model_policy": policy})
        output = self._engine.execute(routed, message)
        if not output.response.strip():
            raise ProviderExecutionError("Le fournisseur a retourné une réponse vide.", "invalid_response")
        return output


class ProviderExecutor:
    def __init__(self, adapter: ProviderAdapter, retries: int = 1, registry: ProviderRegistry | None = None, retry_delay_seconds: float = 0.2) -> None:
        self._adapter = adapter
        self._retries = max(0, min(retries, 1))
        self._registry = registry
        self._retry_delay_seconds = max(0.0, min(retry_delay_seconds, 1.0))

    def execute(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str) -> tuple[EngineOutput, tuple[ProviderAttempt, ...]]:
        attempts: list[ProviderAttempt] = []
        for attempt in range(1, self._retries + 2):
            result = self._attempt(context, message, provider, model, attempt)
            attempts.append(result[1])
            if result[0] is not None:
                self._set_health(provider.id, ProviderHealth.HEALTHY)
                return result[0], tuple(attempts)
            if attempt <= self._retries:
                sleep(self._retry_delay_seconds)
        self._set_health(provider.id, ProviderHealth.DEGRADED)
        raise ProviderExecutionError("Le fournisseur IA est indisponible après une nouvelle tentative.", "unavailable", tuple(attempts))

    def _set_health(self, provider_id: str, health: ProviderHealth) -> None:
        if self._registry is not None:
            self._registry.update_health(provider_id, health)

    def _attempt(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str, attempt: int) -> tuple[EngineOutput | None, ProviderAttempt]:
        started = perf_counter()
        try:
            output = self._adapter.execute(context, message, provider, model)
            if not output.response.strip():
                raise ProviderExecutionError("Le fournisseur a retourné une réponse vide.", "invalid_response")
        except Exception as exc:
            error = _provider_error(exc)
            return None, self._trace(provider.id, model, attempt, error.code, started)
        return output, self._trace(provider.id, model, attempt, "success", started)

    def _trace(self, provider: str, model: str, attempt: int, status: str, started: float) -> ProviderAttempt:
        normalized = status if status in {"success", "failed", "rate_limited", "timeout", "invalid_response"} else "failed"
        error_code = None if normalized == "success" else normalized
        return ProviderAttempt(provider=provider, model=model, attempt=attempt, status=normalized, duration_ms=(perf_counter() - started) * 1_000, error_code=error_code)


def provider_is_available(provider: ProviderDescriptor) -> bool:
    return provider.enabled and provider.health is not ProviderHealth.UNAVAILABLE


def _provider_error(exc: Exception) -> ProviderExecutionError:
    if isinstance(exc, ProviderExecutionError):
        return exc
    chain: BaseException | None = exc
    while chain is not None:
        status = getattr(chain, "status_code", None)
        if status == 429:
            return ProviderExecutionError("Le fournisseur limite temporairement les requêtes.", "rate_limited")
        if isinstance(chain, TimeoutError) or "timeout" in type(chain).__name__.casefold():
            return ProviderExecutionError("Le fournisseur n’a pas répondu dans le délai imparti.", "timeout")
        chain = chain.__cause__
    return ProviderExecutionError("Échec contrôlé du fournisseur IA.", "failed")
