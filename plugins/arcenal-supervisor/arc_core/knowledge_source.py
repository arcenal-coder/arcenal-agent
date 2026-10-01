"""Normalisation du coffre Markdown canonique vers le RAG central."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .knowledge_models import ConfidentialityLevel, DocumentStatus, KnowledgeDocument, SourceType


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
LIST_VALUE_RE = re.compile(r"[,;]")


class KnowledgeSourceError(RuntimeError):
    """Signale une source documentaire impossible à normaliser."""


class KnowledgeSource(Protocol):
    def load(self) -> tuple[tuple[tuple[KnowledgeDocument, str], ...], tuple[str, ...]]: ...


class CompositeKnowledgeSource:
    def __init__(self, sources: tuple[KnowledgeSource, ...]) -> None:
        self._sources = sources

    def load(self) -> tuple[tuple[tuple[KnowledgeDocument, str], ...], tuple[str, ...]]:
        loaded: list[tuple[KnowledgeDocument, str]] = []
        errors: list[str] = []
        for source in self._sources:
            documents, source_errors = source.load()
            loaded.extend(documents)
            errors.extend(source_errors)
        return tuple(loaded), tuple(errors)


class MarkdownKnowledgeSource:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def load(self) -> tuple[tuple[tuple[KnowledgeDocument, str], ...], tuple[str, ...]]:
        documents: list[tuple[KnowledgeDocument, str]] = []
        errors: list[str] = []
        for path in self._paths():
            try:
                documents.append(self._load_path(path))
            except KnowledgeSourceError as exc:
                errors.append(str(exc))
        return tuple(documents), tuple(errors)

    def _paths(self) -> Iterable[Path]:
        if not self._root.exists():
            return ()
        return (
            path
            for path in sorted(self._root.rglob("*.md"))
            if not {".history", ".attachments"}.intersection(path.relative_to(self._root).parts)
        )

    def _load_path(self, path: Path) -> tuple[KnowledgeDocument, str]:
        try:
            content = path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(content)
            return self._document(path, metadata, body), body
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise KnowledgeSourceError(f"Source illisible : {path.name}") from exc

    def _document(self, path: Path, metadata: dict[str, str], body: str) -> KnowledgeDocument:
        relative = path.relative_to(self._root).as_posix()
        scopes = _values(metadata, "knowledge_scopes", "scopes", "tags") or ("company",)
        return KnowledgeDocument(
            document_id=metadata.get("document_id", relative),
            title=_title(metadata, body, path),
            reference=metadata.get("reference", path.stem.upper()),
            version=metadata.get("version", metadata.get("revision", "1")),
            status=_status(metadata.get("statut", "Brouillon")),
            owner=metadata.get("proprietaire", ""),
            domain=metadata.get("domaine", metadata.get("activite", metadata.get("perimetre", ""))),
            knowledge_scopes=scopes,
            confidentiality=_confidentiality(metadata.get("confidentialite", "internal")),
            applicable_from=metadata.get("date_application", ""),
            review_date=metadata.get("prochaine_revue", ""),
            source_type=_source_type(metadata.get("source_type", "markdown")),
            source_path=relative,
            updated_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
            allowed_applications=_values(metadata, "applications"),
            allowed_agents=_values(metadata, "agents"),
            allowed_users=_values(metadata, "utilisateurs", "users"),
            required_permissions=_values(metadata, "permissions"),
        )


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(content)
    if match is None:
        return {}, content.strip()
    return _metadata(match.group(1).splitlines()), content[match.end() :].strip()


def _metadata(lines: list[str]) -> dict[str, str]:
    pairs = (line.partition(":") for line in lines)
    return {
        key.strip().lower(): value.strip().strip('"\'')
        for key, separator, value in pairs
        if separator and key.strip()
    }


def _values(metadata: dict[str, str], *keys: str) -> tuple[str, ...]:
    raw = next((metadata[key] for key in keys if metadata.get(key)), "")
    cleaned = raw.strip().removeprefix("[").removesuffix("]")
    return tuple(dict.fromkeys(item.strip().strip('"\'').casefold() for item in LIST_VALUE_RE.split(cleaned) if item.strip()))


def _title(metadata: dict[str, str], body: str, path: Path) -> str:
    heading = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), "")
    return metadata.get("titre", heading or path.stem.replace("-", " ").title())


def _status(value: str) -> DocumentStatus:
    try:
        return DocumentStatus(value)
    except ValueError:
        return DocumentStatus.DRAFT


def _confidentiality(value: str) -> ConfidentialityLevel:
    try:
        return ConfidentialityLevel(value.casefold())
    except ValueError:
        return ConfidentialityLevel.INTERNAL


def _source_type(value: str) -> SourceType:
    try:
        return SourceType(value.casefold())
    except ValueError:
        return SourceType.MARKDOWN
