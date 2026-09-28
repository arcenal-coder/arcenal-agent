"""Tests unitaires de la politique de sécurité ARCenal."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


PACKAGE = Path(__file__).parents[2] / "plugins/arcenal-supervisor/security"
SPEC = importlib.util.spec_from_file_location(
    "arcenal_security",
    PACKAGE / "__init__.py",
    submodule_search_locations=[str(PACKAGE)],
)
assert SPEC and SPEC.loader
security = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = security
SPEC.loader.exec_module(security)


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin = security.Actor(username="admin", roles=("admins",))

    def test_read_action_is_allowed_without_confirmation(self) -> None:
        request = security.ActionRequest("yunohost.apps.read", self.admin)

        decision = security.evaluate_action(request)

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.confirmation_required)

    def test_level_three_action_requires_confirmation(self) -> None:
        request = security.ActionRequest("nginx.reload", self.admin)

        decision = security.evaluate_action(request)

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.confirmation_required)

    def test_level_three_action_accepts_explicit_confirmation(self) -> None:
        request = security.ActionRequest("nginx.reload", self.admin, confirmed=True)

        decision = security.evaluate_action(request)

        self.assertTrue(decision.allowed)

    def test_unknown_target_is_rejected(self) -> None:
        request = security.ActionRequest(
            "service.restart",
            self.admin,
            target="ssh",
            confirmed=True,
        )

        decision = security.evaluate_action(request)

        self.assertFalse(decision.allowed)
        self.assertIn("cible", decision.reason)

    def test_backup_restore_accepts_only_a_bounded_archive_name(self) -> None:
        valid = security.ActionRequest("arcenal.backup.restore", self.admin, "arcenal-manual", True)
        invalid = security.ActionRequest("arcenal.backup.restore", self.admin, "../../etc/passwd", True)

        self.assertTrue(security.evaluate_action(valid).allowed)
        self.assertFalse(security.evaluate_action(invalid).allowed)

    def test_notification_accepts_an_email_but_rejects_header_injection(self) -> None:
        valid = security.ActionRequest("arcenal.notification.test", self.admin, "admin@example.test")
        invalid = security.ActionRequest("arcenal.notification.test", self.admin, "admin@example.test\nBcc:x@example.test")

        self.assertTrue(security.evaluate_action(valid).allowed)
        self.assertFalse(security.evaluate_action(invalid).allowed)

    def test_non_admin_is_rejected(self) -> None:
        actor = security.Actor(username="reader", roles=("all_users",))
        request = security.ActionRequest("yunohost.version.read", actor)

        decision = security.evaluate_action(request)

        self.assertFalse(decision.allowed)

    def test_empty_identity_is_rejected(self) -> None:
        with self.assertRaises(security.SecurityContractError):
            security.Actor(username=" ", roles=("admins",))

    def test_control_characters_in_identity_are_rejected(self) -> None:
        with self.assertRaises(security.SecurityContractError):
            security.Actor(username="admin\nforged", roles=("admins",))

    def test_unknown_action_is_rejected(self) -> None:
        request = security.ActionRequest("shell.execute", self.admin)

        with self.assertRaises(security.SecurityContractError):
            security.evaluate_action(request)


if __name__ == "__main__":
    unittest.main()
