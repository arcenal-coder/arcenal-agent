"""Coffre de secrets local et minimal d’ARC."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

_SECRET_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_RESERVED_KEYS = frozenset({"HOME", "LD_PRELOAD", "PATH", "PYTHONPATH"})


class ArcVaultError(RuntimeError):
    """Erreur d’accès au coffre ARC."""


class ArcSecretKeyError(ArcVaultError):
    """Nom de secret non conforme."""


class ArcSecretValueError(ArcVaultError):
    """Valeur de secret non conforme."""


class ArcSecretMissingError(ArcVaultError):
    """Secret obligatoire absent."""


class ArcVault(Protocol):
    """Contrat du coffre de secrets ARC."""

    def get_secret(self, key: str) -> str | None: ...

    def require_secret(self, key: str) -> str: ...

    def set_secret(self, key: str, value: str) -> None: ...

    def delete_secret(self, key: str) -> None: ...

    def has_secret(self, key: str) -> bool: ...


class ArcFileVault:
    """Coffre atomique compatible avec le fichier .env historique."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def get_secret(self, key: str) -> str | None:
        _validate_key(key)
        runtime = os.environ.get(key)
        value = runtime if runtime is not None else self._read().get(key)
        return value if value and value.strip() else None

    def require_secret(self, key: str) -> str:
        value = self.get_secret(key)
        if value is None:
            raise ArcSecretMissingError(f"Secret ARC absent : {key}.")
        return value

    def set_secret(self, key: str, value: str) -> None:
        _validate_key(key)
        _validate_value(value)
        self._write({**self._read(), key: value})

    def delete_secret(self, key: str) -> None:
        _validate_key(key)
        self._write({item: value for item, value in self._read().items() if item != key})

    def has_secret(self, key: str) -> bool:
        return self.get_secret(key) is not None

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return _parse_env(self._path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ArcVaultError(f"Coffre ARC illisible : {self._path}.") from exc

    def _write(self, values: dict[str, str]) -> None:
        self._prepare_directory()
        descriptor, temporary = tempfile.mkstemp(prefix=".arc-vault-", dir=self._path.parent)
        try:
            _write_vault(descriptor, values)
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            _remove_temporary(temporary)
            raise ArcVaultError(f"Coffre ARC non enregistré : {self._path}.") from exc

    def _prepare_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._path.parent.chmod(0o700)


def _validate_key(key: str) -> None:
    if not _SECRET_PATTERN.fullmatch(key) or key in _RESERVED_KEYS:
        raise ArcSecretKeyError(f"Nom de secret ARC invalide : {key!r}.")


def _validate_value(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 65_536:
        raise ArcSecretValueError("Le secret ARC doit être une chaîne non vide de taille bornée.")


def _parse_env(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        parsed = _parse_line(line, line_number)
        if parsed is not None:
            result[parsed[0]] = parsed[1]
    return result


def _parse_line(line: str, line_number: int) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    candidate = stripped[7:] if stripped.startswith("export ") else stripped
    if "=" not in candidate:
        raise ArcVaultError(f"Ligne {line_number} invalide dans le coffre ARC.")
    key, raw = candidate.split("=", 1)
    _validate_key(key.strip())
    return key.strip(), _decode_value(raw.strip(), line_number)


def _decode_value(raw: str, line_number: int) -> str:
    if raw.startswith('"'):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArcVaultError(f"Secret mal encodé à la ligne {line_number}.") from exc
        if not isinstance(decoded, str):
            raise ArcVaultError(f"Secret non textuel à la ligne {line_number}.")
        return decoded
    if len(raw) >= 2 and raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    return raw


def _write_vault(descriptor: int, values: dict[str, str]) -> None:
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        for key in sorted(values):
            stream.write(f"{key}={json.dumps(values[key], ensure_ascii=False)}\n")
        stream.flush()
        os.fsync(stream.fileno())


def _remove_temporary(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        return
