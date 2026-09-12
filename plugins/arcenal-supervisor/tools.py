"""Outils utilisés par le chat pour superviser ARCenal Système."""

from __future__ import annotations

import importlib.util
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


@lru_cache(maxsize=1)
def _supervisor_module():
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
            "service": {"type": "string", "enum": ["arcenal", "nginx", "yunohost-api", "yunohost-portal-api", "slapd", "redis-server"]},
            "confirmed": {"type": "boolean", "description": "Vrai uniquement après confirmation explicite de l’utilisateur."},
        },
        "required": ["operation", "confirmed"],
    },
}
