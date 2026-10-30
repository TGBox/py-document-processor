"""OptionsBar widget (needs PySide6; runs headless via the offscreen platform)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.core.options import MAX_SCALE_PERCENT, MIN_SCALE_PERCENT, ExportOptions, ImageFormat
from src.gui.options_bar import OptionsBar


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_shows_defaults(app: QApplication):
    assert OptionsBar().options() == ExportOptions()


def test_set_options_round_trip(app: QApplication):
    bar = OptionsBar()
    options = ExportOptions(scale_percent=50, image_format=ImageFormat.JPG, save_text=True)

    bar.set_options(options)

    assert bar.options() == options


def test_scale_range_matches_core_limits(app: QApplication):
    bar = OptionsBar()

    assert (bar.scale.minimum(), bar.scale.maximum()) == (MIN_SCALE_PERCENT, MAX_SCALE_PERCENT)


def test_changes_emit_options_changed(app: QApplication):
    bar = OptionsBar()
    received: list[ExportOptions] = []
    bar.options_changed.connect(received.append)

    bar.scale.setValue(200)
    bar.image_format.setCurrentIndex(bar.image_format.findData(ImageFormat.JPG.value))
    bar.save_text.setChecked(True)

    assert received[-1] == ExportOptions(
        scale_percent=200, image_format=ImageFormat.JPG, save_text=True
    )
    assert len(received) == 3


def test_set_options_does_not_emit(app: QApplication):
    bar = OptionsBar()
    received: list[ExportOptions] = []
    bar.options_changed.connect(received.append)

    bar.set_options(ExportOptions(scale_percent=300))

    assert received == []
