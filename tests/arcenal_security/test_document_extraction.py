from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
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


def _archive(name: str, xml: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, xml)
    return buffer.getvalue()


def test_extracts_text_docx_and_odt_without_external_dependency() -> None:
    docx = _archive("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Procédure qualité</w:t></w:r></w:p></w:document>')
    odt = _archive("content.xml", '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><text:p>Consigne sécurité</text:p></office:document-content>')

    assert CORE.extract_attachment_text("note.txt", b"Texte UTF-8") == "Texte UTF-8"
    assert CORE.extract_attachment_text("procedure.docx", docx) == "Procédure qualité"
    assert CORE.extract_attachment_text("consigne.odt", odt) == "Consigne sécurité"


def test_rejects_malformed_or_unsupported_documents() -> None:
    with pytest.raises(CORE.DocumentExtractionError):
        CORE.extract_attachment_text("faux.docx", b"not-a-zip")
    with pytest.raises(CORE.DocumentExtractionError):
        CORE.extract_attachment_text("image.png", b"png")


def test_pdf_extraction_is_bounded_and_reports_unavailable_converter() -> None:
    with pytest.raises(CORE.DocumentExtractionUnavailable):
        CORE.extract_attachment_text("document.pdf", b"%PDF-1.7", converter=lambda _data: None)

    assert CORE.extract_attachment_text("document.pdf", b"%PDF-1.7", converter=lambda _data: "Texte PDF") == "Texte PDF"
