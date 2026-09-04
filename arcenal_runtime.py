"""Règles de distribution propres à ARCenal.

ARCenal est distribué comme application YunoHost. Ce petit module reste séparé
des composants internes Hermes afin de simplifier les fusions avec upstream.
"""

from __future__ import annotations

import os
from pathlib import Path


YUNOHOST_MARKER_CONTENT = "managed-by-yunohost"


def yunohost_marker_path() -> Path:
    """Renvoie le marqueur écrit par le paquet YunoHost ARCenal."""
    override = os.environ.get("ARCENAL_YUNOHOST_MARKER", "").strip()
    if override:
        return Path(override).expanduser()

    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        return Path(hermes_home).expanduser() / ".arcenal-yunohost"

    return Path.home() / ".hermes" / ".arcenal-yunohost"


def require_yunohost_installation() -> None:
    """Refuse l'exécution hors de l'installation YunoHost prise en charge.

    ``ARCENAL_DEV_MODE=1`` est volontairement explicite et réservé au
    développement et à la CI. Le paquet de production ne doit jamais l'activer.
    """
    if os.environ.get("ARCENAL_DEV_MODE", "") == "1":
        return

    marker = yunohost_marker_path()
    try:
        valid_marker = marker.is_file() and marker.read_text(
            encoding="utf-8"
        ).strip() == YUNOHOST_MARKER_CONTENT
    except OSError:
        valid_marker = False

    if valid_marker:
        return

    raise SystemExit(
        "ARCenal Agent fonctionne exclusivement comme application YunoHost.\n"
        "Installez-le avec le paquet ARCenal pour YunoHost.\n"
        "Pour contribuer au code source uniquement, définissez "
        "ARCENAL_DEV_MODE=1."
    )
