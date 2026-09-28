"""Tests des confirmations critiques à usage unique."""

from __future__ import annotations

import importlib.util
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

from arcenal_security.approvals import ApprovalError, consume_approval, issue_approval  # noqa: E402


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        os.environ["ARCENAL_APPROVAL_DB"] = str(Path(self.directory.name, "approvals.sqlite3"))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_matching_approval_is_consumed(self) -> None:
        approval_id = issue_approval("admin", "nginx.reload", None)

        consume_approval(approval_id, "admin", "nginx.reload", None)

        with self.assertRaises(ApprovalError):
            consume_approval(approval_id, "admin", "nginx.reload", None)

    def test_approval_cannot_authorize_another_target(self) -> None:
        approval_id = issue_approval("admin", "service.restart", "nginx")

        with self.assertRaises(ApprovalError):
            consume_approval(approval_id, "admin", "service.restart", "slapd")

    def test_invalid_expiry_is_rejected(self) -> None:
        with self.assertRaises(ApprovalError):
            issue_approval("admin", "nginx.reload", None, ttl_seconds=0)


if __name__ == "__main__":
    unittest.main()
