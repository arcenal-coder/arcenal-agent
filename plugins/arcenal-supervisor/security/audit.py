"""Journal d'audit chaîné et expurgé des actions administratives."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, TextIO


SENSITIVE_KEYS = frozenset({"api_key", "authorization", "password", "secret", "token"})


class AuditWriteError(RuntimeError):
    """Signale l'impossibilité de conserver une preuve d'administration."""


def _audit_path() -> Path:
    root = Path(os.environ.get("ARCENAL_AUDIT_DIR", "/var/log/arcenal-control"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "actions.jsonl"


def _redact(details: Mapping[str, object]) -> dict[str, object]:
    return {
        key: "[EXPURGÉ]" if key.lower() in SENSITIVE_KEYS else value
        for key, value in details.items()
    }


def _previous_hash(stream: TextIO) -> str:
    stream.seek(0)
    try:
        last_line = stream.read().splitlines()[-1]
        value = json.loads(last_line).get("hash", "")
    except IndexError:
        return ""
    except json.JSONDecodeError as exc:
        raise AuditWriteError("Le journal d'audit ARCenal est corrompu.") from exc
    if not isinstance(value, str) or len(value) != 64:
        raise AuditWriteError("La chaîne d'audit ARCenal est invalide.")
    return value


def _record(event: str, actor: str, details: Mapping[str, object], previous_hash: str) -> dict[str, object]:
    record: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "details": _redact(details),
        "previous_hash": previous_hash,
    }
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record["hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return record


def append_event(event: str, actor: str, details: Mapping[str, object]) -> dict[str, object]:
    """Ajoute une preuve dont l'empreinte dépend de l'événement précédent."""
    path = _audit_path()
    try:
        with path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            record = _record(event, actor, details, _previous_hash(stream))
            stream.seek(0, os.SEEK_END)
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o600)
    except OSError as exc:
        raise AuditWriteError("Le journal d'audit ARCenal est indisponible.") from exc
    return record
