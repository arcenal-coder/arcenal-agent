"""Confirmations humaines à usage unique pour les actions critiques."""

from __future__ import annotations

import os
import secrets
import sqlite3
import time
from pathlib import Path


class ApprovalError(RuntimeError):
    """Signale une confirmation absente, expirée ou non concordante."""


def _database_path() -> Path:
    configured = os.environ.get("ARCENAL_APPROVAL_DB")
    if configured:
        return Path(configured)
    root = Path(os.environ.get("ARCENAL_AUDIT_DIR", "/var/lib/arcenal-control"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "approvals.sqlite3"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=5)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS approvals "
        "(id TEXT PRIMARY KEY, actor TEXT NOT NULL, action_id TEXT NOT NULL, "
        "target TEXT, expires_at INTEGER NOT NULL)"
    )
    return connection


def issue_approval(actor: str, action_id: str, target: str | None, ttl_seconds: int = 300) -> str:
    """Crée un identifiant imprévisible lié à une demande exacte."""
    if ttl_seconds < 1 or ttl_seconds > 900:
        raise ApprovalError("La durée de confirmation est invalide.")
    approval_id = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ttl_seconds
    with _connect() as connection:
        connection.execute(
            "INSERT INTO approvals VALUES (?, ?, ?, ?, ?)",
            (approval_id, actor, action_id, target, expires_at),
        )
    return approval_id


def _validate_row(
    row: tuple[str, str, str | None, int] | None,
    actor: str,
    action_id: str,
    target: str | None,
) -> None:
    if row is None:
        raise ApprovalError("La confirmation est inconnue ou déjà utilisée.")
    if row[:3] != (actor, action_id, target):
        raise ApprovalError("La confirmation ne correspond pas à cette action.")
    if row[3] < int(time.time()):
        raise ApprovalError("La confirmation a expiré.")


def consume_approval(approval_id: str, actor: str, action_id: str, target: str | None) -> None:
    """Consomme atomiquement une confirmation et interdit sa réutilisation."""
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT actor, action_id, target, expires_at FROM approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()
        _validate_row(row, actor, action_id, target)
        connection.execute("DELETE FROM approvals WHERE id = ?", (approval_id,))


def pending_approvals(limit: int = 100) -> list[dict[str, object]]:
    """Expose les confirmations actives sans divulguer leur jeton."""
    if limit < 1 or limit > 500:
        raise ApprovalError("La limite de confirmations est invalide.")
    now = int(time.time())
    with _connect() as connection:
        connection.execute("DELETE FROM approvals WHERE expires_at < ?", (now,))
        rows = connection.execute(
            "SELECT actor, action_id, target, expires_at FROM approvals ORDER BY expires_at LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"actor": row[0], "action_id": row[1], "target": row[2], "expires_at": row[3]} for row in rows]
