"""Assemblage du RAG central sur les répertoires persistants ARCenal."""

from __future__ import annotations

from pathlib import Path

from .knowledge_index import KnowledgeIndexer, KnowledgeIndexError, KnowledgeIndexRepository
from .knowledge_metrics import KnowledgeMetricsError, KnowledgeMetricsRepository
from .knowledge_models import KnowledgeIndex, KnowledgeIndexStatus, KnowledgeMetricsState
from .knowledge_search import KnowledgeRetriever, RagAuditWriter
from .knowledge_source import CompositeKnowledgeSource, MarkdownKnowledgeSource
from .memory_repository import EnterpriseMemoryRepository
from .memory_source import EnterpriseMemoryKnowledgeSource


def create_retriever(home: Path, audit: RagAuditWriter | None = None) -> KnowledgeRetriever:
    indexer = create_indexer(home)
    metrics = KnowledgeMetricsRepository(_metrics_path(home))
    return KnowledgeRetriever(indexer, metrics, audit)


def create_indexer(home: Path) -> KnowledgeIndexer:
    memory_repository = EnterpriseMemoryRepository(memory_database_path(home))
    source = CompositeKnowledgeSource((
        MarkdownKnowledgeSource(home / "knowledge"),
        EnterpriseMemoryKnowledgeSource(memory_repository),
    ))
    repository = KnowledgeIndexRepository(_index_path(home))
    return KnowledgeIndexer(source, repository)


def rebuild_index(home: Path) -> KnowledgeIndex:
    return create_indexer(home).rebuild()


def index_status(home: Path) -> KnowledgeIndexStatus:
    index = _load_index(home)
    metrics = _load_metrics(home)
    searches = metrics.searches
    return KnowledgeIndexStatus(
        documents=len(index.documents) if index else 0,
        chunks=len(index.chunks) if index else 0,
        built_at=index.built_at if index else None,
        errors=index.errors if index else ("Index non construit.",),
        searches=searches,
        average_duration_ms=_average(metrics.duration_ms_total, searches),
        average_documents_found=_average(metrics.documents_found_total, searches),
        average_chunks_selected=_average(metrics.chunks_selected_total, searches),
        no_result_rate=_average(metrics.no_results, searches),
        average_context_characters=_average(metrics.context_characters_total, searches),
        average_context_tokens_estimated=_average(metrics.context_tokens_total, searches),
        sources_by_agent=metrics.sources_by_agent,
        memories=sum(document.source_type.value == "enterprise_memory" for document in index.documents) if index else 0,
        memory_chunks_selected=metrics.memory_chunks_selected_total,
        average_memory_chunks_per_search=_average(metrics.memory_chunks_selected_total, searches),
    )


def _load_index(home: Path) -> KnowledgeIndex | None:
    try:
        return KnowledgeIndexRepository(_index_path(home)).load()
    except KnowledgeIndexError:
        return None


def _load_metrics(home: Path) -> KnowledgeMetricsState:
    try:
        return KnowledgeMetricsRepository(_metrics_path(home)).load()
    except KnowledgeMetricsError:
        return KnowledgeMetricsState()


def _average(total: int, count: int) -> float:
    return round(total / count, 2) if count else 0.0


def _index_path(home: Path) -> Path:
    return home / "arcenal" / "knowledge-index.json"


def _metrics_path(home: Path) -> Path:
    return home / "arcenal" / "knowledge-metrics.json"


def memory_database_path(home: Path) -> Path:
    return home / "arcenal" / "enterprise-memory.sqlite3"
