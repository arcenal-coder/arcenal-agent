from pathlib import Path

import pytest

from arcenal_runtime import require_yunohost_installation


def test_runtime_accepts_yunohost_marker(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / ".arcenal-yunohost"
    marker.write_text("managed-by-yunohost\n", encoding="utf-8")
    monkeypatch.setenv("ARCENAL_YUNOHOST_MARKER", str(marker))

    require_yunohost_installation()


def test_runtime_rejects_missing_yunohost_marker(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ARCENAL_YUNOHOST_MARKER", str(tmp_path / "missing"))
    monkeypatch.delenv("ARCENAL_DEV_MODE", raising=False)

    with pytest.raises(SystemExit, match="exclusivement.*YunoHost"):
        require_yunohost_installation()


def test_runtime_allows_explicit_development_mode(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ARCENAL_YUNOHOST_MARKER", str(tmp_path / "missing"))
    monkeypatch.setenv("ARCENAL_DEV_MODE", "1")

    require_yunohost_installation()
