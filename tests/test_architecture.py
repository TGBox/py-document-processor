"""Layering rules: core stays Qt-free, GUI stays free of document-processing internals."""

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def imports_in(folder: Path) -> dict[Path, set[str]]:
    pattern = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE)
    return {
        path: set(pattern.findall(path.read_text(encoding="utf-8"))) for path in folder.glob("*.py")
    }


def test_core_does_not_import_qt():
    offenders = {
        path.name: modules
        for path, modules in imports_in(SRC / "core").items()
        if any(module.startswith("PySide6") for module in modules)
    }

    assert offenders == {}


def test_gui_uses_only_the_public_core_api():
    allowed_core = {"src.core.pipeline", "src.core.options", "src.core.errors"}
    forbidden_prefixes = ("pypdfium2", "PIL", "win32", "pythoncom")

    offenders = {}
    for path, modules in imports_in(SRC / "gui").items():
        bad = {
            module
            for module in modules
            if (module.startswith("src.core") and module not in allowed_core)
            or module.startswith(forbidden_prefixes)
        }
        if bad:
            offenders[path.name] = bad

    assert offenders == {}
