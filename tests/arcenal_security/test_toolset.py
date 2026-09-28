"""Tests de la surface d'outils livrée au superviseur ARC."""

from __future__ import annotations

import unittest

from toolsets import resolve_toolset


FORBIDDEN_TOOLS = frozenset(
    {
        "cronjob",
        "browser_exec",
        "browser_navigate",
        "delegate_task",
        "execute_code",
        "patch",
        "process",
        "read_file",
        "terminal",
        "write_file",
    }
)


class ArcenalToolsetTests(unittest.TestCase):
    def test_supervision_tools_are_available(self) -> None:
        tools = set(resolve_toolset("arcenal-admin"))

        self.assertIn("arcenal_system_status", tools)
        self.assertIn("arcenal_repair", tools)
        self.assertIn("arcenal_knowledge_search", tools)

    def test_local_execution_tools_are_absent(self) -> None:
        tools = set(resolve_toolset("arcenal-admin"))

        self.assertFalse(tools & FORBIDDEN_TOOLS)


if __name__ == "__main__":
    unittest.main()
