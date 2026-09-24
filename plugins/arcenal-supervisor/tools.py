"""Outils utilisés par le chat pour superviser ARCenal Système."""

from __future__ import annotations

import importlib.util
import re
import subprocess
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, TypedDict

from hermes_cli.config import load_config_readonly, load_env
from tools.registry import tool_error, tool_result


ACCESS_ENV_PATTERN = re.compile(r"^ARCENAL_ACCESS_[A-Z0-9_]+_(?:API_KEY|PASSWORD)$")


class AccessRecord(TypedDict):
    """Description non secrète d’un accès confié à ARC."""

    autonomy: str
    id: str
    kind: str
    label: str
    login: str | None
    secretAvailable: bool
    secretEnv: str
    serviceUrl: str


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


def access_catalog(args: dict[str, Any], **_: Any) -> str:
    """Liste les accès autorisés sans jamais exposer leurs secrets."""
    try:
        return tool_result(accesses=_access_records(load_config_readonly(), load_env()))
    except Exception as exc:
        return tool_error(f"Lecture du coffre d’accès impossible : {exc}")


def yunohost_query(args: dict[str, Any], **_: Any) -> str:
    """Interroge l’interface locale YunoHost au travers du pont privilégié."""
    resource = str(args.get("resource") or "").strip()
    if resource not in {"apps", "services", "version"}:
        return tool_error("Ressource YunoHost non autorisée.")
    command = ["sudo", "-n", "/usr/local/sbin/arcenal-supervisor-helper", "yunohost-query", resource]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return tool_error(f"API locale YunoHost indisponible : {exc}")
    output = (result.stdout or result.stderr).strip()[:20000]
    if result.returncode != 0:
        return tool_error("L’API locale YunoHost a refusé la requête.", resource=resource, details=output)
    return tool_result(resource=resource, details=output)


def _access_records(config: Mapping[str, object], environment: Mapping[str, str]) -> list[AccessRecord]:
    arcenal = config.get("arcenal")
    if not isinstance(arcenal, Mapping):
        return []
    credentials = arcenal.get("access_credentials")
    if not isinstance(credentials, list):
        return []
    return [record for item in credentials if (record := _safe_access_record(item, environment))]


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
    return AccessRecord(**values, login=login if isinstance(login, str) else None, secretAvailable=bool(environment.get(values["secretEnv"])))


def repair(args: dict[str, Any], **_: Any) -> str:
    """Prépare ou exécute une réparation appartenant à la liste autorisée."""
    operation = str(args.get("operation") or "").strip()
    service = str(args.get("service") or "").strip()
    confirmed = args.get("confirmed") is True
    catalog = {item["id"]: item for item in _supervisor_module().MAINTENANCE_CATALOG}
    if operation not in catalog:
        return tool_error("Opération de maintenance non autorisée.")
    if operation == "restart-service" and service not in _supervisor_module().RESTARTABLE_SERVICES:
        return tool_error("Ce service ne peut pas être redémarré par ARCenal Agent.")

    proposal = {
        "operation": operation,
        "service": service or None,
        "risk": catalog[operation]["risk"],
        "description": catalog[operation]["description"],
    }
    if not confirmed:
        return tool_result(
            status="confirmation_required",
            message="Demandez l’accord explicite de l’utilisateur avant d’exécuter cette réparation.",
            proposal=proposal,
        )

    command = ["sudo", "-n", "/usr/local/sbin/arcenal-supervisor-helper", operation]
    if service:
        command.append(service)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return tool_error(f"La réparation n’a pas pu être lancée : {exc}")
    output = (result.stdout or result.stderr).strip()[:8000]
    if result.returncode != 0:
        return tool_error("La réparation a échoué.", operation=operation, details=output)
    return tool_result(
        status="completed",
        operation=operation,
        details=output,
        overview=_supervisor_module().collect_overview(),
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
    "description": "Prépare ou exécute une réparation ARCenal autorisée. Ne jamais mettre confirmed=true sans accord explicite de l’utilisateur dans la conversation en cours.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["refresh-diagnostics", "reload-nginx", "restart-service"]},
            "service": {"type": "string", "enum": ["arcenal", "nginx", "yunohost-api", "yunohost-portal-api", "slapd"]},
            "confirmed": {"type": "boolean", "description": "Vrai uniquement après confirmation explicite de l’utilisateur."},
        },
        "required": ["operation", "confirmed"],
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
