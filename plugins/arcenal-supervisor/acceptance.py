"""Contrat stable des critères d’acceptation du produit ARCenal Agent."""

from __future__ import annotations

import re


REQUIRED_ACCEPTANCE_IDS = frozenset(
    {
        "AC-ACC-01", "AC-AGT-01", "AC-AGT-02", "AC-AI-01", "AC-ARC-01",
        "AC-ARC-02", "AC-ARC-03", "AC-BKP-01", "AC-RAG-01", "AC-RAG-02",
        "AC-RAG-03", "AC-SEC-01", "AC-SEC-02", "AC-SET-01", "AC-UP-01",
        "AC-UX-01", "AC-YH-01",
    }
)


def acceptance_ids(markdown: str) -> frozenset[str]:
    return frozenset(re.findall(r"\bAC-[A-Z]+-\d{2}\b", markdown))


def missing_acceptance_ids(markdown: str) -> frozenset[str]:
    return REQUIRED_ACCEPTANCE_IDS - acceptance_ids(markdown)
