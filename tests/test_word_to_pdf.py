"""Unit tests for ``word_to_pdf`` against a fake Word COM object (run everywhere)."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.core.errors import PasswordProtectedError, WordExportError
from src.core.word_to_pdf import (
    MSO_AUTOMATION_SECURITY_FORCE_DISABLE,
    WD_ALERTS_NONE,
    WD_DO_NOT_SAVE_CHANGES,
    WD_EXPORT_DOCUMENT_CONTENT,
    WD_EXPORT_FORMAT_PDF,
    WD_REVISIONS_MARKUP_NONE,
    WD_REVISIONS_VIEW_FINAL,
    WORD_ERROR_WRONG_PASSWORD,
    word_to_pdf,
)


class FakeComError(Exception):
    """Mimics ``pywintypes.com_error``: excepinfo[5] holds the Word scode."""

    def __init__(self, scode: int | None = None) -> None:
        super().__init__("COM failure")
        self.excepinfo = (0, "Microsoft Word", "message", None, 0, scode)


class FakeDocument:
    def __init__(self, log: list[str], export_error: Exception | None = None) -> None:
        self.log = log
        self.export_error = export_error
        self.export_kwargs: dict[str, Any] = {}
        self.close_kwargs: dict[str, Any] | None = None
        view = SimpleNamespace(
            RevisionsFilter=SimpleNamespace(Markup=2, View=0),
            ShowRevisionsAndComments=True,
            RevisionsView=0,
        )
        self.ActiveWindow = SimpleNamespace(View=view)

    def ExportAsFixedFormat(self, **kwargs: Any) -> None:
        self.log.append("export")
        self.export_kwargs = kwargs
        view = self.ActiveWindow.View
        self.markup_at_export = (view.RevisionsFilter.Markup, view.ShowRevisionsAndComments)
        if self.export_error:
            raise self.export_error
        Path(kwargs["OutputFileName"]).write_bytes(b"%PDF-fake")

    def Close(self, **kwargs: Any) -> None:
        self.log.append("close")
        self.close_kwargs = kwargs


class FakeDocuments:
    def __init__(self, document: FakeDocument, open_error: Exception | None) -> None:
        self.document = document
        self.open_error = open_error
        self.open_kwargs: dict[str, Any] = {}

    def Open(self, **kwargs: Any) -> FakeDocument:
        self.document.log.append("open")
        self.open_kwargs = kwargs
        if self.open_error:
            raise self.open_error
        return self.document


class FakeWord:
    def __init__(
        self,
        open_error: Exception | None = None,
        export_error: Exception | None = None,
        quit_error: Exception | None = None,
    ) -> None:
        self.log: list[str] = []
        self.document = FakeDocument(self.log, export_error)
        self.Documents = FakeDocuments(self.document, open_error)
        self.quit_error = quit_error
        self.Visible = True
        self.DisplayAlerts = -1
        self.AutomationSecurity = 1

    def Quit(self, **kwargs: Any) -> None:
        self.log.append("quit")
        if self.quit_error:
            raise self.quit_error


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "Brief.docx"
    path.write_bytes(b"fake docx")
    return path


def run(word: FakeWord, source: Path, tmp_path: Path) -> Path:
    target = tmp_path / "out.pdf"
    word_to_pdf(source, target, word_factory=lambda: word)
    return target


def test_word_runs_invisible_without_alerts_and_macros(source: Path, tmp_path: Path):
    word = FakeWord()

    run(word, source, tmp_path)

    assert word.Visible is False
    assert word.DisplayAlerts == WD_ALERTS_NONE
    assert word.AutomationSecurity == MSO_AUTOMATION_SECURITY_FORCE_DISABLE


def test_document_is_opened_read_only_without_dialogs(source: Path, tmp_path: Path):
    word = FakeWord()

    run(word, source, tmp_path)

    kwargs = word.Documents.open_kwargs
    assert kwargs["FileName"] == str(source)
    assert kwargs["ReadOnly"] is True
    assert kwargs["AddToRecentFiles"] is False
    assert kwargs["ConfirmConversions"] is False
    assert kwargs["OpenAndRepair"] is False
    assert kwargs["NoEncodingDialog"] is True
    assert kwargs["PasswordDocument"]  # dummy password: encrypted files fail instead of prompting


def test_markup_is_hidden_before_export(source: Path, tmp_path: Path):
    word = FakeWord()

    run(word, source, tmp_path)

    view = word.document.ActiveWindow.View
    assert view.RevisionsFilter.Markup == WD_REVISIONS_MARKUP_NONE
    assert view.RevisionsFilter.View == WD_REVISIONS_VIEW_FINAL
    assert word.document.markup_at_export == (WD_REVISIONS_MARKUP_NONE, False)


def test_exports_document_content_as_pdf(source: Path, tmp_path: Path):
    word = FakeWord()

    target = run(word, source, tmp_path)

    kwargs = word.document.export_kwargs
    assert kwargs["OutputFileName"] == str(target)
    assert kwargs["ExportFormat"] == WD_EXPORT_FORMAT_PDF
    assert kwargs["Item"] == WD_EXPORT_DOCUMENT_CONTENT
    assert kwargs["OpenAfterExport"] is False
    assert target.read_bytes() == b"%PDF-fake"


def test_closes_without_saving_and_quits(source: Path, tmp_path: Path):
    word = FakeWord()

    run(word, source, tmp_path)

    assert word.log == ["open", "export", "close", "quit"]
    assert word.document.close_kwargs == {"SaveChanges": WD_DO_NOT_SAVE_CHANGES}


def test_export_failure_raises_word_export_error_and_still_cleans_up(source: Path, tmp_path: Path):
    word = FakeWord(export_error=FakeComError())

    with pytest.raises(WordExportError):
        run(word, source, tmp_path)

    assert word.log == ["open", "export", "close", "quit"]


def test_wrong_password_raises_password_protected_error(source: Path, tmp_path: Path):
    word = FakeWord(open_error=FakeComError(scode=WORD_ERROR_WRONG_PASSWORD))

    with pytest.raises(PasswordProtectedError):
        run(word, source, tmp_path)

    assert word.log == ["open", "quit"]


def test_other_open_failure_raises_word_export_error(source: Path, tmp_path: Path):
    word = FakeWord(open_error=FakeComError(scode=-2146822000))

    with pytest.raises(WordExportError) as info:
        run(word, source, tmp_path)

    assert not isinstance(info.value, PasswordProtectedError)
    assert word.log == ["open", "quit"]


def test_quit_failure_does_not_mask_original_error(source: Path, tmp_path: Path):
    word = FakeWord(export_error=FakeComError(), quit_error=FakeComError())

    with pytest.raises(WordExportError):
        run(word, source, tmp_path)


def test_word_start_failure_raises_word_export_error(source: Path, tmp_path: Path):
    def broken_factory() -> FakeWord:
        raise FakeComError()

    with pytest.raises(WordExportError):
        word_to_pdf(source, tmp_path / "out.pdf", word_factory=broken_factory)
