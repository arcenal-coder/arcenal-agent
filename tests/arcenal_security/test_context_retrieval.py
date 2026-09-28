"""Vérifie la récupération ciblée du contexte organisationnel."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _load_tools() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "managed_files_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_context_files", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module d’outils ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOLS = _load_tools()


class ContextRetrievalTests(unittest.TestCase):
    def test_search_returns_only_matching_sections(self) -> None:
        content = "# Activités\nConseil QSSE et audit.\n# Implantations\nParis et Lyon."
        with patch.object(TOOLS, "read_managed_file", return_value={"content": content}):
            passages = TOOLS.search_context("audit QSSE")

        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0]["section"], "Activités")

    def test_search_returns_nothing_without_matching_terms(self) -> None:
        detail = {"content": "# Équipe\nDirection et qualité."}
        with patch.object(TOOLS, "read_managed_file", return_value=detail):
            passages = TOOLS.search_context("hébergement")

        self.assertEqual(passages, [])

    def test_search_limits_the_number_and_size_of_passages(self) -> None:
        content = "\n".join(f"# Section {index}\nserveur {'x' * 1500}" for index in range(8))
        with patch.object(TOOLS, "read_managed_file", return_value={"content": content}):
            passages = TOOLS.search_context("serveur")

        self.assertEqual(len(passages), 5)
        self.assertTrue(all(len(item["content"]) <= 1200 for item in passages))


if __name__ == "__main__":
    unittest.main()
