"""StatusList widget (needs PySide6; runs headless via the offscreen platform)."""

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.gui.status_list import StatusList


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_success_and_failure_lines(app: QApplication, tmp_path: Path):
    status = StatusList()

    status.add_success("a.docx", tmp_path / "a_pages")
    status.add_failure("b.docx", "Das Dokument ist kennwortgeschützt.")

    texts = [status.item(i).text() for i in range(status.count())]
    assert texts == [
        f"✓ a.docx → {tmp_path / 'a_pages'}",
        "✗ b.docx: Das Dokument ist kennwortgeschützt.",
    ]


def test_success_item_remembers_folder(app: QApplication, tmp_path: Path):
    status = StatusList()
    status.add_success("a.docx", tmp_path)

    assert status.item(0).data(Qt.ItemDataRole.UserRole) == str(tmp_path)


def test_failure_item_has_no_folder(app: QApplication):
    status = StatusList()
    status.add_failure("b.docx", "Fehler")

    assert status.item(0).data(Qt.ItemDataRole.UserRole) is None


def test_info_line_and_clear(app: QApplication):
    status = StatusList()
    status.add_info("Abgebrochen.")

    assert status.item(0).text() == "Abgebrochen."
    status.clear()
    assert status.count() == 0
