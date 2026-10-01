"""Adaptateur transitoire en lecture seule vers la configuration HERMES."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from .configuration import (
    ArcConfigurationReadOnlyError,
    ConfigValue,
    validate_config_value,
)

LegacyLoader = Callable[[], Mapping[str, object]]


class HermesConfigAdapter:
    """Expose les valeurs HERMES selon les espaces de noms ARC."""

    def __init__(self, loader: LegacyLoader | None = None) -> None:
        self._loader = loader or _legacy_loader()

    def get(self, namespace: str, key: str, default: ConfigValue = None) -> ConfigValue:
        return self.list(namespace).get(key, default)

    def set(self, namespace: str, key: str, value: ConfigValue) -> None:
        raise ArcConfigurationReadOnlyError("La configuration HERMES est accessible en lecture seule.")

    def delete(self, namespace: str, key: str) -> None:
        raise ArcConfigurationReadOnlyError("La configuration HERMES est accessible en lecture seule.")

    def exists(self, namespace: str, key: str) -> bool:
        return key in self.list(namespace)

    def list(self, namespace: str) -> dict[str, ConfigValue]:
        raw = self._loader()
        if namespace == "models":
            return _model_values(raw.get("model"), raw.get("auxiliary"))
        if namespace == "providers":
            return _object_values(raw.get("providers"))
        if namespace == "system":
            return _system_values(raw.get("arcenal"))
        if namespace == "core":
            return _core_values(raw.get("approvals"))
        if namespace == "ui":
            return _ui_values(raw.get("arcenal"))
        return {}


def _legacy_loader() -> LegacyLoader:
    # L'import tardif garantit que le démarrage natif ne charge pas Hermes Config.
    from hermes_cli.config import load_config_readonly

    return load_config_readonly


def _model_values(raw: object, auxiliary: object) -> dict[str, ConfigValue]:
    values = _object_values(raw)
    result = {key: value for key, value in values.items() if key in {"provider", "default"}}
    auxiliary_values = _object_values(auxiliary)
    return {**result, **({"auxiliary": auxiliary_values} if auxiliary_values else {})}


def _system_values(raw: object) -> dict[str, ConfigValue]:
    values = _object_values(raw)
    credentials = values.get("access_credentials")
    return {"access_credentials": credentials} if credentials is not None else {}


def _core_values(raw: object) -> dict[str, ConfigValue]:
    values = _object_values(raw)
    return {"approvals": values} if values else {}


def _ui_values(raw: object) -> dict[str, ConfigValue]:
    values = _object_values(raw)
    allowed = {"appearance", "general", "onboarding"}
    return {key: value for key, value in values.items() if key in allowed}


def _object_values(raw: object) -> dict[str, ConfigValue]:
    if not isinstance(raw, Mapping):
        return {}
    checked = validate_config_value(dict(raw))
    return cast(dict[str, ConfigValue], checked)
