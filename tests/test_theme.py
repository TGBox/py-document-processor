import pytest

from src.gui.settings import KEY_THEME, load_theme, save_theme
from src.gui.theme import (
    DARK,
    LIGHT,
    Theme,
    build_stylesheet,
    contrast_ratio,
    palette_for,
)

WCAG_AA_TEXT = 4.5


class FakeSettings:
    def __init__(self, values=None) -> None:
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value) -> None:
        self.values[key] = value


def test_contrast_ratio_reference_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)


@pytest.mark.parametrize("palette", [LIGHT, DARK], ids=["light", "dark"])
@pytest.mark.parametrize(
    ("foreground", "background"),
    [
        ("text", "window"),
        ("text", "surface"),
        ("text", "drop"),
        ("text", "drop_active"),
        ("muted", "window"),
        ("muted", "surface"),
        ("muted", "drop"),
        ("accent_text", "accent"),
    ],
)
def test_text_contrast_meets_wcag_aa(palette, foreground: str, background: str):
    ratio = contrast_ratio(getattr(palette, foreground), getattr(palette, background))

    assert ratio >= WCAG_AA_TEXT, f"{foreground} on {background}: {ratio:.2f}"


@pytest.mark.parametrize(
    ("theme", "system_dark", "expected"),
    [
        (Theme.LIGHT, True, LIGHT),
        (Theme.DARK, False, DARK),
        (Theme.SYSTEM, True, DARK),
        (Theme.SYSTEM, False, LIGHT),
    ],
)
def test_palette_for_resolves_system_theme(theme: Theme, system_dark: bool, expected):
    assert palette_for(theme, system_is_dark=system_dark) is expected


@pytest.mark.parametrize("palette", [LIGHT, DARK], ids=["light", "dark"])
def test_stylesheet_uses_palette_and_styles_drop_zone_states(palette):
    qss = build_stylesheet(palette)

    assert palette.window in qss
    assert palette.accent in qss
    assert "QLabel#dropZone" in qss
    assert 'QLabel#dropZone[dragActive="true"]' in qss
    assert "QLabel#dropZone:disabled" in qss
    assert "{palette" not in qss  # no unformatted placeholders


def test_light_and_dark_stylesheets_differ():
    assert build_stylesheet(LIGHT) != build_stylesheet(DARK)


def test_theme_defaults_to_system():
    assert load_theme(FakeSettings()) is Theme.SYSTEM


def test_theme_round_trip():
    settings = FakeSettings()

    save_theme(settings, Theme.DARK)

    assert settings.values == {KEY_THEME: "dark"}
    assert load_theme(settings) is Theme.DARK


@pytest.mark.parametrize("raw", ["neon", "", 3, None])
def test_invalid_theme_falls_back_to_system(raw):
    assert load_theme(FakeSettings({KEY_THEME: raw})) is Theme.SYSTEM
