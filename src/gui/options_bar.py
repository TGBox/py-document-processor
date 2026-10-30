"""Row of export options above the drop zone."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QWidget

from src.core.options import MAX_SCALE_PERCENT, MIN_SCALE_PERCENT, ExportOptions, ImageFormat

FORMAT_LABELS = {ImageFormat.PNG: "PNG", ImageFormat.JPG: "JPG"}


class OptionsBar(QWidget):
    """Edits ExportOptions; emits ``options_changed`` on every user change."""

    options_changed = Signal(object)  # ExportOptions

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.scale = QSpinBox()
        self.scale.setRange(MIN_SCALE_PERCENT, MAX_SCALE_PERCENT)
        self.scale.setSingleStep(10)
        self.scale.setSuffix(" %")
        self.scale.setToolTip("100 % entspricht 150 DPI (A4: 1240 × 1754 Pixel)")

        self.image_format = QComboBox()
        for image_format, label in FORMAT_LABELS.items():
            self.image_format.addItem(label, image_format.value)

        self.save_text = QCheckBox("Text pro Seite speichern")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Skalierung:"))
        layout.addWidget(self.scale)
        layout.addSpacing(16)
        layout.addWidget(QLabel("Format:"))
        layout.addWidget(self.image_format)
        layout.addSpacing(16)
        layout.addWidget(self.save_text)
        layout.addStretch()

        self.set_options(ExportOptions())
        self.scale.valueChanged.connect(self._emit_changed)
        self.image_format.currentIndexChanged.connect(self._emit_changed)
        self.save_text.toggled.connect(self._emit_changed)

    def options(self) -> ExportOptions:
        return ExportOptions(
            scale_percent=self.scale.value(),
            image_format=ImageFormat(self.image_format.currentData()),
            save_text=self.save_text.isChecked(),
        )

    def set_options(self, options: ExportOptions) -> None:
        """Show ``options`` without emitting ``options_changed``."""
        widgets = (self.scale, self.image_format, self.save_text)
        for widget in widgets:
            widget.blockSignals(True)
        try:
            self.scale.setValue(options.scale_percent)
            self.image_format.setCurrentIndex(
                self.image_format.findData(options.image_format.value)
            )
            self.save_text.setChecked(options.save_text)
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    def _emit_changed(self, *_args: object) -> None:
        self.options_changed.emit(self.options())
