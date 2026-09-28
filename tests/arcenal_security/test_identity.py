"""Tests de l'identité administrateur héritée de YunoHost."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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

from arcenal_security.identity import (  # noqa: E402
    AdministratorDeniedError,
    AdministratorLookupError,
    administrator_actor,
)


class IdentityTests(unittest.TestCase):
    def test_yunohost_admin_is_accepted(self) -> None:
        with patch("arcenal_security.identity.grp.getgrnam", return_value=SimpleNamespace(gr_mem=["alice"])):
            actor = administrator_actor("alice", "alice")

        self.assertEqual(actor.roles, ("admins", "owner"))

    def test_non_admin_is_rejected(self) -> None:
        with patch("arcenal_security.identity.grp.getgrnam", return_value=SimpleNamespace(gr_mem=["alice"])):
            with self.assertRaises(AdministratorDeniedError):
                administrator_actor("bob", "alice")

    def test_missing_admin_group_fails_closed(self) -> None:
        with patch("arcenal_security.identity.grp.getgrnam", side_effect=KeyError("admins")):
            with self.assertRaises(AdministratorLookupError):
                administrator_actor("alice", "alice")


if __name__ == "__main__":
    unittest.main()
