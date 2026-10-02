"""Construction centrale du contexte effectif d’un agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .errors import AgentAccessDeniedError
from .knowledge_models import (
    ConfidentialityLevel,
    ContextBudget,
    ContextPlan,
    DocumentStatus,
    RetrievalMetrics,
    RetrievalResult,
    SourceType,
)
from .knowledge_search import KnowledgeRetriever
from .models import AgentDefinition, ApplicationIdentity, EffectiveContext, RequestIdentity


@dataclass(frozen=True, slots=True)
class GlobalAgentPolicy:
    instructions: tuple[str, ...]
    forbidden_permissions: frozenset[str] = frozenset()


class ContextBuilder:
    def __init__(self, policy: GlobalAgentPolicy, retriever: KnowledgeRetriever | None = None) -> None:
        self._policy = policy
        self._retriever = retriever

    def build(
        self,
        agent: AgentDefinition,
        caller: ApplicationIdentity,
        session_id: str | None,
        request_context: dict[str, str] | None = None,
        message: str = "",
    ) -> EffectiveContext:
        if caller.application_id != agent.application:
            raise AgentAccessDeniedError("Cette application ne peut pas utiliser l’agent demandé.")
        permissions = tuple(item for item in agent.permissions if item not in self._policy.forbidden_permissions)
        identity = self._identity(agent, caller, session_id, permissions)
        plan = self._plan(identity, agent, message)
        retrieval = self._retrieve(plan)
        return self._effective_context(agent, identity, permissions, plan, retrieval, request_context)

    def _effective_context(
        self,
        agent: AgentDefinition,
        identity: RequestIdentity,
        permissions: tuple[str, ...],
        plan: ContextPlan,
        retrieval: RetrievalResult,
        request_context: dict[str, str] | None,
    ) -> EffectiveContext:
        return EffectiveContext(
            identity=identity,
            agent=agent,
            system_prompt=self._prompt(agent),
            permissions=permissions,
            tools=agent.tools,
            knowledge_scopes=agent.knowledge_scopes,
            model_policy=agent.model_policy,
            context_plan=plan,
            knowledge_context=retrieval.context,
            document_context=retrieval.document_context,
            memory_context=retrieval.memory_context,
            sources=retrieval.sources,
            retrieval_metrics=retrieval.metrics,
            request_context=request_context or {},
        )

    def _identity(self, agent: AgentDefinition, caller: ApplicationIdentity, session_id: str | None, permissions: tuple[str, ...]) -> RequestIdentity:
        return RequestIdentity(request_id=str(uuid4()), user_id=caller.user_id, user_source=caller.user_source, application_id=caller.application_id, agent_id=agent.id, session_id=session_id, permissions=permissions, timestamp=datetime.now(timezone.utc))

    def _prompt(self, agent: AgentDefinition) -> str:
        sections = (
            "# Politique globale ARCenal",
            *self._policy.instructions,
            "# Politique de l’agent",
            *(item.content for item in agent.system_instructions),
            *_harness_sections(agent),
        )
        return "\n\n".join(section for section in sections if section)

    def _plan(self, identity: RequestIdentity, agent: AgentDefinition, message: str) -> ContextPlan:
        return ContextPlan(
            request_id=identity.request_id,
            agent_id=agent.id,
            application_id=identity.application_id,
            user_id=identity.user_id,
            knowledge_scopes=agent.knowledge_scopes,
            permissions=identity.permissions,
            document_statuses=self._statuses(message, identity.permissions),
            source_types=self._source_types(identity.permissions),
            confidentiality_level=self._confidentiality(identity.permissions),
            query=message.strip() or "contexte général",
            max_context_size=ContextBudget(),
        )

    def _source_types(self, permissions: tuple[str, ...]) -> tuple[SourceType, ...]:
        official = (SourceType.LDA, SourceType.WIKI, SourceType.DOCUMENT, SourceType.MARKDOWN)
        return (*official, SourceType.ENTERPRISE_MEMORY) if "memory.read" in permissions else official

    def _retrieve(self, plan: ContextPlan) -> RetrievalResult:
        if self._retriever is not None:
            return self._retriever.retrieve(plan)
        metrics = RetrievalMetrics(documents_considered=0, documents_selected=0, chunks_selected=0, context_characters=0, context_tokens_estimated=0, duration_ms=0)
        return RetrievalResult(chunks=(), sources=(), context="Aucune source documentaire applicable trouvée.", document_context="", memory_context="", metrics=metrics)

    def _statuses(self, message: str, permissions: tuple[str, ...]) -> tuple[DocumentStatus, ...]:
        history_requested = any(term in message.casefold() for term in ("historique", "ancienne version", "obsolète"))
        if history_requested and "lda.history" in permissions:
            return (DocumentStatus.APPLICABLE, DocumentStatus.ARCHIVED)
        return (DocumentStatus.APPLICABLE,)

    def _confidentiality(self, permissions: tuple[str, ...]) -> ConfidentialityLevel:
        if "system.admin" in permissions:
            return ConfidentialityLevel.ADMIN
        if "knowledge.confidential" in permissions:
            return ConfidentialityLevel.CONFIDENTIAL
        if "knowledge.restricted" in permissions:
            return ConfidentialityLevel.RESTRICTED
        return ConfidentialityLevel.INTERNAL


def _harness_sections(agent: AgentDefinition) -> tuple[str, ...]:
    values = (
        ("Contexte propre à l’agent", agent.harness.context),
        ("Directives propres à l’agent", agent.harness.directives),
        ("Mémoire propre à l’agent", agent.harness.memory),
    )
    return tuple(f"# {title}\n\n{content.strip()}" for title, content in values if content.strip())
