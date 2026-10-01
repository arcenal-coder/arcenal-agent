"""Contrats immuables de la mémoire d’entreprise gouvernée."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from .contracts import Permission, StrictModel
from .knowledge_models import ConfidentialityLevel


class MemoryType(str, Enum):
    FACT = "fact"
    DECISION = "decision"
    PERSON = "person"
    PROJECT = "project"
    RULE = "rule"
    PREFERENCE = "preference"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


class MemorySourceType(str, Enum):
    MANUAL = "manual"
    CONVERSATION = "conversation"
    APPLICATION = "application"
    DOCUMENT = "document"
    AGENT = "agent"
    IMPORT = "import"
    API = "api"


class RetentionMode(str, Enum):
    PERMANENT = "permanent"
    EXPIRING = "expiring"


class RuleKind(str, Enum):
    OBSERVED = "observed"
    BUSINESS = "business"
    DERIVED = "derived"
    OFFICIAL_REFERENCE = "official_reference"


class MemoryProvenance(StrictModel):
    source_type: MemorySourceType
    source_id: str = Field(min_length=1, max_length=240)
    recorded_at: datetime
    author: str | None = Field(default=None, max_length=160)
    request_id: str | None = Field(default=None, max_length=160)
    agent_id: str | None = Field(default=None, max_length=64)
    application_id: str | None = Field(default=None, max_length=64)


class MemoryRelation(StrictModel):
    relation_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    target_kind: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    target_id: str = Field(min_length=1, max_length=240)


class MemoryDraft(StrictModel):
    memory_type: MemoryType
    summary: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=16_000)
    provenance: MemoryProvenance
    confidence: float = Field(default=1.0, ge=0, le=1)
    status: MemoryStatus = MemoryStatus.ACTIVE
    retention_mode: RetentionMode = RetentionMode.PERMANENT
    expires_at: datetime | None = None
    knowledge_scopes: tuple[str, ...] = Field(min_length=1)
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    allowed_applications: tuple[str, ...] = ()
    allowed_agents: tuple[str, ...] = ()
    allowed_users: tuple[str, ...] = ()
    required_permissions: tuple[Permission, ...] = ("memory.read",)
    project: str | None = Field(default=None, max_length=240)
    person: str | None = Field(default=None, max_length=240)
    decision_context: str | None = Field(default=None, max_length=2_000)
    decision_reason: str | None = Field(default=None, max_length=2_000)
    decision_maker: str | None = Field(default=None, max_length=240)
    review_date: datetime | None = None
    person_service: str | None = Field(default=None, max_length=240)
    person_role: str | None = Field(default=None, max_length=240)
    responsibilities: tuple[str, ...] = ()
    project_status: str | None = Field(default=None, max_length=120)
    rule_kind: RuleKind | None = None
    official_reference: str | None = Field(default=None, max_length=240)
    preference_owner: str | None = Field(default=None, max_length=240)
    preference_scope: str | None = Field(default=None, max_length=240)
    preference_context: str | None = Field(default=None, max_length=500)
    relations: tuple[MemoryRelation, ...] = ()

    @field_validator("knowledge_scopes", "allowed_applications", "allowed_agents", "allowed_users")
    @classmethod
    def validate_identifiers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        invalid = tuple(value for value in values if not value or len(value) > 128 or any(character.isspace() for character in value))
        if invalid:
            raise ValueError("Un identifiant de portée ou d’accès est invalide.")
        return values

    @field_validator("expires_at", "review_date")
    @classmethod
    def validate_dates(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Une date de mémoire doit inclure son fuseau horaire.")
        return value

    @model_validator(mode="after")
    def validate_governance(self) -> MemoryDraft:
        if self.retention_mode is RetentionMode.EXPIRING and self.expires_at is None:
            raise ValueError("Une mémoire expirante exige une date d’expiration.")
        if self.memory_type is MemoryType.RULE and self.rule_kind is None:
            raise ValueError("Une règle mémorisée exige une nature de règle.")
        if self.rule_kind is RuleKind.OFFICIAL_REFERENCE and not self.official_reference:
            raise ValueError("Une règle de référence exige un document officiel.")
        return self


class EnterpriseMemory(MemoryDraft):
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    version: int = Field(ge=1)


class MemoryRevision(StrictModel):
    id: str
    memory_id: str
    version: int = Field(ge=1)
    previous: EnterpriseMemory
    current: EnterpriseMemory
    corrected_by: str
    corrected_at: datetime
    reason: str = Field(max_length=500)


class MemorySearchFilters(StrictModel):
    query: str = Field(default="", max_length=300)
    memory_type: MemoryType | None = None
    status: MemoryStatus | None = None
    source_type: MemorySourceType | None = None
    scope: str | None = Field(default=None, max_length=100)
    confidentiality: ConfidentialityLevel | None = None
    project: str | None = Field(default=None, max_length=240)
    person: str | None = Field(default=None, max_length=240)
    created_from: datetime | None = None
    created_to: datetime | None = None

    @field_validator("created_from", "created_to")
    @classmethod
    def validate_dates(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Une date de recherche doit inclure son fuseau horaire.")
        return value


class MemoryMetrics(StrictModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    archived: int = Field(ge=0)
    expired: int = Field(ge=0)
    pending_review: int = Field(ge=0)
    deleted: int = Field(ge=0)
    by_type: dict[str, int]
    by_scope: dict[str, int]
    used_by_rag: int = Field(ge=0)
