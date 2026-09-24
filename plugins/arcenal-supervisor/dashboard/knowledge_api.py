"""Coffre documentaire ARCenal : Markdown, LDA et wiki salarié."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
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
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
WORD_RE = re.compile(r"[\wÀ-ÿ-]{2,}", re.UNICODE)


class DocumentWrite(BaseModel):
    """Contenu Markdown validé avant écriture dans le coffre."""

    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_DOCUMENT_BYTES)


class SearchRequest(BaseModel):
    """Recherche plein texte bornée pour le RAG."""

    query: str = Field(min_length=2, max_length=300)
    limit: int = Field(default=8, ge=1, le=30)


def knowledge_root() -> Path:
    """Retourne le coffre privé attaché au répertoire de données ARC."""
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = home / "knowledge"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root.resolve()


def _safe_path(relative_path: str) -> Path:
    """Résout un chemin Markdown sans permettre de sortir du coffre."""
    candidate = Path(relative_path.strip().replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or ".history" in candidate.parts:
        raise HTTPException(status_code=422, detail="Chemin documentaire invalide.")
    if candidate.suffix.lower() != ".md":
        raise HTTPException(status_code=422, detail="Seuls les documents Markdown sont acceptés.")
    target = (knowledge_root() / candidate).resolve()
    if knowledge_root().resolve() not in target.parents:
        raise HTTPException(status_code=422, detail="Chemin documentaire invalide.")
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
        "version": metadata.get("version", "1"),
        "status": _status(metadata),
        "owner": metadata.get("proprietaire", ""),
        "application_date": metadata.get("date_application", ""),
        "review_date": metadata.get("prochaine_revue", ""),
        "scope": metadata.get("perimetre", ""),
        "tags": _tags(metadata.get("tags", "")),
        "links": sorted(set(LINK_RE.findall(body))),
        "backlinks": [],
        "excerpt": _excerpt(body),
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "history_count": _history_count(path),
    }


def list_documents() -> list[dict[str, Any]]:
    """Liste les notes lisibles et ignore un document isolé devenu invalide."""
    documents: list[dict[str, Any]] = []
    root = knowledge_root()
    for path in sorted(root.rglob("*.md")):
        if ".history" in path.relative_to(root).parts:
            continue
        try:
            resolved = path.resolve(strict=True)
            if root not in resolved.parents:
                continue
            documents.append(_document_summary(resolved))
        except (OSError, UnicodeDecodeError):
            continue
    return documents


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
    applicable = [item for item in documents if item["status"] == "Applicable"]
    return {
        "documents": documents,
        "lda": sorted(applicable, key=lambda item: (item["reference"], item["title"])),
        "wiki": sorted(applicable, key=lambda item: (item["type"], item["title"])),
        "statistics": _statistics(documents),
        "statuses": list(ALLOWED_STATUSES),
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


def write_document(payload: DocumentWrite) -> dict[str, Any]:
    _validate_content(payload.content)
    target = _safe_path(payload.path)
    _archive_existing(target)
    _atomic_write(target, payload.content)
    return {"ok": True, "document": _document_summary(target)}


def create_document(payload: DocumentWrite) -> dict[str, Any]:
    target = _safe_path(payload.path)
    if target.exists():
        raise HTTPException(status_code=409, detail="Un document existe déjà à cet emplacement.")
    return write_document(payload)


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


@router.get("/overview")
def overview() -> dict[str, Any]:
    return knowledge_overview()


@router.get("/document")
def document(path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    return read_document(path)


@router.put("/document")
def save_document(payload: DocumentWrite) -> dict[str, Any]:
    return write_document(payload)


@router.post("/document", status_code=201)
def new_document(payload: DocumentWrite) -> dict[str, Any]:
    return create_document(payload)


@router.get("/wiki/overview")
def published_wiki() -> dict[str, Any]:
    return wiki_overview()


@router.get("/wiki/document")
def published_document(path: str = Query(min_length=1, max_length=240)) -> dict[str, Any]:
    return read_wiki_document(path)


@router.post("/search")
def search(payload: SearchRequest) -> dict[str, Any]:
    return {"query": payload.query, "results": search_documents(payload.query, payload.limit)}
