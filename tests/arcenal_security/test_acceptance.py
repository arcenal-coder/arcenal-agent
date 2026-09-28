"""Tests du contrat de recette ARCenal."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[2] / "plugins/arcenal-supervisor/acceptance.py"
MATRIX = Path(__file__).parents[2] / "docs/arcenal-acceptance-matrix.md"
SPEC = importlib.util.spec_from_file_location("arcenal_acceptance", SOURCE)
assert SPEC and SPEC.loader
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


class AcceptanceContractTests(unittest.TestCase):
    def test_complete_matrix_has_no_missing_criterion(self) -> None:
        markdown = MATRIX.read_text(encoding="utf-8")

        self.assertEqual(acceptance.missing_acceptance_ids(markdown), frozenset())

    def test_duplicate_criterion_is_counted_once(self) -> None:
        self.assertEqual(acceptance.acceptance_ids("AC-ARC-01 AC-ARC-01"), frozenset({"AC-ARC-01"}))

    def test_missing_criterion_is_reported(self) -> None:
        missing = acceptance.missing_acceptance_ids("AC-ARC-01")

        self.assertIn("AC-BKP-01", missing)


if __name__ == "__main__":
    unittest.main()
