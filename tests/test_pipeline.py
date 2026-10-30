import shutil
from pathlib import Path

import pytest

from src.core.errors import (
    DocumentError,
    SourceNotFoundError,
    UnsupportedFileError,
    WordExportError,
)
from src.core.options import ExportOptions, ImageFormat
from src.core.pipeline import SUPPORTED_SUFFIXES, main, process_document

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


class FakeConverter:
    """Stands in for ``word_to_pdf``: copies the sample PDF and remembers the target."""

    def __init__(self, error: Exception | None = None, content: bytes | None = None) -> None:
        self.error = error
        self.content = content
        self.calls: list[tuple[Path, Path]] = []

    def __call__(self, src: Path, dst_pdf: Path) -> None:
        self.calls.append((src, dst_pdf))
        if self.error:
            raise self.error
        if self.content is not None:
            dst_pdf.write_bytes(self.content)
        else:
            shutil.copyfile(SAMPLE_PDF, dst_pdf)

    @property
    def temp_pdf(self) -> Path:
        return self.calls[-1][1]


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "Brief.docx"
    path.write_bytes(b"fake docx")
    return path


def test_supported_suffixes_match_spec():
    assert SUPPORTED_SUFFIXES == {".docx", ".docm", ".doc", ".rtf"}


def test_writes_pages_next_to_source_and_returns_folder(source: Path):
    converter = FakeConverter()

    out_dir = process_document(source, ExportOptions(), converter=converter)

    assert out_dir == source.parent / "Brief_pages"
    assert sorted(p.name for p in out_dir.iterdir()) == ["page_01.png", "page_02.png"]
    assert converter.calls[0][0] == source


def test_suffix_check_is_case_insensitive(tmp_path: Path):
    source = tmp_path / "BRIEF.DOCX"
    source.write_bytes(b"fake")

    assert process_document(source, ExportOptions(), converter=FakeConverter()) is not None


def test_options_are_passed_to_rendering(source: Path):
    out_dir = process_document(
        source,
        ExportOptions(image_format=ImageFormat.JPG, save_text=True),
        converter=FakeConverter(),
    )

    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["page_01.jpg", "page_01.txt", "page_02.jpg", "page_02.txt"]


def test_unsupported_suffix_raises_without_side_effects(tmp_path: Path):
    source = tmp_path / "Tabelle.xlsx"
    source.write_bytes(b"fake")
    converter = FakeConverter()

    with pytest.raises(UnsupportedFileError):
        process_document(source, ExportOptions(), converter=converter)

    assert converter.calls == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Tabelle.xlsx"]


def test_missing_source_raises_source_not_found(tmp_path: Path):
    with pytest.raises(SourceNotFoundError):
        process_document(tmp_path / "fehlt.docx", ExportOptions(), converter=FakeConverter())


def test_temp_pdf_is_deleted_after_success(source: Path):
    converter = FakeConverter()

    process_document(source, ExportOptions(), converter=converter)

    assert not converter.temp_pdf.exists()
    assert not converter.temp_pdf.parent.exists()


def test_converter_error_propagates_and_cleans_up(source: Path):
    converter = FakeConverter(error=WordExportError("boom"))

    with pytest.raises(WordExportError):
        process_document(source, ExportOptions(), converter=converter)

    assert not converter.temp_pdf.parent.exists()
    assert not (source.parent / "Brief_pages").exists()


def test_render_failure_raises_document_error_without_empty_folder(source: Path):
    converter = FakeConverter(content=b"this is not a pdf")

    with pytest.raises(DocumentError):
        process_document(source, ExportOptions(), converter=converter)

    assert not converter.temp_pdf.parent.exists()
    assert not (source.parent / "Brief_pages").exists()


def test_cancel_before_rendering_returns_none_without_folder(source: Path):
    converter = FakeConverter()

    result = process_document(
        source, ExportOptions(), converter=converter, is_cancelled=lambda: True
    )

    assert result is None
    assert not (source.parent / "Brief_pages").exists()
    assert not converter.temp_pdf.parent.exists()


def test_cancel_during_rendering_keeps_written_pages(source: Path):
    converter = FakeConverter()
    pages: list[int] = []

    out_dir = process_document(
        source,
        ExportOptions(),
        converter=converter,
        on_page=lambda i, n: pages.append(i),
        is_cancelled=lambda: len(pages) >= 1,
    )

    assert sorted(p.name for p in out_dir.iterdir()) == ["page_01.png"]
    assert not converter.temp_pdf.parent.exists()


def test_second_run_writes_into_numbered_folder(source: Path):
    first = process_document(source, ExportOptions(), converter=FakeConverter())
    second = process_document(source, ExportOptions(), converter=FakeConverter())

    assert first.name == "Brief_pages"
    assert second.name == "Brief_pages (2)"


def test_cli_reports_output_folder(source: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main([str(source)], converter=FakeConverter())

    assert exit_code == 0
    assert "Brief_pages" in capsys.readouterr().out


def test_cli_reports_german_error_and_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    source = tmp_path / "Tabelle.xlsx"
    source.write_bytes(b"fake")

    exit_code = main([str(source)], converter=FakeConverter())

    assert exit_code == 1
    assert UnsupportedFileError.user_message in capsys.readouterr().out
