"""Pont vers le journal d’audit chaîné déjà fourni par ARCenal."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _audit_module() -> ModuleType:
    name = "arcenal_agent_audit"
    if name in sys.modules:
        return sys.modules[name]
    source = Path(__file__).parents[1] / "security" / "audit.py"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le journal d’audit ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def append_agent_event(event: str, actor: str, details: dict[str, object]) -> object:
    return _audit_module().append_event(event, actor, details)
