#!/usr/bin/env python3
"""Active et vérifie la configuration native ARC d’une installation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_core(application_root: Path) -> ModuleType:
    source = application_root / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location("arcenal_arc_core", source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable dans les sources installées.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def migrate(application_root: Path, data_root: Path) -> dict[str, object]:
    runtime = _load_core(application_root).runtime_configuration(data_root)
    if runtime.backend != "arc":
        raise RuntimeError("La migration refuse d’activer un backend autre qu’ARC.")
    return {
        "backend": runtime.backend, "conflicts": list(runtime.migration.conflicts),
        "copied": runtime.migration.copied, "status": runtime.migration_state,
        "unchanged": runtime.migration.unchanged,
    }


def main(arguments: list[str]) -> int:
    if len(arguments) != 3:
        raise RuntimeError("Usage : arcenal_config_migrate.py APPLICATION_ROOT DATA_ROOT")
    report = migrate(Path(arguments[1]).resolve(), Path(arguments[2]).resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
