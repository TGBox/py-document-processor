"""One line per processed file; double-click on a success opens its output folder."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

FOLDER_ROLE = Qt.ItemDataRole.UserRole


class StatusList(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusList")
        self.setToolTip("Doppelklick öffnet den Ausgabeordner")
        self.itemDoubleClicked.connect(self._open_folder)

    def add_success(self, name: str, out_dir: Path) -> None:
        item = QListWidgetItem(f"✓ {name} → {out_dir}")
        item.setData(FOLDER_ROLE, str(out_dir))
        self._append(item)

    def add_failure(self, name: str, message: str) -> None:
        item = QListWidgetItem(f"✗ {name}: {message}")
        self._append(item)

    def add_info(self, text: str) -> None:
        self._append(QListWidgetItem(text))

    def _append(self, item: QListWidgetItem) -> None:
        self.addItem(item)
        self.scrollToItem(item)

    def _open_folder(self, item: QListWidgetItem) -> None:
        folder = item.data(FOLDER_ROLE)
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
