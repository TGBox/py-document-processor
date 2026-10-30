"""Process one document end to end: source → temporary PDF → page images.

Also runnable without GUI for smoke tests:  uv run python -m src.core.pipeline <file> [...]
"""

import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from src.core.errors import DocumentError, RenderError, SourceNotFoundError, UnsupportedFileError
from src.core.options import ExportOptions
from src.core.pdf_to_images import CancelCheck, ProgressCallback, render_pages
from src.core.word_to_pdf import word_to_pdf

SUPPORTED_SUFFIXES = frozenset({".docx", ".docm", ".doc", ".rtf"})
OUTPUT_DIR_SUFFIX = "_pages"
TEMP_PREFIX = "py-document-processor-"

Converter = Callable[[Path, Path], None]


def _never_cancelled() -> bool:
    return False


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def next_output_dir(src: Path) -> Path:
    """Return ``<stem>_pages`` next to ``src``, or ``<stem>_pages (n)`` if that name is taken."""
    base = f"{src.stem}{OUTPUT_DIR_SUFFIX}"
    candidate = src.parent / base
    number = 2
    while candidate.exists():
        candidate = src.parent / f"{base} ({number})"
        number += 1
    return candidate


def process_document(
    src: Path,
    options: ExportOptions,
    on_page: ProgressCallback | None = None,
    is_cancelled: CancelCheck = _never_cancelled,
    converter: Converter | None = None,
) -> Path | None:
    """Export every page of ``src`` as an image and return the output folder.

    Returns ``None`` if cancelled before any page was written. The temporary PDF is always
    removed. Raises a ``DocumentError`` subclass on failure.
    """
    if not is_supported(src):
        raise UnsupportedFileError(f"suffix {src.suffix!r}")
    if not src.is_file():
        raise SourceNotFoundError(str(src))
    convert = converter or word_to_pdf

    with tempfile.TemporaryDirectory(prefix=TEMP_PREFIX) as temp_dir:
        pdf_path = Path(temp_dir) / "document.pdf"
        convert(src, pdf_path)
        if is_cancelled():
            return None

        out_dir = next_output_dir(src)
        out_dir.mkdir()
        try:
            render_pages(pdf_path, out_dir, options, on_page=on_page, is_cancelled=is_cancelled)
        except Exception as exc:
            _remove_if_empty(out_dir)
            raise RenderError(type(exc).__name__) from exc
        return out_dir


def _remove_if_empty(folder: Path) -> None:
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()


def main(argv: Sequence[str] | None = None, converter: Converter | None = None) -> int:
    """Smoke-test entry point: process files with default options, report per file."""
    paths = [Path(arg).resolve() for arg in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print("Aufruf: python -m src.core.pipeline <datei.docx> [...]")
        return 2
    failed = False
    for path in paths:
        try:
            out_dir = process_document(path, ExportOptions(), converter=converter)
        except DocumentError as error:
            failed = True
            print(f"FEHLER  {path.name}: {error.user_message}")
        else:
            print(f"OK      {path.name} -> {out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
