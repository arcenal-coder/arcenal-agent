"""Projection reconstruisible de la mémoire gouvernée vers le RAG central."""

from __future__ import annotations

from datetime import timezone

from .knowledge_models import DocumentStatus, KnowledgeDocument, SourceType
from .memory_models import EnterpriseMemory
from .memory_repository import EnterpriseMemoryRepository


class EnterpriseMemoryKnowledgeSource:
    def __init__(self, repository: EnterpriseMemoryRepository) -> None:
        self._repository = repository

    def load(self) -> tuple[tuple[tuple[KnowledgeDocument, str], ...], tuple[str, ...]]:
        try:
            loaded = tuple((_document(memory), _body(memory)) for memory in self._repository.active())
            return loaded, ()
        except RuntimeError as exc:
            return (), (str(exc),)


def _document(memory: EnterpriseMemory) -> KnowledgeDocument:
    return KnowledgeDocument(
        document_id=f"memory:{memory.id}", title=memory.summary,
        reference=f"MEM-{memory.id[:8].upper()}", version=str(memory.version),
        status=DocumentStatus.APPLICABLE, owner=memory.created_by,
        domain=memory.project or memory.memory_type.value,
        knowledge_scopes=memory.knowledge_scopes,
        confidentiality=memory.confidentiality, applicable_from=memory.created_at.date().isoformat(),
        review_date=memory.review_date.date().isoformat() if memory.review_date else "",
        source_type=SourceType.ENTERPRISE_MEMORY, source_path=f"memory://{memory.id}",
        updated_at=memory.updated_at.astimezone(timezone.utc),
        allowed_applications=memory.allowed_applications, allowed_agents=memory.allowed_agents,
        allowed_users=memory.allowed_users, required_permissions=memory.required_permissions,
        authority="enterprise_memory", provenance_label=_provenance(memory),
    )


def _body(memory: EnterpriseMemory) -> str:
    fields = (f"# {memory.summary}", memory.content, f"Type : {memory.memory_type.value}", f"Provenance : {_provenance(memory)}", f"Confiance : {memory.confidence:.2f}")
    return "\n\n".join(fields)


def _provenance(memory: EnterpriseMemory) -> str:
    source = memory.provenance
    return f"{source.source_type.value} · {source.source_id} · {source.recorded_at.date().isoformat()}"
