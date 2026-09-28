from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException


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


class KnowledgeWorkflowTests(TestCase):
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
