"""Tests du journal d'audit ARCenal."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).parents[2] / "plugins/arcenal-supervisor/security"
if "arcenal_security" not in sys.modules:
    SPEC = importlib.util.spec_from_file_location(
        "arcenal_security",
        PACKAGE / "__init__.py",
        submodule_search_locations=[str(PACKAGE)],
    )
    assert SPEC and SPEC.loader
    module = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = module
    SPEC.loader.exec_module(module)

from arcenal_security.audit import AuditWriteError, append_event  # noqa: E402


class AuditTests(unittest.TestCase):
    def test_events_are_chained_and_secrets_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["ARCENAL_AUDIT_DIR"] = directory
            first = append_event("action.requested", "admin", {"token": "secret"})
            second = append_event("action.completed", "admin", {"action_id": "nginx.reload"})
            lines = Path(directory, "actions.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual(first["details"], {"token": "[EXPURGÉ]"})
        self.assertEqual(second["previous_hash"], first["hash"])
        self.assertNotIn("secret", json.dumps(first))

    def test_empty_log_starts_a_new_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["ARCENAL_AUDIT_DIR"] = directory
            event = append_event("action.requested", "admin", {})

        self.assertEqual(event["previous_hash"], "")

    def test_corrupted_chain_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["ARCENAL_AUDIT_DIR"] = directory
            Path(directory, "actions.jsonl").write_text("not-json\n", encoding="utf-8")

            with self.assertRaises(AuditWriteError):
                append_event("action.requested", "admin", {})


if __name__ == "__main__":
    unittest.main()
