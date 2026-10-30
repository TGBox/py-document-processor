"""Light and dark colour palettes and the application stylesheet (Qt-free)."""

from dataclasses import dataclass
from enum import Enum


class Theme(Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


THEME_LABELS = {Theme.SYSTEM: "System", Theme.LIGHT: "Hell", Theme.DARK: "Dunkel"}


@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    text: str
    muted: str
    border: str
    accent: str
    accent_text: str
    drop: str
    drop_active: str


LIGHT = Palette(
    window="#f4f5f7",
    surface="#ffffff",
    text="#1b1f24",
    muted="#4a5563",
    border="#b8c0cc",
    accent="#0b5cad",
    accent_text="#ffffff",
    drop="#eaf1fa",
    drop_active="#d6e6f8",
)

DARK = Palette(
    window="#1d2025",
    surface="#262a30",
    text="#e8eaed",
    muted="#aab2bd",
    border="#4a515b",
    accent="#6ea8fe",
    accent_text="#10141a",
    drop="#222932",
    drop_active="#2b3a4d",
)


def palette_for(theme: Theme, system_is_dark: bool) -> Palette:
    if theme is Theme.SYSTEM:
        return DARK if system_is_dark else LIGHT
    return DARK if theme is Theme.DARK else LIGHT


def build_stylesheet(p: Palette) -> str:
    return f"""
QWidget {{
    background-color: {p.window};
    color: {p.text};
    font-size: 10pt;
}}
QMenuBar, QMenu {{
    background-color: {p.surface};
    color: {p.text};
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
}}
QSpinBox, QComboBox, QListWidget, QProgressBar {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 3px 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.surface};
    color: {p.text};
    selection-background-color: {p.accent};
    selection-color: {p.accent_text};
}}
QListWidget::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
}}
QProgressBar {{
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: 3px;
}}
QPushButton {{
    background-color: {p.accent};
    color: {p.accent_text};
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
}}
QPushButton:disabled {{
    background-color: {p.border};
    color: {p.muted};
}}
QWidget:disabled {{
    color: {p.muted};
}}
QToolTip {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
}}
QLabel#dropZone {{
    background-color: {p.drop};
    border: 2px dashed {p.border};
    border-radius: 10px;
    font-size: 13pt;
    padding: 24px;
}}
QLabel#dropZone:hover {{
    border-color: {p.accent};
}}
QLabel#dropZone[dragActive="true"] {{
    background-color: {p.drop_active};
    border: 2px solid {p.accent};
}}
QLabel#dropZone:disabled {{
    color: {p.muted};
    border-color: {p.border};
}}
"""


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.x contrast ratio between two ``#rrggbb`` colours."""
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
