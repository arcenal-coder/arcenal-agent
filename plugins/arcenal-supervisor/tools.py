"""Outils utilisés par le chat pour superviser ARCenal Système."""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, TypedDict

from tools.registry import tool_error, tool_result

from .arc_core import runtime_configuration
from .security.broker_client import BrokerUnavailableError, execute_readonly


ACCESS_ENV_PATTERN = re.compile(r"^ARCENAL_ACCESS_[A-Z0-9_]+_(?:API_KEY|PASSWORD)$")


class AccessRecord(TypedDict):
    """Description non secrète d’un accès confié à ARC."""

    autonomy: str
    enabled: bool
    id: str
    kind: str
    label: str
    login: str | None
    permissions: list[str]
    secretAvailable: bool
    secretEnv: str
    serviceUrl: str


class SecretAvailability(Protocol):
    def has_secret(self, key: str) -> bool: ...


@lru_cache(maxsize=1)
def _supervisor_module() -> ModuleType:
    """Charge la même logique que l’API du dashboard, sans la dupliquer."""
    source = Path(__file__).parent / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_supervisor_api", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module de supervision ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def system_status(args: dict[str, Any], **_: Any) -> str:
    """Retourne l’état réel du serveur pour guider le diagnostic du chat."""
    try:
        return tool_result(_supervisor_module().collect_overview())
    except Exception as exc:
        return tool_error(f"Diagnostic ARCenal impossible : {exc}")


def create_report(args: dict[str, Any], **_: Any) -> str:
    """Crée un compte rendu horodaté et renvoie son contenu au chat."""
    try:
        return tool_result(_supervisor_module().create_report())
    except Exception as exc:
        return tool_error(f"Création du compte rendu impossible : {exc}")


def knowledge_search(args: dict[str, Any], **_: Any) -> str:
    """Recherche les passages utiles et conserve référence et version."""
    query = str(args.get("query") or "").strip()
    if len(query) < 2:
        return tool_error("La recherche documentaire doit contenir au moins deux caractères.")
    try:
        results = _supervisor_module().knowledge.search_documents(query, 8)
        return tool_result(query=query, results=results)
    except Exception as exc:
        return tool_error(f"Recherche documentaire impossible : {exc}")


def knowledge_document(args: dict[str, Any], **_: Any) -> str:
    """Lit une source précise retenue par la recherche documentaire."""
    path = str(args.get("path") or "").strip()
    if not path:
        return tool_error("Le chemin du document est requis.")
    try:
        return tool_result(_supervisor_module().knowledge.read_document(path))
    except Exception as exc:
        return tool_error(f"Lecture documentaire impossible : {exc}")


def context_search(args: dict[str, Any], **_: Any) -> str:
    """Restitue uniquement les sections du contexte liées à la requête."""
    query = str(args.get("query") or "").strip()
    if len(query) < 2:
        return tool_error("La recherche de contexte doit contenir au moins deux caractères.")
    try:
        passages = _supervisor_module().managed_files.search_context(query)
        return tool_result(query=query, passages=passages)
    except Exception as exc:
        return tool_error(f"Recherche dans le contexte impossible : {exc}")


def memory_search(args: dict[str, Any], **_: Any) -> str:
    """Retrouve les souvenirs durables qui correspondent à une requête."""
    query = str(args.get("query") or "").strip()
    if len(query) < 2:
        return tool_error("La recherche mémoire doit contenir au moins deux caractères.")
    try:
        entries = _supervisor_module().managed_files.list_memory_entries(query)
        return tool_result(query=query, entries=entries[:10])
    except Exception as exc:
        return tool_error(f"Recherche dans la mémoire impossible : {exc}")


def access_catalog(args: dict[str, Any], **_: Any) -> str:
    """Liste les accès autorisés sans jamais exposer leurs secrets."""
    try:
        return tool_result(accesses=_runtime_access_records())
    except Exception as exc:
        return tool_error(f"Lecture du coffre d’accès impossible : {exc}")


def yunohost_query(args: dict[str, Any], **_: Any) -> str:
    """Interroge l’interface locale YunoHost au travers du pont privilégié."""
    resource = str(args.get("resource") or "").strip()
    if resource not in {"apps", "services", "version"}:
        return tool_error("Ressource YunoHost non autorisée.")
    action_id = f"yunohost.{resource}.read"
    try:
        result = execute_readonly({"action_id": action_id, "target": None})
    except BrokerUnavailableError as exc:
        return tool_error(f"API locale YunoHost indisponible : {exc}")
    if not result["ok"]:
        return tool_error("L’API locale YunoHost a refusé la requête.", resource=resource)
    return tool_result(resource=resource, details=result.get("output", ""))


def _access_records(config: Mapping[str, object], environment: Mapping[str, str]) -> list[AccessRecord]:
    arcenal = config.get("arcenal")
    if not isinstance(arcenal, Mapping):
        return []
    credentials = arcenal.get("access_credentials")
    if not isinstance(credentials, list):
        return []
    active = [item for item in credentials if not isinstance(item, Mapping) or item.get("enabled") is not False]
    return [record for item in active if (record := _safe_access_record(item, environment))]


