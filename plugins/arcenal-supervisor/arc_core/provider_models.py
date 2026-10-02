"""Contrats stricts des fournisseurs interchangeables d’ARC."""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from .contracts import StrictModel
from .frugal_models import ModelLocation


class ProviderCapability(str, Enum):
    CHAT = "chat"
    STREAMING = "streaming"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    EMBEDDINGS = "embeddings"
    TOKEN_USAGE = "token_usage"
    COST_REPORTING = "cost_reporting"


class ProviderHealth(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class AuthenticationType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"


class ProviderDescriptor(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")
    enabled: bool = False
    base_url: str | None = Field(default=None, max_length=2_048)
    authentication_type: AuthenticationType
    secret_reference: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{1,127}$")
    location: ModelLocation
    jurisdiction: str | None = Field(default=None, max_length=80)
    capabilities: tuple[ProviderCapability, ...]
    priority: int = Field(default=100, ge=0, le=10_000)
    health: ProviderHealth = ProviderHealth.UNKNOWN

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: tuple[ProviderCapability, ...]) -> tuple[ProviderCapability, ...]:
        if ProviderCapability.CHAT not in value:
            raise ValueError("Un fournisseur de génération doit prendre en charge le chat.")
        return tuple(dict.fromkeys(value))


class ProviderAttempt(StrictModel):
    provider: str
    model: str
    attempt: int = Field(ge=1, le=3)
    status: str = Field(pattern=r"^(success|failed|rate_limited|timeout|unavailable|invalid_response)$")
    duration_ms: float = Field(ge=0)
    error_code: str | None = Field(default=None, max_length=80)
