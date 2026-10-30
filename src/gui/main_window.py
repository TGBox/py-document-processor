"""Main window: options bar, drop zone, progress with cancel, and a per-file status list."""

from pathlib import Path

from PySide6.QtCore import QSettings, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.options import ExportOptions
from src.gui.drop_zone import DropZone
from src.gui.options_bar import OptionsBar
from src.gui.progress import BatchProgress
from src.gui.settings import load_options, save_options
from src.gui.status_list import StatusList
from src.gui.worker import ExportWorker

WINDOW_TITLE = "py-document-processor"
CANCEL_TEXT = "Abbrechen"
CANCELLING_TEXT = "Wird abgebrochen …"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(800, 600)

        self._settings = QSettings()
        self._options_bar = OptionsBar()
        self._options_bar.set_options(load_options(self._settings))
        self._options_bar.options_changed.connect(self._save_options)

        self._drop_zone = DropZone()
        self._drop_zone.files_selected.connect(self.start_export)

        self._progress_label = QLabel("Bereit.")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._cancel_button = QPushButton(CANCEL_TEXT)
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self.cancel_export)
        progress_row = QHBoxLayout()
        progress_row.addWidget(self._progress_bar, stretch=1)
        progress_row.addWidget(self._cancel_button)

        self._status_list = StatusList()

        layout = QVBoxLayout()
        layout.addWidget(self._options_bar)
        layout.addWidget(self._drop_zone, stretch=2)
        layout.addWidget(self._progress_label)
        layout.addLayout(progress_row)
        layout.addWidget(self._status_list, stretch=1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._progress = BatchProgress()
        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None
        self._last_output: Path | None = None
        self._succeeded = 0
        self._failed = 0
        self._close_requested = False

    def is_busy(self) -> bool:
        return self._thread is not None

    def start_export(self, paths: list[Path]) -> None:
        if self.is_busy() or not paths:
            return
        self._last_output = None
        self._succeeded = 0
        self._failed = 0
        self._progress = BatchProgress()
        self._status_list.clear()
        self._progress_bar.setValue(0)

        self._thread = QThread(self)
        self._worker = ExportWorker(paths, self._current_options())
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.page_done.connect(self._on_page_done)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._set_busy(True)
        self._thread.start()

    def cancel_export(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        self._cancel_button.setEnabled(False)
        self._cancel_button.setText(CANCELLING_TEXT)

    def _current_options(self) -> ExportOptions:
        return self._options_bar.options()

    def _save_options(self, options: ExportOptions) -> None:
        save_options(self._settings, options)

    def _set_busy(self, busy: bool) -> None:
        self._options_bar.setEnabled(not busy)
        self._drop_zone.setEnabled(not busy)
        self._cancel_button.setEnabled(busy)
        self._cancel_button.setText(CANCEL_TEXT)

    def _show_progress(self) -> None:
        self._progress_bar.setValue(self._progress.percent())
        self._progress_label.setText(self._progress.text())

    def _on_file_started(self, index: int, total: int, name: str) -> None:
        self._progress.start_file(index, total, name)
        self._show_progress()

    def _on_page_done(self, page: int, pages: int) -> None:
        self._progress.page_done(page, pages)
        self._show_progress()

    def _on_file_done(self, source: str, out_dir: str) -> None:
        self._succeeded += 1
        self._last_output = Path(out_dir)
        self._status_list.add_success(Path(source).name, Path(out_dir))

    def _on_file_failed(self, source: str, message: str) -> None:
        self._failed += 1
        self._status_list.add_failure(Path(source).name, message)

    def _on_finished(self) -> None:
        cancelled = self._worker is not None and self._worker.is_cancelled()
        self._thread = None
        self._worker = None
        self._set_busy(False)

        summary = f"{self._succeeded} erfolgreich, {self._failed} fehlgeschlagen."
        if cancelled:
            self._progress_label.setText(f"Abgebrochen – {summary}")
            self._status_list.add_info("Abgebrochen. Bereits erzeugte Bilder bleiben erhalten.")
        else:
            self._progress_bar.setValue(100)
            self._progress_label.setText(f"Fertig – {summary}")

        if self._close_requested:
            self.close()
            return
        if self._last_output is not None and not cancelled:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def closeEvent(self, event) -> None:
        """While busy: cancel and close once the current step has finished (no frozen UI)."""
        if self._worker is not None:
            self._close_requested = True
            self.cancel_export()
            self._progress_label.setText("Wird nach dem aktuellen Schritt beendet …")
            event.ignore()
            return
        super().closeEvent(event)
