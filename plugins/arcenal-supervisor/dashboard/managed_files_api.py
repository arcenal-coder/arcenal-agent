"""Gestion bornée des fichiers de contexte et de directives ARC."""

from __future__ import annotations

import hashlib
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
    "memory": {
        "category": "memory",
        "filename": "MEMORY.md",
        "label": "Mémoire durable",
        "role": "Conserve les décisions, préférences, conventions, projets et actions.",
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


class MemoryEntryWrite(BaseModel):
    """Entrée mémoire validée à la frontière HTTP."""

    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=16_000)


class MemoryEntryDelete(BaseModel):
    """Confirmation exigée avant une suppression de mémoire."""

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
    if file_id == "memory" and content.strip() and not content.startswith("# Mémoire ARC"):
        raise HTTPException(status_code=422, detail="Le format de MEMORY.md est invalide.")
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


def _memory_id(title: str, content: str) -> str:
    source = f"{title}\n{content}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()[:16]


def _memory_entries(content: str) -> list[dict[str, str]]:
    blocks = re.split(r"(?m)^##\s+", content)
    entries: list[dict[str, str]] = []
    for block in blocks[1:]:
        title, separator, body = block.partition("\n")
        normalized_title = title.strip()
        normalized_body = body.strip() if separator else ""
        if normalized_title and normalized_body:
            entries.append(_memory_entry(normalized_title, normalized_body))
    return entries


def _memory_entry(title: str, content: str) -> dict[str, str]:
    return {"id": _memory_id(title, content), "title": title, "content": content}


def _serialize_memory(entries: list[dict[str, str]]) -> str:
    sections = [f"## {entry['title']}\n\n{entry['content']}" for entry in entries]
    body = "\n\n".join(sections)
    return f"# Mémoire ARC\n\n{body}\n" if body else "# Mémoire ARC\n"


def _normalized_memory(payload: MemoryEntryWrite) -> tuple[str, str]:
    title = payload.title.strip()
    content = payload.content.strip()
    if not title or not content:
        raise HTTPException(status_code=422, detail="Le titre et le contenu sont obligatoires.")
    if "\n" in title or "\r" in title or re.search(r"(?m)^##\s+", content):
        raise HTTPException(status_code=422, detail="La structure de l’entrée mémoire est invalide.")
    _validate_content(content)
    return title, content


def _memory_index(entries: list[dict[str, str]], entry_id: str) -> int:
    index = next((position for position, item in enumerate(entries) if item["id"] == entry_id), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="Entrée mémoire introuvable.")
    return index


def list_memory_entries(query: str = "") -> list[dict[str, str]]:
    entries = _memory_entries(_read_text(_target("memory")))
    normalized = query.strip().casefold()
    if not normalized:
        return entries
    return [entry for entry in entries if normalized in f"{entry['title']}\n{entry['content']}".casefold()]


def add_memory_entry(payload: MemoryEntryWrite, author: str) -> dict[str, str]:
    title, content = _normalized_memory(payload)
    entries = list_memory_entries()
    entry = _memory_entry(title, content)
    if any(item["id"] == entry["id"] for item in entries):
        raise HTTPException(status_code=409, detail="Cette entrée mémoire existe déjà.")
    write_managed_file("memory", _serialize_memory([*entries, entry]), author)
    return entry


def update_memory_entry(entry_id: str, payload: MemoryEntryWrite, author: str) -> dict[str, str]:
    title, content = _normalized_memory(payload)
    entries = list_memory_entries()
    index = _memory_index(entries, entry_id)
    replacement = _memory_entry(title, content)
    if any(item["id"] == replacement["id"] for position, item in enumerate(entries) if position != index):
        raise HTTPException(status_code=409, detail="Cette entrée mémoire existe déjà.")
    updated = [replacement if position == index else item for position, item in enumerate(entries)]
    write_managed_file("memory", _serialize_memory(updated), author)
    return replacement


def delete_memory_entry(entry_id: str, author: str) -> None:
    entries = list_memory_entries()
    index = _memory_index(entries, entry_id)
    updated = [item for position, item in enumerate(entries) if position != index]
    write_managed_file("memory", _serialize_memory(updated), author)


@router.get("")
def list_managed_files(category: str | None = None) -> dict[str, object]:
    if category not in {None, "context", "directive", "memory"}:
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


@router.get("/memory/entries")
def memory_entries(query: str = "") -> dict[str, object]:
    return {"entries": list_memory_entries(query)}


@router.post("/memory/entries")
def create_memory_entry(payload: MemoryEntryWrite, request: Request) -> dict[str, object]:
    return {"entry": add_memory_entry(payload, _actor(request))}


@router.put("/memory/entries/{entry_id}")
def edit_memory_entry(
    entry_id: str,
    payload: MemoryEntryWrite,
    request: Request,
) -> dict[str, object]:
    return {"entry": update_memory_entry(entry_id, payload, _actor(request))}


@router.post("/memory/entries/{entry_id}/delete")
def remove_memory_entry(
    entry_id: str,
    payload: MemoryEntryDelete,
    request: Request,
) -> dict[str, bool]:
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="La suppression doit être confirmée.")
    delete_memory_entry(entry_id, _actor(request))
    return {"deleted": True}
