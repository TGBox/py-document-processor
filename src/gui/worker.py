"""Background worker that runs the document pipeline for a batch of files."""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from src.core.errors import DocumentError
from src.core.options import ExportOptions
from src.core.pipeline import process_document

logger = logging.getLogger(__name__)

UNEXPECTED_ERROR_MESSAGE = "Unerwarteter Fehler bei der Verarbeitung."

ProcessFunction = Callable[..., Path | None]


class ExportWorker(QObject):
    """Processes files one after another; lives in a QThread and reports via signals.

    Word COM is initialised by the pipeline in its own helper thread, so this worker
    needs no COM setup.
    """

    file_started = Signal(int, int, str)  # index (1-based), total, file name
    page_done = Signal(int, int)  # page (1-based), pages of current file
    file_done = Signal(str, str)  # source path, output folder
    file_failed = Signal(str, str)  # source path, German user message
    finished = Signal()

    def __init__(
        self,
        paths: list[Path],
        options: ExportOptions,
        process: ProcessFunction = process_document,
    ) -> None:
        super().__init__()
        self._paths = list(paths)
        self._options = options
        self._process = process
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation; takes effect after the current page or Word export."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @Slot()
    def run(self) -> None:
        total = len(self._paths)
        try:
            for index, path in enumerate(self._paths, start=1):
                if self.is_cancelled():
                    break
                self.file_started.emit(index, total, path.name)
                self._process_one(path)
        finally:
            self.finished.emit()

    def _process_one(self, path: Path) -> None:
        try:
            out_dir = self._process(
                path,
                self._options,
                on_page=self.page_done.emit,
                is_cancelled=self.is_cancelled,
            )
        except DocumentError as error:
            logger.warning("Processing failed: %s (%s)", path.name, error.detail)
            self.file_failed.emit(str(path), error.user_message)
        except Exception:
            logger.exception("Unexpected error while processing %s", path.name)
            self.file_failed.emit(str(path), UNEXPECTED_ERROR_MESSAGE)
        else:
            if out_dir is not None:
                self.file_done.emit(str(path), str(out_dir))
