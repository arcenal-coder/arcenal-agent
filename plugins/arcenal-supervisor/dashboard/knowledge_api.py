"""Coffre documentaire ARCenal : Markdown, LDA et wiki salarié."""

from __future__ import annotations

import mimetypes
import os
import re
import sys
import tempfile
import fcntl
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge")

ALLOWED_STATUSES = (
    "Brouillon",
    "En révision",
    "À approuver",
    "Applicable",
    "Archivé",
)
MAX_DOCUMENT_BYTES = 1_048_576
MAX_ATTACHMENT_BYTES = 20 * 1_048_576
ALLOWED_ATTACHMENT_SUFFIXES = {".docx", ".md", ".odt", ".pdf", ".txt"}
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
WORD_RE = re.compile(r"[\wÀ-ÿ-]{2,}", re.UNICODE)
HISTORY_ID_RE = re.compile(r"^\d{8}T\d{12}Z$")
STATUS_TRANSITIONS = {
    "Brouillon": {"En révision", "Archivé"},
    "En révision": {"À approuver", "Archivé"},
    "À approuver": {"En révision", "Applicable", "Archivé"},
    "Applicable": {"Archivé"},
    "Archivé": {"En révision"},
}
KNOWLEDGE_WRITE_LOCK = threading.RLock()


class DocumentWrite(BaseModel):
    """Contenu Markdown validé avant écriture dans le coffre."""

    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_DOCUMENT_BYTES)


class SearchRequest(BaseModel):
    """Recherche plein texte bornée pour le RAG."""

    query: str = Field(min_length=2, max_length=300)
    limit: int = Field(default=8, ge=1, le=30)


class WorkflowRequest(BaseModel):
    """Transition documentaire contrôlée et motivée."""

    status: str = Field(max_length=30)
    reason: str = Field(default="", max_length=500)


def knowledge_root() -> Path:
    """Retourne le coffre privé attaché au répertoire de données ARC."""
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    root = home / "knowledge"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root.resolve()


