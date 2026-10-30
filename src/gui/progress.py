"""Batch progress bookkeeping for the progress bar (Qt-free)."""


class BatchProgress:
    """Tracks "file x of y, page a of b" and derives an overall percentage."""

    def __init__(self) -> None:
        self._file_index = 0
        self._file_total = 0
        self._file_name = ""
        self._page = 0
        self._pages = 0

    def start_file(self, index: int, total: int, name: str) -> None:
        self._file_index = index
        self._file_total = total
        self._file_name = name
        self._page = 0
        self._pages = 0

    def page_done(self, page: int, pages: int) -> None:
        self._page = page
        self._pages = pages

    def percent(self) -> int:
        if self._file_total == 0:
            return 0
        page_fraction = self._page / self._pages if self._pages else 0.0
        done_files = self._file_index - 1 + page_fraction
        return int(100 * done_files / self._file_total)

    def text(self) -> str:
        if self._file_total == 0:
            return ""
        prefix = f"Datei {self._file_index}/{self._file_total}: {self._file_name}"
        if self._pages:
            return f"{prefix} – Seite {self._page}/{self._pages}"
        return f"{prefix} – Word exportiert …"
