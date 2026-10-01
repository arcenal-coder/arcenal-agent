"""Point de passage commun entre Agent Manager et le moteur Hermes."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

from .context import ContextBuilder
from .manager import AgentManager
from .models import AgentQueryResponse, ApplicationIdentity, AutonomyLevel, EffectiveContext, EngineOutput


class AgentEngine(Protocol):
    def execute(self, context: EffectiveContext, message: str) -> EngineOutput: ...


AuditWriter = Callable[[str, str, dict[str, object]], object]


class ArcCore:
    def __init__(self, manager: AgentManager, context_builder: ContextBuilder, engine: AgentEngine, audit: AuditWriter) -> None:
        self._manager = manager
        self._context_builder = context_builder
        self._engine = engine
        self._audit = audit

    def query(
        self,
        agent_id: str,
        caller: ApplicationIdentity,
        message: str,
        session_id: str | None = None,
        request_context: dict[str, str] | None = None,
    ) -> AgentQueryResponse:
        agent = self._manager.get(agent_id, require_enabled=True)
        context = self._context_builder.build(agent, caller, session_id, request_context, message)
        started = perf_counter()
        self._audit("agent.query.started", caller.application_id, self._audit_details(context, "started", 0))
        try:
            output = self._engine.execute(context, message)
        except Exception:
            duration = round((perf_counter() - started) * 1000)
            self._audit("agent.query.failed", caller.application_id, self._audit_details(context, "failed", duration))
            raise
        duration = round((perf_counter() - started) * 1000)
        self._audit("agent.query.completed", caller.application_id, self._audit_details(context, "completed", duration, output))
        return self._response(context, output)

    def _response(self, context: EffectiveContext, output: EngineOutput) -> AgentQueryResponse:
        approval = context.agent.autonomy_level is AutonomyLevel.APPROVAL_REQUIRED
        sources = tuple(source.model_dump(mode="json") for source in context.sources)
        return AgentQueryResponse(request_id=context.identity.request_id, agent_id=context.agent.id, response=output.response, status="completed", approval_required=approval, sources=sources, actions=output.actions, usage=output.usage)

    def _audit_details(self, context: EffectiveContext, status: str, duration_ms: int, output: EngineOutput | None = None) -> dict[str, object]:
        return {
            "request_id": context.identity.request_id,
            "agent": context.agent.id,
            "application": context.identity.application_id,
            "user": context.identity.user_id,
            "user_source": context.identity.user_source.value,
            "status": status,
            "duration_ms": duration_ms,
            "tools": list(context.tools),
            "rag": context.retrieval_metrics.model_dump(mode="json"),
            "actions": [dict(action) for action in output.actions] if output else [],
            "usage": dict(output.usage) if output else {},
        }
