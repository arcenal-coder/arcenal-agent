"""Inventaire YunoHost lu par la passerelle privilégiée ARCenal."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter


router = APIRouter(prefix="/system")
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")
COLLECTION_ACTIONS = {
    "applications": ("yunohost.apps.read", ("apps", "applications")),
    "backups": ("yunohost.backups.read", ("archives", "backups")),
    "diagnostics": ("yunohost.diagnostics.read", ("reports", "issues")),
    "domains": ("yunohost.domains.read", ("domains",)),
    "updates": ("yunohost.updates.read", ("apps", "applications")),
    "users": ("yunohost.users.read", ("users",)),
}


@lru_cache(maxsize=1)
def _load_broker_client() -> ModuleType:
    source = Path(__file__).parents[1] / "security" / "broker_client.py"
    spec = importlib.util.spec_from_file_location("arcenal_system_broker_client", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le client de la passerelle ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _query(action_id: str, target: str | None = None) -> tuple[str, str]:
    payload = {"action_id": action_id, "target": target}
    try:
        response = _load_broker_client().execute_readonly(payload)
    except RuntimeError as exc:
        return "", str(exc)
    if not response.get("ok"):
        return "", str(response.get("error") or "Lecture YunoHost impossible.")
    return str(response.get("output") or ""), ""


def _read_json(action_id: str, target: str | None = None) -> tuple[object | None, str]:
    output, error = _query(action_id, target)
    if error:
        return None, error
    try:
        return json.loads(output), ""
    except json.JSONDecodeError:
        return None, "Réponse YunoHost invalide."


def _records(payload: object, keys: tuple[str, ...]) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        records = _records_from_value(payload.get(key))
        if records is not None:
            return records
    return []


def _records_from_value(value: object) -> list[dict[str, object]] | None:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [{"id": name, **item} if isinstance(item, dict) else {"id": name, "value": item} for name, item in value.items()]
    return None


def _collection(action_id: str, keys: tuple[str, ...]) -> dict[str, object]:
    payload, error = _read_json(action_id)
    return {"items": _records(payload, keys) if payload is not None else [], "error": error}


def _certificate(domain: str) -> dict[str, object]:
    if not DOMAIN_RE.fullmatch(domain):
        return {"domain": domain, "error": "Nom de domaine invalide."}
    payload, error = _read_json("yunohost.certificate.read", domain)
    return {"domain": domain, "details": payload, "error": error}


def _domains_with_certificates() -> tuple[dict[str, object], list[dict[str, object]]]:
    action_id, keys = COLLECTION_ACTIONS["domains"]
    domains = _collection(action_id, keys)
    raw_items = domains.get("items", [])
    items = raw_items if isinstance(raw_items, list) else []
    names = [str(item.get("domain") or item.get("id") or "") for item in items if isinstance(item, dict)]
    return domains, [_certificate(name) for name in names if name]


def _error_journal() -> list[str]:
    output, error = _query("system.errors.read")
    return [] if error else output.splitlines()[-30:]


def collect_inventory() -> dict[str, object]:
    domains, certificates = _domains_with_certificates()
    collections = {name: _collection(*contract) for name, contract in COLLECTION_ACTIONS.items() if name != "domains"}
    return {**collections, "certificates": certificates, "domains": domains, "errors": _error_journal()}


@router.get("/inventory")
def system_inventory() -> dict[str, object]:
    return collect_inventory()
