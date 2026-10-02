"""Orchestrateur des quatre chemins d'exécution d'ARC Frugal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from .automation_engine import ProcessObserver, WorkflowEngine
from .deterministic_engine import DeterministicEngine
from .frugal_cache import FrugalCache
from .frugal_metrics import FrugalMetricsRepository
from .frugal_models import CapabilityProfile, ExecutionMeasurement, ExecutionMode, FrugalExecutionPlan, ModelDescriptor, RoutingDecision, RoutingNeed, TaskType
from .model_router import ModelRouter
from .errors import ProviderExecutionError
from .models import EffectiveContext, EngineOutput
from .provider_adapter import ProviderExecutor
from .provider_registry import ProviderRegistry
from .service import AgentEngine
from .task_classifier import classify_task, required_capability


@dataclass(frozen=True)
class ProviderCandidateResult:
    output: EngineOutput | None
    provider: str
    attempts: int


class FrugalAgentEngine:
    def __init__(self, llm: AgentEngine, deterministic: DeterministicEngine, cache: FrugalCache, workflows: WorkflowEngine, router: ModelRouter, metrics: FrugalMetricsRepository, observer: ProcessObserver, providers: ProviderRegistry | None = None, executor: ProviderExecutor | None = None) -> None:
        self._llm = llm
        self._deterministic = deterministic
        self._cache = cache
        self._workflows = workflows
        self._router = router
        self._metrics = metrics
        self._observer = observer
        self._providers = providers
        self._executor = executor

    def execute(self, context: EffectiveContext, message: str) -> EngineOutput:
        started = perf_counter()
        task_type = classify_task(message)
        deterministic = self._deterministic.execute(context, message)
        if deterministic is not None:
            return self._finish(context, task_type, ExecutionMode.DETERMINISTIC, deterministic, started, "Règle déterministe applicable")
        cached = self._cache.lookup(context, message)
        if cached is not None:
            return self._finish(context, task_type, ExecutionMode.CACHE, cached[0], started, f"Cache {cached[1]} fiable")
        workflow = self._workflows.execute(context, message)
        if workflow is not None:
            return self._execute_workflow(context, workflow, task_type, started)
        return self._execute_llm(context, message, task_type, started)

    def _execute_workflow(self, context: EffectiveContext, workflow: EngineOutput, task_type: TaskType, started: float) -> EngineOutput:
        if not workflow.usage.get("workflow_agent_prompt"):
            return self._finish(context, task_type, ExecutionMode.WORKFLOW, workflow, started, "Workflow actif et validé")
        output = self._execute_llm(context, workflow.response, classify_task(workflow.response), started)
        usage = {**output.usage, "workflow_id": workflow.usage.get("workflow_id", ""), "workflow_version": workflow.usage.get("workflow_version", 1)}
        return output.model_copy(update={"usage": usage})

    def _execute_llm(self, context: EffectiveContext, message: str, task_type: TaskType, started: float) -> EngineOutput:
        routing_started = perf_counter()
        capability = self._capability(context, task_type, message)
        decision = self._router.route(self._need(context, task_type, capability))
        routing_duration = (perf_counter() - routing_started) * 1_000
        output = self._execute_decision(context, message, decision)
        enriched = self._enrich(output, ExecutionMode.LLM, decision.reason, capability, routing_duration, decision.registry_id)
        self._cache.store(context, message, enriched)
        return self._finish(context, task_type, ExecutionMode.LLM, enriched, started, decision.reason, routing_duration)

    def _execute_decision(self, context: EffectiveContext, message: str, decision: RoutingDecision) -> EngineOutput:
        if self._providers is None or self._executor is None:
            return self._llm.execute(self._routed_context(context, decision.provider, decision.model), message)
        candidates = (decision.registry_id, *decision.fallbacks)
        failures: list[str] = []
        total_attempts = 0
        for model_id in candidates:
            result = self._execute_candidate(context, message, model_id)
            total_attempts += result.attempts
            if result.output is not None:
                usage = {**result.output.usage, "provider_failures": len(failures), "provider_attempts": total_attempts, "fallbacks": ",".join(failures)}
                return result.output.model_copy(update={"usage": usage})
            failures.append(result.provider)
        raise ProviderExecutionError("Aucun fournisseur autorisé n’a répondu.", "unavailable")

    def _execute_candidate(self, context: EffectiveContext, message: str, model_id: str) -> ProviderCandidateResult:
        model = self._router_model(model_id)
        provider = self._providers.get(model.provider) if self._providers is not None and model is not None else None
        if model is None or provider is None or self._executor is None:
            return ProviderCandidateResult(None, model_id, 0)
        try:
            output, attempts = self._executor.execute(context, message, provider, model.model_name)
        except ProviderExecutionError as exc:
            return ProviderCandidateResult(None, provider.id, len(exc.attempts))
        usage = {**output.usage, "provider": provider.id, "model": model.model_name}
        return ProviderCandidateResult(output.model_copy(update={"usage": usage}), provider.id, len(attempts))

    def _router_model(self, model_id: str) -> ModelDescriptor | None:
        return self._router.model(model_id)

    def _finish(self, context: EffectiveContext, task_type: TaskType, mode: ExecutionMode, output: EngineOutput, started: float, reason: str, routing_ms: float = 0) -> EngineOutput:
        duration = (perf_counter() - started) * 1_000
        baseline = self._metrics.baseline(context.agent.id, task_type) if mode is not ExecutionMode.LLM else None
        measurement = self._measurement(context, task_type, mode, output, duration, routing_ms, baseline)
        self._metrics.record(measurement)
        tools = tuple(action.get("tool", "") for action in output.actions if action.get("tool"))
        self._observer.observe(context, tools, output.response)
        plan = self._plan(context, task_type, mode, output, reason)
        usage = {**output.usage, **measurement.model_dump(mode="json", exclude={"created_at", "request_id", "agent_id", "task_type"}, exclude_none=True), "route_reason": reason, "plan": plan.model_dump_json()}
        return output.model_copy(update={"usage": usage})

    def _need(self, context: EffectiveContext, task_type: TaskType, capability: CapabilityProfile) -> RoutingNeed:
        policy = context.model_policy
        return RoutingNeed(agent_id=context.agent.id, task_type=task_type, required_capability=capability, confidentiality=context.context_plan.confidentiality_level, tools_required=task_type is TaskType.TOOL_EXECUTION, context_size=context.retrieval_metrics.context_tokens_estimated, allowed_providers=policy.allowed_providers, denied_providers=policy.denied_providers, allowed_models=policy.allowed_models, local_only=policy.local_only, local_preferred=policy.local_preferred, max_cost=policy.max_cost)

    def _capability(self, context: EffectiveContext, task_type: TaskType, message: str) -> CapabilityProfile:
        if context.model_policy.mode == "fixed":
            return context.model_policy.preferred_capability
        capability = required_capability(task_type, message)
        return CapabilityProfile.STANDARD if capability is CapabilityProfile.DETERMINISTIC else capability

    def _routed_context(self, context: EffectiveContext, provider: str, model: str) -> EffectiveContext:
        policy = context.model_policy.model_copy(update={"allowed_providers": (provider,), "allowed_models": (model,)})
        return context.model_copy(update={"model_policy": policy})

    def _enrich(self, output: EngineOutput, mode: ExecutionMode, reason: str, capability: CapabilityProfile, routing_ms: float, registry_id: str) -> EngineOutput:
        registry = {"registry_id": registry_id} if registry_id else {}
        usage = {**output.usage, **registry, "execution_mode": mode.value, "route_reason": reason, "capability": capability.value, "routing_duration_ms": routing_ms}
        return output.model_copy(update={"usage": usage})

    def _measurement(self, context: EffectiveContext, task_type: TaskType, mode: ExecutionMode, output: EngineOutput, duration: float, routing_ms: float, baseline: tuple[int, float] | None) -> ExecutionMeasurement:
        usage = output.usage
        avoided_tokens, avoided_cost = baseline or (0, 0.0)
        return ExecutionMeasurement(request_id=context.identity.request_id, agent_id=context.agent.id, task_type=task_type, execution_mode=mode, provider=_text(usage.get("provider")), model=_text(usage.get("model")), input_tokens=_integer(usage.get("input_tokens")), output_tokens=_integer(usage.get("output_tokens")), estimated_cost=_number(usage.get("cost")), duration_ms=duration, routing_duration_ms=routing_ms, rag_duration_ms=context.retrieval_metrics.duration_ms, context_tokens=context.retrieval_metrics.context_tokens_estimated, provider_attempts=_integer(usage.get("provider_attempts")), provider_failures=_integer(usage.get("provider_failures")), cache_hit=mode is ExecutionMode.CACHE, deterministic_hit=mode is ExecutionMode.DETERMINISTIC, workflow_hit=mode is ExecutionMode.WORKFLOW, tokens_avoided_estimate=avoided_tokens, estimated_cost_avoided=avoided_cost, created_at=datetime.now(timezone.utc))

    def _plan(self, context: EffectiveContext, task_type: TaskType, mode: ExecutionMode, output: EngineOutput, reason: str) -> FrugalExecutionPlan:
        return FrugalExecutionPlan(request_id=context.identity.request_id, agent_id=context.agent.id, task_type=task_type, execution_mode=mode, cache_policy="exact_generated_semantic_validated", model_policy=context.model_policy.mode, selected_model=_text(output.usage.get("model")), selected_provider=_text(output.usage.get("provider")), estimated_context=context.retrieval_metrics.context_tokens_estimated, reason=reason)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
