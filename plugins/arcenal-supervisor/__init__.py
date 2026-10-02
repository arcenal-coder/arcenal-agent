"""Branche les outils de supervision ARCenal dans le chat Hermes."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .arc_core import AgentHarness

from .capabilities import record_usage

from .tools import (
    ACCESS_CATALOG_SCHEMA,
    CONTEXT_SEARCH_SCHEMA,
    CREATE_REPORT_SCHEMA,
    KNOWLEDGE_DOCUMENT_SCHEMA,
    KNOWLEDGE_SEARCH_SCHEMA,
    MEMORY_SEARCH_SCHEMA,
    REPAIR_SCHEMA,
    SYSTEM_STATUS_SCHEMA,
    YUNOHOST_QUERY_SCHEMA,
    access_catalog,
    context_search,
    create_report,
    knowledge_document,
    knowledge_search,
    memory_search,
    repair,
    system_status,
    yunohost_query,
)


HARNESS_PROMPT_MAX_CHARS = 4_000
HARNESS_SECTION_MAX_CHARS = 1_250


class PromptBudgetError(ValueError):
    """Le budget ne peut pas préserver le marqueur de continuation."""


def _bounded_excerpt(content: str, max_chars: int, continuation: str) -> str:
    if max_chars <= len(continuation) + 1:
        raise PromptBudgetError("Le budget du prompt est trop petit.")
    normalized = content.strip()
    if len(normalized) <= max_chars:
        return normalized
    available = max_chars - len(continuation) - 1
    clipped = normalized[:available].rsplit("\n", 1)[0].rstrip()
    if not clipped:
        clipped = normalized[:available].rstrip()
    return f"{clipped}\n{continuation}"


def _agent_harness_prompt(session_info: Mapping[str, Any]) -> str:
    profile_name = str(session_info.get("profile_name") or "default")
    harness = _harness_for_profile(profile_name)
    sections = (
        _harness_section("Contexte", harness.context),
        _harness_section("Directives", harness.directives),
        _harness_section("Mémoire", harness.memory),
    )
    content = "\n\n".join(section for section in sections if section)
    if not content:
        return ""
    return _bounded_excerpt(content, HARNESS_PROMPT_MAX_CHARS, "[Harnais agent tronqué]")


def _harness_for_profile(profile_name: str) -> AgentHarness:
    from hermes_constants import get_hermes_home
    from .arc_core import AgentHarness, AgentRepository, default_agents, migrate_legacy_harness

    home = get_hermes_home()
    profile_harness = _profile_harness(home, profile_name)
    if profile_harness is not None:
        return profile_harness
    repository = AgentRepository(home / "arcenal" / "agents.json", default_agents())
    agents = migrate_legacy_harness(repository, home / "arcenal" / "managed-files")
    expected = "arc" if profile_name == "default" else profile_name
    agent = next((item for item in agents if item.metadata.get("profile") == profile_name or item.id == expected), None)
    return agent.harness if agent is not None else AgentHarness()


def _profile_harness(home: Path, profile_name: str) -> AgentHarness | None:
    from .arc_core import AgentHarness

    if profile_name == "default":
        return None
    root = home if home.name == profile_name else home / "profiles" / profile_name
    values = {
        "context": _read_profile_parameter(root / "CONTEXT.md"),
        "directives": _read_profile_parameter(root / "DIRECTIVES.md"),
        "memory": _read_profile_parameter(root / "memories" / "MEMORY.md"),
    }
    return AgentHarness(**values) if any(values.values()) else None


def _read_profile_parameter(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Le paramètre d’agent {path.name} est illisible.") from exc


def _harness_section(title: str, content: str) -> str:
    if not content.strip():
        return ""
    excerpt = _bounded_excerpt(content, HARNESS_SECTION_MAX_CHARS, "[Suite du paramètre non injectée]")
    return f"# {title} propre à l’agent\n\n{excerpt}"


def _record_tool_usage(
    *, tool_name: str = "", duration_ms: int = 0, status: str = "", **_: object
) -> None:
    """Conserve uniquement les métadonnées nécessaires à la gouvernance."""
    normalized = "success" if status in {"ok", "success"} else status
    record_usage(tool_name, normalized, duration_ms)


def _register_application_auth(ctx) -> None:
    from .arc_core.app_auth_provider import ArcenalApplicationProvider
    from .arc_core.auth import is_strong_secret
    from hermes_cli.dashboard_auth.token_auth import register_token_route

    configured_tokens = {
        "arcenal-system": os.environ.get("ARCENAL_APP_ARCENAL_SYSTEM_TOKEN", "").strip(),
        "arcenal-ats": os.environ.get("ARCENAL_APP_ARCENAL_ATS_TOKEN", "").strip(),
    }
    tokens = {key: value for key, value in configured_tokens.items() if is_strong_secret(value)}
    if not tokens:
        return
    ctx.register_dashboard_auth_provider(ArcenalApplicationProvider(tokens))
    register_token_route("/api/v1/agents/arc/query")
    register_token_route("/api/v1/agents/ats/query")


def register(ctx) -> None:
    """Enregistre les outils sans modifier le cœur commun Hermes."""
    _register_application_auth(ctx)
    ctx.register_system_prompt_section(
        id="arcenal.harness",
        content=_agent_harness_prompt,
        position="after_memory",
        max_chars=HARNESS_PROMPT_MAX_CHARS,
    )
    ctx.register_hook("post_tool_call", _record_tool_usage)
    for name, schema, handler, emoji in (
        ("arcenal_access_catalog", ACCESS_CATALOG_SCHEMA, access_catalog, "🔐"),
        ("arcenal_yunohost_query", YUNOHOST_QUERY_SCHEMA, yunohost_query, "🧩"),
        ("arcenal_system_status", SYSTEM_STATUS_SCHEMA, system_status, "🩺"),
        ("arcenal_create_report", CREATE_REPORT_SCHEMA, create_report, "📋"),
        ("arcenal_repair", REPAIR_SCHEMA, repair, "🛠️"),
        ("arcenal_knowledge_search", KNOWLEDGE_SEARCH_SCHEMA, knowledge_search, "🔎"),
        ("arcenal_knowledge_document", KNOWLEDGE_DOCUMENT_SCHEMA, knowledge_document, "📚"),
        ("arcenal_context_search", CONTEXT_SEARCH_SCHEMA, context_search, "🧭"),
        ("arcenal_memory_search", MEMORY_SEARCH_SCHEMA, memory_search, "🧠"),
    ):
        ctx.register_tool(
            name=name,
            toolset="arcenal-supervisor",
            schema=schema,
            handler=handler,
            emoji=emoji,
        )
