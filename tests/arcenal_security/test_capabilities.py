"""Tests du catalogue et du journal d’utilisation des capacités ARC."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "capabilities.py"
    spec = importlib.util.spec_from_file_location("arcenal_capabilities_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des capacités est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class CapabilityUsageTests(unittest.TestCase):
    def test_usage_is_counted_without_arguments_or_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            MODULE.record_usage("arcenal_system_status", "success", 12)
            record = MODULE.record_usage("arcenal_system_status", "error", 21)
            payload = json.loads(MODULE.usage_path().read_text(encoding="utf-8"))

        self.assertEqual(record["count"], 2)
        self.assertEqual(record["last_status"], "error")
        self.assertNotIn("args", payload)
        self.assertNotIn("result", payload)

    def test_invalid_tool_name_is_rejected(self) -> None:
        with self.assertRaises(MODULE.CapabilityUsageError):
            MODULE.record_usage("outil avec espaces", "success", 1)

    def test_corrupted_usage_log_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            path = MODULE.usage_path()
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(MODULE.CapabilityUsageError):
                MODULE.read_usage()

    def test_catalog_distinguishes_arc_origin_and_security(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HERMES_HOME": directory}):
            rows = MODULE.capability_rows()

        repair = next(row for row in rows if row["name"] == "arcenal_repair")
        self.assertEqual(repair["origin"], "arcenal")
        self.assertEqual(repair["risk"], "high")
        self.assertTrue(repair["confirmation"])


if __name__ == "__main__":
    unittest.main()
