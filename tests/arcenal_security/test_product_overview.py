from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


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


def test_platform_versions_expose_release_traceability(monkeypatch) -> None:
    monkeypatch.setenv("ARCENAL_RELEASE", "0.21.0-arcenal21")
    monkeypatch.setenv("ARCENAL_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ARCENAL_PACKAGE_VERSION", "0.21.0~ynh36")

    versions = MODULE._platform_versions()

    assert versions["arc"] == "0.21.0-arcenal21"
    assert versions["source_revision"] == "a" * 40
    assert versions["package"] == "0.21.0~ynh36"


def test_platform_versions_keep_explicit_unknown_metadata(monkeypatch) -> None:
    monkeypatch.delenv("ARCENAL_RELEASE", raising=False)
    monkeypatch.delenv("ARCENAL_SOURCE_REVISION", raising=False)
    monkeypatch.delenv("ARCENAL_PACKAGE_VERSION", raising=False)

    with patch.object(MODULE, "_installed_distribution_version", return_value="0.21.0+arcenal.6"):
        versions = MODULE._platform_versions()

    assert versions["arc"] == "0.21.0+arcenal.6"
    assert versions["source_revision"] == "Non vérifié"
    assert versions["package"] == "Non vérifié"


def test_release_metadata_rejects_invalid_external_value(monkeypatch) -> None:
    monkeypatch.setenv("ARCENAL_SOURCE_REVISION", "branche-flottante")

    with pytest.raises(MODULE.ReleaseMetadataError, match="ARCENAL_SOURCE_REVISION"):
        MODULE._platform_versions()
