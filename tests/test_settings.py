"""Persistence of ExportOptions; uses a dict-backed fake instead of QSettings."""

from typing import Any

import pytest

from src.core.options import ExportOptions, ImageFormat
from src.gui.settings import (
    KEY_IMAGE_FORMAT,
    KEY_SAVE_TEXT,
    KEY_SCALE_PERCENT,
    load_options,
    save_options,
)


class FakeSettings:
    """Mimics the QSettings subset we use. QSettings returns strings from INI/registry."""

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = dict(values or {})

    def value(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def setValue(self, key: str, value: Any) -> None:
        self.values[key] = value


def test_empty_settings_give_defaults():
    assert load_options(FakeSettings()) == ExportOptions()


def test_round_trip_keeps_all_values():
    settings = FakeSettings()
    options = ExportOptions(scale_percent=250, image_format=ImageFormat.JPG, save_text=True)

    save_options(settings, options)

    assert load_options(settings) == options


def test_values_are_stored_as_plain_types():
    settings = FakeSettings()

    save_options(settings, ExportOptions(scale_percent=50, image_format=ImageFormat.JPG))

    assert settings.values == {
        KEY_SCALE_PERCENT: 50,
        KEY_IMAGE_FORMAT: "jpg",
        KEY_SAVE_TEXT: False,
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("false", False), (True, True), (False, False), ("1", True), ("0", False)],
)
def test_save_text_accepts_qsettings_string_forms(raw: Any, expected: bool):
    assert load_options(FakeSettings({KEY_SAVE_TEXT: raw})).save_text is expected


def test_scale_given_as_string_is_parsed():
    assert load_options(FakeSettings({KEY_SCALE_PERCENT: "75"})).scale_percent == 75


@pytest.mark.parametrize("raw", ["abc", "", None, "5", "999", -10, "12.5"])
def test_invalid_scale_falls_back_to_default(raw: Any):
    settings = FakeSettings({KEY_SCALE_PERCENT: raw, KEY_IMAGE_FORMAT: "jpg"})

    options = load_options(settings)

    assert options.scale_percent == ExportOptions().scale_percent
    assert options.image_format is ImageFormat.JPG  # other valid values are kept


@pytest.mark.parametrize("raw", ["gif", "", None, 3])
def test_invalid_format_falls_back_to_png(raw: Any):
    assert load_options(FakeSettings({KEY_IMAGE_FORMAT: raw})).image_format is ImageFormat.PNG


@pytest.mark.parametrize("raw", ["vielleicht", 7, None])
def test_invalid_save_text_falls_back_to_false(raw: Any):
    assert load_options(FakeSettings({KEY_SAVE_TEXT: raw})).save_text is False
