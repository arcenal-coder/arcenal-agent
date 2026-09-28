"""Ressources graphiques persistantes et contrôlées d’ARCenal."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse


router = APIRouter(prefix="/branding")
MAX_ASSET_BYTES = 2 * 1024 * 1024
KINDS = frozenset({"logo", "favicon"})
SIGNATURES = {"image/png": ("png", b"\x89PNG\r\n\x1a\n"), "image/jpeg": ("jpg", b"\xff\xd8\xff")}


class BrandingAssetError(ValueError):
    """Signale une ressource graphique externe invalide."""


def _branding_root() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return home / "arcenal" / "branding"


def validate_brand_asset(kind: str, content_type: str, payload: bytes) -> str:
    if kind not in KINDS:
        raise BrandingAssetError("Le type de ressource graphique est inconnu.")
    signature = SIGNATURES.get(content_type)
    if signature is None or not payload.startswith(signature[1]):
        raise BrandingAssetError("Le fichier doit être une image PNG ou JPEG valide.")
    if not payload or len(payload) > MAX_ASSET_BYTES:
        raise BrandingAssetError("L’image doit peser au maximum 2 Mo.")
    return signature[0]


def store_brand_asset(kind: str, content_type: str, payload: bytes) -> Path:
    suffix = validate_brand_asset(kind, content_type, payload)
    root = _branding_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _remove_previous_assets(root, kind)
    destination = root / f"{kind}.{suffix}"
    destination.write_bytes(payload)
    destination.chmod(0o600)
    return destination


def _remove_previous_assets(root: Path, kind: str) -> None:
    for suffix in ("png", "jpg"):
        (root / f"{kind}.{suffix}").unlink(missing_ok=True)


def _existing_asset(kind: str) -> Path:
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Ressource graphique inconnue.")
    for suffix in ("png", "jpg"):
        candidate = _branding_root() / f"{kind}.{suffix}"
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="Ressource graphique absente.")


@router.post("/assets")
async def upload_brand_asset(
    asset_type: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> dict[str, object]:
    payload = await file.read(MAX_ASSET_BYTES + 1)
    try:
        path = store_brand_asset(asset_type, file.content_type or "", payload)
    except BrandingAssetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"kind": asset_type, "size": len(payload), "url": f"/api/plugins/arcenal-supervisor/branding/assets/{asset_type}", "filename": path.name}


@router.get("/assets/{asset_type}")
def brand_asset(asset_type: str) -> FileResponse:
    path = _existing_asset(asset_type)
    media_type = "image/png" if path.suffix == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, max-age=300"})
