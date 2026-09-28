"""Décisions de politique indépendantes du transport et du modèle IA."""

from __future__ import annotations

import re

from .catalog import action_definition
from .models import ActionDefinition, ActionRequest, AuthorizationLevel, PolicyDecision


def _target_is_allowed(request: ActionRequest) -> bool:
    action = action_definition(request.action_id)
    if action.allowed_targets:
        return request.target in action.allowed_targets
    if action.target_pattern and request.target:
        return re.fullmatch(action.target_pattern, request.target) is not None
    return request.target is None


def _denied(action: ActionDefinition, reason: str, confirmation: bool = False) -> PolicyDecision:
    return PolicyDecision.create(
        allowed=False,
        confirmation_required=confirmation,
        reason=reason,
        action=action,
    )


def evaluate_action(request: ActionRequest) -> PolicyDecision:
    """Évalue une action sans l'exécuter et sans dépendre du LLM."""
    action = action_definition(request.action_id)
    if "admins" not in request.actor.roles:
        return _denied(action, "Seuls les administrateurs YunoHost peuvent agir sur ARCenal Système.")
    if not _target_is_allowed(request):
        return _denied(action, "La cible demandée n'est pas autorisée pour cette action.")
    confirmation_required = action.authorization is AuthorizationLevel.CONFIRMED
    if confirmation_required and not request.confirmed:
        return _denied(action, "Une confirmation humaine explicite est obligatoire.", True)
    return PolicyDecision.create(
        allowed=True,
        confirmation_required=confirmation_required,
        reason="Action autorisée par la politique ARCenal.",
        action=action,
    )
