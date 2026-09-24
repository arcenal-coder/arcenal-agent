"""API de supervision ARCenal, isolée du cœur Hermes.

Ce module ne construit jamais de commande depuis une donnée utilisateur.
Les futures réparations privilégiées passeront par des identifiants d’action
strictement autorisés dans le paquet YunoHost.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


def _load_knowledge_api() -> ModuleType:
    """Charge le volet documentaire sans coupler le moteur Hermes à ARCenal."""
    source = Path(__file__).with_name("knowledge_api.py")
    spec = importlib.util.spec_from_file_location("arcenal_knowledge_api", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module documentaire ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


knowledge = _load_knowledge_api()
router.include_router(knowledge.router)

SERVICES = (
    ("arcenal", "ARCenal Agent"),
    ("nginx", "Serveur web"),
    ("yunohost-api", "API YunoHost"),
    ("yunohost-portal-api", "Portail YunoHost"),
    ("slapd", "Annuaire LDAP"),
)

RESTARTABLE_SERVICES = tuple(service for service, _label in SERVICES)

MAINTENANCE_CATALOG = (
    {
        "id": "refresh-diagnostics",
        "label": "Actualiser les diagnostics YunoHost",
        "risk": "low",
        "approval_required": True,
        "description": "Relance les contrôles officiels sans modifier les applications.",
    },
    {
        "id": "reload-nginx",
        "label": "Vérifier et recharger Nginx",
        "risk": "medium",
        "approval_required": True,
        "description": "Valide la configuration avant tout rechargement du serveur web.",
    },
    {
        "id": "restart-service",
        "label": "Redémarrer un service autorisé",
        "risk": "medium",
        "approval_required": True,
        "description": "Redémarrage borné aux services gérés par ARCenal Système.",
    },
)

MAINTENANCE_BY_ID = {item["id"]: item for item in MAINTENANCE_CATALOG}


class MaintenanceRequest(BaseModel):
    """Demande bornée provenant du panneau de supervision."""

    operation: str
    service: str | None = None
    confirmed: bool = False


class OpenRouterProbeRequest(BaseModel):
    """Clé facultative à tester sans jamais la persister dans cette API."""

    api_key: str | None = Field(default=None, max_length=512)


class OpenRouterProbeResponse(BaseModel):
    """État de connexion présentable sans exposer le secret utilisé."""

    configured: bool
    connection: str = Field(pattern="^(connected|invalid|missing|unreachable)$")
    message: str


def _configured_openrouter_key() -> str:
    """Lit la clé gérée par Hermes depuis le magasin privé de l'application."""
    from hermes_cli.config import load_env

    return load_env().get("OPENROUTER_API_KEY", "").strip()


def _openrouter_probe_result(status_code: int) -> OpenRouterProbeResponse:
    """Traduit la réponse distante en état métier stable pour l'interface."""
    if status_code in {200, 429}:
        return OpenRouterProbeResponse(configured=True, connection="connected", message="Connexion OpenRouter opérationnelle.")
    if status_code in {401, 403}:
        return OpenRouterProbeResponse(configured=True, connection="invalid", message="OpenRouter a refusé cette clé API.")
    return OpenRouterProbeResponse(configured=True, connection="unreachable", message=f"OpenRouter répond avec le code HTTP {status_code}.")


async def _probe_openrouter(api_key: str) -> OpenRouterProbeResponse:
    """Teste une clé avec l'endpoint de lecture OpenRouter prévu à cet effet."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/key",
                headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"},
            )
    except httpx.HTTPError:
        return OpenRouterProbeResponse(configured=True, connection="unreachable", message="OpenRouter est temporairement inaccessible.")
    return _openrouter_probe_result(response.status_code)


def _run(command: list[str], timeout: int = 8) -> tuple[int, str]:
    """Exécute une commande de lecture déterministe, sans interpréteur shell."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    output = (result.stdout or result.stderr).strip()
    return result.returncode, output[:4000]


def _service_status(service: str, label: str) -> dict[str, Any]:
    code, state = _run(["systemctl", "is-active", service])
    state = state or "unknown"
    return {
        "id": service,
        "label": label,
        "state": state,
        "healthy": code == 0 and state == "active",
    }


def _memory() -> dict[str, float]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError):
        return {"total": 0, "used": 0, "percent": 0}
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(total - available, 0)
    return {
        "total": total,
        "used": used,
        "percent": round((used / total * 100) if total else 0, 1),
    }


