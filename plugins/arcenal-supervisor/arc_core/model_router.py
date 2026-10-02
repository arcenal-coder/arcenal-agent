"""Registre et sélection déterministe des modèles autorisés."""

from __future__ import annotations

from pathlib import Path

from .errors import ModelRoutingError
from .frugal_models import CapabilityProfile, ModelAvailability, ModelDescriptor, ModelLocation, RoutingDecision, RoutingNeed
from .frugal_store import JsonCollectionStore
from .provider_models import ProviderCapability, ProviderHealth
from .provider_registry import ProviderRegistry


class ModelRegistry:
    def __init__(self, path: Path) -> None:
        self._store = JsonCollectionStore(path, ModelDescriptor, "models")

    def list(self) -> tuple[ModelDescriptor, ...]:
        return self._store.load()

    def upsert(self, model: ModelDescriptor) -> ModelDescriptor:
        values = tuple(item for item in self.list() if item.id != model.id)
        self._store.save((*values, model))
        return model

    def remove(self, model_id: str) -> None:
        values = tuple(item for item in self.list() if item.id != model_id)
        self._store.save(values)

    def get(self, model_id: str) -> ModelDescriptor | None:
        return next((item for item in self.list() if item.id == model_id), None)


class ModelRouter:
    def __init__(self, registry: ModelRegistry, allowed_providers: tuple[str, ...] = (), denied_providers: tuple[str, ...] = (), local_only: bool = False, providers: ProviderRegistry | None = None) -> None:
        self._registry = registry
        self._allowed_providers = allowed_providers
        self._denied_providers = denied_providers
        self._local_only = local_only
        self._providers = providers

    def model(self, model_id: str) -> ModelDescriptor | None:
        return self._registry.get(model_id)

    def route(self, need: RoutingNeed) -> RoutingDecision:
        registered = self._registry.list()
        if not registered:
            raise ModelRoutingError("Aucun modèle n’est enregistré dans ARC. Connectez un fournisseur puis attribuez un modèle à l’agent.")
        eligible = tuple(item for item in registered if self._eligible(item, need))
        relaxed = self._relaxed_capability(need) if not eligible else None
        if relaxed is not None:
            eligible = tuple(item for item in registered if self._eligible(item, need, relaxed))
        if not eligible:
            raise ModelRoutingError("Aucun modèle activé ne respecte la capacité et la confidentialité requises.")
        ranked = tuple(sorted(eligible, key=lambda item: self._rank(item, need)))
        selected = ranked[0]
        return self._decision(selected, ranked[1:], need, relaxed)

    def _eligible(self, model: ModelDescriptor, need: RoutingNeed, capability: CapabilityProfile | None = None) -> bool:
        checks = (
            model.enabled,
            model.availability is not ModelAvailability.UNAVAILABLE,
            (capability or need.required_capability) in model.capabilities,
            model.context_window is None or model.context_window >= need.context_size,
            not need.tools_required or model.supports_tools,
            not need.structured_output or model.supports_structured_output,
            not need.vision_required or model.supports_vision,
            not need.local_only or model.location is ModelLocation.LOCAL,
            not self._local_only or model.location is ModelLocation.LOCAL,
            not self._allowed_providers or model.provider in self._allowed_providers,
            model.provider not in self._denied_providers,
            not need.allowed_providers or model.provider in need.allowed_providers,
            model.provider not in need.denied_providers,
            not need.allowed_models or model.id in need.allowed_models or model.model_name in need.allowed_models,
            need.max_cost is None or model.input_cost + model.output_cost <= need.max_cost,
            self._privacy_allows(model, need),
            self._provider_allows(model, need),
        )
        return all(checks)

    def _relaxed_capability(self, need: RoutingNeed) -> CapabilityProfile | None:
        if need.required_capability in {CapabilityProfile.LIGHT, CapabilityProfile.ADVANCED}:
            return CapabilityProfile.STANDARD
        return None

    def _provider_allows(self, model: ModelDescriptor, need: RoutingNeed) -> bool:
        if self._providers is None:
            return True
        provider = self._providers.get(model.provider)
        if provider is None or not provider.enabled or provider.health is ProviderHealth.UNAVAILABLE:
            return False
        required = {ProviderCapability.CHAT}
        if need.tools_required:
            required.add(ProviderCapability.TOOL_CALLING)
        if need.structured_output:
            required.add(ProviderCapability.STRUCTURED_OUTPUT)
        if need.vision_required:
            required.add(ProviderCapability.VISION)
        return required.issubset(provider.capabilities)

    def _privacy_allows(self, model: ModelDescriptor, need: RoutingNeed) -> bool:
        levels = {"public": 0, "internal": 1, "restricted": 2, "confidential": 3, "admin": 4}
        return levels[model.privacy_class.value] >= levels[need.confidentiality.value]

    def _rank(self, model: ModelDescriptor, need: RoutingNeed) -> tuple[float, ...]:
        remote_penalty = 1.0 if need.local_preferred and model.location is ModelLocation.REMOTE else 0.0
        provider_penalty = self._provider_penalty(model.provider)
        cost = model.input_cost + model.output_cost
        quality = -float(model.context_window or 0) if need.latency_preference == "quality" else 0.0
        return remote_penalty, provider_penalty, cost, float(model.priority), quality

    def _provider_penalty(self, provider_id: str) -> float:
        if self._providers is None:
            return 0.0
        provider = self._providers.get(provider_id)
        return float(provider.priority) if provider is not None else 10_000.0

    def _decision(self, selected: ModelDescriptor, fallbacks: tuple[ModelDescriptor, ...], need: RoutingNeed, relaxed: CapabilityProfile | None = None) -> RoutingDecision:
        cost = selected.input_cost + selected.output_cost
        locality = "local" if selected.location is ModelLocation.LOCAL else "distant autorisé"
        profile = f"repli {relaxed.value}" if relaxed is not None else need.required_capability.value
        reason = f"capacité {profile}, coût minimal éligible, fournisseur {locality}"
        return RoutingDecision(provider=selected.provider, model=selected.model_name, registry_id=selected.id, capability=need.required_capability, reason=reason, estimated_cost=cost, fallbacks=tuple(item.id for item in fallbacks))
