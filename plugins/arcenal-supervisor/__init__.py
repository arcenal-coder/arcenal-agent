"""Branche les outils de supervision ARCenal dans le chat Hermes."""

from __future__ import annotations

from .tools import (
    ACCESS_CATALOG_SCHEMA,
    CREATE_REPORT_SCHEMA,
    KNOWLEDGE_DOCUMENT_SCHEMA,
    KNOWLEDGE_SEARCH_SCHEMA,
    REPAIR_SCHEMA,
    SYSTEM_STATUS_SCHEMA,
    YUNOHOST_QUERY_SCHEMA,
    access_catalog,
    create_report,
    knowledge_document,
    knowledge_search,
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
- exige une confirmation explicite dans la conversation en cours avant toute
  opération destructive, interruption de service ou modification sensible ;
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

Tu t’adresses en français par défaut, avec des réponses accessibles à un
administrateur non développeur. Tu peux donner les détails techniques utiles,
mais tu conduis d’abord vers un diagnostic, une décision et un résultat clair.
"""


def register(ctx) -> None:
    """Enregistre les outils sans modifier le cœur commun Hermes."""
    ctx.register_system_prompt_section(
        id="arcenal.identity",
        content=ARC_SYSTEM_PROMPT,
        position="after_memory",
        max_chars=4000,
    )
    for name, schema, handler, emoji in (
        ("arcenal_access_catalog", ACCESS_CATALOG_SCHEMA, access_catalog, "🔐"),
        ("arcenal_yunohost_query", YUNOHOST_QUERY_SCHEMA, yunohost_query, "🧩"),
        ("arcenal_system_status", SYSTEM_STATUS_SCHEMA, system_status, "🩺"),
        ("arcenal_create_report", CREATE_REPORT_SCHEMA, create_report, "📋"),
        ("arcenal_repair", REPAIR_SCHEMA, repair, "🛠️"),
        ("arcenal_knowledge_search", KNOWLEDGE_SEARCH_SCHEMA, knowledge_search, "🔎"),
        ("arcenal_knowledge_document", KNOWLEDGE_DOCUMENT_SCHEMA, knowledge_document, "📚"),
    ):
        ctx.register_tool(
            name=name,
            toolset="arcenal-supervisor",
            schema=schema,
            handler=handler,
            emoji=emoji,
        )
