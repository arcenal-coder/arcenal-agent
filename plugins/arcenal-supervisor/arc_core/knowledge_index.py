"""Index documentaire dérivé, atomique et reconstruisible."""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .knowledge_chunking import chunk_document
from .knowledge_models import KnowledgeDocument, KnowledgeIndex
from .knowledge_source import MarkdownKnowledgeSource


_INDEX_LOCK = threading.Lock()


class KnowledgeIndexError(RuntimeError):
    """Signale un index absent, invalide ou impossible à écrire."""


class KnowledgeIndexRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> KnowledgeIndex:
        try:
            return KnowledgeIndex.model_validate_json(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KnowledgeIndexError("L’index documentaire doit être reconstruit.") from exc
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise KnowledgeIndexError("L’index documentaire est invalide.") from exc

    def save(self, index: KnowledgeIndex) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".knowledge-index.", dir=self._path.parent)
        self._replace(descriptor, Path(temporary_name), index)

    def delete(self) -> None:
        self._path.unlink(missing_ok=True)

    def _replace(self, descriptor: int, temporary: Path, index: KnowledgeIndex) -> None:
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(index.model_dump_json(indent=2))
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise KnowledgeIndexError("Écriture atomique de l’index impossible.") from exc


class KnowledgeIndexer:
    def __init__(self, source: MarkdownKnowledgeSource, repository: KnowledgeIndexRepository) -> None:
        self._source = source
        self._repository = repository

    def rebuild(self) -> KnowledgeIndex:
        with _INDEX_LOCK:
            return self._rebuild_locked()

    def _rebuild_locked(self) -> KnowledgeIndex:
        self._repository.delete()
        documents, bodies, errors = self._load_sources()
        chunks = tuple(chunk for document, body in zip(documents, bodies, strict=True) for chunk in chunk_document(document, body))
        index = KnowledgeIndex(built_at=datetime.now(timezone.utc), documents=documents, chunks=chunks, errors=errors)
        self._repository.save(index)
        return index

    def current_or_rebuild(self) -> KnowledgeIndex:
        try:
            return self._repository.load()
        except KnowledgeIndexError:
            return self.rebuild()

    def _load_sources(self) -> tuple[tuple[KnowledgeDocument, ...], tuple[str, ...], tuple[str, ...]]:
        loaded, errors = self._source.load()
        return tuple(item[0] for item in loaded), tuple(item[1] for item in loaded), errors


IndexAuditWriter = Callable[[str, str, dict[str, object]], object]
