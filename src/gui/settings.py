"""Load and save ExportOptions and UI preferences via QSettings.

Works with any object offering ``value(key, default)`` and ``setValue(key, value)`` so the
parsing can be tested without Qt. QSettings may hand back strings (INI/registry), so every
value is parsed defensively; invalid values fall back to the default individually.
"""

from typing import Any, Protocol

from src.core.options import MAX_SCALE_PERCENT, MIN_SCALE_PERCENT, ExportOptions, ImageFormat
from src.gui.theme import Theme

KEY_SCALE_PERCENT = "export/scale_percent"
KEY_IMAGE_FORMAT = "export/image_format"
KEY_SAVE_TEXT = "export/save_text"
KEY_THEME = "ui/theme"
KEY_GEOMETRY = "ui/geometry"

_TRUE_VALUES = {"true", "1"}
_FALSE_VALUES = {"false", "0"}


class SettingsStore(Protocol):
    def value(self, key: str, default: Any = None) -> Any: ...

    def setValue(self, key: str, value: Any) -> None: ...


def load_options(settings: SettingsStore) -> ExportOptions:
    defaults = ExportOptions()
    return ExportOptions(
        scale_percent=_parse_scale(settings.value(KEY_SCALE_PERCENT), defaults.scale_percent),
        image_format=_parse_format(settings.value(KEY_IMAGE_FORMAT), defaults.image_format),
        save_text=_parse_bool(settings.value(KEY_SAVE_TEXT), defaults.save_text),
    )


def save_options(settings: SettingsStore, options: ExportOptions) -> None:
    settings.setValue(KEY_SCALE_PERCENT, options.scale_percent)
    settings.setValue(KEY_IMAGE_FORMAT, options.image_format.value)
    settings.setValue(KEY_SAVE_TEXT, options.save_text)


def _parse_scale(raw: Any, default: int) -> int:
    if isinstance(raw, bool):
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return value if MIN_SCALE_PERCENT <= value <= MAX_SCALE_PERCENT else default


def _parse_format(raw: Any, default: ImageFormat) -> ImageFormat:
    try:
        return ImageFormat(raw)
    except ValueError:
        return default


def _parse_bool(raw: Any, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return default


def load_theme(settings: SettingsStore) -> Theme:
    try:
        return Theme(settings.value(KEY_THEME))
    except ValueError:
        return Theme.SYSTEM


def save_theme(settings: SettingsStore, theme: Theme) -> None:
    settings.setValue(KEY_THEME, theme.value)
