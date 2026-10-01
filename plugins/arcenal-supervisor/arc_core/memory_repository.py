"""Stockage SQLite versionné de la mémoire d’entreprise."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from .memory_models import (
    EnterpriseMemory,
    MemoryDraft,
    MemoryMetrics,
    MemoryRevision,
    MemorySearchFilters,
    MemoryStatus,
)


SCHEMA_VERSION = 1
_LOCK = threading.RLock()


class MemoryRepositoryError(RuntimeError):
    """Signale un stockage mémoire absent, corrompu ou indisponible."""


class MemoryNotFoundError(MemoryRepositoryError):
    """Signale une mémoire inconnue ou physiquement supprimée."""


class MemoryConflictError(MemoryRepositoryError):
    """Signale une transition de gouvernance incohérente."""


class EnterpriseMemoryRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._initialize()

    def create(self, draft: MemoryDraft, actor: str) -> EnterpriseMemory:
        now = datetime.now(timezone.utc)
        memory = EnterpriseMemory(id=str(uuid4()), created_at=now, updated_at=now, created_by=actor, version=1, **draft.model_dump())
        with _LOCK, self._connection() as connection:
            self._insert(connection, memory)
        return memory

    def get(self, memory_id: str) -> EnterpriseMemory:
        with self._connection() as connection:
            row = connection.execute("SELECT payload FROM enterprise_memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise MemoryNotFoundError("Mémoire d’entreprise introuvable.")
        return self._decode(str(row["payload"]))

    def search(self, filters: MemorySearchFilters) -> tuple[EnterpriseMemory, ...]:
        self.expire_due()
        with self._connection() as connection:
            rows = connection.execute("SELECT payload FROM enterprise_memories ORDER BY updated_at DESC").fetchall()
        memories = (self._decode(str(row["payload"])) for row in rows)
        return tuple(memory for memory in memories if _matches(memory, filters))

    def correct(self, memory_id: str, draft: MemoryDraft, actor: str, reason: str) -> EnterpriseMemory:
        with _LOCK:
            previous = self.get(memory_id)
            current = EnterpriseMemory(id=previous.id, created_at=previous.created_at, updated_at=datetime.now(timezone.utc), created_by=previous.created_by, version=previous.version + 1, **draft.model_dump())
            with self._connection() as connection:
                self._replace(connection, previous, current, actor, reason)
            return current

    def set_status(self, memory_id: str, status: MemoryStatus, actor: str, reason: str) -> EnterpriseMemory:
        with _LOCK:
            previous = self.get(memory_id)
            if previous.status is MemoryStatus.DELETED and status is not MemoryStatus.DELETED:
                raise MemoryConflictError("Une mémoire supprimée ne peut pas être réactivée.")
            draft = MemoryDraft.model_validate({**previous.model_dump(exclude={"id", "created_at", "updated_at", "created_by", "version"}), "status": status})
            return self.correct(memory_id, draft, actor, reason)

    def delete_physical(self, memory_id: str) -> None:
        with _LOCK, self._connection() as connection:
            cursor = connection.execute("DELETE FROM enterprise_memories WHERE id = ?", (memory_id,))
            connection.execute("DELETE FROM memory_revisions WHERE memory_id = ?", (memory_id,))
        if cursor.rowcount == 0:
            raise MemoryNotFoundError("Mémoire d’entreprise introuvable.")

    def history(self, memory_id: str) -> tuple[MemoryRevision, ...]:
        self.get(memory_id)
        with self._connection() as connection:
            rows = connection.execute("SELECT payload FROM memory_revisions WHERE memory_id = ? ORDER BY version DESC", (memory_id,)).fetchall()
        try:
            return tuple(MemoryRevision.model_validate_json(str(row["payload"])) for row in rows)
        except ValidationError as exc:
            raise MemoryRepositoryError("Historique de mémoire invalide.") from exc

    def expire_due(self, now: datetime | None = None) -> tuple[str, ...]:
        with _LOCK:
            instant = now or datetime.now(timezone.utc)
            candidates = self.search_without_expiration()
            expired = tuple(item for item in candidates if _is_due(item, instant))
            for memory in expired:
                self.set_status(memory.id, MemoryStatus.EXPIRED, "system", "Expiration automatique")
            return tuple(memory.id for memory in expired)

    def active(self) -> tuple[EnterpriseMemory, ...]:
        return self.search(MemorySearchFilters(status=MemoryStatus.ACTIVE))

    def metrics(self, used_by_rag: int = 0) -> MemoryMetrics:
        self.expire_due()
        memories = self.search_without_expiration()
        statuses = _count_values(memory.status.value for memory in memories)
        return MemoryMetrics(total=len(memories), active=statuses.get("active", 0), archived=statuses.get("archived", 0), expired=statuses.get("expired", 0), pending_review=statuses.get("pending_review", 0), deleted=statuses.get("deleted", 0), by_type=_count_values(item.memory_type.value for item in memories), by_scope=_count_values(scope for item in memories for scope in item.knowledge_scopes), used_by_rag=used_by_rag)

    def search_without_expiration(self) -> tuple[EnterpriseMemory, ...]:
        with self._connection() as connection:
            rows = connection.execute("SELECT payload FROM enterprise_memories ORDER BY updated_at DESC").fetchall()
        return tuple(self._decode(str(row["payload"])) for row in rows)

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with self._connection() as connection:
                installed_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if installed_version > SCHEMA_VERSION:
                    raise MemoryRepositoryError("Le schéma mémoire est plus récent que cette version d’ARC.")
                connection.executescript(_schema())
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._path.chmod(0o600)
        except sqlite3.Error as exc:
            raise MemoryRepositoryError("Initialisation de la mémoire impossible.") from exc

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _insert(self, connection: sqlite3.Connection, memory: EnterpriseMemory) -> None:
        try:
            connection.execute("INSERT INTO enterprise_memories (id, status, memory_type, updated_at, payload) VALUES (?, ?, ?, ?, ?)", _row(memory))
        except sqlite3.Error as exc:
            raise MemoryRepositoryError("Création de la mémoire impossible.") from exc

    def _replace(self, connection: sqlite3.Connection, previous: EnterpriseMemory, current: EnterpriseMemory, actor: str, reason: str) -> None:
        revision = MemoryRevision(id=str(uuid4()), memory_id=current.id, version=current.version, previous=previous, current=current, corrected_by=actor, corrected_at=current.updated_at, reason=reason)
        try:
            connection.execute("UPDATE enterprise_memories SET status = ?, memory_type = ?, updated_at = ?, payload = ? WHERE id = ?", (*_row(current)[1:], current.id))
            connection.execute("INSERT INTO memory_revisions (id, memory_id, version, corrected_at, payload) VALUES (?, ?, ?, ?, ?)", (revision.id, revision.memory_id, revision.version, revision.corrected_at.isoformat(), revision.model_dump_json()))
        except sqlite3.Error as exc:
            raise MemoryRepositoryError("Correction de la mémoire impossible.") from exc

    def _decode(self, payload: str) -> EnterpriseMemory:
        try:
            return EnterpriseMemory.model_validate_json(payload)
        except ValidationError as exc:
            raise MemoryRepositoryError("Une mémoire persistée est invalide.") from exc


def _row(memory: EnterpriseMemory) -> tuple[str, str, str, str, str]:
    return memory.id, memory.status.value, memory.memory_type.value, memory.updated_at.isoformat(), memory.model_dump_json()


def _matches(memory: EnterpriseMemory, filters: MemorySearchFilters) -> bool:
    checks = (_matches_enum(memory.memory_type, filters.memory_type), _matches_enum(memory.status, filters.status), _matches_enum(memory.provenance.source_type, filters.source_type), _matches_enum(memory.confidentiality, filters.confidentiality), _matches_value(memory.project, filters.project), _matches_value(memory.person, filters.person), not filters.scope or filters.scope.casefold() in memory.knowledge_scopes, not filters.created_from or memory.created_at >= filters.created_from, not filters.created_to or memory.created_at <= filters.created_to, _matches_query(memory, filters.query))
    return all(checks)


def _matches_enum(actual: object, expected: object | None) -> bool:
    return expected is None or actual == expected


def _matches_value(actual: str | None, expected: str | None) -> bool:
    return expected is None or (actual is not None and expected.casefold() == actual.casefold())


def _matches_query(memory: EnterpriseMemory, query: str) -> bool:
    normalized = query.strip().casefold()
    haystack = "\n".join((memory.summary, memory.content, memory.project or "", memory.person or "", memory.provenance.source_id)).casefold()
    return not normalized or normalized in haystack


def _is_due(memory: EnterpriseMemory, now: datetime) -> bool:
    return memory.status is MemoryStatus.ACTIVE and memory.expires_at is not None and memory.expires_at <= now


def _count_values(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def _schema() -> str:
    return """
    CREATE TABLE IF NOT EXISTS enterprise_memories (
        id TEXT PRIMARY KEY, status TEXT NOT NULL, memory_type TEXT NOT NULL,
        updated_at TEXT NOT NULL, payload TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_memory_status ON enterprise_memories(status);
    CREATE INDEX IF NOT EXISTS idx_memory_type ON enterprise_memories(memory_type);
    CREATE TABLE IF NOT EXISTS memory_revisions (
        id TEXT PRIMARY KEY, memory_id TEXT NOT NULL, version INTEGER NOT NULL,
        corrected_at TEXT NOT NULL, payload TEXT NOT NULL,
        FOREIGN KEY(memory_id) REFERENCES enterprise_memories(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_memory_revision ON memory_revisions(memory_id, version);
    """
