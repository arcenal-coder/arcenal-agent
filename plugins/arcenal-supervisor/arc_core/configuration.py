"""Contrats et stockage de configuration natifs d’ARC."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias, cast

JsonScalar: TypeAlias = str | bool | int | float | None
ConfigValue: TypeAlias = JsonScalar | list["ConfigValue"] | dict[str, "ConfigValue"]

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_NAMESPACES = frozenset({"core", "agents", "providers", "models", "rag", "memory", "automation", "ui", "system"})


class ArcConfigurationError(RuntimeError):
    """Erreur de configuration ARC."""


class ArcConfigurationKeyError(ArcConfigurationError):
    """Clé ou espace de noms de configuration invalide."""


class ArcConfigurationValueError(ArcConfigurationError):
    """Valeur incompatible avec le contrat de configuration."""


class ArcConfigurationReadOnlyError(ArcConfigurationError):
    """Tentative d’écriture dans un adaptateur en lecture seule."""


class ArcConfigStore(Protocol):
    """Contrat minimal d’un stockage de configuration ARC."""

    def get(self, namespace: str, key: str, default: ConfigValue = None) -> ConfigValue: ...

    def set(self, namespace: str, key: str, value: ConfigValue) -> None: ...

    def delete(self, namespace: str, key: str) -> None: ...

    def exists(self, namespace: str, key: str) -> bool: ...

    def list(self, namespace: str) -> dict[str, ConfigValue]: ...


def validate_config_value(value: object) -> ConfigValue:
    """Valide récursivement une valeur sérialisable et fortement bornée."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ArcConfigurationValueError("Les nombres non finis sont interdits.")
    if value is None or isinstance(value, (str, bool, int, float)):
        return cast(ConfigValue, value)
    if isinstance(value, list):
        return [validate_config_value(item) for item in value]
    if isinstance(value, dict):
        return _validate_mapping(cast(dict[object, object], value))
    raise ArcConfigurationValueError(f"Type de configuration interdit : {type(value).__name__}.")


def _validate_mapping(value: Mapping[object, object]) -> dict[str, ConfigValue]:
    if not all(isinstance(key, str) for key in value):
        raise ArcConfigurationValueError("Les clés d’objet doivent être des chaînes.")
    return {cast(str, key): validate_config_value(item) for key, item in value.items()}


def _validate_key(namespace: str, key: str) -> None:
    if namespace not in _NAMESPACES:
        raise ArcConfigurationKeyError(f"Espace de noms ARC invalide : {namespace!r}.")
    if not _KEY_PATTERN.fullmatch(key):
        raise ArcConfigurationKeyError(f"Clé ARC invalide : {key!r}.")


class ArcNativeConfigStore:
    """Stockage JSON atomique, local et protégé de la configuration ARC."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, namespace: str, key: str, default: ConfigValue = None) -> ConfigValue:
        _validate_key(namespace, key)
        return self._read().get(namespace, {}).get(key, default)

    def set(self, namespace: str, key: str, value: ConfigValue) -> None:
        _validate_key(namespace, key)
        checked = validate_config_value(value)
        current = self._read()
        section = {**current.get(namespace, {}), key: checked}
        self._write({**current, namespace: section})

    def delete(self, namespace: str, key: str) -> None:
        _validate_key(namespace, key)
        current = self._read()
        section = {item: value for item, value in current.get(namespace, {}).items() if item != key}
        updated = {item: value for item, value in current.items() if item != namespace}
        self._write({**updated, **({namespace: section} if section else {})})

    def exists(self, namespace: str, key: str) -> bool:
        _validate_key(namespace, key)
        return key in self._read().get(namespace, {})

    def list(self, namespace: str) -> dict[str, ConfigValue]:
        if namespace not in _NAMESPACES:
            raise ArcConfigurationKeyError(f"Espace de noms ARC invalide : {namespace!r}.")
        return dict(self._read().get(namespace, {}))

    def _read(self) -> dict[str, dict[str, ConfigValue]]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArcConfigurationError(f"Configuration ARC illisible : {self._path}.") from exc
        return _validate_document(raw)

    def _write(self, document: dict[str, dict[str, ConfigValue]]) -> None:
        self._prepare_directory()
        descriptor, temporary = tempfile.mkstemp(prefix=".arc-config-", dir=self._path.parent)
        try:
            _write_document(descriptor, document)
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            _remove_temporary(temporary)
            raise ArcConfigurationError(f"Configuration ARC non enregistrée : {self._path}.") from exc

    def _prepare_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._path.parent.chmod(0o700)


def _validate_document(raw: object) -> dict[str, dict[str, ConfigValue]]:
    if not isinstance(raw, dict):
        raise ArcConfigurationValueError("La racine de configuration doit être un objet.")
    result: dict[str, dict[str, ConfigValue]] = {}
    for namespace, section in raw.items():
        if not isinstance(namespace, str) or namespace not in _NAMESPACES or not isinstance(section, dict):
            raise ArcConfigurationValueError("Structure de configuration ARC invalide.")
        result[namespace] = _validate_mapping(cast(dict[object, object], section))
    return result


def _write_document(descriptor: int, document: dict[str, dict[str, ConfigValue]]) -> None:
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _remove_temporary(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        return


@dataclass(frozen=True)
class ArcMigrationReport:
    copied: int
    unchanged: int
    conflicts: tuple[str, ...]


def migrate_hermes_configuration(native: ArcConfigStore, legacy: ArcConfigStore) -> ArcMigrationReport:
    copied = 0
    unchanged = 0
    conflicts: list[str] = []
    for namespace in ("core", "models", "providers", "system", "ui"):
        for key, value in legacy.list(namespace).items():
            outcome = _migrate_value(native, namespace, key, value)
            copied += outcome == "copied"
            unchanged += outcome == "unchanged"
            if outcome == "conflict":
                conflicts.append(f"{namespace}.{key}")
    return ArcMigrationReport(copied, unchanged, tuple(sorted(conflicts)))


def _migrate_value(store: ArcConfigStore, namespace: str, key: str, value: ConfigValue) -> str:
    if not store.exists(namespace, key):
        store.set(namespace, key, value)
        return "copied"
    if store.get(namespace, key) == value:
        return "unchanged"
    return "conflict"
