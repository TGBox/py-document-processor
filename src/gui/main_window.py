"""Main window: options bar, drop zone, background export and a short status line."""

from pathlib import Path

from PySide6.QtCore import QSettings, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from src.core.options import ExportOptions
from src.gui.drop_zone import DropZone
from src.gui.options_bar import OptionsBar
from src.gui.settings import load_options, save_options
from src.gui.worker import ExportWorker

WINDOW_TITLE = "py-document-processor"


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
        self._status = QLabel("Bereit.")
        self._status.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self._options_bar)
        layout.addWidget(self._drop_zone, stretch=1)
        layout.addWidget(self._status)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None
        self._last_output: Path | None = None
        self._succeeded = 0
        self._failed: list[str] = []
        self._close_requested = False

    def is_busy(self) -> bool:
        return self._thread is not None

    def start_export(self, paths: list[Path]) -> None:
        if self.is_busy() or not paths:
            return
        self._last_output = None
        self._succeeded = 0
        self._failed = []

        self._thread = QThread(self)
        self._worker = ExportWorker(paths, self._current_options())
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._set_inputs_enabled(False)
        self._thread.start()

    def _current_options(self) -> ExportOptions:
        return self._options_bar.options()

    def _save_options(self, options: ExportOptions) -> None:
        save_options(self._settings, options)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self._options_bar.setEnabled(enabled)
        self._drop_zone.setEnabled(enabled)

    def _on_file_started(self, index: int, total: int, name: str) -> None:
        self._status.setText(f"Verarbeite {name} ({index}/{total}) …")

    def _on_file_done(self, _source: str, out_dir: str) -> None:
        self._succeeded += 1
        self._last_output = Path(out_dir)

    def _on_file_failed(self, source: str, message: str) -> None:
        self._failed.append(f"{Path(source).name}: {message}")

    def _on_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_inputs_enabled(True)
        self._status.setText(self._summary())
        if self._close_requested:
            self.close()
            return
        if self._last_output is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def _summary(self) -> str:
        lines = [f"Fertig: {self._succeeded} erfolgreich, {len(self._failed)} fehlgeschlagen."]
        lines += self._failed
        return "\n".join(lines)

    def closeEvent(self, event) -> None:
        """While busy: cancel and close once the current step has finished (no frozen UI)."""
        if self._worker is not None:
            self._close_requested = True
            self._worker.cancel()
            self._status.setText("Wird nach dem aktuellen Schritt beendet …")
            event.ignore()
            return
        super().closeEvent(event)
