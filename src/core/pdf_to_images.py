"""Render PDF pages to image files (and optional text files) with pypdfium2."""

from collections.abc import Callable
from pathlib import Path

import pypdfium2 as pdfium

from src.core.options import ExportOptions

BASE_DPI = 150
PDF_POINTS_PER_INCH = 72
MIN_INDEX_DIGITS = 2

ProgressCallback = Callable[[int, int], None]
CancelCheck = Callable[[], bool]


def _never_cancelled() -> bool:
    return False


def render_pages(
    pdf_path: Path,
    out_dir: Path,
    options: ExportOptions,
    on_page: ProgressCallback | None = None,
    is_cancelled: CancelCheck = _never_cancelled,
) -> list[Path]:
    """Render every page of ``pdf_path`` into ``out_dir`` and return the written image paths.

    ``on_page(index, total)`` is called after each page (1-based). ``is_cancelled`` is checked
    before each page; rendering stops early when it returns True.
    """
    scale = BASE_DPI * options.scale_percent / 100 / PDF_POINTS_PER_INCH
    extension = options.image_format.extension
    written: list[Path] = []

    pdf = pdfium.PdfDocument(pdf_path)
    try:
        total = len(pdf)
        digits = max(MIN_INDEX_DIGITS, len(str(total)))
        for index in range(1, total + 1):
            if is_cancelled():
                break
            page = pdf[index - 1]
            try:
                stem = f"page_{index:0{digits}d}"
                image_path = out_dir / f"{stem}.{extension}"
                bitmap = page.render(scale=scale)
                bitmap.to_pil().save(image_path, **options.image_format.save_kwargs)
                written.append(image_path)
                if options.save_text:
                    (out_dir / f"{stem}.txt").write_text(_page_text(page), encoding="utf-8")
            finally:
                page.close()
            if on_page is not None:
                on_page(index, total)
    finally:
        pdf.close()
    return written


def _page_text(page: pdfium.PdfPage) -> str:
    text_page = page.get_textpage()
    try:
        return text_page.get_text_bounded()
    finally:
        text_page.close()
