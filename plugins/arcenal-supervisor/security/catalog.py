"""Catalogue fermé des actions autorisées sur ARCenal Système."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .models import ActionDefinition, AuthorizationLevel, RiskLevel, SecurityContractError


_SERVICES = ("arcenal", "nginx", "yunohost-api", "yunohost-portal-api", "slapd")

ACTION_CATALOG: Mapping[str, ActionDefinition] = MappingProxyType(
    {
        "yunohost.version.read": ActionDefinition(
            "yunohost.version.read",
            AuthorizationLevel.READ,
            RiskLevel.NONE,
            "Lire la version de YunoHost.",
            "Aucune modification du serveur.",
            "Aucun retour arrière requis.",
        ),
        "yunohost.apps.read": ActionDefinition(
            "yunohost.apps.read",
            AuthorizationLevel.READ,
            RiskLevel.NONE,
            "Lister les applications YunoHost.",
            "Aucune modification du serveur.",
            "Aucun retour arrière requis.",
        ),
        "yunohost.services.read": ActionDefinition(
            "yunohost.services.read",
            AuthorizationLevel.READ,
            RiskLevel.NONE,
            "Lire l'état des services YunoHost.",
            "Aucune modification du serveur.",
            "Aucun retour arrière requis.",
        ),
        "yunohost.diagnosis.refresh": ActionDefinition(
            "yunohost.diagnosis.refresh",
            AuthorizationLevel.CONTROLLED,
            RiskLevel.LOW,
            "Actualiser les diagnostics officiels YunoHost.",
            "Déclenche les contrôles système sans modifier les applications.",
            "Aucun retour arrière requis.",
        ),
        "nginx.reload": ActionDefinition(
            "nginx.reload",
            AuthorizationLevel.CONFIRMED,
            RiskLevel.MEDIUM,
            "Valider puis recharger Nginx.",
            "Les accès web peuvent être brièvement perturbés.",
            "Le rechargement est refusé si la configuration est invalide.",
        ),
        "service.restart": ActionDefinition(
            "service.restart",
            AuthorizationLevel.CONFIRMED,
            RiskLevel.HIGH,
            "Redémarrer un service système autorisé.",
            "Le service ciblé sera temporairement indisponible.",
            "Vérifier l'état puis relancer ou restaurer sa configuration.",
            _SERVICES,
        ),
    }
)


def action_definition(action_id: str) -> ActionDefinition:
    """Retourne une action connue ou refuse tout identifiant non catalogué."""
    try:
        return ACTION_CATALOG[action_id]
    except KeyError as exc:
        raise SecurityContractError("L'action demandée n'appartient pas au catalogue ARCenal.") from exc
