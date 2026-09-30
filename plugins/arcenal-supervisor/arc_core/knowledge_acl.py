"""Politique de cloisonnement appliquée avant la recherche RAG."""

from __future__ import annotations

from .knowledge_models import ConfidentialityLevel, ContextPlan, KnowledgeDocument, KnowledgeFilters


CONFIDENTIALITY_RANK = {
    ConfidentialityLevel.PUBLIC: 0,
    ConfidentialityLevel.INTERNAL: 1,
    ConfidentialityLevel.RESTRICTED: 2,
    ConfidentialityLevel.CONFIDENTIAL: 3,
    ConfidentialityLevel.ADMIN: 4,
}


class KnowledgeAcl:
    def allows(self, plan: ContextPlan, document: KnowledgeDocument) -> bool:
        checks = (
            document.status in plan.document_statuses,
            document.source_type in plan.source_types,
            bool(set(plan.knowledge_scopes).intersection(document.knowledge_scopes)),
            self._within_confidentiality(plan, document),
            self._matches(document.allowed_applications, plan.application_id),
            self._matches(document.allowed_agents, plan.agent_id),
            self._matches_user(document.allowed_users, plan.user_id),
            set(document.required_permissions).issubset(plan.permissions),
            self._matches_filters(plan.filters, document),
        )
        return all(checks)

    def filter(self, plan: ContextPlan, documents: tuple[KnowledgeDocument, ...]) -> tuple[KnowledgeDocument, ...]:
        return tuple(document for document in documents if self.allows(plan, document))

    def _within_confidentiality(self, plan: ContextPlan, document: KnowledgeDocument) -> bool:
        return CONFIDENTIALITY_RANK[document.confidentiality] <= CONFIDENTIALITY_RANK[plan.confidentiality_level]

    def _matches(self, allowed: tuple[str, ...], actual: str) -> bool:
        return not allowed or actual.casefold() in allowed

    def _matches_user(self, allowed: tuple[str, ...], actual: str | None) -> bool:
        return not allowed or (actual is not None and actual.casefold() in allowed)

    def _matches_filters(self, filters: KnowledgeFilters, document: KnowledgeDocument) -> bool:
        requested = filters.model_dump(exclude_none=True)
        values = {
            "domain": document.domain,
            "reference": document.reference,
            "source_path": document.source_path,
            "version": document.version,
        }
        return all(values[key].casefold() == value.casefold() for key, value in requested.items())
