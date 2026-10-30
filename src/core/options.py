"""Export options shared by the pipeline and the GUI."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

MIN_SCALE_PERCENT = 10
MAX_SCALE_PERCENT = 400
JPG_QUALITY = 90


class ImageFormat(Enum):
    """Output image format for rendered pages."""

    PNG = "png"
    JPG = "jpg"

    @property
    def extension(self) -> str:
        return self.value

    @property
    def save_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for ``PIL.Image.save``."""
        if self is ImageFormat.JPG:
            return {"format": "JPEG", "quality": JPG_QUALITY}
        return {"format": "PNG"}


@dataclass(frozen=True)
class ExportOptions:
    """How pages are written: scale relative to 150 DPI, image format, optional text."""

    scale_percent: int = 100
    image_format: ImageFormat = ImageFormat.PNG
    save_text: bool = False

    def __post_init__(self) -> None:
        if not MIN_SCALE_PERCENT <= self.scale_percent <= MAX_SCALE_PERCENT:
            raise ValueError(
                f"scale_percent must be between {MIN_SCALE_PERCENT} and {MAX_SCALE_PERCENT}, "
                f"got {self.scale_percent}"
            )
