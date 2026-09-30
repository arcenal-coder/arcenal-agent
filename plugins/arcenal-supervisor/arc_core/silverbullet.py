"""Synchronisation incrémentale du coffre SilverBullet vers ARC."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlparse

from pydantic import Field, field_validator

from .contracts import StrictModel

MAX_PAGE_BYTES = 2 * 1_048_576


class SilverBulletError(RuntimeError):
    """Erreur de synchronisation SilverBullet expurgée de tout secret."""


class SilverBulletAuthenticationError(SilverBulletError):
    """Le jeton SilverBullet a été refusé."""


class SilverBulletProtocolError(SilverBulletError):
    """La réponse SilverBullet ne respecte pas le contrat attendu."""


class SilverBulletSettings(StrictModel):
    base_url: str
    token: str = Field(min_length=1, max_length=4096, repr=False)

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("L’adresse SilverBullet doit utiliser HTTP ou HTTPS.")
        if parsed.username or parsed.password:
            raise ValueError("L’adresse SilverBullet ne doit contenir aucun identifiant.")
        return value.strip().rstrip("/")


class SilverBulletResponse(StrictModel):
    status_code: int = Field(ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    payload: object = None
    content: bytes = b""


class SilverBulletEntry(StrictModel):
    path: str
    etag: str


class SilverBulletSyncState(StrictModel):
    etags: dict[str, str] = Field(default_factory=dict)
    last_sync_at: datetime | None = None
    last_error: str = ""


class SilverBulletSyncResult(StrictModel):
    downloaded: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    removed: int = Field(ge=0)
    synchronized_at: datetime


class SilverBulletTransport(Protocol):
    async def request(self, method: str, url: str, headers: dict[str, str]) -> SilverBulletResponse: ...


class JsonResponse(Protocol):
    def json(self) -> object: ...


class HttpxSilverBulletTransport:
    async def request(self, method: str, url: str, headers: dict[str, str]) -> SilverBulletResponse:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=False) as client:
                response = await client.request(method, url, headers=headers)
        except httpx.HTTPError as exc:
            raise SilverBulletError("SilverBullet est temporairement inaccessible.") from exc
        return SilverBulletResponse(
            status_code=response.status_code,
            headers={key.casefold(): value for key, value in response.headers.items()},
            payload=_json_payload(response),
            content=response.content,
        )


class SilverBulletSynchronizer:
    def __init__(self, settings: SilverBulletSettings, home: Path, transport: SilverBulletTransport) -> None:
        self._settings = settings
        self._mirror = home / "knowledge" / ".silverbullet"
        self._state = SilverBulletStateRepository(home / "arcenal" / "silverbullet-sync.json")
        self._transport = transport

    async def sync(self) -> SilverBulletSyncResult:
        previous = self._state.load()
        entries = await self._list_entries()
        downloaded = await self._download_changes(entries, previous)
        removed = self._remove_stale(entries)
        synchronized_at = datetime.now(timezone.utc)
        self._state.save(SilverBulletSyncState(etags=_etags(entries), last_sync_at=synchronized_at))
        return SilverBulletSyncResult(downloaded=downloaded, unchanged=len(entries) - downloaded, removed=removed, synchronized_at=synchronized_at)

    async def _list_entries(self) -> tuple[SilverBulletEntry, ...]:
        response = await self._request("GET", "/.fs")
        _raise_for_status(response)
        return _entries(response.payload)

    async def _download_changes(self, entries: tuple[SilverBulletEntry, ...], state: SilverBulletSyncState) -> int:
        changed = tuple(entry for entry in entries if self._changed(entry, state))
        for entry in changed:
            await self._download(entry)
        return len(changed)

    def _changed(self, entry: SilverBulletEntry, state: SilverBulletSyncState) -> bool:
        target = _mirror_path(self._mirror, entry.path)
        return state.etags.get(entry.path) != entry.etag or not target.is_file()

    async def _download(self, entry: SilverBulletEntry) -> None:
        encoded = "/".join(quote(part, safe="") for part in Path(entry.path).parts)
        response = await self._request("GET", f"/.fs/{encoded}")
        _raise_for_status(response)
        _atomic_write(_mirror_path(self._mirror, entry.path), _validated_markdown(response.content))

    def _remove_stale(self, entries: tuple[SilverBulletEntry, ...]) -> int:
        expected = {entry.path for entry in entries}
        existing = tuple(self._mirror.rglob("*.md")) if self._mirror.is_dir() else ()
        stale = tuple(path for path in existing if path.relative_to(self._mirror).as_posix() not in expected)
        for path in stale:
            path.unlink(missing_ok=True)
        return len(stale)

    async def _request(self, method: str, path: str) -> SilverBulletResponse:
        headers = {"accept": "application/json", "authorization": f"Bearer {self._settings.token}"}
        return await self._transport.request(method, f"{self._settings.base_url}{path}", headers)


class SilverBulletStateRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> SilverBulletSyncState:
        if not self._path.is_file():
            return SilverBulletSyncState()
        try:
            return SilverBulletSyncState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise SilverBulletProtocolError("L’état de synchronisation SilverBullet est invalide.") from exc

    def save(self, state: SilverBulletSyncState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".silverbullet.", dir=self._path.parent)
        _replace_state(descriptor, Path(temporary_name), self._path, state)

    def record_error(self, message: str) -> None:
        current = self.load()
        self.save(current.model_copy(update={"last_error": message[:500]}))


def _json_payload(response: JsonResponse) -> object:
    try:
        return response.json()
    except (TypeError, ValueError):
        return None


def _raise_for_status(response: SilverBulletResponse) -> None:
    if response.status_code in {401, 403}:
        raise SilverBulletAuthenticationError("SilverBullet a refusé le jeton d’accès.")
    if not 200 <= response.status_code < 300:
        raise SilverBulletProtocolError(f"SilverBullet répond avec le code HTTP {response.status_code}.")


def _entries(payload: object) -> tuple[SilverBulletEntry, ...]:
    record = _record(payload)
    raw_entries = record.get("files") if record is not None else payload
    if not isinstance(raw_entries, list) or len(raw_entries) > 10_000:
        raise SilverBulletProtocolError("La liste des fichiers SilverBullet est invalide.")
    entries = tuple(_entry(item) for item in raw_entries)
    return tuple(sorted((entry for entry in entries if entry is not None), key=lambda item: item.path))


def _entry(value: object) -> SilverBulletEntry | None:
    record = _record(value)
    if record is None:
        raise SilverBulletProtocolError("Une entrée SilverBullet est invalide.")
    raw_path = record.get("name", record.get("path"))
    if not isinstance(raw_path, str):
        raise SilverBulletProtocolError("Un chemin SilverBullet est absent.")
    path = _safe_relative_path(raw_path)
    if path.suffix.casefold() != ".md":
        return None
    raw_etag = record.get("etag", record.get("ETag", _fallback_revision(record)))
    return SilverBulletEntry(path=path.as_posix(), etag=str(raw_etag))


def _safe_relative_path(value: str) -> Path:
    path = Path(value.strip().replace("\\", "/"))
    invalid = path.is_absolute() or not path.parts or ".." in path.parts or any(part.startswith(".") for part in path.parts)
    if invalid or len(value) > 500 or "\x00" in value:
        raise SilverBulletProtocolError("Un chemin SilverBullet sort du coffre autorisé.")
    return path


def _mirror_path(root: Path, relative: str) -> Path:
    target = (root / _safe_relative_path(relative)).resolve()
    if root.resolve() not in target.parents:
        raise SilverBulletProtocolError("Un chemin SilverBullet sort du miroir autorisé.")
    return target


def _atomic_write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, target)
        target.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise SilverBulletError("Le miroir SilverBullet ne peut pas être mis à jour.") from exc


def _replace_state(descriptor: int, temporary: Path, target: Path, state: SilverBulletSyncState) -> None:
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(state.model_dump_json(indent=2))
        os.replace(temporary, target)
        target.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise SilverBulletError("L’état SilverBullet ne peut pas être enregistré.") from exc


def _etags(entries: tuple[SilverBulletEntry, ...]) -> dict[str, str]:
    return {entry.path: entry.etag for entry in entries}


def _fallback_revision(record: dict[str, object]) -> str:
    modified = record.get("lastModified", record.get("last_modified", ""))
    return f"{modified}:{record.get('size', '')}"


def _validated_markdown(content: bytes) -> bytes:
    if not content or len(content) > MAX_PAGE_BYTES:
        raise SilverBulletProtocolError("Une page SilverBullet est vide ou dépasse 2 Mio.")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SilverBulletProtocolError("Une page SilverBullet n’est pas encodée en UTF-8.") from exc
    return content


def _record(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    return {str(key): item for key, item in value.items()}
