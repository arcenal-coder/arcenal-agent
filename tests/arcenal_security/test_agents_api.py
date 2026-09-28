from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "agents_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_agents_api_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des agents est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class AgentMemoryTests(TestCase):
    def test_memory_round_trip_is_isolated_in_the_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "_profile_dir", return_value=Path(directory)):
            written = MODULE._write_memory("veille", "# Mémoire\nUne préférence.")
            read = MODULE._read_memory("veille")

        self.assertEqual(written.content, read.content)
        self.assertEqual(read.profile, "veille")
        self.assertIsNotNone(read.updated_at)

    def test_default_profile_cannot_be_targeted(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE._profile_dir("default")

        self.assertEqual(raised.exception.status_code, 422)

    def test_invalid_profile_name_is_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            MODULE._profile_dir("../default")
