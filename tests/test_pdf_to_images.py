from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image

from src.core.options import ExportOptions, ImageFormat
from src.core.pdf_to_images import render_pages

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES / "sample.pdf"

A4_WIDTH_PT = 595.28
A4_HEIGHT_PT = 841.89


def make_blank_pdf(path: Path, page_count: int) -> Path:
    pdf = pdfium.PdfDocument.new()
    for _ in range(page_count):
        pdf.new_page(A4_WIDTH_PT, A4_HEIGHT_PT)
    pdf.save(path)
    pdf.close()
    return path


def assert_size_close(image_path: Path, expected: tuple[int, int]) -> None:
    with Image.open(image_path) as image:
        width, height = image.size
    assert abs(width - expected[0]) <= 1, (width, height)
    assert abs(height - expected[1]) <= 1, (width, height)


def test_renders_one_png_per_page_at_original_size(tmp_path: Path):
    written = render_pages(SAMPLE_PDF, tmp_path, ExportOptions())

    assert [p.name for p in written] == ["page_01.png", "page_02.png"]
    assert all(p.is_file() for p in written)
    assert_size_close(written[0], (1240, 1754))


@pytest.mark.parametrize(
    ("scale", "expected"),
    [(50, (620, 877)), (200, (2480, 3508))],
)
def test_scale_changes_pixel_size(tmp_path: Path, scale: int, expected: tuple[int, int]):
    written = render_pages(SAMPLE_PDF, tmp_path, ExportOptions(scale_percent=scale))

    assert_size_close(written[0], expected)


def test_jpg_format_writes_jpeg_files(tmp_path: Path):
    written = render_pages(SAMPLE_PDF, tmp_path, ExportOptions(image_format=ImageFormat.JPG))

    assert [p.suffix for p in written] == [".jpg", ".jpg"]
    with Image.open(written[0]) as image:
        assert image.format == "JPEG"


def test_no_text_files_by_default(tmp_path: Path):
    render_pages(SAMPLE_PDF, tmp_path, ExportOptions())

    assert list(tmp_path.glob("*.txt")) == []


def test_save_text_writes_page_text_as_utf8(tmp_path: Path):
    render_pages(SAMPLE_PDF, tmp_path, ExportOptions(save_text=True))

    first = (tmp_path / "page_01.txt").read_text(encoding="utf-8")
    second = (tmp_path / "page_02.txt").read_text(encoding="utf-8")
    assert "Seite eins Alpha" in first
    assert "Seite zwei Beta" in second
    assert "Beta" not in first


def test_zero_padding_grows_with_page_count(tmp_path: Path):
    pdf = make_blank_pdf(tmp_path / "many.pdf", 100)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    written = render_pages(pdf, out_dir, ExportOptions(scale_percent=10))

    assert written[0].name == "page_001.png"
    assert written[-1].name == "page_100.png"


def test_progress_callback_reports_each_page(tmp_path: Path):
    calls: list[tuple[int, int]] = []

    render_pages(SAMPLE_PDF, tmp_path, ExportOptions(), on_page=lambda i, n: calls.append((i, n)))

    assert calls == [(1, 2), (2, 2)]


def test_cancel_stops_before_next_page(tmp_path: Path):
    rendered: list[int] = []

    written = render_pages(
        SAMPLE_PDF,
        tmp_path,
        ExportOptions(),
        on_page=lambda i, n: rendered.append(i),
        is_cancelled=lambda: len(rendered) >= 1,
    )

    assert [p.name for p in written] == ["page_01.png"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page_01.png"]


def test_pdf_file_is_released_after_rendering(tmp_path: Path):
    pdf = tmp_path / "copy.pdf"
    pdf.write_bytes(SAMPLE_PDF.read_bytes())
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    render_pages(pdf, out_dir, ExportOptions())

    pdf.unlink()  # fails on Windows if the file handle is still open
    assert not pdf.exists()
