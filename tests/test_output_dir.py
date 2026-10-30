from pathlib import Path

from src.core.pipeline import next_output_dir


def test_uses_stem_with_pages_suffix_next_to_source(tmp_path: Path):
    source = tmp_path / "Befund Müller.docx"

    assert next_output_dir(source) == tmp_path / "Befund Müller_pages"


def test_existing_folder_gets_numbered_alternative(tmp_path: Path):
    source = tmp_path / "Brief.docx"
    (tmp_path / "Brief_pages").mkdir()

    assert next_output_dir(source) == tmp_path / "Brief_pages (2)"


def test_numbering_skips_all_taken_names(tmp_path: Path):
    source = tmp_path / "Brief.docx"
    (tmp_path / "Brief_pages").mkdir()
    (tmp_path / "Brief_pages (2)").mkdir()
    (tmp_path / "Brief_pages (3)").write_text("a file blocks the name too")

    assert next_output_dir(source) == tmp_path / "Brief_pages (4)"


def test_existing_folders_are_left_untouched(tmp_path: Path):
    source = tmp_path / "Brief.docx"
    existing = tmp_path / "Brief_pages"
    existing.mkdir()
    (existing / "page_01.png").write_bytes(b"old")

    next_output_dir(source)

    assert (existing / "page_01.png").read_bytes() == b"old"
