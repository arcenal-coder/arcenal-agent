from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "knowledge_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_knowledge_workflow_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module documentaire est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _document(status: str) -> str:
    return f"""---
reference: PR-QSSE-001
titre: Gestion documentaire
version: 4
statut: {status}
---
# Gestion documentaire

Contenu applicable.
"""


def _versioned_document(version: int, status: str = "À approuver") -> str:
    return _document(status).replace("version: 4", f"version: {version}").replace("Contenu applicable.", f"Contenu V{version}.")


class KnowledgeWorkflowTests(TestCase):
    def test_second_version_gets_a_distinct_path_and_replaces_the_applicable_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            first = MODULE.create_document(MODULE.DocumentWrite(path="procedure.md", content=_versioned_document(1)))
            MODULE.transition_document(first["document"]["path"], "Applicable", "admin")
            second = MODULE.create_document(MODULE.DocumentWrite(path="procedure.md", content=_versioned_document(2)))
            MODULE.transition_document(second["document"]["path"], "Applicable", "admin")
            documents = {item["path"]: item for item in MODULE.list_documents()}
            wiki = MODULE.wiki_overview()

        self.assertEqual(second["document"]["path"], "procedure-v2.md")
        self.assertEqual(documents["procedure.md"]["status"], "Archivé")
        self.assertEqual([item["path"] for item in wiki["documents"]], ["procedure-v2.md"])

    def test_approval_records_actor_and_builds_lda(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.write_document(MODULE.DocumentWrite(path="procedure.md", content=_document("À approuver")))
            result = MODULE.transition_document("procedure.md", "Applicable", "admin", "Validation")
            overview = MODULE.knowledge_overview()

        self.assertEqual(result["document"]["approved_by"], "admin")
        self.assertEqual([item["path"] for item in overview["lda"]], ["procedure.md"])

    def test_draft_cannot_be_published_directly(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.write_document(MODULE.DocumentWrite(path="procedure.md", content=_document("Brouillon")))
            with self.assertRaises(HTTPException) as raised:
                MODULE.transition_document("procedure.md", "Applicable", "admin")

        self.assertEqual(raised.exception.status_code, 409)

    def test_history_restores_previous_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.write_document(MODULE.DocumentWrite(path="note.md", content="# Première"))
            MODULE.write_document(MODULE.DocumentWrite(path="note.md", content="# Deuxième"))
            version = MODULE.list_history("note.md")[0]
            MODULE.restore_history("note.md", version["id"])
            restored = MODULE.read_document("note.md")["content"]

        self.assertEqual(restored, "# Première")

    def test_index_rebuild_requires_yunohost_identity_and_confirmation(self) -> None:
        app = FastAPI()
        app.include_router(MODULE.router)
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            anonymous = client.post("/knowledge/index/rebuild?confirmed=true")
            unconfirmed = client.post("/knowledge/index/rebuild", headers={"Remote-User": "admin"})
            rebuilt = client.post("/knowledge/index/rebuild?confirmed=true", headers={"Remote-User": "admin"})

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(unconfirmed.status_code, 409)
        self.assertEqual(rebuilt.status_code, 200)
        self.assertTrue(rebuilt.json()["ok"])

    def test_same_reference_and_version_are_globally_unique(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.create_document(MODULE.DocumentWrite(path="premier.md", content=_versioned_document(1)))
            with self.assertRaises(HTTPException) as raised:
                MODULE.create_document(MODULE.DocumentWrite(path="second.md", content=_versioned_document(1)))

        self.assertEqual(raised.exception.status_code, 409)

    def test_concurrent_duplicate_creation_has_one_controlled_conflict(self) -> None:
        def create(path: str) -> int:
            try:
                MODULE.create_document(MODULE.DocumentWrite(path=path, content=_versioned_document(1)))
            except HTTPException as exc:
                return exc.status_code
            return 201

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = sorted(pool.map(create, ("concurrent-a.md", "concurrent-b.md")))

        self.assertEqual(statuses, [201, 409])

    def test_reference_and_version_identity_is_trimmed_casefolded_and_unicode_normalized(self) -> None:
        first = _versioned_document(1).replace("PR-QSSE-001", "PR-ÉCO-001")
        duplicate = _versioned_document(1).replace("PR-QSSE-001", "  pr-éco-001  ")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.create_document(MODULE.DocumentWrite(path="normalise-a.md", content=first))
            with self.assertRaises(HTTPException) as raised:
                MODULE.create_document(MODULE.DocumentWrite(path="normalise-b.md", content=duplicate))

        self.assertEqual(raised.exception.status_code, 409)

    def test_three_versions_keep_distinct_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            paths = tuple(
                MODULE.create_document(MODULE.DocumentWrite(path="procedure.md", content=_versioned_document(version)))["document"]["path"]
                for version in (1, 2, 3)
            )

        self.assertEqual(paths, ("procedure.md", "procedure-v2.md", "procedure-v3.md"))

    def test_revision_only_metadata_uses_the_same_global_identity(self) -> None:
        first = _versioned_document(2).replace("version: 2", "revision: 2")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.create_document(MODULE.DocumentWrite(path="historique-a.md", content=first))
            with self.assertRaises(HTTPException) as raised:
                MODULE.create_document(MODULE.DocumentWrite(path="historique-b.md", content=first))

        self.assertEqual(raised.exception.status_code, 409)
