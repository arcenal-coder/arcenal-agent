"""Extraction bornée des pièces jointes vers le corpus Markdown."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree


class DocumentExtractionError(RuntimeError):
    """Le document fourni est invalide ou non pris en charge."""


class DocumentExtractionUnavailable(DocumentExtractionError):
    """Le convertisseur requis n’est pas présent sur le serveur."""


PdfConverter = Callable[[bytes], str | None]
MAX_EXTRACTED_CHARACTERS = 250_000


def extract_attachment_text(filename: str, data: bytes, converter: PdfConverter | None = None) -> str:
    suffix = Path(filename).suffix.casefold()
    extractors: dict[str, Callable[[bytes], str]] = {
        ".md": _text,
        ".txt": _text,
        ".docx": lambda content: _xml_archive(content, "word/document.xml"),
        ".odt": lambda content: _xml_archive(content, "content.xml"),
    }
    if suffix == ".pdf":
        return _bounded(_pdf(data, converter or _pdftotext))
    extractor = extractors.get(suffix)
    if extractor is None:
        raise DocumentExtractionError("Ce format documentaire ne peut pas être extrait.")
    return _bounded(extractor(data))


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("Le document texte doit être encodé en UTF-8.") from exc


def _xml_archive(data: bytes, member: str) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read(member)
        root = ElementTree.fromstring(xml)
    except (KeyError, OSError, ElementTree.ParseError, zipfile.BadZipFile) as exc:
        raise DocumentExtractionError("Le document bureautique est invalide.") from exc
    text = " ".join(value.strip() for value in root.itertext() if value.strip())
    return re.sub(r"\s+", " ", text).strip()


def _pdf(data: bytes, converter: PdfConverter) -> str:
    text = converter(data)
    if text is None:
        raise DocumentExtractionUnavailable("L’extraction PDF nécessite l’outil système pdftotext.")
    return text


def _pdftotext(data: bytes) -> str | None:
    executable = shutil.which("pdftotext")
    if executable is None:
        return None
    with tempfile.TemporaryDirectory(prefix="arcenal-pdf-") as directory:
        source = Path(directory) / "source.pdf"
        source.write_bytes(data)
        return _run_pdftotext(executable, source)


def _run_pdftotext(executable: str, source: Path) -> str:
    try:
        result = subprocess.run([executable, "-layout", str(source), "-"], capture_output=True, check=True, timeout=30)
        return result.stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as exc:
        raise DocumentExtractionError("Le contenu PDF ne peut pas être extrait.") from exc


def _bounded(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise DocumentExtractionError("Aucun texte exploitable n’a été extrait du document.")
    if len(normalized) > MAX_EXTRACTED_CHARACTERS:
        return f"{normalized[:MAX_EXTRACTED_CHARACTERS].rstrip()}\n\n[Contenu tronqué par ARC]"
    return normalized
