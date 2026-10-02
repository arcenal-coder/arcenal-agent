"""Modèles stricts et immuables du contrat interne des agents."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import Permission, StrictModel
from .frugal_models import CapabilityProfile
from .knowledge_models import ContextPlan, RetrievalMetrics, SourceCitation


IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
class AutonomyLevel(str, Enum):
    AUTOMATIC = "automatic"
    CONTROLLED = "controlled"
    APPROVAL_REQUIRED = "approval_required"


class UserIdentitySource(str, Enum):
    YUNOHOST = "yunohost"
    APPLICATION = "application"
    NONE = "none"


class InstructionBlock(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    content: str = Field(min_length=1, max_length=8_000)


class ModelPolicy(StrictModel):
    mode: str = Field(default="auto", pattern=r"^(auto|fixed)$")
    preferred_capability: CapabilityProfile = CapabilityProfile.STANDARD
    local_preferred: bool = True
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    allowed_models: tuple[str, ...] = ()
    local_only: bool = False
    max_cost: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if self.mode == "auto" and self.allowed_models:
            raise ValueError("Le mode AUTO ne référence aucun modèle fictif.")
        if self.mode == "fixed" and len(self.allowed_models) != 1:
            raise ValueError("Le mode FIXED exige exactement un modèle.")
        if self.mode == "fixed" and len(self.allowed_providers) != 1:
            raise ValueError("Le mode FIXED exige exactement un fournisseur.")
        if any(model.casefold() == "auto" for model in self.allowed_models):
            raise ValueError("Le mode FIXED exige un modèle concret et non AUTO.")
        if any(provider in self.denied_providers for provider in self.allowed_providers):
            raise ValueError("Un fournisseur autorisé ne peut pas être simultanément interdit.")
        return self


class AgentDefinition(StrictModel):
    id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    role: str = Field(min_length=1, max_length=80)
    application: str
    system_instructions: tuple[InstructionBlock, ...]
    permissions: tuple[Permission, ...]
    tools: tuple[str, ...] = ()
    knowledge_scopes: tuple[str, ...]
    model_policy: ModelPolicy = ModelPolicy()
    autonomy_level: AutonomyLevel
    enabled: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "application")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("Identifiant ARCenal invalide.")
        return value


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    autonomy_level: AutonomyLevel | None = None
    enabled: bool | None = None
    model_policy: ModelPolicy | None = None

    @field_validator("autonomy_level", mode="before")
    @classmethod
    def parse_autonomy_level(cls, value: object) -> object:
        return AutonomyLevel(value) if isinstance(value, str) else value


class ApplicationIdentity(StrictModel):
    application_id: str
    user_id: str | None = Field(default=None, max_length=128)
    user_source: UserIdentitySource = UserIdentitySource.NONE

    @field_validator("application_id")
    @classmethod
    def validate_application_id(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("Identité applicative invalide.")
        return value


class RequestIdentity(StrictModel):
    request_id: str
    user_id: str | None
    user_source: UserIdentitySource
    application_id: str
    agent_id: str
    session_id: str | None
    permissions: tuple[Permission, ...]
    timestamp: datetime


class EffectiveContext(StrictModel):
    identity: RequestIdentity
    agent: AgentDefinition
    system_prompt: str
    permissions: tuple[Permission, ...]
    tools: tuple[str, ...]
    knowledge_scopes: tuple[str, ...]
    model_policy: ModelPolicy
    context_plan: ContextPlan
    knowledge_context: str
    document_context: str
    memory_context: str
    sources: tuple[SourceCitation, ...]
    retrieval_metrics: RetrievalMetrics
    request_context: dict[str, str] = Field(default_factory=dict)


class EngineOutput(StrictModel):
    response: str
    sources: tuple[dict[str, str], ...] = ()
    actions: tuple[dict[str, str], ...] = ()
    usage: dict[str, bool | int | float | str] = Field(default_factory=dict)


class AgentQueryResponse(StrictModel):
    request_id: str
    agent_id: str
    response: str
    status: str
    approval_required: bool
    sources: tuple[dict[str, str], ...] = ()
    actions: tuple[dict[str, str], ...] = ()
    usage: dict[str, bool | int | float | str] = Field(default_factory=dict)