def _runtime_access_records() -> list[AccessRecord]:
    runtime = runtime_configuration()
    credentials = list(runtime.access_credentials())
    environment = _secret_availability(credentials, runtime.vault)
    return _access_records({"arcenal": {"access_credentials": credentials}}, environment)


def _secret_availability(credentials: list[object], vault: SecretAvailability) -> dict[str, str]:
    references = [item.get("secretEnv") for item in credentials if isinstance(item, Mapping)]
    return {item: "configured" for item in references if isinstance(item, str) and ACCESS_ENV_PATTERN.fullmatch(item) and vault.has_secret(item)}


def _safe_access_record(item: object, environment: Mapping[str, str]) -> AccessRecord | None:
    if not isinstance(item, Mapping):
        return None
    required = ("id", "kind", "label", "serviceUrl", "secretEnv", "autonomy")
    if not all(isinstance(item.get(key), str) for key in required):
        return None
    values = {key: str(item[key]) for key in required}
    if not ACCESS_ENV_PATTERN.fullmatch(values["secretEnv"]):
        return None
    login = item.get("login")
    permissions = item.get("permissions")
    allowed = [str(value) for value in permissions if isinstance(value, str)][:20] if isinstance(permissions, list) else []
    return AccessRecord(**values, enabled=True, login=login if isinstance(login, str) else None, permissions=allowed, secretAvailable=bool(environment.get(values["secretEnv"])))


def repair(args: dict[str, Any], **_: Any) -> str:
    """Prépare ou exécute une réparation appartenant à la liste autorisée."""
    operation = str(args.get("operation") or "").strip()
    service = str(args.get("service") or "").strip()
    catalog = {item["id"]: item for item in _supervisor_module().MAINTENANCE_CATALOG}
    if operation not in catalog:
        return tool_error("Opération de maintenance non autorisée.")
    if operation == "service.restart" and service not in _supervisor_module().RESTARTABLE_SERVICES:
        return tool_error("Ce service ne peut pas être redémarré par ARCenal Agent.")

    proposal = {
        "operation": operation,
        "service": service or None,
        "risk": catalog[operation]["risk"],
        "description": catalog[operation]["description"],
    }
    return tool_result(
        status="control_panel_required",
        message="Présentez cette proposition dans le panneau ARC pour obtenir une confirmation authentifiée.",
        proposal=proposal,
    )


SYSTEM_STATUS_SCHEMA = {
    "name": "arcenal_system_status",
    "description": "Inspecte l’état d’ARCenal Système, ses ressources, services et incidents. À utiliser quand l’utilisateur signale un problème serveur.",
    "parameters": {"type": "object", "properties": {}},
}

CREATE_REPORT_SCHEMA = {
    "name": "arcenal_create_report",
    "description": "Crée un compte rendu de supervision horodaté dans l’espace privé ARCenal.",
    "parameters": {"type": "object", "properties": {}},
}

REPAIR_SCHEMA = {
    "name": "arcenal_repair",
    "description": "Prépare une réparation ARCenal autorisée. L’exécution reste réservée au panneau authentifié et n’est jamais déclenchée par le modèle.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["yunohost.diagnosis.refresh", "nginx.reload", "service.restart"]},
            "service": {"type": "string", "enum": ["arcenal", "nginx", "yunohost-api", "yunohost-portal-api", "slapd"]},
        },
        "required": ["operation"],
    },
}

KNOWLEDGE_SEARCH_SCHEMA = {
    "name": "arcenal_knowledge_search",
    "description": "Recherche dans le RAG Markdown, la LDA et le wiki ARCenal. Renvoie des sources avec référence, version et statut.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 2}},
        "required": ["query"],
    },
}

KNOWLEDGE_DOCUMENT_SCHEMA = {
    "name": "arcenal_knowledge_document",
    "description": "Lit un document précis du coffre après une recherche RAG.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "pattern": "^[^/].*\\.md$"}},
        "required": ["path"],
    },
}

CONTEXT_SEARCH_SCHEMA = {
    "name": "arcenal_context_search",
    "description": "Recherche les seules sections pertinentes du contexte organisationnel administré.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 2}},
        "required": ["query"],
    },
}

MEMORY_SEARCH_SCHEMA = {
    "name": "arcenal_memory_search",
    "description": "Recherche les décisions, préférences, conventions, projets et actions mémorisés.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 2}},
        "required": ["query"],
    },
}

ACCESS_CATALOG_SCHEMA = {
    "name": "arcenal_access_catalog",
    "description": "Liste les comptes et API confiés à ARC, leur autonomie et leur variable secrète, sans révéler le secret.",
    "parameters": {"type": "object", "properties": {}},
}

YUNOHOST_QUERY_SCHEMA = {
    "name": "arcenal_yunohost_query",
    "description": "Interroge l’API locale YunoHost sans mot de passe pour obtenir la version, les applications ou les services.",
    "parameters": {
        "type": "object",
        "properties": {"resource": {"type": "string", "enum": ["apps", "services", "version"]}},
        "required": ["resource"],
    },
}
