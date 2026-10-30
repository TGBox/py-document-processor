"""Drop target for Word files; a click opens a file dialog instead."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QWidget

from src.core.pipeline import SUPPORTED_SUFFIXES

FILE_DIALOG_FILTER = "Word-Dokumente ({patterns});;Alle Dateien (*)".format(
    patterns=" ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_SUFFIXES))
)
IDLE_TEXT = "Word-Dateien hierher ziehen\noder klicken, um Dateien auszuwählen"
BUSY_TEXT = "Verarbeitung läuft …"


class DropZone(QLabel):
    """Emits ``files_selected`` with local file paths from drag & drop or the file dialog.

    Unsupported file types are passed on as well; the pipeline reports them per file.
    """

    files_selected = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(IDLE_TEXT, parent)
        self.setObjectName("dropZone")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(320, 200)
        self._set_drag_active(False)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.setText(IDLE_TEXT if enabled else BUSY_TEXT)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.isEnabled() and _local_files(event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
        paths = _local_files(event.mimeData().urls())
        if paths:
            event.acceptProposedAction()
            self.files_selected.emit(paths)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            names, _filter = QFileDialog.getOpenFileNames(
                self, "Word-Dateien auswählen", "", FILE_DIALOG_FILTER
            )
            if names:
                self.files_selected.emit([Path(name) for name in names])
        super().mouseReleaseEvent(event)

    def _set_drag_active(self, active: bool) -> None:
        """Expose drag state as dynamic property for the stylesheet (``[dragActive="true"]``)."""
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)


def _local_files(urls) -> list[Path]:
    return [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
