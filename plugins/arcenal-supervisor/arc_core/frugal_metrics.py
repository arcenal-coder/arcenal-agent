"""Mesures réelles et baselines observées d'ARC Frugal."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .frugal_models import ExecutionMeasurement, ExecutionMode, FrugalMetrics, TaskType
from .frugal_store import JsonCollectionStore


class FrugalMetricsRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonCollectionStore(path, ExecutionMeasurement, "measurements")

    def record(self, measurement: ExecutionMeasurement) -> None:
        self._store.save((*self._store.load(), measurement))

    def baseline(self, agent_id: str, task_type: TaskType) -> tuple[int, float] | None:
        matches = tuple(item for item in self._store.load() if item.agent_id == agent_id and item.task_type is task_type and item.execution_mode is ExecutionMode.LLM)
        if not matches:
            return None
        tokens = round(sum(item.input_tokens + item.output_tokens for item in matches) / len(matches))
        cost = sum(item.estimated_cost for item in matches) / len(matches)
        return tokens, cost

    def metrics(self) -> FrugalMetrics:
        values = self._store.load()
        llm = sum(item.execution_mode is ExecutionMode.LLM for item in values)
        providers = Counter(item.provider for item in values if item.provider and item.execution_mode is ExecutionMode.LLM)
        models = Counter(item.model for item in values if item.model and item.execution_mode is ExecutionMode.LLM)
        latency = sum(item.routing_duration_ms for item in values) / len(values) if values else 0
        total_latency = sum(item.duration_ms for item in values) / len(values) if values else 0
        rag_latency = sum(item.rag_duration_ms for item in values) / len(values) if values else 0
        context_tokens = sum(item.context_tokens for item in values) / len(values) if values else 0
        return FrugalMetrics(total_requests=len(values), llm_requests=llm, non_llm_requests=len(values) - llm, cache_hits=sum(item.cache_hit for item in values), deterministic_hits=sum(item.deterministic_hit for item in values), workflow_hits=sum(item.workflow_hit for item in values), input_tokens=sum(item.input_tokens for item in values), output_tokens=sum(item.output_tokens for item in values), tokens_avoided_estimate=sum(item.tokens_avoided_estimate for item in values), actual_estimated_cost=sum(item.estimated_cost for item in values), estimated_cost_avoided=sum(item.estimated_cost_avoided for item in values), average_routing_latency_ms=latency, average_total_latency_ms=total_latency, average_rag_latency_ms=rag_latency, average_context_tokens=context_tokens, provider_failures=sum(item.provider_failures for item in values), by_provider=dict(providers), by_model=dict(models))

    def recent(self, limit: int = 50) -> tuple[ExecutionMeasurement, ...]:
        return self._store.load()[-limit:]
