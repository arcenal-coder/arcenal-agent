"""Recherche lexicale filtrée, reranking et budget du RAG central."""

from __future__ import annotations

import re
from collections.abc import Callable
from time import perf_counter

from .knowledge_acl import KnowledgeAcl
from .knowledge_index import KnowledgeIndexer
from .knowledge_metrics import KnowledgeMetricsRepository
from .knowledge_models import (
    ContextPlan,
    KnowledgeChunk,
    KnowledgeDocument,
    RetrievalMetrics,
    RetrievalResult,
    RetrievedChunk,
    SourceCitation,
)


WORD_RE = re.compile(r"[\wÀ-ÿ-]{2,}", re.UNICODE)
STOP_WORDS = frozenset({"au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "et", "la", "le", "les", "leur", "lui", "ma", "mais", "mes", "mon", "ne", "nos", "notre", "ou", "par", "pas", "pour", "que", "qui", "sa", "se", "ses", "son", "sur", "tes", "ton", "une", "vos", "votre"})
RagAuditWriter = Callable[[str, str, dict[str, object]], object]


class KnowledgeRetriever:
    def __init__(
        self,
        indexer: KnowledgeIndexer,
        metrics: KnowledgeMetricsRepository,
        audit: RagAuditWriter | None = None,
    ) -> None:
        self._indexer = indexer
        self._metrics = metrics
        self._audit = audit
        self._acl = KnowledgeAcl()

    def retrieve(self, plan: ContextPlan) -> RetrievalResult:
        started = perf_counter()
        index = self._indexer.current_or_rebuild()
        allowed = self._acl.filter(plan, index.documents)
        ranked = self._rank(plan, allowed, index.chunks)
        selected = self._within_budget(plan, ranked)
        result = self._result(allowed, selected, started)
        self._metrics.record(plan.agent_id, result.metrics)
        self._write_audit(plan, result)
        return result

    def _rank(
        self,
        plan: ContextPlan,
        documents: tuple[KnowledgeDocument, ...],
        chunks: tuple[KnowledgeChunk, ...],
    ) -> tuple[RetrievedChunk, ...]:
        terms = _terms(plan.query)
        by_id = {document.document_id: document for document in documents}
        results = tuple(self._retrieved(terms, chunk, by_id[chunk.document_id]) for chunk in chunks if chunk.document_id in by_id)
        matching = (result for result in results if result.score > 0)
        return tuple(sorted(matching, key=_ranking_key))

    def _retrieved(self, terms: frozenset[str], chunk: KnowledgeChunk, document: KnowledgeDocument) -> RetrievedChunk:
        score = _score(terms, chunk, document)
        return RetrievedChunk(chunk=chunk, document=document, score=score, citation=_citation(chunk, document))

    def _within_budget(self, plan: ContextPlan, ranked: tuple[RetrievedChunk, ...]) -> tuple[RetrievedChunk, ...]:
        selected: list[RetrievedChunk] = []
        characters = 0
        for result in ranked:
            if len(selected) >= plan.max_context_size.max_chunks:
                break
            if characters + len(result.chunk.content) > plan.max_context_size.max_characters:
                continue
            if (characters + len(result.chunk.content) + 3) // 4 > plan.max_context_size.max_tokens_estimated:
                continue
            selected.append(result)
            characters += len(result.chunk.content)
        return tuple(selected)

    def _result(self, allowed: tuple[KnowledgeDocument, ...], selected: tuple[RetrievedChunk, ...], started: float) -> RetrievalResult:
        context = _context(selected)
        official = tuple(item for item in selected if item.document.authority == "official")
        memory = tuple(item for item in selected if item.document.authority == "enterprise_memory")
        metrics = RetrievalMetrics(
            documents_considered=len(allowed),
            documents_selected=len({item.document.document_id for item in selected}),
            chunks_selected=len(selected),
            context_characters=len(context),
            context_tokens_estimated=(len(context) + 3) // 4,
            duration_ms=max(0, round((perf_counter() - started) * 1_000)),
            memory_chunks_selected=sum(item.document.source_type.value == "enterprise_memory" for item in selected),
        )
        return RetrievalResult(chunks=selected, sources=_unique_sources(selected), context=context, document_context=_context_section("Official Knowledge", official), memory_context=_context_section("Enterprise Memory", memory), metrics=metrics)

    def _write_audit(self, plan: ContextPlan, result: RetrievalResult) -> None:
        if self._audit is None:
            return
        details: dict[str, object] = {
            "request_id": plan.request_id,
            "agent_id": plan.agent_id,
            "application_id": plan.application_id,
            "user_id": plan.user_id,
            "query": plan.query,
            "knowledge_scopes": list(plan.knowledge_scopes),
            "filters": plan.filters.model_dump(exclude_none=True),
            **result.metrics.model_dump(mode="json"),
        }
        self._audit("rag.search", plan.application_id, details)
        memory_ids = [item.document.document_id.removeprefix("memory:") for item in result.chunks if item.document.authority == "enterprise_memory"]
        if memory_ids:
            self._audit("memory.retrieve", plan.application_id, {"request_id": plan.request_id, "agent_id": plan.agent_id, "memory_ids": memory_ids})


def _terms(query: str) -> frozenset[str]:
    return frozenset(word.casefold() for word in WORD_RE.findall(query) if word.casefold() not in STOP_WORDS)


def _score(terms: frozenset[str], chunk: KnowledgeChunk, document: KnowledgeDocument) -> int:
    content = chunk.content.casefold()
    title = document.title.casefold()
    reference = document.reference.casefold()
    heading = chunk.heading.casefold()
    lexical = sum(content.count(term) + 5 * (term in title) + 8 * (term in reference) + 3 * (term in heading) for term in terms)
    official = 8 if document.status.value == "Applicable" else 0
    source = 4 if document.source_type.value in {"lda", "wiki", "markdown"} else 0
    scope = 2 * len(terms.intersection(document.knowledge_scopes))
    return lexical + official + source + scope if lexical else 0


def _citation(chunk: KnowledgeChunk, document: KnowledgeDocument) -> SourceCitation:
    return SourceCitation(
        source_id=chunk.chunk_id,
        document_id=document.document_id,
        title=document.title,
        reference=document.reference,
        version=document.version,
        section=chunk.section,
        url_or_path=document.source_path,
        status=document.status,
        source_type=document.source_type,
        authority=document.authority,
        provenance=document.provenance_label,
    )


def _ranking_key(result: RetrievedChunk) -> tuple[int, int, str, int, str]:
    authority = 1 if result.document.authority == "enterprise_memory" else 0
    return (authority, -result.score, result.document.reference, result.chunk.position, result.chunk.chunk_id)


def _context(selected: tuple[RetrievedChunk, ...]) -> str:
    if not selected:
        return "Aucune source documentaire applicable trouvée. Ne fabriquez aucune référence."
    official = tuple(item for item in selected if item.document.authority == "official")
    memory = tuple(item for item in selected if item.document.authority == "enterprise_memory")
    sections = tuple(section for section in (_context_section("Official Knowledge", official), _context_section("Enterprise Memory", memory)) if section)
    return "\n\n".join(sections)


def _context_section(title: str, selected: tuple[RetrievedChunk, ...]) -> str:
    if not selected:
        return ""
    return f"## {title}\n\n" + "\n\n".join(_context_fragment(result) for result in selected)


def _context_fragment(result: RetrievedChunk) -> str:
    source = result.citation
    label = f"{source.source_id} | {source.reference} V{source.version} | {source.section} | {source.status.value}"
    provenance = f" | {source.provenance}" if source.provenance else ""
    return f"[{label}{provenance}]\n{result.chunk.content}"


def _unique_sources(selected: tuple[RetrievedChunk, ...]) -> tuple[SourceCitation, ...]:
    sources: list[SourceCitation] = []
    seen: set[str] = set()
    for result in selected:
        if result.citation.source_id in seen:
            continue
        sources.append(result.citation)
        seen.add(result.citation.source_id)
    return tuple(sources)
