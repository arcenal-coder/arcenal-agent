"""Tests du module de supervision ARCenal."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


MODULE = Path(__file__).parents[1] / "plugins/arcenal-supervisor/dashboard/plugin_api.py"
SPEC = importlib.util.spec_from_file_location("arcenal_supervisor_test", MODULE)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


class PluginContext:
    def __init__(self) -> None:
        self.hooks: list[tuple[str, object]] = []
        self.prompt_sections: list[dict[str, object]] = []
        self.tools: list[dict[str, object]] = []

    def register_system_prompt_section(self, **kwargs: object) -> None:
        self.prompt_sections.append(kwargs)

    def register_tool(self, **kwargs: object) -> None:
        self.tools.append(kwargs)

    def register_hook(self, name: str, callback: object) -> None:
        self.hooks.append((name, callback))


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
    assert set(overview["resources"]) == {"cpu", "disk", "memory", "load"}


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
    request = supervisor.MaintenanceRequest(operation="yunohost.diagnosis.refresh")

    try:
        supervisor._validate_maintenance(request)
    except supervisor.HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("La maintenance non confirmée devait être refusée.")


def test_maintenance_rejects_unknown_service() -> None:
    request = supervisor.MaintenanceRequest(
        operation="service.restart", service="ssh", confirmed=True
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


def test_maintenance_uses_the_authenticated_control_channel() -> None:
    request = supervisor.MaintenanceRequest(
        operation="service.restart", service="nginx", confirmed=True
    )

    try:
        supervisor.execute_maintenance(request)
    except supervisor.HTTPException as error:
        assert error.status_code == 410
        assert "authentifié" in error.detail
    else:
        raise AssertionError("L’ancien canal privilégié devait être fermé.")


def test_plugin_specializes_the_agent_as_arc() -> None:
    plugin = _load_plugin()
    context = PluginContext()
    plugin.register(context)

    assert len(context.prompt_sections) == 3
    section = next(item for item in context.prompt_sections if item["id"] == "arcenal.identity")
    assert section["id"] == "arcenal.identity"
    assert section["position"] == "after_memory"
    assert "Tu es ARC" in section["content"]
    assert "panneau ARC authentifié" in section["content"]
    assert "AACP/1" in section["content"]
    assert {tool["name"] for tool in context.tools} == {
        "arcenal_system_status",
        "arcenal_create_report",
        "arcenal_repair",
        "arcenal_knowledge_search",
        "arcenal_knowledge_document",
        "arcenal_context_search",
        "arcenal_memory_search",
        "arcenal_access_catalog",
        "arcenal_yunohost_query",
    }
    assert [name for name, _callback in context.hooks] == ["post_tool_call"]


def test_access_catalog_reports_availability_without_secret() -> None:
    plugin = _load_plugin()
    tools = sys.modules[plugin.access_catalog.__module__]
    config = {"arcenal": {"access_credentials": [{"autonomy": "smart", "id": "nextcloud", "kind": "account", "label": "Nextcloud", "login": "arc", "secretEnv": "ARCENAL_ACCESS_NEXTCLOUD_PASSWORD", "serviceUrl": "https://cloud.test/"}]}}

    records = tools._access_records(config, {"ARCENAL_ACCESS_NEXTCLOUD_PASSWORD": "never-returned"})

    assert records[0]["secretAvailable"] is True
    assert "never-returned" not in str(records)


def test_access_catalog_ignores_unsafe_secret_variable() -> None:
    plugin = _load_plugin()
    tools = sys.modules[plugin.access_catalog.__module__]
    config = {"arcenal": {"access_credentials": [{"autonomy": "off", "id": "bad", "kind": "api", "label": "Bad", "secretEnv": "PATH", "serviceUrl": "https://bad.test/"}]}}

    assert tools._access_records(config, {"PATH": "secret"}) == []


def test_access_catalog_accepts_an_empty_configuration() -> None:
    plugin = _load_plugin()
    tools = sys.modules[plugin.access_catalog.__module__]

    assert tools._access_records({}, {}) == []


def test_access_catalog_filters_disabled_access_and_exposes_permissions() -> None:
    plugin = _load_plugin()
    tools = sys.modules[plugin.access_catalog.__module__]
    active = {
        "autonomy": "manual",
        "enabled": True,
        "id": "wiki",
        "kind": "api",
        "label": "Wiki",
        "permissions": ["lecture", "publication"],
        "secretEnv": "ARCENAL_ACCESS_WIKI_API_KEY",
        "serviceUrl": "https://wiki.test/",
    }
    disabled = {**active, "enabled": False, "id": "archive", "secretEnv": "ARCENAL_ACCESS_ARCHIVE_API_KEY"}

    records = tools._access_records({"arcenal": {"access_credentials": [active, disabled]}}, {})

    assert [record["id"] for record in records] == ["wiki"]
    assert records[0]["permissions"] == ["lecture", "publication"]


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


def test_knowledge_upload_stores_attachment_and_document(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="QSSERP/procedure.md", content=_applicable_document())

    saved = supervisor.knowledge.create_document_with_attachment(
        payload, "procédure validée.pdf", "application/pdf", b"%PDF-1.7\nsource"
    )

    document = saved["document"]
    attachment = supervisor.knowledge.knowledge_root() / document["attachment_path"]
    assert document["attachment_name"] == "procédure validée.pdf"
    assert attachment.read_bytes() == b"%PDF-1.7\nsource"
    assert "Document source" in supervisor.knowledge.read_document(payload.path)["content"]


def test_knowledge_upload_rejects_unsupported_format(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="QSSERP/script.md", content="# Script")

    try:
        supervisor.knowledge.create_document_with_attachment(
            payload, "script.exe", "application/octet-stream", b"executable"
        )
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Un format exécutable devait être refusé.")


def test_knowledge_upload_rejects_empty_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="QSSERP/vide.md", content="# Vide")

    try:
        supervisor.knowledge.create_document_with_attachment(payload, "vide.pdf", "application/pdf", b"")
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Une pièce jointe vide devait être refusée.")


def test_knowledge_upload_rejects_fake_pdf(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = supervisor.knowledge.DocumentWrite(path="QSSERP/faux.md", content="# Faux")

    try:
        supervisor.knowledge.create_document_with_attachment(
            payload, "faux.pdf", "application/pdf", b"contenu non PDF"
        )
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Un faux PDF devait être refusé.")


def test_knowledge_attachment_rejects_path_escape(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    try:
        supervisor.knowledge._safe_attachment_path(".attachments/../../secret.pdf")
    except supervisor.HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("La sortie du répertoire des pièces jointes devait être refusée.")


def test_knowledge_workflow_approves_with_authenticated_actor(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    content = _applicable_document().replace("statut: Applicable", "statut: À approuver")
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(path="procedure.md", content=content)
    )

    result = supervisor.knowledge.transition_document(
        "procedure.md", "Applicable", "admin", "Validation annuelle"
    )

    assert result["document"]["status"] == "Applicable"
    assert result["document"]["approved_by"] == "admin"
    assert result["document"]["reason"] == "Validation annuelle"


def test_knowledge_workflow_rejects_invalid_transition(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    content = _applicable_document().replace("statut: Applicable", "statut: Brouillon")
    supervisor.knowledge.write_document(
        supervisor.knowledge.DocumentWrite(path="procedure.md", content=content)
    )

    try:
        supervisor.knowledge.transition_document("procedure.md", "Applicable", "admin")
    except supervisor.HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("La publication directe d’un brouillon devait être refusée.")


def test_knowledge_direct_edit_cannot_change_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    draft = _applicable_document().replace("statut: Applicable", "statut: Brouillon")
    target = supervisor.knowledge.DocumentWrite(path="procedure.md", content=draft)
    supervisor.knowledge.write_document(target)

    try:
        supervisor.knowledge.write_document(
            supervisor.knowledge.DocumentWrite(path="procedure.md", content=_applicable_document()),
            allow_status_change=False,
        )
    except supervisor.HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("L’édition libre du statut devait être refusée.")


def test_knowledge_restores_an_archived_version(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    first = supervisor.knowledge.DocumentWrite(path="note.md", content="# Première")
    second = supervisor.knowledge.DocumentWrite(path="note.md", content="# Deuxième")
    supervisor.knowledge.write_document(first)
    supervisor.knowledge.write_document(second)
    version = supervisor.knowledge.list_history("note.md")[0]

    supervisor.knowledge.restore_history("note.md", version["id"])

    assert supervisor.knowledge.read_document("note.md")["content"] == "# Première"
