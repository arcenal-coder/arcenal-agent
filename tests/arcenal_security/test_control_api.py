"""Tests du routage fermé entre les deux sockets ARCenal."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor"


def _load_security() -> ModuleType:
    spec = importlib.util.spec_from_file_location("security", ROOT / "security" / "__init__.py", submodule_search_locations=[str(ROOT / "security")])
    if spec is None or spec.loader is None:
        raise RuntimeError("Le contrat de sécurité ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_control_api() -> ModuleType:
    _load_security()
    spec = importlib.util.spec_from_file_location("arcenal_control_api_test", ROOT / "control_api.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("L’API de contrôle ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_read_action_uses_the_readonly_socket() -> None:
    module = _load_control_api()

    assert module._broker_executor("yunohost.version.read") is module.execute_readonly


def test_controlled_action_keeps_the_privileged_socket() -> None:
    module = _load_control_api()

    assert module._broker_executor("service.restart") is module.execute
