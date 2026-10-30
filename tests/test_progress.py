import pytest

from src.gui.progress import BatchProgress


def test_start_of_batch_is_zero_percent():
    progress = BatchProgress()
    progress.start_file(1, 4, "a.docx")

    assert progress.percent() == 0
    assert progress.text() == "Datei 1/4: a.docx – Word exportiert …"


def test_pages_advance_within_current_file():
    progress = BatchProgress()
    progress.start_file(2, 4, "b.docx")
    progress.page_done(1, 2)

    assert progress.percent() == 37  # (1 + 1/2) / 4 = 37.5 %
    assert progress.text() == "Datei 2/4: b.docx – Seite 1/2"


def test_last_page_of_last_file_is_complete():
    progress = BatchProgress()
    progress.start_file(3, 3, "c.docx")
    progress.page_done(5, 5)

    assert progress.percent() == 100


def test_new_file_resets_page_progress():
    progress = BatchProgress()
    progress.start_file(1, 2, "a.docx")
    progress.page_done(3, 3)
    progress.start_file(2, 2, "b.docx")

    assert progress.percent() == 50
    assert "Seite" not in progress.text()


@pytest.mark.parametrize(("page", "pages"), [(0, 0), (3, 0)])
def test_zero_pages_does_not_divide_by_zero(page: int, pages: int):
    progress = BatchProgress()
    progress.start_file(1, 1, "a.docx")
    progress.page_done(page, pages)

    assert progress.percent() == 0


def test_idle_progress_is_empty():
    progress = BatchProgress()

    assert progress.percent() == 0
    assert progress.text() == ""
