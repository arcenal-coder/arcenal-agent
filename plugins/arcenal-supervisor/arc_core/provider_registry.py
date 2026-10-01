"""Registre persistant des fournisseurs, sans stockage de secrets."""

from __future__ import annotations

from pathlib import Path

from .frugal_store import JsonCollectionStore
from .provider_models import ProviderDescriptor, ProviderHealth


class ProviderRegistry:
    def __init__(self, path: Path) -> None:
        self._store = JsonCollectionStore(path, ProviderDescriptor, "providers")

    def list(self) -> tuple[ProviderDescriptor, ...]:
        return self._store.load()

    def get(self, provider_id: str) -> ProviderDescriptor | None:
        return next((item for item in self.list() if item.id == provider_id), None)

    def upsert(self, provider: ProviderDescriptor) -> ProviderDescriptor:
        values = tuple(item for item in self.list() if item.id != provider.id)
        self._store.save((*values, provider))
        return provider

    def remove(self, provider_id: str) -> None:
        self._store.save(tuple(item for item in self.list() if item.id != provider_id))

    def update_health(self, provider_id: str, health: ProviderHealth) -> ProviderDescriptor:
        provider = self.get(provider_id)
        if provider is None:
            raise LookupError("Fournisseur introuvable.")
        return self.upsert(provider.model_copy(update={"health": health}))
