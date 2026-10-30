"""ExportWorker runs synchronously here (``run()`` called directly, no thread/event loop)."""

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from src.core.errors import PasswordProtectedError
from src.core.options import ExportOptions, ImageFormat
from src.gui.worker import ExportWorker


class FakeProcess:
    """Stands in for ``process_document``."""

    def __init__(self, failing: dict[str, Exception] | None = None) -> None:
        self.failing = failing or {}
        self.calls: list[tuple[Path, ExportOptions]] = []

    def __call__(self, src: Path, options: ExportOptions, on_page=None, is_cancelled=None):
        self.calls.append((src, options))
        if src.name in self.failing:
            raise self.failing[src.name]
        if on_page:
            on_page(1, 2)
            on_page(2, 2)
        return src.parent / f"{src.stem}_pages"


class Recorder:
    def __init__(self, worker: ExportWorker) -> None:
        self.events: list[tuple] = []
        worker.file_started.connect(lambda i, n, name: self.events.append(("started", i, n, name)))
        worker.page_done.connect(lambda page, pages: self.events.append(("page", page, pages)))
        worker.file_done.connect(lambda src, out: self.events.append(("done", src, out)))
        worker.file_failed.connect(lambda src, msg: self.events.append(("failed", src, msg)))
        worker.finished.connect(lambda: self.events.append(("finished",)))

    def of(self, kind: str) -> list[tuple]:
        return [event for event in self.events if event[0] == kind]


def make_paths(tmp_path: Path, *names: str) -> list[Path]:
    return [tmp_path / name for name in names]


def test_processes_all_files_in_order_and_reports(tmp_path: Path):
    paths = make_paths(tmp_path, "a.docx", "b.docx")
    process = FakeProcess()
    worker = ExportWorker(paths, ExportOptions(), process=process)
    recorder = Recorder(worker)

    worker.run()

    assert [call[0] for call in process.calls] == paths
    assert recorder.of("started") == [("started", 1, 2, "a.docx"), ("started", 2, 2, "b.docx")]
    assert recorder.of("done") == [
        ("done", str(paths[0]), str(tmp_path / "a_pages")),
        ("done", str(paths[1]), str(tmp_path / "b_pages")),
    ]
    assert recorder.events[-1] == ("finished",)


def test_options_are_passed_through(tmp_path: Path):
    options = ExportOptions(scale_percent=50, image_format=ImageFormat.JPG)
    process = FakeProcess()

    ExportWorker(make_paths(tmp_path, "a.docx"), options, process=process).run()

    assert process.calls[0][1] == options


def test_page_progress_is_forwarded(tmp_path: Path):
    worker = ExportWorker(make_paths(tmp_path, "a.docx"), ExportOptions(), process=FakeProcess())
    recorder = Recorder(worker)

    worker.run()

    assert recorder.of("page") == [("page", 1, 2), ("page", 2, 2)]


def test_failure_reports_german_message_and_continues(tmp_path: Path):
    paths = make_paths(tmp_path, "geheim.docx", "b.docx")
    process = FakeProcess(failing={"geheim.docx": PasswordProtectedError("detail")})
    worker = ExportWorker(paths, ExportOptions(), process=process)
    recorder = Recorder(worker)

    worker.run()

    assert recorder.of("failed") == [("failed", str(paths[0]), PasswordProtectedError.user_message)]
    assert len(recorder.of("done")) == 1


def test_unexpected_exception_becomes_generic_failure(tmp_path: Path):
    paths = make_paths(tmp_path, "a.docx")
    worker = ExportWorker(paths, ExportOptions(), process=FakeProcess({"a.docx": KeyError("x")}))
    recorder = Recorder(worker)

    worker.run()

    [(_, _, message)] = recorder.of("failed")
    assert message.startswith("Unerwarteter Fehler")
    assert recorder.events[-1] == ("finished",)


def test_cancel_stops_before_next_file(tmp_path: Path):
    paths = make_paths(tmp_path, "a.docx", "b.docx")
    process = FakeProcess()
    worker = ExportWorker(paths, ExportOptions(), process=process)
    worker.file_done.connect(lambda *_: worker.cancel())

    worker.run()

    assert [call[0] for call in process.calls] == [paths[0]]
    assert worker.is_cancelled()


def test_cancelled_before_any_page_is_not_reported_as_done(tmp_path: Path):
    class CancelledProcess(FakeProcess):
        def __call__(self, src, options, on_page=None, is_cancelled=None):
            return None

    worker = ExportWorker(make_paths(tmp_path, "a.docx"), ExportOptions(), CancelledProcess())
    recorder = Recorder(worker)

    worker.run()

    assert recorder.of("done") == []
    assert recorder.of("failed") == []
