from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_core() -> ModuleType:
    name = "arcenal_arc_core"
    if name in sys.modules:
        return sys.modules[name]
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_core()


class FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    async def request(self, method: str, url: str, headers: dict[str, str]) -> object:
        self.requests.append((method, url, headers))
        return self.responses.pop(0)


def _response(status: int, *, payload: object = None, content: bytes = b"", etag: str = "") -> object:
    return CORE.SilverBulletResponse(status_code=status, headers={"etag": etag} if etag else {}, payload=payload, content=content)


@pytest.mark.asyncio
async def test_sync_downloads_markdown_and_persists_etag(tmp_path: Path) -> None:
    transport = FakeTransport([
        _response(200, payload=[{"name": "LDA/procedure.md", "etag": '"v1"'}]),
        _response(200, content=b"# Procedure\n\nContenu applicable.", etag='"v1"'),
    ])
    synchronizer = CORE.SilverBulletSynchronizer(
        CORE.SilverBulletSettings(base_url="https://notes.example.test", token="secret"),
        tmp_path,
        transport,
    )

    result = await synchronizer.sync()

    assert result.downloaded == 1
    assert result.unchanged == 0
    assert (tmp_path / "knowledge" / ".silverbullet" / "LDA" / "procedure.md").read_text() == "# Procedure\n\nContenu applicable."
    assert transport.requests[1][2]["authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_sync_skips_unchanged_etag(tmp_path: Path) -> None:
    first = FakeTransport([
        _response(200, payload=[{"name": "note.md", "etag": '"v1"'}]),
        _response(200, content=b"# Note", etag='"v1"'),
    ])
    settings = CORE.SilverBulletSettings(base_url="https://notes.example.test/", token="secret")
    await CORE.SilverBulletSynchronizer(settings, tmp_path, first).sync()
    second = FakeTransport([_response(200, payload=[{"name": "note.md", "etag": '"v1"'}])])

    result = await CORE.SilverBulletSynchronizer(settings, tmp_path, second).sync()

    assert result.downloaded == 0
    assert result.unchanged == 1
    assert len(second.requests) == 1


@pytest.mark.asyncio
async def test_sync_removes_stale_mirror_without_touching_local_vault(tmp_path: Path) -> None:
    mirror = tmp_path / "knowledge" / ".silverbullet"
    mirror.mkdir(parents=True)
    (mirror / "obsolete.md").write_text("# Ancien", encoding="utf-8")
    local = tmp_path / "knowledge" / "local.md"
    local.write_text("# Local", encoding="utf-8")
    transport = FakeTransport([_response(200, payload=[])])

    result = await CORE.SilverBulletSynchronizer(
        CORE.SilverBulletSettings(base_url="https://notes.example.test", token="secret"),
        tmp_path,
        transport,
    ).sync()

    assert result.removed == 1
    assert not (mirror / "obsolete.md").exists()
    assert local.is_file()


@pytest.mark.parametrize("url", ["file:///tmp/notes", "https://user:pass@example.test", "not-an-url"])
def test_settings_reject_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        CORE.SilverBulletSettings(base_url=url, token="secret")


@pytest.mark.asyncio
async def test_sync_rejects_traversal_and_authentication_failure(tmp_path: Path) -> None:
    traversal = FakeTransport([_response(200, payload=[{"name": "../secret.md", "etag": '"v1"'}])])
    settings = CORE.SilverBulletSettings(base_url="https://notes.example.test", token="secret")
    with pytest.raises(CORE.SilverBulletProtocolError):
        await CORE.SilverBulletSynchronizer(settings, tmp_path, traversal).sync()

    unauthorized = FakeTransport([_response(401, payload={})])
    with pytest.raises(CORE.SilverBulletAuthenticationError):
        await CORE.SilverBulletSynchronizer(settings, tmp_path, unauthorized).sync()


@pytest.mark.asyncio
async def test_sync_rejects_invalid_or_oversized_markdown(tmp_path: Path) -> None:
    settings = CORE.SilverBulletSettings(base_url="https://notes.example.test", token="secret")
    invalid = FakeTransport([
        _response(200, payload=[{"name": "note.md", "etag": '"v1"'}]),
        _response(200, content=b"\xff\xfe", etag='"v1"'),
    ])

    with pytest.raises(CORE.SilverBulletProtocolError):
        await CORE.SilverBulletSynchronizer(settings, tmp_path, invalid).sync()

    oversized = FakeTransport([
        _response(200, payload=[{"name": "note.md", "etag": '"v2"'}]),
        _response(200, content=b"a" * (2 * 1_048_576 + 1), etag='"v2"'),
    ])
    with pytest.raises(CORE.SilverBulletProtocolError):
        await CORE.SilverBulletSynchronizer(settings, tmp_path, oversized).sync()
