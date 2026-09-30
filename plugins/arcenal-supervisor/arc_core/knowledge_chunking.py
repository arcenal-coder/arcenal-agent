"""Découpage structuré et stable des documents Markdown."""

from __future__ import annotations

import re
from hashlib import sha256

from .knowledge_models import KnowledgeChunk, KnowledgeDocument


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
MAX_CHUNK_CHARACTERS = 1_800


def chunk_document(document: KnowledgeDocument, body: str) -> tuple[KnowledgeChunk, ...]:
    sections = _sections(body)
    chunks: list[KnowledgeChunk] = []
    for heading, content in sections:
        for fragment in _bounded_fragments(content):
            chunks.append(_chunk(document, heading, fragment, len(chunks)))
    return tuple(chunks)


def _sections(body: str) -> tuple[tuple[str, str], ...]:
    sections: list[tuple[str, str]] = []
    heading = "Introduction"
    lines: list[str] = []
    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if match is None:
            lines.append(line)
            continue
        _append_section(sections, heading, lines)
        heading, lines = match.group(2).strip(), []
    _append_section(sections, heading, lines)
    return tuple(sections)


def _append_section(sections: list[tuple[str, str]], heading: str, lines: list[str]) -> None:
    content = "\n".join(lines).strip()
    if content:
        sections.append((heading, content))


def _bounded_fragments(content: str) -> tuple[str, ...]:
    blocks = tuple(block.strip() for block in re.split(r"\n\s*\n", content) if block.strip())
    fragments: list[str] = []
    current = ""
    for block in blocks:
        current = _merge_or_flush(current, block, fragments)
    if current:
        fragments.extend(_split_large(current))
    return tuple(fragments)


def _merge_or_flush(current: str, block: str, fragments: list[str]) -> str:
    candidate = f"{current}\n\n{block}".strip()
    if len(candidate) <= MAX_CHUNK_CHARACTERS:
        return candidate
    if current:
        fragments.extend(_split_large(current))
    if len(block) > MAX_CHUNK_CHARACTERS:
        fragments.extend(_split_large(block))
        return ""
    return block


def _split_large(content: str) -> tuple[str, ...]:
    lines = content.splitlines()
    parts = tuple("\n".join(lines[index : index + 12]).strip() for index in range(0, len(lines), 12))
    return tuple(part for part in parts if part)


def _chunk(document: KnowledgeDocument, heading: str, content: str, position: int) -> KnowledgeChunk:
    identity = f"{document.document_id}|{document.version}|{heading}|{position}|{content}"
    return KnowledgeChunk(
        chunk_id=sha256(identity.encode("utf-8")).hexdigest()[:24],
        document_id=document.document_id,
        version=document.version,
        heading=heading,
        section=heading,
        position=position,
        content=content,
        knowledge_scopes=document.knowledge_scopes,
        confidentiality=document.confidentiality,
        status=document.status,
    )
