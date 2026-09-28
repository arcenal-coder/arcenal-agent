"""Résolution de l'identité administrateur depuis le groupe système YunoHost."""

from __future__ import annotations

import grp

from .models import Actor


class AdministratorLookupError(RuntimeError):
    """Signale que l'annuaire YunoHost ne peut pas être interrogé."""


class AdministratorDeniedError(PermissionError):
    """Signale qu'un compte authentifié n'est pas administrateur YunoHost."""


def administrator_actor(remote_user: str, primary_admin: str) -> Actor:
    """Construit un acteur uniquement après contrôle du groupe YunoHost."""
    username = remote_user.strip()
    try:
        candidate = Actor(username=username, roles=("admins",))
        members = tuple(grp.getgrnam("admins").gr_mem)
    except KeyError as exc:
        raise AdministratorLookupError("Le groupe administrateur YunoHost est introuvable.") from exc
    if candidate.username not in members:
        raise AdministratorDeniedError("Ce compte n'est pas administrateur YunoHost.")
    roles = ("admins", "owner") if candidate.username == primary_admin else ("admins",)
    return Actor(username=candidate.username, roles=roles)
