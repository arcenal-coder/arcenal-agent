"""Branche les outils de supervision ARCenal dans le chat Hermes."""

from __future__ import annotations

from .tools import (
    CREATE_REPORT_SCHEMA,
    REPAIR_SCHEMA,
    SYSTEM_STATUS_SCHEMA,
    create_report,
    repair,
    system_status,
)


def register(ctx) -> None:
    """Enregistre les outils sans modifier le cœur commun Hermes."""
    for name, schema, handler, emoji in (
        ("arcenal_system_status", SYSTEM_STATUS_SCHEMA, system_status, "🩺"),
        ("arcenal_create_report", CREATE_REPORT_SCHEMA, create_report, "📋"),
        ("arcenal_repair", REPAIR_SCHEMA, repair, "🛠️"),
    ):
        ctx.register_tool(
            name=name,
            toolset="arcenal-supervisor",
            schema=schema,
            handler=handler,
            emoji=emoji,
        )
