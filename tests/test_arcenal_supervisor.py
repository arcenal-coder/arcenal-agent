"""Tests du module de supervision ARCenal."""

import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "plugins/arcenal-supervisor/dashboard/plugin_api.py"
SPEC = importlib.util.spec_from_file_location("arcenal_supervisor_test", MODULE)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


def test_overview_shape(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "_service_status",
        lambda service, label: {"id": service, "label": label, "state": "active", "healthy": True},
    )
    overview = supervisor.collect_overview()
    assert overview["health"] == "healthy"
    assert len(overview["services"]) == len(supervisor.SERVICES)
    assert set(overview["resources"]) == {"disk", "memory", "load"}


def test_degraded_when_service_is_inactive(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "_service_status",
        lambda service, label: {"id": service, "label": label, "state": "failed", "healthy": False},
    )
    overview = supervisor.collect_overview()
    assert overview["health"] == "degraded"
    assert len(overview["incidents"]) >= len(supervisor.SERVICES)


def test_reports_stay_in_hermes_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert supervisor._reports_dir() == tmp_path / "reports" / "supervision"


def test_maintenance_catalog_requires_approval():
    assert supervisor.MAINTENANCE_CATALOG
    assert all(action["approval_required"] for action in supervisor.MAINTENANCE_CATALOG)
    assert set(supervisor.RESTARTABLE_SERVICES) == {service for service, _label in supervisor.SERVICES}
