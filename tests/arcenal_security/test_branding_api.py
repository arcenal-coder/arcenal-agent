"""Tests de la frontière d’import des ressources graphiques."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SOURCE = Path(__file__).parents[2] / "plugins/arcenal-supervisor/dashboard/branding_api.py"
SPEC = importlib.util.spec_from_file_location("arcenal_branding_api", SOURCE)
assert SPEC and SPEC.loader
branding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(branding)


class BrandingAssetTests(unittest.TestCase):
    def test_valid_png_is_stored_under_a_fixed_name(self) -> None:
        root = MagicMock(spec=Path)
        destination = MagicMock(spec=Path)
        root.__truediv__.return_value = destination

        with patch.object(branding, "_branding_root", return_value=root):
            result = branding.store_brand_asset("logo", "image/png", b"\x89PNG\r\n\x1a\ncontent")

        self.assertIs(result, destination)
        destination.write_bytes.assert_called_once()
        destination.chmod.assert_called_once_with(0o600)

    def test_empty_or_oversized_asset_is_rejected(self) -> None:
        with self.assertRaises(branding.BrandingAssetError):
            branding.validate_brand_asset("logo", "image/png", b"")
        oversized = b"\x89PNG\r\n\x1a\n" + b"x" * branding.MAX_ASSET_BYTES
        with self.assertRaises(branding.BrandingAssetError):
            branding.validate_brand_asset("logo", "image/png", oversized)

    def test_spoofed_or_unknown_asset_is_rejected(self) -> None:
        with self.assertRaises(branding.BrandingAssetError):
            branding.validate_brand_asset("logo", "image/png", b"<script>")
        with self.assertRaises(branding.BrandingAssetError):
            branding.validate_brand_asset("background", "image/jpeg", b"\xff\xd8\xff")


if __name__ == "__main__":
    unittest.main()