def collect_overview() -> dict[str, Any]:
    """Construit un instantané système stable et sérialisable."""
    disk = shutil.disk_usage("/")
    services = [_service_status(service, label) for service, label in SERVICES]
    incidents = [
        {
            "severity": "critical",
            "source": service["id"],
            "message": f"{service['label']} n’est pas actif ({service['state']}).",
        }
        for service in services
        if not service["healthy"]
    ]
    disk_percent = round(disk.used / disk.total * 100, 1) if disk.total else 0
    if disk_percent >= 85:
        incidents.append(
            {
                "severity": "warning",
                "source": "storage",
                "message": f"Le volume système est utilisé à {disk_percent} %.",
            }
        )
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "name": "ARCenal Système" if Path("/etc/yunohost/installed").exists() else platform.system(),
            "hostname": platform.node(),
            "kernel": platform.release(),
            "yunohost": Path("/etc/yunohost/installed").exists(),
        },
        "resources": {
            "disk": {"total": disk.total, "used": disk.used, "percent": disk_percent},
            "memory": _memory(),
            "load": [round(value, 2) for value in load],
        },
        "services": services,
        "incidents": incidents,
        "health": "healthy" if not incidents else "degraded",
    }


def _reports_dir() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    target = home / "reports" / "supervision"
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    return target


def _maintenance_helper() -> Path:
    return Path("/usr/local/sbin/arcenal-supervisor-helper")


def _validate_maintenance(request: MaintenanceRequest) -> dict[str, Any]:
    action = MAINTENANCE_BY_ID.get(request.operation)
    if action is None:
        raise HTTPException(status_code=422, detail="Opération de maintenance non autorisée.")
    if request.operation == "restart-service" and request.service not in RESTARTABLE_SERVICES:
        raise HTTPException(status_code=422, detail="Service non autorisé.")
    if request.operation != "restart-service" and request.service is not None:
        raise HTTPException(status_code=422, detail="Cette opération n’accepte aucun service.")
    if not request.confirmed:
        raise HTTPException(status_code=409, detail="Une confirmation administrateur est requise.")
    return action


def _execute_maintenance(request: MaintenanceRequest) -> tuple[int, str]:
    command = ["sudo", "-n", str(_maintenance_helper()), request.operation]
    if request.service:
        command.append(request.service)
    return _run(command, timeout=120)


@router.get("/overview")
def overview() -> dict[str, Any]:
    return collect_overview()


@router.post("/openrouter/test", response_model=OpenRouterProbeResponse)
async def test_openrouter(request: OpenRouterProbeRequest) -> OpenRouterProbeResponse:
    """Teste la clé saisie ou, à défaut, la clé déjà configurée."""
    api_key = (request.api_key or "").strip() or _configured_openrouter_key()
    if not api_key:
        return OpenRouterProbeResponse(
            configured=False,
            connection="missing",
            message="Ajoutez une clé API OpenRouter pour établir la connexion.",
        )
    return await _probe_openrouter(api_key)


@router.get("/maintenance")
def maintenance_catalog() -> dict[str, Any]:
    helper = _maintenance_helper()
    return {"actions": MAINTENANCE_CATALOG, "execution_enabled": helper.is_file()}


@router.post("/maintenance/execute")
def execute_maintenance(request: MaintenanceRequest) -> dict[str, Any]:
    action = _validate_maintenance(request)
    if not _maintenance_helper().is_file():
        raise HTTPException(status_code=503, detail="Le canal de maintenance ARCenal est indisponible.")
    code, output = _execute_maintenance(request)
    if code != 0:
        raise HTTPException(status_code=500, detail=output or "La maintenance a échoué.")
    return {
        "status": "completed",
        "action": action,
        "service": request.service,
        "details": output,
        "overview": collect_overview(),
    }


@router.get("/reports")
def list_reports() -> dict[str, Any]:
    reports = []
    for path in sorted(_reports_dir().glob("*.json"), reverse=True)[:50]:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        reports.append({"id": path.stem, **data})
    return {"reports": reports}


@router.post("/reports", status_code=201)
def create_report() -> dict[str, Any]:
    snapshot = collect_overview()
    report_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = _reports_dir() / f"{report_id}.json"
    try:
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        path.chmod(0o600)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Impossible d’enregistrer le rapport.") from exc
    return {"id": report_id, **snapshot}
