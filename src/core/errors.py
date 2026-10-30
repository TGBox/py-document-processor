"""Errors raised while processing a document.

Each error carries a German ``user_message`` for the GUI and an optional technical
``detail`` for debugging. Neither may contain document content.
"""


class DocumentError(Exception):
    """Base class for all expected processing failures."""

    user_message = "Das Dokument konnte nicht verarbeitet werden."

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.user_message)
        self.detail = detail


class UnsupportedFileError(DocumentError):
    user_message = "Dateityp wird nicht unterstützt."


class SourceNotFoundError(DocumentError):
    user_message = "Die Datei wurde nicht gefunden."


class RenderError(DocumentError):
    user_message = "Die Seiten konnten nicht als Bilder gespeichert werden."


class PasswordProtectedError(DocumentError):
    user_message = "Das Dokument ist kennwortgeschützt und kann nicht verarbeitet werden."


class WordExportError(DocumentError):
    user_message = "Word konnte das Dokument nicht als PDF exportieren."


class WordTimeoutError(DocumentError):
    user_message = "Word reagiert nicht – Verarbeitung abgebrochen."
