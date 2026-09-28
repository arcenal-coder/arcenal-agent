"""Modèles immuables de la politique d'administration ARCenal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Mapping


class AuthorizationLevel(IntEnum):
    """Niveau maximal d'autonomie accordé à une action."""

    READ = 0
    RECOMMEND = 1
    CONTROLLED = 2
    CONFIRMED = 3


class RiskLevel(str, Enum):
    """Impact potentiel d'une action sur ARCenal Système."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SecurityContractError(ValueError):
    """Signale un contrat de sécurité invalide à la frontière du système."""


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")


@dataclass(frozen=True, slots=True)
class Actor:
    username: str
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not USERNAME_PATTERN.fullmatch(self.username):
            raise SecurityContractError("L'identité administrateur est invalide.")
        if not self.roles:
            raise SecurityContractError("Au moins un rôle est requis.")


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    action_id: str
    authorization: AuthorizationLevel
    risk: RiskLevel
    description: str
    consequence: str
    rollback: str
    allowed_targets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action_id: str
    actor: Actor
    target: str | None = None
    confirmed: bool = False


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    confirmation_required: bool
    reason: str
    action: ActionDefinition
    metadata: Mapping[str, str]

    @classmethod
    def create(
        cls,
        *,
        allowed: bool,
        confirmation_required: bool,
        reason: str,
        action: ActionDefinition,
        metadata: Mapping[str, str] | None = None,
    ) -> "PolicyDecision":
        frozen_metadata = MappingProxyType(dict(metadata or {}))
        return cls(allowed, confirmation_required, reason, action, frozen_metadata)
