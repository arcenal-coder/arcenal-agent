"""Erreurs métier stables exposées par ARC Core."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .provider_models import ProviderAttempt


class AgentContractError(ValueError):
    """Signale une définition ou une requête d’agent invalide."""


class AgentNotFoundError(LookupError):
    """Signale qu’un identifiant d’agent n’existe pas."""


class AgentDisabledError(PermissionError):
    """Signale qu’un agent connu est désactivé."""


class AgentAccessDeniedError(PermissionError):
    """Signale que l’application ne peut pas utiliser l’agent demandé."""


class ApplicationAuthenticationError(PermissionError):
    """Signale une preuve d’identité applicative absente ou invalide."""


class AgentExecutionError(RuntimeError):
    """Signale un échec contrôlé du moteur IA interne."""


class FrugalConfigurationError(ValueError):
    """Signale une configuration ARC Frugal incohérente."""


class ModelRoutingError(RuntimeError):
    """Signale qu'aucun modèle autorisé ne peut traiter la demande."""


class AutomationPolicyError(PermissionError):
    """Signale qu'un workflow tente de dépasser son contrat."""


class FrugalStorageError(RuntimeError):
    """Signale une persistance ARC Frugal indisponible ou invalide."""


class ProviderExecutionError(RuntimeError):
    """Signale un échec fournisseur expurgé et exploitable par le fallback."""

    RETRYABLE_CODES = frozenset({"rate_limited", "timeout", "unavailable", "invalid_response"})
    FALLBACK_CODES = frozenset({"rate_limited", "timeout", "unavailable"})

    def __init__(self, message: str, code: str, attempts: tuple[ProviderAttempt, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.attempts = attempts

    @property
    def retryable(self) -> bool:
        return self.code in self.RETRYABLE_CODES

    @property
    def fallback_allowed(self) -> bool:
        return self.code in self.FALLBACK_CODES
