from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "system_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_system_api_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module système est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class SystemApiTests(TestCase):
    def test_collection_normalizes_a_mapping(self) -> None:
        with patch.object(MODULE, "_read_json", return_value=({"apps": {"nextcloud": {"version": "30"}}}, "")):
            result = MODULE._collection("yunohost.apps.read", ("apps",))

        self.assertEqual(result["items"], [{"id": "nextcloud", "version": "30"}])
        self.assertEqual(result["error"], "")

    def test_collection_surfaces_yunohost_error(self) -> None:
        with patch.object(MODULE, "_read_json", return_value=(None, "Accès refusé")):
            result = MODULE._collection("yunohost.backups.read", ("archives",))

        self.assertEqual(result, {"items": [], "error": "Accès refusé"})

    def test_invalid_domain_never_reaches_command_runner(self) -> None:
        with patch.object(MODULE, "_read_json") as reader:
            result = MODULE._certificate("../../root")

        reader.assert_not_called()
        self.assertEqual(result["error"], "Nom de domaine invalide.")
