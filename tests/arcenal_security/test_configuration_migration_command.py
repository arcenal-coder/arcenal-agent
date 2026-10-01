from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_command() -> ModuleType:
    source = Path(__file__).parents[2] / "scripts" / "arcenal_config_migrate.py"
    spec = importlib.util.spec_from_file_location("arcenal_config_migrate_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("La commande de migration ARC est introuvable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMAND = _load_command()


def test_command_activates_native_configuration_without_legacy_file(tmp_path: Path) -> None:
    application_root = Path(__file__).parents[2]

    report = COMMAND.migrate(application_root, tmp_path)

    assert report == {"backend": "arc", "conflicts": [], "copied": 0, "status": "not_required", "unchanged": 0}
    assert (tmp_path / "arcenal" / "config.json").is_file()
