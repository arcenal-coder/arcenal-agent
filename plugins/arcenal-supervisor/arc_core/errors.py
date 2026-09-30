"""Erreurs métier stables exposées par ARC Core."""


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
