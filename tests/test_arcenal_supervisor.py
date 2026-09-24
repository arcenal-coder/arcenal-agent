"""Tests du module de supervision ARCenal."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
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
        supervisor.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=20, free=80),
    )
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


def test_maintenance_rejects_missing_confirmation() -> None:
    request = supervisor.MaintenanceRequest(operation="refresh-diagnostics")

    try:
        supervisor._validate_maintenance(request)
    except supervisor.HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("La maintenance non confirmée devait être refusée.")


def test_maintenance_rejects_unknown_service() -> None:
    request = supervisor.MaintenanceRequest(
        operation="restart-service", service="ssh", confirmed=True
    )

    try:
        supervisor._validate_maintenance(request)
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Le service hors liste devait être refusé.")


def test_maintenance_rejects_unknown_operation() -> None:
    request = supervisor.MaintenanceRequest(operation="run-shell", confirmed=True)

    try:
        supervisor._validate_maintenance(request)
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("L’opération hors catalogue devait être refusée.")


def test_maintenance_builds_a_fixed_command(monkeypatch, tmp_path) -> None:
    helper = tmp_path / "helper"
    captured = []
    monkeypatch.setattr(supervisor, "_maintenance_helper", lambda: helper)
    monkeypatch.setattr(supervisor, "_run", lambda command, timeout: captured.append((command, timeout)) or (0, "ok"))
    request = supervisor.MaintenanceRequest(
        operation="restart-service", service="nginx", confirmed=True
    )

    assert supervisor._execute_maintenance(request) == (0, "ok")
    assert captured == [(["sudo", "-n", str(helper), "restart-service", "nginx"], 120)]


def test_maintenance_executes_allowlisted_action(monkeypatch, tmp_path) -> None:
    helper = tmp_path / "helper"
    helper.touch()
    monkeypatch.setattr(supervisor, "_maintenance_helper", lambda: helper)
    monkeypatch.setattr(supervisor, "_execute_maintenance", lambda _request: (0, "ok"))
    monkeypatch.setattr(supervisor, "collect_overview", lambda: {"health": "healthy"})
    request = supervisor.MaintenanceRequest(
        operation="restart-service", service="nginx", confirmed=True
    )

    result = supervisor.execute_maintenance(request)

    assert result["status"] == "completed"
    assert result["service"] == "nginx"
    assert result["details"] == "ok"


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
        "arcenal_knowledge_search",
        "arcenal_knowledge_document",
    }


def _applicable_document() -> str:
    return """---
reference: PR-QSSE-001
titre: Gestion documentaire
type: Procédure
version: 4
statut: Applicable
proprietaire: Direction Q&D
date_application: 2026-09-22
prochaine_revue: 2027-09-22
tags: [qualité, documentation]
---
# Gestion documentaire

La version applicable définit la maîtrise des documents. Voir [[Politique QSSE]].
"""


def test_knowledge_persists_markdown_and_builds_lda(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(
        path="QSSERP/PR-QSSE-001.md", content=_applicable_document()
    )

    saved = supervisor.knowledge.write_document(payload)
    overview = supervisor.knowledge.knowledge_overview()

    assert saved["document"]["reference"] == "PR-QSSE-001"
    assert [item["path"] for item in overview["lda"]] == ["QSSERP/PR-QSSE-001.md"]
    assert overview["statistics"] == {
        "documents": 1,
        "applicable": 1,
        "pending": 0,
        "overdue": 0,
    }


def test_knowledge_search_returns_traceable_source(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(path="procedure.md", content=_applicable_document())
    )

    results = supervisor.knowledge.search_documents("maîtrise documents")

    assert len(results) == 1
    assert results[0]["reference"] == "PR-QSSE-001"
    assert results[0]["version"] == "4"
    assert results[0]["score"] > 0


def test_knowledge_builds_obsidian_style_backlinks(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(path="procedure.md", content=_applicable_document())
    )
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(
            path="politique.md",
            content="---\ntitre: Politique QSSE\nstatut: Applicable\n---\n# Politique QSSE\n",
        )
    )

    documents = supervisor.knowledge.knowledge_overview()["documents"]
    policy = next(item for item in documents if item["title"] == "Politique QSSE")

    assert policy["backlinks"] == ["Gestion documentaire"]


def test_knowledge_empty_vault_is_valid(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    overview = supervisor.knowledge.knowledge_overview()

    assert overview["documents"] == []
    assert overview["lda"] == []
    assert overview["wiki"] == []


def test_knowledge_rejects_path_escape(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="../secret.md", content="# Secret")

    try:
        supervisor.knowledge.write_document(payload)
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("La sortie du coffre documentaire devait être refusée.")


def test_knowledge_never_indexes_a_symlink_outside_vault(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    external = tmp_path / "secret.md"
    external.write_text("# Secret extérieur", encoding="utf-8")
    root = supervisor.knowledge.knowledge_root()
    (root / "secret.md").symlink_to(external)

    assert supervisor.knowledge.knowledge_overview()["documents"] == []


def test_knowledge_rejects_unknown_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    content = "---\ntitre: Test\nstatut: Publié\n---\n# Test\n"
    payload = supervisor.knowledge.DocumentWrite(path="test.md", content=content)

    try:
        supervisor.knowledge.write_document(payload)
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Un statut inconnu devait être refusé.")


def test_wiki_never_exposes_a_draft(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    draft = "---\ntitre: Projet\nstatut: Brouillon\n---\n# Projet\n"
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(path="projet.md", content=draft)
    )

    assert supervisor.knowledge.wiki_overview()["documents"] == []
    try:
        supervisor.knowledge.read_wiki_document("projet.md")
    except supervisor.HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Le wiki ne devait pas exposer un brouillon.")


def test_knowledge_create_never_overwrites_existing_document(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="note.md", content="# Première version")
    supervisor.knowledge.create_document(payload)

    try:
        supervisor.knowledge.create_document(
            supervisor.knowledge.DocumentWrite(path="note.md", content="# Remplacement")
        )
    except supervisor.HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("La création ne devait pas écraser un document existant.")
    assert supervisor.knowledge.read_document("note.md")["content"] == "# Première version"


def test_knowledge_update_archives_previous_version(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    first = supervisor.knowledge.DocumentWrite(path="note.md", content="# Version 1")
    second = supervisor.knowledge.DocumentWrite(path="note.md", content="# Version 2")
    supervisor.knowledge.write_document(first)

    supervisor.knowledge.write_document(second)

    summary = supervisor.knowledge.read_document("note.md")["document"]
    assert summary["history_count"] == 1
    assert supervisor.knowledge.knowledge_overview()["statistics"]["documents"] == 1
