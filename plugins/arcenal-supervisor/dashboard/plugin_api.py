"""API de supervision ARCenal, isolée du cœur Hermes.

Ce module ne construit jamais de commande depuis une donnée utilisateur.
Les futures réparations privilégiées passeront par des identifiants d’action
strictement autorisés dans le paquet YunoHost.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

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


@router.get("/overview")
def overview() -> dict[str, Any]:
    return collect_overview()


@router.get("/maintenance")
def maintenance_catalog() -> dict[str, Any]:
    helper = Path("/usr/local/sbin/arcenal-supervisor-helper")
    return {"actions": MAINTENANCE_CATALOG, "execution_enabled": helper.is_file()}


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
