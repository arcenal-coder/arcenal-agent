"""Agrégats sobres du RAG, sans contenu documentaire ni requête brute."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

from pydantic import ValidationError

from .knowledge_models import KnowledgeMetricsState, RetrievalMetrics


_METRICS_LOCK = threading.Lock()


class KnowledgeMetricsError(RuntimeError):
    """Signale une impossibilité de persister les métriques RAG."""


class KnowledgeMetricsRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> KnowledgeMetricsState:
        if not self._path.is_file():
            return KnowledgeMetricsState()
        try:
            return KnowledgeMetricsState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise KnowledgeMetricsError("Les métriques RAG sont invalides.") from exc

    def record(self, agent_id: str, metrics: RetrievalMetrics) -> KnowledgeMetricsState:
        with _METRICS_LOCK:
            return self._record_locked(agent_id, metrics)

    def _record_locked(self, agent_id: str, metrics: RetrievalMetrics) -> KnowledgeMetricsState:
        current = self.load()
        agents = {**current.sources_by_agent, agent_id: current.sources_by_agent.get(agent_id, 0) + metrics.chunks_selected}
        updated = KnowledgeMetricsState(
            searches=current.searches + 1,
            no_results=current.no_results + int(metrics.chunks_selected == 0),
            duration_ms_total=current.duration_ms_total + metrics.duration_ms,
            documents_found_total=current.documents_found_total + metrics.documents_selected,
            chunks_selected_total=current.chunks_selected_total + metrics.chunks_selected,
            context_characters_total=current.context_characters_total + metrics.context_characters,
            context_tokens_total=current.context_tokens_total + metrics.context_tokens_estimated,
            sources_by_agent=agents,
            memory_chunks_selected_total=current.memory_chunks_selected_total + metrics.memory_chunks_selected,
        )
        self._save(updated)
        return updated

    def _save(self, metrics: KnowledgeMetricsState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".knowledge-metrics.", dir=self._path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(metrics.model_dump_json(indent=2))
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise KnowledgeMetricsError("Écriture des métriques RAG impossible.") from exc
