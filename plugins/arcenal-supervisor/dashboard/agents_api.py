"""Administration bornée de la mémoire isolée des agents ARCenal."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/agents")
PROFILE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class AgentMemoryUpdate(BaseModel):
    """Contenu Markdown borné de la mémoire propre à un agent."""

    content: str = Field(max_length=100_000)


class AgentMemoryResponse(BaseModel):
    """Mémoire présentable sans exposer le reste du profil."""

    content: str
    profile: str
    updated_at: str | None


def _profile_dir(name: str) -> Path:
    if not PROFILE_NAME_PATTERN.fullmatch(name) or name == "default":
        raise HTTPException(status_code=422, detail="Identifiant d’agent invalide.")
    from hermes_cli import profiles as profiles_mod

    profile = next((item for item in profiles_mod.list_profiles() if item.name == name), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="Agent introuvable.")
    return Path(profile.path).resolve()


def _memory_path(name: str) -> Path:
    root = _profile_dir(name)
    path = root / "memories" / "MEMORY.md"
    if root not in path.resolve().parents:
        raise HTTPException(status_code=422, detail="Chemin de mémoire invalide.")
    return path


def _read_memory(name: str) -> AgentMemoryResponse:
    path = _memory_path(name)
    try:
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        updated_at = path.stat().st_mtime if path.is_file() else None
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Mémoire de l’agent illisible.") from exc
    timestamp = datetime.fromtimestamp(updated_at, timezone.utc).isoformat() if updated_at is not None else None
    return AgentMemoryResponse(content=content, profile=name, updated_at=timestamp)


def _write_memory(name: str, content: str) -> AgentMemoryResponse:
    path = _memory_path(name)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".memory.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Mémoire de l’agent impossible à enregistrer.") from exc
    return _read_memory(name)


@router.get("/{name}/memory", response_model=AgentMemoryResponse)
def get_agent_memory(name: str) -> AgentMemoryResponse:
    return _read_memory(name)


@router.put("/{name}/memory", response_model=AgentMemoryResponse)
def update_agent_memory(name: str, request: AgentMemoryUpdate) -> AgentMemoryResponse:
    return _write_memory(name, request.content)
