"""Build the standalone Windows app with PyInstaller:  uv run build"""

import sys
from collections.abc import Sequence

APP_NAME = "py-document-processor"
ENTRY_SCRIPT = "src/main.py"


def build_args(argv: Sequence[str] | None = None) -> list[str]:
    """PyInstaller arguments; explicit ``argv`` replaces the defaults entirely."""
    if argv:
        return list(argv)
    return [
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        # src/main.py imports the "src" package, so the project root must be importable.
        "--paths",
        ".",
        # pdfium ships as a native library inside these packages.
        "--collect-all",
        "pypdfium2",
        "--collect-all",
        "pypdfium2_raw",
        # Commonly required by pywin32 at runtime, but not detected automatically.
        "--hidden-import",
        "win32timezone",
        ENTRY_SCRIPT,
    ]


def main() -> None:
    import PyInstaller.__main__

    PyInstaller.__main__.run(build_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
