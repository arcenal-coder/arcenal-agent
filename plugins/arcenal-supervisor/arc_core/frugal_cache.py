"""Cache exact et sémantique cloisonné par contexte et permissions."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .frugal_models import CacheDependency, CachedResponse, CacheValidation
from .frugal_store import JsonCollectionStore
from .models import EffectiveContext, EngineOutput


class FrugalCache:
    def __init__(self, path: Path, semantic_threshold: float = 0.9) -> None:
        if not 0.5 <= semantic_threshold <= 1:
            raise ValueError("Le seuil sémantique doit être compris entre 0,5 et 1.")
        self._store = JsonCollectionStore(path, CachedResponse, "responses")
        self._threshold = semantic_threshold

    def lookup(self, context: EffectiveContext, message: str) -> tuple[EngineOutput, str] | None:
        now = datetime.now(timezone.utc)
        candidates = tuple(item for item in self._store.load() if self._authorized(item, context, now))
        exact = next((item for item in candidates if item.id == self._key(context, message)), None)
        selected = exact or self._semantic(candidates, message)
        if selected is None:
            return None
        usage = {"cache_validation": selected.validation.value, "provider": selected.provider or "", "model": selected.model or "", "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        return EngineOutput(response=selected.response, usage=usage), "exact" if exact else "semantic"

    def store(self, context: EffectiveContext, message: str, output: EngineOutput, validated: bool = False) -> None:
        item = self._entry(context, message, output, validated)
        values = tuple(value for value in self._store.load() if value.id != item.id)
        self._store.save((*values, item))

    def validate(self, cache_id: str) -> CachedResponse:
        values = self._store.load()
        current = next((item for item in values if item.id == cache_id), None)
        if current is None:
            raise LookupError("Réponse cachée introuvable.")
        updated = current.model_copy(update={"validation": CacheValidation.VALIDATED})
        self._store.save(tuple(updated if item.id == cache_id else item for item in values))
        return updated

    def invalidate(self, kind: str, identifier: str) -> int:
        values = self._store.load()
        retained = tuple(item for item in values if not self._depends_on(item, kind, identifier))
        self._store.save(retained)
        return len(values) - len(retained)

    def list(self) -> tuple[CachedResponse, ...]:
        return self._store.load()

    def _authorized(self, item: CachedResponse, context: EffectiveContext, now: datetime) -> bool:
        signatures = (
            item.agent_id == context.agent.id,
            item.application_id == context.identity.application_id,
            item.permission_signature == _permission_signature(context),
            item.context_signature == _context_signature(context),
            item.knowledge_signature == _knowledge_signature(context),
            item.expires_at > now,
        )
        return all(signatures)

    def _semantic(self, candidates: tuple[CachedResponse, ...], message: str) -> CachedResponse | None:
        validated = (item for item in candidates if item.validation is CacheValidation.VALIDATED)
        scored = tuple((self._similarity(item.request_normalized, message), item) for item in validated)
        eligible = tuple(pair for pair in scored if pair[0] >= self._threshold)
        return max(eligible, default=(0.0, None), key=lambda pair: pair[0])[1]

    def _similarity(self, left: str, right: str) -> float:
        left_tokens = _tokens(left)
        right_tokens = _tokens(right)
        union = left_tokens | right_tokens
        return len(left_tokens & right_tokens) / len(union) if union else 0

    def _entry(self, context: EffectiveContext, message: str, output: EngineOutput, validated: bool) -> CachedResponse:
        now = datetime.now(timezone.utc)
        usage = output.usage
        return CachedResponse(id=self._key(context, message), agent_id=context.agent.id, application_id=context.identity.application_id, request_normalized=_normalize(message), context_signature=_context_signature(context), knowledge_signature=_knowledge_signature(context), permission_signature=_permission_signature(context), response=output.response, validation=CacheValidation.VALIDATED if validated else CacheValidation.GENERATED, dependencies=_dependencies(context, usage), provider=_optional_string(usage.get("provider")), model=_optional_string(usage.get("model")), input_tokens=_integer(usage.get("input_tokens")), output_tokens=_integer(usage.get("output_tokens")), cost=_number(usage.get("cost")), created_at=now, expires_at=now + timedelta(hours=24 if validated else 1))

    def _key(self, context: EffectiveContext, message: str) -> str:
        parts = (context.agent.id, _normalize(message), _context_signature(context), _knowledge_signature(context), _permission_signature(context))
        return hashlib.sha256("\0".join(parts).encode()).hexdigest()

    def _depends_on(self, item: CachedResponse, kind: str, identifier: str) -> bool:
        return any(value.kind == kind and value.identifier == identifier for value in item.dependencies)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> frozenset[str]:
    return frozenset(re.findall(r"[\wà-ÿ]+", _normalize(value)))


def _signature(values: tuple[str, ...]) -> str:
    return hashlib.sha256("\0".join(sorted(values)).encode()).hexdigest()


def _permission_signature(context: EffectiveContext) -> str:
    return _signature(tuple(context.permissions))


def _context_signature(context: EffectiveContext) -> str:
    values = tuple(f"{key}={value}" for key, value in sorted(context.request_context.items()))
    return _signature(values)


def _knowledge_signature(context: EffectiveContext) -> str:
    values = tuple(f"{source.source_id}:{source.version}" for source in context.sources)
    return _signature(values)


def _dependencies(context: EffectiveContext, usage: dict[str, bool | int | float | str]) -> tuple[CacheDependency, ...]:
    sources = tuple(CacheDependency(kind="knowledge", identifier=item.source_id, version=item.version) for item in context.sources)
    model_id = _optional_string(usage.get("registry_id"))
    model = (CacheDependency(kind="model", identifier=model_id, version="1"),) if model_id else ()
    return (*sources, *model, CacheDependency(kind="agent", identifier=context.agent.id, version="1"), CacheDependency(kind="acl", identifier=_permission_signature(context), version="1"))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
