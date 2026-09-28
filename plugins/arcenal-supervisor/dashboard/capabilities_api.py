"""API d’inventaire gouverné des outils accessibles à ARC."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/capabilities")


def _load_capabilities() -> ModuleType:
    source = Path(__file__).parents[1] / "capabilities.py"
    spec = importlib.util.spec_from_file_location("arcenal_capabilities", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des capacités ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


capabilities = _load_capabilities()


@router.get("")
def list_capabilities() -> dict[str, object]:
    try:
        return {"capabilities": capabilities.capability_rows(), "usage": capabilities.read_usage()}
    except capabilities.CapabilityUsageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
