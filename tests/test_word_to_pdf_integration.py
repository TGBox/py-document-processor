"""Integration tests against a real Microsoft Word installation.

Only run on Windows with Word installed:  uv run pytest -v -m word
"""

import faulthandler
import subprocess
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pytest

from src.core.errors import PasswordProtectedError
from src.core.word_to_pdf import word_to_pdf

pytestmark = [
    pytest.mark.word,
    pytest.mark.skipif(sys.platform != "win32", reason="requires Windows with Microsoft Word"),
]

FIXTURES = Path(__file__).parent / "fixtures"
MARKUP_DOCX = FIXTURES / "markup.docx"
PASSWORD_DOCX = FIXTURES / "password.docx"


def pdf_texts(pdf_path: Path) -> list[str]:
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        texts = []
        for page in pdf:
            text_page = page.get_textpage()
            texts.append(text_page.get_text_bounded())
            text_page.close()
            page.close()
        return texts
    finally:
        pdf.close()


@pytest.fixture(autouse=True)
def _quiet_faulthandler():
    """Silence faulthandler during Word tests.

    Releasing COM proxies after ``Quit()`` raises RPC errors (0x800706BA/BE) that COM handles
    internally; pytest's faulthandler still prints them as "Windows fatal exception".
    """
    was_enabled = faulthandler.is_enabled()
    faulthandler.disable()
    yield
    if was_enabled:
        faulthandler.enable(file=sys.__stderr__)


def word_process_ids() -> set[int]:
    # tasklist answers in the console code page (e.g. cp850 with German umlauts)
    output = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
        capture_output=True,
        encoding="oem",
        errors="replace",
        check=True,
    ).stdout
    ids = set()
    for line in output.splitlines():
        parts = [part.strip('"') for part in line.split('","')]
        if len(parts) > 1 and parts[1].isdigit():
            ids.add(int(parts[1]))
    return ids


def test_markup_document_exports_final_version_only(tmp_path: Path):
    target = tmp_path / "markup.pdf"

    word_to_pdf(MARKUP_DOCX, target)

    texts = pdf_texts(target)
    full_text = "\n".join(texts)
    assert len(texts) == 2
    assert "Omega" in full_text
    assert "Zweite Seite" in full_text
    assert "Alpha" not in full_text
    assert "Kommentar Geheim" not in full_text


def test_source_document_is_not_modified(tmp_path: Path):
    before = (MARKUP_DOCX.stat().st_mtime_ns, MARKUP_DOCX.read_bytes())

    word_to_pdf(MARKUP_DOCX, tmp_path / "markup.pdf")

    assert (MARKUP_DOCX.stat().st_mtime_ns, MARKUP_DOCX.read_bytes()) == before


def test_password_document_fails_fast_without_leftover_word(tmp_path: Path):
    before = word_process_ids()

    with pytest.raises(PasswordProtectedError):
        word_to_pdf(PASSWORD_DOCX, tmp_path / "password.pdf")

    assert word_process_ids() - before == set()
