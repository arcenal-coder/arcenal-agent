"""Adaptation générique entre ARC et la couche d’inférence Hermes."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter, sleep
from typing import Protocol

from .errors import ProviderExecutionError
from .models import EffectiveContext, EngineOutput
from .provider_models import ProviderAttempt, ProviderDescriptor, ProviderHealth
from .provider_registry import ProviderRegistry


class ProviderAdapter(Protocol):
    def execute(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str) -> EngineOutput: ...


class ProviderAwareAgentEngine(Protocol):
    def execute_provider(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str, api_key: str | None) -> EngineOutput: ...


class HermesProviderAdapter:
    """Traduit un choix ARC en paramètres Hermes, sans décision métier."""

    def __init__(self, engine: ProviderAwareAgentEngine, secret_resolver: Callable[[str], str | None]) -> None:
        self._engine = engine
        self._secret_resolver = secret_resolver

    def execute(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str) -> EngineOutput:
        api_key = self._secret_resolver(provider.secret_reference) if provider.secret_reference else None
        output = self._engine.execute_provider(context, message, provider, model, api_key)
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
            if result[2] is not None and not result[2].retryable:
                raise ProviderExecutionError(str(result[2]), result[2].code, tuple(attempts))
            if attempt <= self._retries:
                sleep(self._retry_delay_seconds)
        self._set_health(provider.id, ProviderHealth.DEGRADED)
        code = result[2].code if result[2] is not None else "unavailable"
        raise ProviderExecutionError("Le fournisseur IA est indisponible après une nouvelle tentative.", code, tuple(attempts))

    def _set_health(self, provider_id: str, health: ProviderHealth) -> None:
        if self._registry is not None:
            self._registry.update_health(provider_id, health)

    def _attempt(self, context: EffectiveContext, message: str, provider: ProviderDescriptor, model: str, attempt: int) -> tuple[EngineOutput | None, ProviderAttempt, ProviderExecutionError | None]:
        started = perf_counter()
        try:
            output = self._adapter.execute(context, message, provider, model)
            if not output.response.strip():
                raise ProviderExecutionError("Le fournisseur a retourné une réponse vide.", "invalid_response")
        except Exception as exc:
            error = _provider_error(exc)
            return None, self._trace(provider.id, model, attempt, error.code, started), error
        return output, self._trace(provider.id, model, attempt, "success", started), None

    def _trace(self, provider: str, model: str, attempt: int, status: str, started: float) -> ProviderAttempt:
        accepted = {"success", "failed", "rate_limited", "timeout", "unavailable", "invalid_response", "authentication", "configuration"}
        normalized = status if status in accepted else "failed"
        error_code = None if normalized == "success" else normalized
        return ProviderAttempt(provider=provider, model=model, attempt=attempt, status=normalized, duration_ms=(perf_counter() - started) * 1_000, error_code=error_code)


def provider_is_available(provider: ProviderDescriptor) -> bool:
    return provider.enabled and provider.health is not ProviderHealth.UNAVAILABLE


def _provider_error(exc: Exception) -> ProviderExecutionError:
    if isinstance(exc, ProviderExecutionError):
        return exc
    chain = _error_chain(exc)
    explicit_error = _explicit_provider_error(chain)
    if explicit_error is not None:
        return explicit_error
    for error in chain:
        if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.casefold():
            return ProviderExecutionError("Le fournisseur n’a pas répondu dans le délai imparti.", "timeout")
        if _looks_rate_limited(error):
            return ProviderExecutionError("Le fournisseur limite temporairement les requêtes.", "rate_limited")
        if _looks_unavailable(error):
            return ProviderExecutionError("Le fournisseur est temporairement indisponible.", "unavailable")
    return ProviderExecutionError("Échec contrôlé du fournisseur IA.", "failed")


def _error_chain(error: BaseException) -> tuple[BaseException, ...]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__
    return tuple(chain)


def _explicit_provider_error(chain: tuple[BaseException, ...]) -> ProviderExecutionError | None:
    statuses = tuple(getattr(error, "status_code", None) for error in chain)
    if any(status in {401, 403} for status in statuses):
        return ProviderExecutionError("Le fournisseur a refusé l’authentification.", "authentication")
    if any(status in {400, 404, 405, 409, 422} for status in statuses):
        return ProviderExecutionError("La configuration du fournisseur est invalide.", "configuration")
    if 429 in statuses:
        return ProviderExecutionError("Le fournisseur limite temporairement les requêtes.", "rate_limited")
    if any(status in {500, 502, 503, 504} for status in statuses):
        return ProviderExecutionError("Le fournisseur est temporairement indisponible.", "unavailable")
    return None


def _looks_rate_limited(error: BaseException) -> bool:
    message = str(error).casefold()
    markers = ("http 429", "resource_exhausted", "rate limit", "too many requests", "quota exceeded")
    return any(marker in message for marker in markers)


def _looks_unavailable(error: BaseException) -> bool:
    message = str(error).casefold()
    markers = ("http 503", "unavailable", "high demand", "temporarily unavailable")
    return any(marker in message for marker in markers)
