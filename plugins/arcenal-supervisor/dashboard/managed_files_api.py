"""Gestion bornée des fichiers de contexte et de directives ARC."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/managed-files")

MAX_CONTENT_BYTES = 1_048_576
VERSION_RE = re.compile(r"^\d{8}T\d{12}Z$")
ACTOR_RE = re.compile(r"[^\w@.+\- ]", re.UNICODE)

MANAGED_FILES: dict[str, dict[str, str]] = {
    "context": {
        "category": "context",
        "filename": "CONTEXT.md",
        "label": "Contexte de l’organisation",
        "role": "Décrit l’organisation, ses activités, équipes, produits et vocabulaire.",
    },
    "agents": {
        "category": "directive",
        "filename": "AGENTS.md",
        "label": "Règles des agents",
        "role": "Définit le comportement commun des agents ARCenal.",
    },
    "rules": {
        "category": "directive",
        "filename": "RULES.md",
        "label": "Règles opérationnelles",
        "role": "Encadre les décisions et les actions opérationnelles.",
    },
    "security": {
        "category": "directive",
        "filename": "SECURITY.md",
        "label": "Directive de sécurité",
        "role": "Fixe les limites qui ne peuvent pas être contournées par une conversation.",
    },
    "tools": {
        "category": "directive",
        "filename": "TOOLS.md",
        "label": "Politique des outils",
        "role": "Décrit les outils autorisés et leurs conditions d’utilisation.",
    },
}


class ManagedFileWrite(BaseModel):
    """Contenu Markdown et auteur transmis à la frontière HTTP."""

    content: str = Field(max_length=MAX_CONTENT_BYTES)


class ManagedFileRestore(BaseModel):
    """Confirmation explicite exigée avant une restauration."""

    confirmed: bool


def managed_root() -> Path:
    """Retourne l’espace privé réservé aux instructions administrées."""
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = home / "arcenal" / "managed-files"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root.resolve()


def _definition(file_id: str) -> dict[str, str]:
    definition = MANAGED_FILES.get(file_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Fichier administré inconnu.")
    return definition


def _target(file_id: str) -> Path:
    definition = _definition(file_id)
    return managed_root() / definition["filename"]


def _metadata_path(file_id: str) -> Path:
    _definition(file_id)
    return managed_root() / f".{file_id}.metadata.json"


def _history_root(file_id: str) -> Path:
    _definition(file_id)
    return managed_root() / ".history" / file_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _now()).strftime("%Y%m%dT%H%M%S%fZ")


def _actor(request: Request) -> str:
    header_names = ("x-remote-user", "remote-user", "x-auth-user")
    raw = next(
        (request.headers.get(name, "") for name in header_names if request.headers.get(name)),
        "",
    )
    cleaned = ACTOR_RE.sub("", raw).strip()
    return cleaned[:120] or "administrateur"


def _validate_content(content: str) -> None:
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise HTTPException(status_code=413, detail="Le fichier dépasse 1 Mio.")
    if "\x00" in content:
        raise HTTPException(status_code=422, detail="Le contenu Markdown est invalide.")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Lecture du fichier administré impossible.") from exc


def _read_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Métadonnées administrées illisibles.") from exc
    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="Métadonnées administrées invalides.")
    return {str(key): str(value) for key, value in raw.items()}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Écriture du fichier administré impossible.") from exc


def _write_json(path: Path, values: dict[str, str]) -> None:
    _atomic_write(path, json.dumps(values, ensure_ascii=False, indent=2) + "\n")


def _current_metadata(file_id: str) -> dict[str, str]:
    return _read_json(_metadata_path(file_id))


def _version_metadata(file_id: str, version_id: str) -> dict[str, str]:
    return _read_json(_history_root(file_id) / f"{version_id}.json")


def _archive_current(file_id: str) -> None:
    target = _target(file_id)
    if not target.is_file():
        return
    version_id = _timestamp()
    metadata = _current_metadata(file_id)
    _atomic_write(_history_root(file_id) / f"{version_id}.md", _read_text(target))
    _write_json(_history_root(file_id) / f"{version_id}.json", {**metadata, "version_id": version_id})


def _history(file_id: str) -> list[dict[str, str]]:
    root = _history_root(file_id)
    if not root.is_dir():
        return []
    versions = [_history_item(file_id, path.stem) for path in sorted(root.glob("*.md"), reverse=True)]
    return versions


def _history_item(file_id: str, version_id: str) -> dict[str, str]:
    metadata = _version_metadata(file_id, version_id)
    return {
        "version_id": version_id,
        "author": metadata.get("author", "administrateur"),
        "updated_at": metadata.get("updated_at", ""),
    }


def _summary(file_id: str) -> dict[str, object]:
    definition = _definition(file_id)
    target = _target(file_id)
    metadata = _current_metadata(file_id)
    return {
        "id": file_id,
        **definition,
        "status": "actif" if target.is_file() else "à créer",
        "author": metadata.get("author", ""),
        "updated_at": metadata.get("updated_at", ""),
        "history_count": len(_history(file_id)),
    }


def read_managed_file(file_id: str) -> dict[str, object]:
    return {"file": _summary(file_id), "content": _read_text(_target(file_id))}


def write_managed_file(file_id: str, content: str, author: str) -> dict[str, object]:
    _validate_content(content)
    _archive_current(file_id)
    updated_at = _now().isoformat()
    _atomic_write(_target(file_id), content)
    _write_json(_metadata_path(file_id), {"author": author, "updated_at": updated_at})
    return read_managed_file(file_id)


def restore_managed_file(file_id: str, version_id: str, author: str) -> dict[str, object]:
    if not VERSION_RE.fullmatch(version_id):
        raise HTTPException(status_code=422, detail="Version historique invalide.")
    archived = _history_root(file_id) / f"{version_id}.md"
    if not archived.is_file():
        raise HTTPException(status_code=404, detail="Version historique introuvable.")
    return write_managed_file(file_id, _read_text(archived), author)


def search_context(query: str) -> list[dict[str, str]]:
    detail = read_managed_file("context")
    terms = {word.casefold() for word in re.findall(r"[\wÀ-ÿ-]{2,}", query)}
    sections = _markdown_sections(str(detail["content"]))
    scored = [(_section_score(section, terms), title, section) for title, section in sections]
    return [
        {"section": title, "content": section[:1200]}
        for score, title, section in sorted(scored, reverse=True)
        if score > 0
    ][:5]


def _section_score(section: str, terms: set[str]) -> int:
    normalized = section.casefold()
    return sum(normalized.count(term) for term in terms)


def _markdown_sections(content: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = [("Contexte", [])]
    for line in content.splitlines():
        if line.startswith("#") and line.lstrip("#").startswith(" "):
            sections.append((line.lstrip("# ").strip() or "Section", []))
            continue
        sections[-1][1].append(line)
    populated = ((title, "\n".join(lines).strip()) for title, lines in sections)
    return [(title, text) for title, text in populated if text]


@router.get("")
def list_managed_files(category: str | None = None) -> dict[str, object]:
    if category not in {None, "context", "directive"}:
        raise HTTPException(status_code=422, detail="Catégorie de fichier invalide.")
    identifiers = [
        file_id
        for file_id, item in MANAGED_FILES.items()
        if category is None or item["category"] == category
    ]
    return {"files": [_summary(file_id) for file_id in identifiers]}


@router.get("/{file_id}")
def get_managed_file(file_id: str) -> dict[str, object]:
    return read_managed_file(file_id)


@router.put("/{file_id}")
def save_managed_file(
    file_id: str,
    payload: ManagedFileWrite,
    request: Request,
) -> dict[str, object]:
    return write_managed_file(file_id, payload.content, _actor(request))


@router.get("/{file_id}/history")
def managed_file_history(file_id: str) -> dict[str, object]:
    _definition(file_id)
    return {"versions": _history(file_id)}


@router.post("/{file_id}/restore/{version_id}")
def restore_file(
    file_id: str,
    version_id: str,
    payload: ManagedFileRestore,
    request: Request,
) -> dict[str, object]:
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="La restauration doit être confirmée.")
    return restore_managed_file(file_id, version_id, _actor(request))
