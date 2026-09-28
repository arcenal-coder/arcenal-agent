from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _load_plugin_api() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_product_overview", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module de supervision ARCenal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_plugin_api()


def test_os_release_name_reads_pretty_name() -> None:
    source = Path("/etc/os-release")
    with patch.object(Path, "read_text", return_value='NAME="Debian"\nPRETTY_NAME="Debian GNU/Linux 13"\n'):
        assert MODULE._os_release_name(source) == "Debian GNU/Linux 13"


def test_os_release_name_handles_missing_file() -> None:
    source = Path("/etc/os-release")
    with patch.object(Path, "read_text", side_effect=OSError("lecture impossible")):
        assert MODULE._os_release_name(source) == "Indisponible"


def test_yunohost_version_refuses_failed_probe() -> None:
    with patch.object(MODULE, "_run", return_value=(127, "commande absente")):
        assert MODULE._yunohost_version() == "Non détecté"


def test_yunohost_version_uses_first_output_line() -> None:
    with patch.object(MODULE, "_run", return_value=(0, "yunohost 12.1.40\nyunohost-admin 12.1")):
        assert MODULE._yunohost_version() == "yunohost 12.1.40"
