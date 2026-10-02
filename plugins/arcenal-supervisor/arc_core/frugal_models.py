"""Contrats stricts d'ARC Frugal et des automatisations gouvernées."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from .contracts import Permission, StrictModel
from .knowledge_models import ConfidentialityLevel


class CapabilityProfile(str, Enum):
    DETERMINISTIC = "deterministic"
    LIGHT = "light"
    STANDARD = "standard"
    ADVANCED = "advanced"
    SPECIALIZED = "specialized"


class TaskType(str, Enum):
    DETERMINISTIC = "deterministic"
    RETRIEVAL = "retrieval"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    GENERATION = "generation"
    REASONING = "reasoning"
    TOOL_EXECUTION = "tool_execution"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


class ExecutionMode(str, Enum):
    DETERMINISTIC = "deterministic"
    CACHE = "cache"
    LLM = "llm"
    WORKFLOW = "workflow"


class ModelLocation(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class ModelAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ModelCatalogSource(str, Enum):
    CONFIGURED = "configured"
    DISCOVERED = "discovered"
    STATIC = "static"


class CacheValidation(str, Enum):
    GENERATED = "generated"
    VALIDATED = "validated"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class ModelDescriptor(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,95}$")
    provider: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")
    model_name: str = Field(min_length=1, max_length=240)
    display_name: str | None = Field(default=None, min_length=1, max_length=240)
    enabled: bool = True
    availability: ModelAvailability = ModelAvailability.UNKNOWN
    catalog_source: ModelCatalogSource = ModelCatalogSource.STATIC
    capabilities: tuple[CapabilityProfile, ...]
    context_window: int | None = Field(default=None, ge=256, le=10_000_000)
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_vision: bool = False
    privacy_class: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    location: ModelLocation
    hosting_region: str | None = Field(default=None, max_length=80)
    input_cost: float = Field(default=0, ge=0)
    output_cost: float = Field(default=0, ge=0)
    priority: int = Field(default=100, ge=0, le=10_000)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: tuple[CapabilityProfile, ...]) -> tuple[CapabilityProfile, ...]:
        if not value:
            raise ValueError("Au moins une capacité doit être déclarée.")
        return tuple(dict.fromkeys(value))


class RoutingNeed(StrictModel):
    agent_id: str
    task_type: TaskType
    required_capability: CapabilityProfile
    confidentiality: ConfidentialityLevel
    tools_required: bool = False
    structured_output: bool = False
    vision_required: bool = False
    context_size: int = Field(default=0, ge=0)
    latency_preference: str = Field(default="balanced", pattern=r"^(fast|balanced|quality)$")
    cost_policy: str = Field(default="low", pattern=r"^(low|balanced|unrestricted)$")
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    allowed_models: tuple[str, ...] = ()
    local_only: bool = False
    local_preferred: bool = True
    max_cost: float | None = Field(default=None, ge=0)


class RoutingDecision(StrictModel):
    provider: str
    model: str
    registry_id: str
    capability: CapabilityProfile
    reason: str
    estimated_cost: float
    fallbacks: tuple[str, ...] = ()


class FrugalExecutionPlan(StrictModel):
    request_id: str
    agent_id: str
    task_type: TaskType
    execution_mode: ExecutionMode
    cache_policy: str
    model_policy: str
    selected_model: str | None = None
    selected_provider: str | None = None
    estimated_context: int = Field(default=0, ge=0)
    reason: str


class CacheDependency(StrictModel):
    kind: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    identifier: str = Field(min_length=1, max_length=240)
    version: str = Field(min_length=1, max_length=120)


class CachedResponse(StrictModel):
    id: str
    agent_id: str
    application_id: str
    request_normalized: str
    context_signature: str
    knowledge_signature: str
    permission_signature: str
    response: str
    validation: CacheValidation
    dependencies: tuple[CacheDependency, ...]
    provider: str | None = None
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    created_at: datetime
    expires_at: datetime


class ExecutionMeasurement(StrictModel):
    request_id: str
    agent_id: str
    task_type: TaskType
    execution_mode: ExecutionMode
    provider: str | None = None
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0, ge=0)
    duration_ms: float = Field(ge=0)
    routing_duration_ms: float = Field(default=0, ge=0)
    rag_duration_ms: float = Field(default=0, ge=0)
    context_tokens: int = Field(default=0, ge=0)
    provider_attempts: int = Field(default=0, ge=0)
    provider_failures: int = Field(default=0, ge=0)
    cache_hit: bool = False
    deterministic_hit: bool = False
    workflow_hit: bool = False
    tokens_avoided_estimate: int = Field(default=0, ge=0)
    estimated_cost_avoided: float = Field(default=0, ge=0)
    created_at: datetime


class FrugalMetrics(StrictModel):
    total_requests: int = 0
    llm_requests: int = 0
    non_llm_requests: int = 0
    cache_hits: int = 0
    deterministic_hits: int = 0
    workflow_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tokens_avoided_estimate: int = 0
    actual_estimated_cost: float = 0
    estimated_cost_avoided: float = 0
    average_routing_latency_ms: float = 0
    average_total_latency_ms: float = 0
    average_rag_latency_ms: float = 0
    average_context_tokens: float = 0
    provider_failures: int = 0
    by_provider: dict[str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)


class WorkflowStep(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    operation: str = Field(pattern=r"^(agent_prompt|structured_value|template|status)$")
    input_key: str | None = Field(default=None, max_length=80)
    template: str | None = Field(default=None, max_length=4_000)
    tool: str | None = Field(default=None, max_length=120)


class AutomationWorkflow(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1_000)
    version: int = Field(default=1, ge=1)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    agent_id: str
    trigger: str = Field(min_length=1, max_length=500)
    steps: tuple[WorkflowStep, ...]
    permissions: tuple[Permission, ...] = ()
    autonomy: str = Field(pattern=r"^(automatic|controlled|approval_required)$")
    created_at: datetime
    updated_at: datetime
    approved_by: str | None = Field(default=None, max_length=160)
    executions: int = Field(default=0, ge=0)
    exceptions: int = Field(default=0, ge=0)


class ProcessObservation(StrictModel):
    id: str
    agent_id: str
    fingerprint: str
    tools: tuple[str, ...]
    input_keys: tuple[str, ...]
    outcome_signature: str
    created_at: datetime


class AutomationCandidate(StrictModel):
    id: str
    name: str
    description: str
    observations: int = Field(ge=1)
    steps: tuple[WorkflowStep, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    exceptions: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    estimated_savings: float = Field(ge=0)
    risk_level: str = Field(pattern=r"^(low|medium|high)$")
    reviewed: bool = False
