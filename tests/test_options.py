import pytest

from src.core.errors import (
    DocumentError,
    PasswordProtectedError,
    UnsupportedFileError,
    WordExportError,
    WordTimeoutError,
)
from src.core.options import (
    MAX_SCALE_PERCENT,
    MIN_SCALE_PERCENT,
    ExportOptions,
    ImageFormat,
)


def test_defaults_are_original_size_png_without_text():
    options = ExportOptions()

    assert options.scale_percent == 100
    assert options.image_format is ImageFormat.PNG
    assert options.save_text is False


@pytest.mark.parametrize("scale", [MIN_SCALE_PERCENT, 100, MAX_SCALE_PERCENT])
def test_scale_within_bounds_is_accepted(scale: int):
    assert ExportOptions(scale_percent=scale).scale_percent == scale


@pytest.mark.parametrize("scale", [MIN_SCALE_PERCENT - 1, 0, -50, MAX_SCALE_PERCENT + 1])
def test_scale_out_of_bounds_raises(scale: int):
    with pytest.raises(ValueError):
        ExportOptions(scale_percent=scale)


def test_scale_bounds_match_spec():
    assert (MIN_SCALE_PERCENT, MAX_SCALE_PERCENT) == (10, 400)


@pytest.mark.parametrize(
    ("image_format", "extension", "pil_format"),
    [(ImageFormat.PNG, "png", "PNG"), (ImageFormat.JPG, "jpg", "JPEG")],
)
def test_image_format_extension_and_save_kwargs(
    image_format: ImageFormat, extension: str, pil_format: str
):
    assert image_format.extension == extension
    assert image_format.save_kwargs["format"] == pil_format


def test_jpg_uses_fixed_quality_90():
    assert ImageFormat.JPG.save_kwargs["quality"] == 90


@pytest.mark.parametrize(
    "error_class",
    [UnsupportedFileError, PasswordProtectedError, WordExportError, WordTimeoutError],
)
def test_errors_are_document_errors_with_german_user_message(error_class: type[DocumentError]):
    error = error_class()

    assert isinstance(error, DocumentError)
    assert error.user_message
    assert error.user_message != DocumentError.user_message


def test_timeout_error_message_matches_spec():
    assert WordTimeoutError.user_message == "Word reagiert nicht – Verarbeitung abgebrochen."


def test_error_keeps_technical_detail_separate_from_user_message():
    error = WordExportError("COM error -2147352567")

    assert error.detail == "COM error -2147352567"
    assert "COM" not in error.user_message
