"""Tests du module de supervision ARCenal."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


MODULE = Path(__file__).parents[1] / "plugins/arcenal-supervisor/dashboard/plugin_api.py"
SPEC = importlib.util.spec_from_file_location("arcenal_supervisor_test", MODULE)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


class PluginContext:
    def __init__(self) -> None:
        self.prompt_sections: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []

    def register_system_prompt_section(self, **kwargs: Any) -> None:
        self.prompt_sections.append(kwargs)

    def register_tool(self, **kwargs: Any) -> None:
        self.tools.append(kwargs)


def _load_plugin() -> ModuleType:
    package_dir = MODULE.parents[1]
    spec = importlib.util.spec_from_file_location(
        "arcenal_supervisor_plugin",
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    assert spec and spec.loader
    plugin = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = plugin
    spec.loader.exec_module(plugin)
    return plugin


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


def test_plugin_specializes_the_agent_as_arc() -> None:
    plugin = _load_plugin()
    context = PluginContext()
    plugin.register(context)

    assert len(context.prompt_sections) == 1
    section = context.prompt_sections[0]
    assert section["id"] == "arcenal.identity"
    assert section["position"] == "after_memory"
    assert "Tu es ARC" in section["content"]
    assert "confirmation explicite" in section["content"]
    assert "AACP/1" in section["content"]
    assert {tool["name"] for tool in context.tools} == {
        "arcenal_system_status",
        "arcenal_create_report",
        "arcenal_repair",
    }
