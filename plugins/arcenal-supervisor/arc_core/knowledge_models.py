"""Contrats immuables du RAG central ARCenal."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from .contracts import Permission, StrictModel


class DocumentStatus(str, Enum):
    DRAFT = "Brouillon"
    IN_REVIEW = "En révision"
    TO_APPROVE = "À approuver"
    APPLICABLE = "Applicable"
    ARCHIVED = "Archivé"


class ConfidentialityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    ADMIN = "admin"


class SourceType(str, Enum):
    MARKDOWN = "markdown"
    WIKI = "wiki"
    LDA = "lda"
    DOCUMENT = "document"
    MEMORY = "memory"
    ENTERPRISE_MEMORY = "enterprise_memory"


class ContextBudget(StrictModel):
    max_chunks: int = Field(default=6, ge=1, le=20)
    max_characters: int = Field(default=12_000, ge=500, le=50_000)
    max_tokens_estimated: int = Field(default=3_000, ge=125, le=12_500)


class KnowledgeFilters(StrictModel):
    domain: str | None = None
    reference: str | None = None
    source_path: str | None = None
    version: str | None = None


class ContextPlan(StrictModel):
    request_id: str
    agent_id: str
    application_id: str
    user_id: str | None
    knowledge_scopes: tuple[str, ...]
    permissions: tuple[Permission, ...]
    document_statuses: tuple[DocumentStatus, ...]
    source_types: tuple[SourceType, ...]
    confidentiality_level: ConfidentialityLevel
    query: str = Field(min_length=1, max_length=20_000)
    filters: KnowledgeFilters = KnowledgeFilters()
    max_context_size: ContextBudget = ContextBudget()


class KnowledgeDocument(StrictModel):
    document_id: str
    title: str
    reference: str
    version: str
    status: DocumentStatus
    owner: str
    domain: str
    knowledge_scopes: tuple[str, ...]
    confidentiality: ConfidentialityLevel
    applicable_from: str
    review_date: str
    source_type: SourceType
    source_path: str
    updated_at: datetime
    allowed_applications: tuple[str, ...] = ()
    allowed_agents: tuple[str, ...] = ()
    allowed_users: tuple[str, ...] = ()
    required_permissions: tuple[Permission, ...] = ()
    authority: str = Field(default="official", pattern=r"^(official|enterprise_memory)$")
    provenance_label: str = ""


class KnowledgeChunk(StrictModel):
    chunk_id: str
    document_id: str
    version: str
    heading: str
    section: str
    position: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=4_000)
    knowledge_scopes: tuple[str, ...]
    confidentiality: ConfidentialityLevel
    status: DocumentStatus


class KnowledgeIndex(StrictModel):
    schema_version: int = 1
    built_at: datetime
    documents: tuple[KnowledgeDocument, ...]
    chunks: tuple[KnowledgeChunk, ...]
    errors: tuple[str, ...] = ()


class SourceCitation(StrictModel):
    source_id: str
    document_id: str
    title: str
    reference: str
    version: str
    section: str
    url_or_path: str
    status: DocumentStatus
    source_type: SourceType = SourceType.MARKDOWN
    authority: str = Field(default="official", pattern=r"^(official|enterprise_memory)$")
    provenance: str = ""


class RetrievedChunk(StrictModel):
    chunk: KnowledgeChunk
    document: KnowledgeDocument
    score: int = Field(ge=0)
    citation: SourceCitation


class RetrievalMetrics(StrictModel):
    documents_considered: int = Field(ge=0)
    documents_selected: int = Field(ge=0)
    chunks_selected: int = Field(ge=0)
    context_characters: int = Field(ge=0)
    context_tokens_estimated: int = Field(ge=0)
    duration_ms: int = Field(ge=0)
    memory_chunks_selected: int = Field(default=0, ge=0)


class RetrievalResult(StrictModel):
    chunks: tuple[RetrievedChunk, ...]
    sources: tuple[SourceCitation, ...]
    context: str
    document_context: str = ""
    memory_context: str = ""
    metrics: RetrievalMetrics


class KnowledgeIndexStatus(StrictModel):
    documents: int = Field(ge=0)
    chunks: int = Field(ge=0)
    built_at: datetime | None
    errors: tuple[str, ...]
    searches: int = Field(ge=0)
    average_duration_ms: float = Field(ge=0)
    average_documents_found: float = Field(ge=0)
    average_chunks_selected: float = Field(ge=0)
    no_result_rate: float = Field(ge=0, le=1)
    average_context_characters: float = Field(ge=0)
    average_context_tokens_estimated: float = Field(ge=0)
    sources_by_agent: dict[str, int] = Field(default_factory=dict)
    memories: int = Field(default=0, ge=0)
    memory_chunks_selected: int = Field(default=0, ge=0)
    average_memory_chunks_per_search: float = Field(default=0, ge=0)


class KnowledgeMetricsState(StrictModel):
    searches: int = Field(default=0, ge=0)
    no_results: int = Field(default=0, ge=0)
    duration_ms_total: int = Field(default=0, ge=0)
    documents_found_total: int = Field(default=0, ge=0)
    chunks_selected_total: int = Field(default=0, ge=0)
    context_characters_total: int = Field(default=0, ge=0)
    context_tokens_total: int = Field(default=0, ge=0)
    sources_by_agent: dict[str, int] = Field(default_factory=dict)
    memory_chunks_selected_total: int = Field(default=0, ge=0)
