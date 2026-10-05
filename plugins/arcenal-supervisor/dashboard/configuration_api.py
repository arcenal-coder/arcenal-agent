"""API bornée de configuration native et de secrets d’ARC."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

router = APIRouter(prefix="/configuration/v1")
SECRET_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
RESERVED_SECRET_KEYS = frozenset({"HOME", "LD_PRELOAD", "PATH", "PYTHONPATH"})
PROVIDER_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PROVIDER_SECRETS = {
    "anthropic": "ANTHROPIC_API_KEY", "compatible": "OPENAI_COMPATIBLE_API_KEY",
    "gemini": "GEMINI_API_KEY", "internal": "ARCENAL_INTERNAL_LLM_API_KEY",
    "groq": "GROQ_API_KEY", "mistral": "MISTRAL_API_KEY", "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY", "vllm": "VLLM_API_KEY",
}


def _core() -> ModuleType:
    core = sys.modules.get("arcenal_arc_core")
    if core is None:
        raise RuntimeError("ARC Core doit être chargé avant l’API de configuration.")
    return core


CORE = _core()


class StrictModel(BaseModel):
    """Contrat HTTP strict commun aux paramètres ARC."""

    model_config = ConfigDict(extra="forbid", strict=True)


class GeneralSettings(StrictModel):
    agent_name: str = Field(min_length=1, max_length=80)
    language: Literal["fr", "en"]
    notification_email: str = Field(max_length=320)
    organization_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=80)

    @field_validator("notification_email")
    @classmethod
    def validate_notification_email(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Adresse de notification invalide.")
        return value


class AppearanceSettings(StrictModel):
    accent_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    button_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    favicon_url: str = Field(max_length=2_048)
    link_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str = Field(max_length=2_048)
    text_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("favicon_url", "logo_url")
    @classmethod
    def validate_asset_url(cls, value: str) -> str:
        asset_path = r"^/(?:[A-Za-z0-9._~-]+/)*api/plugins/arcenal-supervisor/branding/assets/(?:logo|favicon)(?:\?v=\d+)?$"
        if not value or re.fullmatch(asset_path, value):
            return value
        return _http_url(value)


class OnboardingSettings(StrictModel):
    completed: bool
    completed_at: str = Field(max_length=80)
    version: int = Field(ge=1, le=100)


class AccessCredential(StrictModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join((value.split("_")[0], *(part.title() for part in value.split("_")[1:]))), populate_by_name=True, extra="forbid", strict=True)
    autonomy: Literal["manual", "smart", "off"]
    enabled: bool = True
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]{0,63}$")
    kind: Literal["account", "api"]
    label: str = Field(min_length=1, max_length=120)
    login: str | None = Field(default=None, max_length=240)
    permissions: tuple[str, ...] = Field(max_length=20)
    secret_env: str = Field(pattern=r"^ARCENAL_ACCESS_[A-Z0-9_]+_(API_KEY|PASSWORD)$")
    service_url: str = Field(pattern=r"^https?://", max_length=2_048)

    @field_validator("service_url")
    @classmethod
    def validate_service_url(cls, value: str) -> str:
        return _http_url(value)


class ProductSettings(StrictModel):
    access_credentials: tuple[AccessCredential, ...] | None = None
    appearance: AppearanceSettings | None = None
    general: GeneralSettings | None = None
    onboarding: OnboardingSettings | None = None


class ProviderSettings(StrictModel):
    base_url: str | None = Field(default=None, max_length=2_048)
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return _http_url(value) if value else value


class ApprovalSettings(StrictModel):
    mode: Literal["manual", "smart", "off"]


class ConfigurationPatch(StrictModel):
    approvals: ApprovalSettings | None = None
    arcenal: ProductSettings | None = None
    providers: dict[str, ProviderSettings] | None = None

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, value: dict[str, ProviderSettings] | None) -> dict[str, ProviderSettings] | None:
        if value is not None and any(not PROVIDER_PATTERN.fullmatch(key) for key in value):
            raise ValueError("Identifiant de fournisseur invalide.")
        return value


class SecretWrite(StrictModel):
    value: SecretStr = Field(min_length=1, max_length=65_536)


def _http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Adresse HTTP ou HTTPS invalide.")
    return value


def _runtime():
    return CORE.runtime_configuration()


def _snapshot(runtime) -> dict[str, object]:
    config = runtime.config
    product = {key: config.get("ui", key, {}) for key in ("general", "appearance", "onboarding")}
    product["access_credentials"] = config.get("system", "access_credentials", [])
    return {
        "approvals": config.get("core", "approvals", {}), "arcenal": product,
        "providers": config.list("providers"),
    }


def _secret_keys(runtime) -> tuple[str, ...]:
    credentials = runtime.access_credentials()
    access_keys = tuple(item.get("secretEnv") for item in credentials)
    valid_access = tuple(item for item in access_keys if isinstance(item, str) and SECRET_PATTERN.fullmatch(item))
    return tuple(sorted({*PROVIDER_SECRETS.values(), *valid_access}))


def _secret_status(runtime) -> dict[str, bool]:
    return {key: runtime.vault.has_secret(key) for key in _secret_keys(runtime)}


def _migration_payload(runtime) -> dict[str, object]:
    report = runtime.migration
    return {"conflicts": list(report.conflicts), "copied": report.copied, "state": runtime.migration_state, "unchanged": report.unchanged}


@router.get("")
def read_configuration() -> dict[str, object]:
    runtime = _runtime()
    return {
        "backend": runtime.backend, "config": _snapshot(runtime),
        "migration": _migration_payload(runtime), "secrets": _secret_status(runtime),
        "vault": "ready",
    }


@router.put("")
def write_configuration(payload: ConfigurationPatch) -> dict[str, bool]:
    runtime = _runtime()
    try:
        _write_product(runtime.config, payload.arcenal)
        _write_providers(runtime.config, payload.providers)
        _write_single(runtime.config, "core", "approvals", payload.approvals)
    except CORE.ArcConfigurationReadOnlyError as exc:
        raise HTTPException(status_code=409, detail="Le mode legacy Hermes est en lecture seule.") from exc
    return {"ok": True}


def _write_product(store, product: ProductSettings | None) -> None:
    if product is None:
        return
    for key in ("general", "appearance", "onboarding"):
        _write_single(store, "ui", key, getattr(product, key))
    if product.access_credentials is not None:
        values = [item.model_dump(by_alias=True, exclude_none=True, mode="json") for item in product.access_credentials]
        store.set("system", "access_credentials", values)


def _write_providers(store, providers: dict[str, ProviderSettings] | None) -> None:
    if providers is None:
        return
    for provider_id, settings in providers.items():
        store.set("providers", provider_id, settings.model_dump(exclude_none=True, mode="json"))


def _write_single(store, namespace: str, key: str, value: BaseModel | None) -> None:
    if value is not None:
        store.set(namespace, key, value.model_dump(exclude_none=True, mode="json"))


def _validated_secret_key(key: str) -> str:
    if not SECRET_PATTERN.fullmatch(key) or key in RESERVED_SECRET_KEYS:
        raise HTTPException(status_code=422, detail="Nom de secret ARC invalide.")
    return key


@router.put("/secrets/{key}")
def write_secret(key: str, payload: SecretWrite) -> dict[str, bool]:
    checked = _validated_secret_key(key)
    value = payload.value.get_secret_value()
    _runtime().vault.set_secret(checked, value)
    os.environ[checked] = value
    return {"configured": True}


@router.delete("/secrets/{key}")
def delete_secret(key: str) -> dict[str, bool]:
    checked = _validated_secret_key(key)
    vault = _runtime().vault
    vault.delete_secret(checked)
    os.environ.pop(checked, None)
    return {"configured": vault.has_secret(checked)}