@contextmanager
def _knowledge_write_lock() -> Iterator[None]:
    with KNOWLEDGE_WRITE_LOCK:
        lock_path = knowledge_root() / ".integrity.lock"
        with lock_path.open("a+b") as handle:
            lock_path.chmod(0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _safe_path(relative_path: str, writable: bool = False) -> Path:
    """Résout un chemin Markdown sans permettre de sortir du coffre."""
    candidate = Path(relative_path.strip().replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or ".history" in candidate.parts:
        raise HTTPException(status_code=422, detail="Chemin documentaire invalide.")
    if writable and candidate.parts[:1] == (".silverbullet",):
        raise HTTPException(status_code=409, detail="Modifiez ce document depuis SilverBullet, puis synchronisez ARC.")
    if candidate.suffix.lower() != ".md":
        raise HTTPException(status_code=422, detail="Seuls les documents Markdown sont acceptés.")
    target = (knowledge_root() / candidate).resolve()
    if knowledge_root().resolve() not in target.parents:
        raise HTTPException(status_code=422, detail="Chemin documentaire invalide.")
    return target


def _safe_attachment_name(filename: str) -> str:
    cleaned = Path(filename.replace("\\", "/")).name.strip()
    cleaned = re.sub(r"[^\w .()\-]", "_", cleaned, flags=re.UNICODE)
    if not cleaned or Path(cleaned).suffix.lower() not in ALLOWED_ATTACHMENT_SUFFIXES:
        raise HTTPException(status_code=422, detail="Format de pièce jointe non accepté.")
    return cleaned[:180]


def _attachment_relative_path(document_path: str, filename: str) -> Path:
    document = Path(document_path)
    return Path(".attachments") / document.parent / document.stem / filename


def _safe_attachment_path(relative_path: str) -> Path:
    candidate = Path(relative_path.strip().replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or candidate.parts[:1] != (".attachments",):
        raise HTTPException(status_code=422, detail="Chemin de pièce jointe invalide.")
    target = (knowledge_root() / candidate).resolve()
    if knowledge_root() not in target.parents:
        raise HTTPException(status_code=422, detail="Chemin de pièce jointe invalide.")
    return target


def _frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Lit le sous-ensemble YAML nécessaire au modèle documentaire ARCenal."""
    match = FRONTMATTER_RE.match(content)
    if match is None:
        return {}, content.strip()
    metadata = _parse_metadata_lines(match.group(1).splitlines())
    return metadata, content[match.end() :].strip()


def _parse_metadata_lines(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition(":")
        if separator and key.strip():
            metadata[key.strip().lower()] = value.strip().strip('"\'')
    return metadata


def _tags(raw: str) -> list[str]:
    cleaned = raw.strip().removeprefix("[").removesuffix("]")
    return [tag.strip().strip('"\'') for tag in cleaned.split(",") if tag.strip()]


def _title(metadata: dict[str, str], body: str, path: Path) -> str:
    if metadata.get("titre"):
        return metadata["titre"]
    heading = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), "")
    return heading or path.stem.replace("-", " ").replace("_", " ").title()


def _excerpt(body: str, limit: int = 180) -> str:
    plain = re.sub(r"[#>*_`\[\]]", "", body)
    compact = " ".join(plain.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1].rstrip()}…"


def _status(metadata: dict[str, str]) -> str:
    status = metadata.get("statut", "Brouillon")
    return status if status in ALLOWED_STATUSES else "Brouillon"


def _document_summary(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    metadata, body = _frontmatter(content)
    relative = path.relative_to(knowledge_root()).as_posix()
    return {
        "path": relative,
        "reference": metadata.get("reference", ""),
        "title": _title(metadata, body, path),
        "type": metadata.get("type", "Note"),
        "version": metadata.get("version", metadata.get("revision", "1")),
        "activity": metadata.get("activite", metadata.get("perimetre", "")),
        "number": metadata.get("numerotation", metadata.get("reference", "")),
        "change_type": metadata.get("nature", "Création"),
        "validation_date": metadata.get("date_validation", metadata.get("date_application", "")),
        "revision": metadata.get("revision", metadata.get("version", "1")),
        "reason": metadata.get("motif", ""),
        "attachment_name": metadata.get("piece_jointe_nom", ""),
        "attachment_path": metadata.get("piece_jointe", ""),
        "attachment_size": _integer(metadata.get("piece_jointe_taille", "0")),
        "status": _status(metadata),
        "owner": metadata.get("proprietaire", ""),
        "approved_by": metadata.get("approbateur", ""),
        "application_date": metadata.get("date_application", ""),
        "review_date": metadata.get("prochaine_revue", ""),
        "scope": metadata.get("perimetre", ""),
        "tags": _tags(metadata.get("tags", "")),
        "links": sorted(set(LINK_RE.findall(body))),
        "backlinks": [],
        "excerpt": _excerpt(body),
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "history_count": _history_count(path),
        "confidentiality": metadata.get("confidentialite", "internal"),
        "knowledge_scopes": _tags(metadata.get("knowledge_scopes", metadata.get("scopes", metadata.get("tags", "company")))) or ["company"],
        "indexed_at": None,
        "origin": "silverbullet" if relative.startswith(".silverbullet/") else "arcenal",
        "read_only": relative.startswith(".silverbullet/"),
    }


def list_documents() -> list[dict[str, Any]]:
    """Liste les notes lisibles et ignore un document isolé devenu invalide."""
    documents: list[dict[str, Any]] = []
    root = knowledge_root()
    for path in sorted(root.rglob("*.md")):
        if {".history", ".attachments"}.intersection(path.relative_to(root).parts):
            continue
        try:
            resolved = path.resolve(strict=True)
            if root not in resolved.parents:
                continue
            documents.append(_document_summary(resolved))
        except (OSError, UnicodeDecodeError):
            continue
    return documents


def _integer(value: str) -> int:
    try:
        return max(0, int(value))
    except ValueError:
        return 0


def _statistics(documents: list[dict[str, Any]]) -> dict[str, int]:
    applicable = sum(item["status"] == "Applicable" for item in documents)
    pending = sum(item["status"] in {"En révision", "À approuver"} for item in documents)
    overdue = sum(_is_overdue(str(item["review_date"])) for item in documents)
    return {"documents": len(documents), "applicable": applicable, "pending": pending, "overdue": overdue}


def _is_overdue(raw_date: str) -> bool:
    if not raw_date:
        return False
    try:
        return datetime.fromisoformat(raw_date).date() < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def knowledge_overview() -> dict[str, Any]:
    """Produit les vues cohérentes du coffre, de la LDA et du wiki."""
    documents = _with_backlinks(list_documents())
    status = _index_status()
    indexed_at = status.get("built_at")
    enriched = [{**item, "indexed_at": indexed_at} for item in documents]
    applicable = [item for item in enriched if item["status"] == "Applicable"]
    return {
        "documents": enriched,
        "lda": sorted(applicable, key=lambda item: (item["reference"], item["title"])),
        "wiki": sorted(applicable, key=lambda item: (item["type"], item["title"])),
        "statistics": _statistics(documents),
        "statuses": list(ALLOWED_STATUSES),
        "index": status,
    }


def _with_backlinks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for target in documents:
        aliases = _document_aliases(target)
        sources = [
            item["title"]
            for item in documents
            if item["path"] != target["path"]
            and aliases.intersection(link.casefold() for link in item["links"])
        ]
        enriched.append({**target, "backlinks": sorted(set(sources))})
    return enriched


def _document_aliases(document: dict[str, Any]) -> set[str]:
    stem = Path(str(document["path"])).stem.replace("-", " ").replace("_", " ")
    return {str(document["title"]).casefold(), str(document["reference"]).casefold(), stem.casefold()} - {""}


def wiki_overview() -> dict[str, Any]:
    """N'expose aux salariés que les métadonnées des versions publiées."""
    overview = knowledge_overview()
    published = overview["wiki"]
    return {
        "documents": published,
        "lda": published,
        "wiki": published,
        "statistics": {"documents": len(published), "applicable": len(published), "pending": 0, "overdue": 0},
        "statuses": ["Applicable"],
        "index": overview["index"],
    }


def _validate_content(content: str) -> None:
    encoded_size = len(content.encode("utf-8"))
    if encoded_size > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Le document dépasse 1 Mio.")
    metadata, _body = _frontmatter(content)
    status = metadata.get("statut", "Brouillon")
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail="Statut documentaire invalide.")


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, target)
        target.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Écriture du document impossible.") from exc


def _atomic_write_bytes(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, target)
        target.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Enregistrement de la pièce jointe impossible.") from exc


def _history_directory(target: Path) -> Path:
    relative = target.relative_to(knowledge_root())
    return knowledge_root() / ".history" / relative.parent / relative.stem


def _history_count(target: Path) -> int:
    history = _history_directory(target)
    return len(list(history.glob("*.md"))) if history.is_dir() else 0


def _archive_existing(target: Path) -> None:
    if not target.is_file():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = _history_directory(target) / f"{stamp}.md"
    try:
        _atomic_write(archive, target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Archivage de la version précédente impossible.") from exc


def read_document(relative_path: str) -> dict[str, Any]:
    target = _safe_path(relative_path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Document introuvable.")
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Lecture du document impossible.") from exc
    return {"document": _document_summary(target), "content": content}


def _write_document_locked(payload: DocumentWrite, allow_status_change: bool = True) -> dict[str, Any]:
    _validate_content(payload.content)
    target = _safe_path(payload.path, writable=True)
    _assert_unique_document_identity(payload.content, target)
    if target.is_file() and not allow_status_change:
        _reject_direct_status_change(target, payload.content)
    _archive_existing(target)
    _atomic_write(target, payload.content)
    _rebuild_index()
    return {"ok": True, "document": _document_summary(target)}


def write_document(payload: DocumentWrite, allow_status_change: bool = True) -> dict[str, Any]:
    with _knowledge_write_lock():
        return _write_document_locked(payload, allow_status_change)


def _create_document_locked(payload: DocumentWrite) -> dict[str, Any]:
    payload = _versioned_payload(payload)
    target = _safe_path(payload.path, writable=True)
    if target.exists():
        raise HTTPException(status_code=409, detail="Un document existe déjà à cet emplacement.")
    return _write_document_locked(payload)


def create_document(payload: DocumentWrite) -> dict[str, Any]:
    with _knowledge_write_lock():
        return _create_document_locked(payload)


def _versioned_payload(payload: DocumentWrite) -> DocumentWrite:
    target = _safe_path(payload.path, writable=True)
    reference, version = _document_identity(payload.content)
    _assert_unique_document_identity(payload.content, target)
    if not target.exists():
        return payload
    current_reference, _current_version = _document_identity(target.read_text(encoding="utf-8"))
    if not reference or _normalize_identity(reference) != _normalize_identity(current_reference):
        raise HTTPException(status_code=409, detail="Un document existe déjà à cet emplacement.")
    version_slug = re.sub(r"[^a-z0-9]+", "-", version.casefold()).strip("-")
    if not version_slug:
        raise HTTPException(status_code=422, detail="La version documentaire est obligatoire.")
    relative = target.with_name(f"{target.stem}-v{version_slug}.md").relative_to(knowledge_root()).as_posix()
    return payload.model_copy(update={"path": relative})


def _document_identity(content: str) -> tuple[str, str]:
    metadata, _body = _frontmatter(content)
    return metadata.get("reference", "").strip(), metadata.get("version", metadata.get("revision", "")).strip()


def _normalize_identity(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _assert_unique_document_identity(content: str, target: Path) -> None:
    reference, version = _document_identity(content)
    if not reference or not version:
        return
    identity = (_normalize_identity(reference), _normalize_identity(version))
    for document in list_documents():
        if _safe_path(str(document["path"])) == target:
            continue
        candidate = (_normalize_identity(str(document["reference"])), _normalize_identity(str(document["version"])))
        if candidate == identity:
            raise HTTPException(status_code=409, detail="Cette référence et cette version documentaires existent déjà.")


def _reject_initial_publication(content: str) -> None:
    status = _status(_frontmatter(content)[0])
    if status in {"Applicable", "Archivé"}:
        raise HTTPException(status_code=409, detail="Un document doit suivre le circuit de validation.")


def _reject_direct_status_change(target: Path, content: str) -> None:
    current = _status(_frontmatter(target.read_text(encoding="utf-8"))[0])
    requested = _status(_frontmatter(content)[0])
    if current != requested:
        raise HTTPException(status_code=409, detail="Utilisez le circuit de validation pour changer le statut.")


def _replace_metadata(content: str, updates: dict[str, str]) -> str:
    metadata, body = _frontmatter(content)
    merged = {**metadata, **updates}
    frontmatter = "\n".join(f"{key}: {value}" for key, value in merged.items())
    return f"---\n{frontmatter}\n---\n{body.rstrip()}\n"


def transition_document(path: str, status: str, actor: str, reason: str = "") -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail="Statut documentaire invalide.")
    current = read_document(path)
    previous = str(current["document"]["status"])
    if status not in STATUS_TRANSITIONS.get(previous, set()):
        raise HTTPException(status_code=409, detail=f"Transition {previous} vers {status} interdite.")
    updates = _workflow_metadata(status, actor, reason)
    if status == "Applicable":
        _archive_previous_applicable(current["document"])
    payload = DocumentWrite(path=path, content=_replace_metadata(str(current["content"]), updates))
    return write_document(payload)


def _workflow_metadata(status: str, actor: str, reason: str) -> dict[str, str]:
    updates = {"statut": status, "derniere_action_par": actor}
    if reason.strip():
        updates["motif"] = reason.strip()
    if status == "Applicable":
        today = datetime.now(timezone.utc).date().isoformat()
        updates.update({"approbateur": actor, "date_validation": today, "date_application": today})
    return updates


def _archive_previous_applicable(document: dict[str, Any]) -> None:
    reference = str(document["reference"])
    if not reference:
        return
    for sibling in list_documents():
        if sibling["path"] == document["path"] or sibling["reference"] != reference:
            continue
        if sibling["status"] == "Applicable":
            _set_sibling_archived(str(sibling["path"]))


def _set_sibling_archived(path: str) -> None:
    sibling = read_document(path)
    content = _replace_metadata(str(sibling["content"]), {"statut": "Archivé"})
    write_document(DocumentWrite(path=path, content=content))


def list_history(path: str) -> list[dict[str, str]]:
    target = _safe_path(path)
    history = _history_directory(target)
    if not history.is_dir():
        return []
    return [_history_summary(version) for version in sorted(history.glob("*.md"), reverse=True)]


def _history_summary(path: Path) -> dict[str, str]:
    metadata, body = _frontmatter(path.read_text(encoding="utf-8"))
    return {
        "id": path.stem,
        "status": _status(metadata),
        "title": _title(metadata, body, path),
        "version": metadata.get("version", metadata.get("revision", "1")),
    }


def restore_history(path: str, version_id: str) -> dict[str, Any]:
    if not HISTORY_ID_RE.fullmatch(version_id):
        raise HTTPException(status_code=422, detail="Version historique invalide.")
    target = _safe_path(path, writable=True)
    version = _history_directory(target) / f"{version_id}.md"
    if not version.is_file():
        raise HTTPException(status_code=404, detail="Version historique introuvable.")
    content = version.read_text(encoding="utf-8")
    return write_document(DocumentWrite(path=path, content=content))


def _authenticated_actor(request: Request) -> str:
    actor = request.headers.get("remote-user") or request.headers.get("x-remote-user")
    if not actor or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}", actor):
        raise HTTPException(status_code=401, detail="Administrateur YunoHost non identifié.")
    return actor


def create_document_with_attachment(
    payload: DocumentWrite, filename: str, media_type: str, data: bytes
) -> dict[str, Any]:
    with _knowledge_write_lock():
        payload = _versioned_payload(payload)
        safe_name = _safe_attachment_name(filename)
        _validate_attachment(data, safe_name)
        relative = _attachment_relative_path(payload.path, safe_name)
        attachment = _safe_attachment_path(relative.as_posix())
        if attachment.exists():
            raise HTTPException(status_code=409, detail="Cette pièce jointe existe déjà.")
        _atomic_write_bytes(attachment, data)
        try:
            enriched = _with_attachment(payload.content, relative, safe_name, media_type, len(data))
            enriched = _with_extracted_content(enriched, safe_name, data)
            return _create_document_locked(DocumentWrite(path=payload.path, content=enriched))
        except Exception:
            attachment.unlink(missing_ok=True)
            raise


def _validate_attachment(data: bytes, filename: str) -> None:
    if not data:
        raise HTTPException(status_code=422, detail="La pièce jointe est vide.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="La pièce jointe dépasse 20 Mio.")
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Le fichier PDF est invalide.")
    if suffix in {".docx", ".odt"} and not data.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=422, detail="Le document bureautique est invalide.")
    if suffix in {".md", ".txt"}:
        _validate_text_attachment(data)


def _validate_text_attachment(data: bytes) -> None:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Le document texte doit être encodé en UTF-8.") from exc


def _with_attachment(content: str, path: Path, name: str, media_type: str, size: int) -> str:
    safe_media = media_type.replace("\n", "").replace("\r", "")[:120]
    metadata = (
        f"piece_jointe: {path.as_posix()}\n"
        f"piece_jointe_nom: {name}\n"
        f"piece_jointe_type: {safe_media}\n"
        f"piece_jointe_taille: {size}\n"
    )
    if content.startswith("---\n"):
        content = content.replace("---\n", f"---\n{metadata}", 1)
    encoded_path = quote(path.as_posix(), safe="")
    return f"{content.rstrip()}\n\n## Document source\n\n[{name}](/api/plugins/arcenal-supervisor/knowledge/attachment?path={encoded_path})\n"


def _with_extracted_content(content: str, name: str, data: bytes) -> str:
    core = _load_arc_core()
    try:
        extracted = core.extract_attachment_text(name, data)
    except core.DocumentExtractionUnavailable as exc:
        return _append_extraction_status(content, str(exc))
    except core.DocumentExtractionError as exc:
        if Path(name).suffix.casefold() == ".pdf":
            return _append_extraction_status(content, str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return f"{content.rstrip()}\n\n## Contenu extrait\n\n{extracted}\n"


def _append_extraction_status(content: str, message: str) -> str:
    safe_message = message.replace("\n", " ").replace("\r", " ")
    return f"{content.rstrip()}\n\n## État de l’extraction\n\n{safe_message}\n"


async def _read_upload(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1_048_576):
        size += len(chunk)
        if size > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=413, detail="La pièce jointe dépasse 20 Mio.")
        chunks.append(chunk)
    return b"".join(chunks)


def read_wiki_document(relative_path: str) -> dict[str, Any]:
    result = read_document(relative_path)
    if result["document"]["status"] != "Applicable":
        raise HTTPException(status_code=404, detail="Document publié introuvable.")
    return result


def _query_terms(query: str) -> set[str]:
    return {word.casefold() for word in WORD_RE.findall(query)}


def _score_document(terms: set[str], summary: dict[str, Any], content: str) -> int:
    title = str(summary["title"]).casefold()
    reference = str(summary["reference"]).casefold()
    body = content.casefold()
    return sum((6 if term in reference else 0) + (4 if term in title else 0) + body.count(term) for term in terms)


def search_documents(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Effectue la première étape RAG et restitue des sources traçables."""
    terms = _query_terms(query)
    results: list[dict[str, Any]] = []
    for summary in list_documents():
        document = read_document(str(summary["path"]))
        score = _score_document(terms, summary, str(document["content"]))
        if score > 0:
            results.append({**summary, "score": score})
    return sorted(results, key=lambda item: (-item["score"], item["title"]))[:limit]


def _load_arc_core() -> ModuleType:
    name = "arcenal_arc_core"
    if name in sys.modules:
        return sys.modules[name]
    from importlib.util import module_from_spec, spec_from_file_location

    source = Path(__file__).parents[1] / "arc_core" / "__init__.py"
    spec = spec_from_file_location(name, source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _index_status() -> dict[str, object]:
    from hermes_constants import get_hermes_home

    status = _load_arc_core().index_status(get_hermes_home())
    return status.model_dump(mode="json")


def _rebuild_index() -> dict[str, object]:
    from hermes_constants import get_hermes_home

    index = _load_arc_core().rebuild_index(get_hermes_home())
    return {"ok": True, "index": _index_status(), "built_at": index.built_at.isoformat()}


@router.get("/overview")
def overview() -> dict[str, Any]:
    return knowledge_overview()


@router.get("/index/status")
def knowledge_index_status() -> dict[str, object]:
    return _index_status()


@router.post("/index/rebuild")
def rebuild_knowledge_index(request: Request) -> dict[str, object]:
    _authenticated_actor(request)
    if request.query_params.get("confirmed") != "true":
        raise HTTPException(status_code=409, detail="La reconstruction de l’index doit être confirmée.")
    return _rebuild_index()


@router.get("/document")
def document(path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    return read_document(path)


@router.put("/document")
def save_document(payload: DocumentWrite) -> dict[str, Any]:
    return write_document(payload, allow_status_change=False)


@router.post("/document", status_code=201)
def new_document(payload: DocumentWrite) -> dict[str, Any]:
    _reject_initial_publication(payload.content)
    return create_document(payload)


@router.post("/document/upload", status_code=201)
async def upload_document(
    path: str = Form(..., min_length=1, max_length=240),
    content: str = Form(..., max_length=MAX_DOCUMENT_BYTES),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    try:
        _reject_initial_publication(content)
        data = await _read_upload(file)
        return create_document_with_attachment(
            DocumentWrite(path=path, content=content), file.filename or "", file.content_type or "", data
        )
    finally:
        await file.close()


@router.get("/attachment")
def attachment(path: str = Query(min_length=1, max_length=500)) -> FileResponse:
    target = _safe_attachment_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable.")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=target.name)


@router.get("/wiki/overview")
def published_wiki() -> dict[str, Any]:
    return wiki_overview()


@router.get("/wiki/document")
def published_document(path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    return read_wiki_document(path)


@router.post("/search")
def search(payload: SearchRequest) -> dict[str, Any]:
    return {"query": payload.query, "results": search_documents(payload.query, payload.limit)}


@router.post("/document/workflow")
def document_workflow(path: str, payload: WorkflowRequest, request: Request) -> dict[str, Any]:
    return transition_document(path, payload.status, _authenticated_actor(request), payload.reason)


@router.get("/document/history")
def document_history(path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    return {"versions": list_history(path)}


@router.post("/document/history/{version_id}/restore")
def restore_document_version(request: Request, version_id: str, path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    _authenticated_actor(request)
    if request.query_params.get("confirmed") != "true":
        raise HTTPException(status_code=409, detail="La restauration doit être confirmée.")
    return restore_history(path, version_id)
