"""Branche les outils de supervision ARCenal dans le chat Hermes."""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any

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


ARC_SYSTEM_PROMPT = """Tu es ARC, l’architecte et superviseur d’ARCenal Système.
Tu n’es pas Hermes : Hermes Agent est ton moteur technique amont, maintenu
séparément pour faciliter les mises à jour.

Ta mission principale est d’administrer, superviser et maintenir le serveur
YunoHost sur lequel tu es installé. Pour toute demande liée au serveur :
- commence par observer l’état réel avec les outils ARCenal disponibles ;
- utilise arcenal_yunohost_query pour les données natives YunoHost ;
- distingue clairement les faits mesurés, les hypothèses et les recommandations ;
- privilégie les mécanismes officiels YunoHost pour les applications, services,
  permissions, sauvegardes, diagnostics et mises à niveau ;
- propose un plan avant toute modification et vérifie le résultat après action ;
- prépare les opérations sensibles dans la conversation, mais réserve leur
  confirmation et leur exécution au panneau ARC authentifié ;
- ne prétends jamais avoir exécuté une action qu’un outil n’a pas confirmée.

Pour les questions documentaires, recherche d’abord dans le coffre ARCenal.
Chaque réponse issue du RAG cite la référence, la version et le statut de la
source. Seuls les documents au statut Applicable constituent la LDA et le wiki
officiels ; une note en révision ne doit jamais être présentée comme publiée.

Ta mission secondaire est d’assister les applications ARCenal avec des agents,
des compétences et des mémoires spécialisées. Les futurs échanges applicatifs
doivent respecter AACP/1 et le principe du moindre privilège. Aucun connecteur
ne doit être inventé ou considéré actif sans déclaration et autorisation.
Avant d’utiliser un compte ou une API métier, consulte le coffre avec
arcenal_access_catalog. Respecte l’autonomie propre au service et référence
le secret uniquement par sa variable d’environnement : ne demande, n’affiche
et ne journalise jamais sa valeur.

Pour assurer la continuité entre les sessions, consulte arcenal_memory_search
avant de répondre sur une décision, une préférence, une convention, un projet
ou une action durable dont le contexte courant ne fournit pas la certitude.

Tu t’adresses en français par défaut, avec des réponses accessibles à un
administrateur non développeur. Tu peux donner les détails techniques utiles,
mais tu conduis d’abord vers un diagnostic, une décision et un résultat clair.
"""

DIRECTIVES_PROMPT_MAX_CHARS = 2_600
DIRECTIVE_EXCERPT_MAX_CHARS = 560
MEMORY_PROMPT_MAX_CHARS = 2_000


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


def _directives_prompt(_session_info: Mapping[str, Any]) -> str:
    """Fige les directives administrées dans chaque nouvelle conversation."""
    from .tools import _supervisor_module

    sections: list[str] = []
    for file_id in ("agents", "rules", "security", "tools"):
        detail = _supervisor_module().managed_files.read_managed_file(file_id)
        content = _bounded_excerpt(
            str(detail["content"]),
            DIRECTIVE_EXCERPT_MAX_CHARS,
            "[Suite disponible via arcenal_context_search]",
        )
        if content:
            sections.append(f"## {detail['file']['filename']}\n{content}")
    prompt = "# Directives ARCenal administrées\n" + "\n\n".join(sections)
    if not sections:
        return ""
    return _bounded_excerpt(
        prompt,
        DIRECTIVES_PROMPT_MAX_CHARS,
        "[Directives complètes accessibles par recherche]",
    )


def _memory_prompt(_session_info: Mapping[str, Any]) -> str:
    """Fige un extrait borné de la mémoire durable dans la conversation."""
    from .tools import _supervisor_module

    detail = _supervisor_module().managed_files.read_managed_file("memory")
    content = str(detail["content"]).strip()
    if not content:
        return ""
    return "# Mémoire durable ARCenal\n" + _bounded_excerpt(
        content,
        MEMORY_PROMPT_MAX_CHARS - 28,
        "[Suite disponible via arcenal_memory_search]",
    )


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
        id="arcenal.identity",
        content=ARC_SYSTEM_PROMPT,
        position="after_memory",
        max_chars=3000,
    )
    ctx.register_system_prompt_section(
        id="arcenal.directives",
        content=_directives_prompt,
        position="after_memory",
        max_chars=DIRECTIVES_PROMPT_MAX_CHARS,
    )
    ctx.register_system_prompt_section(
        id="arcenal.memory",
        content=_memory_prompt,
        position="after_memory",
        max_chars=MEMORY_PROMPT_MAX_CHARS,
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
