"""Composition du stockage de configuration et du coffre ARC."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from .configuration import ArcConfigStore, ArcConfigurationError, ArcMigrationReport, ConfigValue, migrate_hermes_configuration
from .configuration import ArcNativeConfigStore
from .hermes_config_adapter import HermesConfigAdapter
from .vault import ArcFileVault, ArcVault


@dataclass(frozen=True)
class ArcRuntimeConfiguration:
    config: ArcConfigStore
    vault: ArcVault
    migration: ArcMigrationReport = ArcMigrationReport(0, 0, ())
    backend: str = "arc"
    migration_state: str = "not_required"

    def provider_enabled(self, provider_id: str, secret_key: str | None = None) -> bool:
        raw = self.config.get("providers", provider_id, {})
        if isinstance(raw, dict) and raw.get("enabled") is False:
            return False
        return self.vault.has_secret(secret_key) if secret_key else True

    def access_credentials(self) -> tuple[dict[str, ConfigValue], ...]:
        raw = self.config.get("system", "access_credentials", [])
        if not isinstance(raw, list):
            return ()
        return tuple(cast(dict[str, ConfigValue], item) for item in raw if isinstance(item, dict))


def runtime_configuration(home: Path | None = None) -> ArcRuntimeConfiguration:
    root = home or _runtime_home()
    vault = ArcFileVault(root / ".env")
    if _configured_backend() == "hermes":
        return ArcRuntimeConfiguration(HermesConfigAdapter(), vault, backend="hermes", migration_state="legacy")
    native = ArcNativeConfigStore(root / "arcenal" / "config.json")
    report, state = _migrate_existing_configuration(root, native)
    return ArcRuntimeConfiguration(native, vault, report, "arc", state)


def migration_status(home: Path | None = None) -> ArcMigrationReport:
    return runtime_configuration(home).migration


def _migrate_existing_configuration(root: Path, native: ArcNativeConfigStore) -> tuple[ArcMigrationReport, str]:
    marker = native.get("system", "hermes_migration")
    legacy_exists = (root / "config.yaml").exists()
    if isinstance(marker, dict):
        completed = marker.get("version") == 1 and marker.get("status") == "complete"
        if completed or not legacy_exists:
            return _report_from_marker(marker), str(marker.get("status", "complete"))
    if not legacy_exists:
        report = ArcMigrationReport(0, 0, ())
        _save_marker(native, report, "not_required")
        return report, "not_required"
    legacy = HermesConfigAdapter()
    report = migrate_hermes_configuration(native, legacy)
    _verify_migration(native, legacy)
    _report_conflicts(report)
    _save_marker(native, report, "complete")
    return report, "complete"


def _save_marker(store: ArcNativeConfigStore, report: ArcMigrationReport, status: str) -> None:
    store.set("system", "hermes_migration", {
        "conflicts": list(report.conflicts), "copied": report.copied,
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "status": status, "unchanged": report.unchanged, "version": 1,
    })


def _report_from_marker(marker: dict[str, ConfigValue]) -> ArcMigrationReport:
    conflicts = marker.get("conflicts", [])
    safe_conflicts = tuple(item for item in conflicts if isinstance(item, str)) if isinstance(conflicts, list) else ()
    copied = marker.get("copied", 0)
    unchanged = marker.get("unchanged", 0)
    return ArcMigrationReport(copied if isinstance(copied, int) else 0, unchanged if isinstance(unchanged, int) else 0, safe_conflicts)


def _report_conflicts(report: ArcMigrationReport) -> None:
    if report.conflicts:
        logging.getLogger(__name__).warning("Conflits de migration ARC conservés : %s", ", ".join(report.conflicts))


def _verify_migration(native: ArcNativeConfigStore, legacy: HermesConfigAdapter) -> None:
    for namespace in ("core", "models", "providers", "system", "ui"):
        for key in legacy.list(namespace):
            if not native.exists(namespace, key):
                raise ArcConfigurationError(f"Migration ARC incomplète pour {namespace}.{key}.")


def _runtime_home() -> Path:
    configured = os.environ.get("ARCENAL_HOME") or os.environ.get("HERMES_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".hermes"


def _configured_backend() -> str:
    backend = os.environ.get("ARCENAL_CONFIG_BACKEND", "arc").strip().casefold()
    if backend not in {"arc", "hermes"}:
        raise ArcConfigurationError(f"Backend de configuration ARC invalide : {backend!r}.")
    return backend
