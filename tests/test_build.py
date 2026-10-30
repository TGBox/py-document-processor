from src.build import APP_NAME, ENTRY_SCRIPT, build_args


def option_values(args: list[str], option: str) -> list[str]:
    return [args[i + 1] for i, arg in enumerate(args) if arg == option]


def test_builds_windowed_onedir_app_with_project_name():
    args = build_args()

    assert {"--noconfirm", "--clean", "--onedir", "--windowed"} <= set(args)
    assert option_values(args, "--name") == [APP_NAME]
    assert args[-1] == ENTRY_SCRIPT


def test_project_root_is_on_the_analysis_path():
    # src/main.py imports "src.gui…", which only resolves with the project root on the path
    assert "." in option_values(build_args(), "--paths")


def test_pdfium_binaries_and_pywin32_helpers_are_bundled():
    args = build_args()

    assert {"pypdfium2", "pypdfium2_raw"} <= set(option_values(args, "--collect-all"))
    assert "win32timezone" in option_values(args, "--hidden-import")


def test_explicit_arguments_replace_defaults():
    assert build_args(["--version"]) == ["--version"]
