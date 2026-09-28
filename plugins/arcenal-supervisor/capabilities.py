"""Inventaire et journal minimal des capacités utilisées par ARC."""

from __future__ import annotations

import json
import fcntl
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, TypedDict


TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class CapabilityDefinition(TypedDict):
    description: str
    permission: str
    risk: str
    confirmation: bool


class UsageRecord(TypedDict):
    count: int
    duration_ms: int
    last_status: str
    last_used: str


ARC_CAPABILITIES: Mapping[str, CapabilityDefinition] = MappingProxyType(
    {
        "arcenal_access_catalog": {"description": "Consulter les accès métier actifs sans lire leurs secrets.", "permission": "Accès métier", "risk": "none", "confirmation": False},
        "arcenal_yunohost_query": {"description": "Lire les versions, applications et services via l’API locale YunoHost.", "permission": "Lecture système", "risk": "none", "confirmation": False},
        "arcenal_system_status": {"description": "Établir l’état de santé du serveur et de ses services.", "permission": "Lecture système", "risk": "none", "confirmation": False},
        "arcenal_create_report": {"description": "Créer un compte rendu de supervision horodaté.", "permission": "Écriture des rapports", "risk": "low", "confirmation": False},
        "arcenal_repair": {"description": "Préparer une réparation appartenant au catalogue fermé ARCenal.", "permission": "Maintenance contrôlée", "risk": "high", "confirmation": True},
        "arcenal_knowledge_search": {"description": "Rechercher dans le RAG, la LDA et le wiki.", "permission": "Lecture documentaire", "risk": "none", "confirmation": False},
        "arcenal_knowledge_document": {"description": "Lire une source documentaire précise du coffre.", "permission": "Lecture documentaire", "risk": "none", "confirmation": False},
        "arcenal_context_search": {"description": "Retrouver le contexte organisationnel pertinent.", "permission": "Lecture du contexte", "risk": "none", "confirmation": False},
        "arcenal_memory_search": {"description": "Retrouver une décision ou convention mémorisée.", "permission": "Lecture de la mémoire", "risk": "none", "confirmation": False},
    }
)


class CapabilityUsageError(RuntimeError):
    """Signale un journal d’utilisation invalide ou indisponible."""


def usage_path() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = home / "arcenal"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "capability-usage.json"


def read_usage() -> dict[str, UsageRecord]:
    path = usage_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CapabilityUsageError("Le journal d’utilisation des outils est illisible.") from exc
    if not isinstance(payload, dict):
        raise CapabilityUsageError("Le journal d’utilisation des outils est invalide.")
    tools = payload.get("tools")
    return _validated_records(tools)


def record_usage(tool_name: str, status: str, duration_ms: int) -> UsageRecord:
    if not TOOL_NAME_PATTERN.fullmatch(tool_name):
        raise CapabilityUsageError("Le nom de l’outil à journaliser est invalide.")
    lock_path = usage_path().with_suffix(".lock")
    try:
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            records = read_usage()
            record = _new_record(records.get(tool_name), status, duration_ms)
            _write_usage({**records, tool_name: record})
        lock_path.chmod(0o600)
    except OSError as exc:
        raise CapabilityUsageError("Le verrou du journal d’utilisation est indisponible.") from exc
    return record


def capability_rows() -> list[dict[str, object]]:
    usage = read_usage()
    return [
        {"name": name, "origin": "arcenal", "enabled": True, "mutable": False, "last_usage": usage.get(name), **definition}
        for name, definition in ARC_CAPABILITIES.items()
    ]


def _new_record(previous: UsageRecord | None, status: str, duration_ms: int) -> UsageRecord:
    count = previous["count"] + 1 if previous else 1
    bounded_duration = max(0, min(int(duration_ms), 3_600_000))
    safe_status = status if status in {"blocked", "error", "success"} else "unknown"
    return {"count": count, "duration_ms": bounded_duration, "last_status": safe_status, "last_used": datetime.now(timezone.utc).isoformat()}


def _validated_records(value: object) -> dict[str, UsageRecord]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name): record
        for name, raw in value.items()
        if TOOL_NAME_PATTERN.fullmatch(str(name)) and (record := _validated_record(raw))
    }


def _validated_record(value: object) -> UsageRecord | None:
    if not isinstance(value, dict):
        return None
    count, duration = value.get("count"), value.get("duration_ms")
    status, last_used = value.get("last_status"), value.get("last_used")
    if not isinstance(count, int) or count < 0 or not isinstance(duration, int):
        return None
    if not isinstance(status, str) or not isinstance(last_used, str):
        return None
    return {"count": count, "duration_ms": duration, "last_status": status, "last_used": last_used}


def _write_usage(records: Mapping[str, UsageRecord]) -> None:
    path = usage_path()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".capabilities.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"version": 1, "tools": records}, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise CapabilityUsageError("Le journal d’utilisation des outils est indisponible.") from exc
