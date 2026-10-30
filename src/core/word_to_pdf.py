"""Export a Word document to PDF via Microsoft Word COM automation (Windows only).

A private, invisible Word instance is started with ``DispatchEx`` so the user's own Word
windows are never touched. The source is opened read-only, macros are disabled, tracked
changes and comments are hidden, and the instance is always quit afterwards.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from src.core.errors import PasswordProtectedError, WordExportError

WORD_PROG_ID = "Word.Application"

# Word / Office constants (see Word VBA enumerations)
WD_ALERTS_NONE = 0
WD_DO_NOT_SAVE_CHANGES = 0
WD_EXPORT_FORMAT_PDF = 17
WD_EXPORT_OPTIMIZE_FOR_PRINT = 0
WD_EXPORT_ALL_DOCUMENT = 0
WD_EXPORT_DOCUMENT_CONTENT = 0
WD_EXPORT_CREATE_NO_BOOKMARKS = 0
WD_REVISIONS_MARKUP_NONE = 0
WD_REVISIONS_VIEW_FINAL = 0
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3

# Word run-time error 5408 ("password is incorrect") as signed HRESULT 0x800A1520
WORD_ERROR_WRONG_PASSWORD = -2146822880

# Passing a password Word cannot match makes encrypted files fail instead of prompting.
# Unencrypted files ignore it.
DUMMY_PASSWORD = "#py-document-processor#"

WordFactory = Callable[[], Any]


def word_to_pdf(src: Path, dst_pdf: Path, word_factory: WordFactory | None = None) -> None:
    """Export ``src`` as PDF to ``dst_pdf`` without markup.

    ``word_factory`` returns a Word Application object; defaults to a new private instance.
    Raises ``PasswordProtectedError`` or ``WordExportError``.
    """
    if word_factory is not None:
        _export(word_factory, src, dst_pdf)
        return
    with _com_apartment():
        _export(_new_word_instance, src, dst_pdf)


def _export(word_factory: WordFactory, src: Path, dst_pdf: Path) -> None:
    try:
        word = word_factory()
    except Exception as exc:
        raise WordExportError(f"Word could not be started: {_describe(exc)}") from exc

    try:
        word.Visible = False
        word.DisplayAlerts = WD_ALERTS_NONE
        word.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        document = _open_document(word, src)
        try:
            _hide_markup(document)
            document.ExportAsFixedFormat(
                OutputFileName=str(dst_pdf),
                ExportFormat=WD_EXPORT_FORMAT_PDF,
                OpenAfterExport=False,
                OptimizeFor=WD_EXPORT_OPTIMIZE_FOR_PRINT,
                Range=WD_EXPORT_ALL_DOCUMENT,
                Item=WD_EXPORT_DOCUMENT_CONTENT,
                IncludeDocProps=False,
                KeepIRM=True,
                CreateBookmarks=WD_EXPORT_CREATE_NO_BOOKMARKS,
                DocStructureTags=False,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        except Exception as exc:
            raise WordExportError(f"PDF export failed: {_describe(exc)}") from exc
        finally:
            _ignore_errors(lambda: document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES))
    finally:
        _ignore_errors(lambda: word.Quit(SaveChanges=WD_DO_NOT_SAVE_CHANGES))


def _open_document(word: Any, src: Path) -> Any:
    try:
        return word.Documents.Open(
            FileName=str(src),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            PasswordDocument=DUMMY_PASSWORD,
            Revert=False,
            Visible=True,  # needed for ActiveWindow; the application itself stays invisible
            OpenAndRepair=False,
            NoEncodingDialog=True,
        )
    except Exception as exc:
        if _com_scode(exc) == WORD_ERROR_WRONG_PASSWORD:
            raise PasswordProtectedError(f"Wrong password: {_describe(exc)}") from exc
        raise WordExportError(f"Opening failed: {_describe(exc)}") from exc


def _hide_markup(document: Any) -> None:
    """Show the final version without tracked changes or comments."""
    view = document.ActiveWindow.View
    view.RevisionsFilter.Markup = WD_REVISIONS_MARKUP_NONE
    view.RevisionsFilter.View = WD_REVISIONS_VIEW_FINAL
    view.ShowRevisionsAndComments = False
    view.RevisionsView = WD_REVISIONS_VIEW_FINAL


def _com_scode(exc: Exception) -> int | None:
    """Return the application error code (``excepinfo[5]``) of a COM error, if any."""
    excepinfo = getattr(exc, "excepinfo", None)
    if isinstance(excepinfo, tuple) and len(excepinfo) > 5:
        return excepinfo[5]
    return None


def _describe(exc: Exception) -> str:
    scode = _com_scode(exc)
    return f"{type(exc).__name__} (scode={scode})" if scode is not None else type(exc).__name__


def _ignore_errors(action: Callable[[], object]) -> None:
    """Run a cleanup step; its failure must never mask the original error."""
    with suppress(Exception):
        action()


def _new_word_instance() -> Any:
    import win32com.client

    return win32com.client.DispatchEx(WORD_PROG_ID)


@contextmanager
def _com_apartment() -> Iterator[None]:
    """Initialise COM for the current thread (required inside worker threads)."""
    try:
        import pythoncom
    except ImportError as exc:
        raise WordExportError("pywin32 is not available on this system") from exc
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()
