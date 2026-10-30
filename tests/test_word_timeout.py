"""Timeout behaviour of ``word_to_pdf`` with a fake, hanging Word instance."""

import threading
from pathlib import Path
from typing import Any

import pytest

from src.core.errors import PasswordProtectedError, WordTimeoutError
from src.core.word_to_pdf import WORD_TIMEOUT_SECONDS, word_to_pdf

FAKE_PID = 4242
SHORT_TIMEOUT = 0.2


class RpcServerUnavailable(Exception):
    """What a blocked COM call raises once the Word process is gone."""


class HangingWord:
    """Fake Word whose ``Documents.Open`` blocks until the process is 'killed'."""

    def __init__(self) -> None:
        self.killed = threading.Event()
        self.quit_called = False
        self.Visible = True
        self.DisplayAlerts = -1
        self.AutomationSecurity = 1
        self.Documents = self

    def Open(self, **kwargs: Any) -> None:
        self.killed.wait(timeout=10)
        raise RpcServerUnavailable()

    def Quit(self, **kwargs: Any) -> None:
        self.quit_called = True


class Terminator:
    def __init__(self, word: HangingWord, error: Exception | None = None) -> None:
        self.word = word
        self.error = error
        self.pids: list[int] = []

    def __call__(self, pid: int) -> None:
        self.pids.append(pid)
        self.word.killed.set()
        if self.error:
            raise self.error


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "Brief.docx"
    path.write_bytes(b"fake")
    return path


def test_default_timeout_is_120_seconds():
    assert WORD_TIMEOUT_SECONDS == 120


def test_hanging_word_is_killed_by_pid_and_reported(source: Path, tmp_path: Path):
    word = HangingWord()
    terminate = Terminator(word)

    with pytest.raises(WordTimeoutError):
        word_to_pdf(
            source,
            tmp_path / "out.pdf",
            word_factory=lambda: word,
            timeout_seconds=SHORT_TIMEOUT,
            process_id_of=lambda _word: FAKE_PID,
            terminate=terminate,
        )

    assert terminate.pids == [FAKE_PID]


def test_unknown_pid_kills_nothing_but_still_reports_timeout(source: Path, tmp_path: Path):
    word = HangingWord()
    terminate = Terminator(word)

    try:
        with pytest.raises(WordTimeoutError):
            word_to_pdf(
                source,
                tmp_path / "out.pdf",
                word_factory=lambda: word,
                timeout_seconds=SHORT_TIMEOUT,
                process_id_of=lambda _word: None,
                terminate=terminate,
            )
        assert terminate.pids == []
    finally:
        word.killed.set()  # let the abandoned helper thread finish


def test_failing_terminate_does_not_mask_timeout(source: Path, tmp_path: Path):
    word = HangingWord()
    terminate = Terminator(word, error=OSError("access denied"))

    with pytest.raises(WordTimeoutError):
        word_to_pdf(
            source,
            tmp_path / "out.pdf",
            word_factory=lambda: word,
            timeout_seconds=SHORT_TIMEOUT,
            process_id_of=lambda _word: FAKE_PID,
            terminate=terminate,
        )


def test_fast_export_does_not_terminate_and_propagates_errors(source: Path, tmp_path: Path):
    class WrongPassword(Exception):
        excepinfo = (0, "Word", "", None, 0, -2146822880)

    class QuickWord(HangingWord):
        def Open(self, **kwargs: Any) -> None:
            raise WrongPassword()

    word = QuickWord()
    terminate = Terminator(word)

    with pytest.raises(PasswordProtectedError):
        word_to_pdf(
            source,
            tmp_path / "out.pdf",
            word_factory=lambda: word,
            timeout_seconds=5,
            process_id_of=lambda _word: FAKE_PID,
            terminate=terminate,
        )

    assert terminate.pids == []
    assert word.quit_called


def test_process_id_is_read_after_word_is_configured(source: Path, tmp_path: Path):
    word = HangingWord()
    seen: list[tuple[bool, int]] = []

    def record_pid(w: HangingWord) -> int:
        seen.append((w.Visible, w.DisplayAlerts))
        return FAKE_PID

    with pytest.raises(WordTimeoutError):
        word_to_pdf(
            source,
            tmp_path / "out.pdf",
            word_factory=lambda: word,
            timeout_seconds=SHORT_TIMEOUT,
            process_id_of=record_pid,
            terminate=Terminator(word),
        )

    assert seen == [(False, 0)]
