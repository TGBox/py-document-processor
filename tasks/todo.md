# Tasks: Word-Seiten als Bilder (MVP)

> Plan: [`tasks/plan.md`](plan.md) · Spec: [`SPEC.md`](../SPEC.md)
> Jeder Task gilt erst als erledigt, wenn `uv run ruff check .` und `uv run pytest -v` grün sind.

---

## Phase 1: Pipeline-Bausteine

### Task 1: Fundament – Abhängigkeiten, `ExportOptions`, Fehlerklassen

**Description:** Neue Abhängigkeiten aufnehmen und die gemeinsamen Datentypen anlegen, auf
die alle weiteren Bausteine aufsetzen. `ExportOptions` (Skalierung 10–400 %, Bildformat
PNG/JPG inkl. Endung und Speicherparameter, Text ja/nein) sowie die Fehlerhierarchie
`DocumentError` mit deutscher `user_message`.

**Acceptance criteria:**

- [x] `pypdfium2`, `pillow`, `pywin32; sys_platform == 'win32'` in `pyproject.toml`, `uv.lock` aktualisiert
- [x] `ExportOptions` validiert Skalierung (außerhalb 10–400 → `ValueError`), Standard 100 % / PNG / Text aus
- [x] Fehlerklassen: `UnsupportedFileError`, `PasswordProtectedError`, `WordExportError`, `WordTimeoutError` – jeweils mit deutscher Meldung

**Verification:**

- [x] `uv sync --all-groups` ok
- [x] `uv run pytest tests/test_options.py -v`

**Dependencies:** None
**Files:** `pyproject.toml`, `uv.lock`, `src/core/__init__.py`, `src/core/options.py`, `src/core/errors.py`, `tests/test_options.py`
**Scope:** S

---

### Task 2: `pdf_to_images` – Seiten rendern, Text extrahieren, Abbruch

**Description:** `render_pages(pdf, out_dir, options, on_page, is_cancelled)` rendert jede
Seite mit 150 DPI × Skalierung als PNG/JPG, schreibt optional `page_NN.txt` und bricht vor
der nächsten Seite ab, wenn `is_cancelled()` wahr ist. Dazu ein eingechecktes Fixture-PDF
(2 Seiten A4, bekannter Text) plus Generator-Skript.

**Acceptance criteria:**

- [x] A4 bei 100 % → 1240 × 1754 px (±1), bei 50 % → 620 × 877 px; Anzahl Bilder == Seitenzahl
- [x] JPG-Option → `.jpg`; Text-Option → `page_NN.txt` (UTF-8) mit Seitentext; Nullpolsterung ≥ 2 Stellen
- [x] Abbruch nach Seite 1 → genau 1 Bild, Rückgabe enthält nur geschriebene Pfade

**Verification:**

- [x] `uv run pytest tests/test_pdf_to_images.py -v`

**Dependencies:** Task 1
**Files:** `src/core/pdf_to_images.py`, `tests/test_pdf_to_images.py`, `tests/fixtures/sample.pdf`, `tests/fixtures/make_sample_pdf.py`
**Scope:** S

---

### Task 3: `word_to_pdf` – Word-COM-Export ohne Markup

**Description:** `word_to_pdf(src, dst_pdf)` startet eine eigene unsichtbare Word-Instanz
(`DispatchEx`), öffnet die Datei schreibgeschützt ohne Dialoge, blendet Änderungen und
Kommentare aus, exportiert per `ExportAsFixedFormat` als PDF und beendet Word immer im
`finally`. COM-Fehler werden auf die Fehlerklassen aus Task 1 abgebildet. `win32com` wird
lazy importiert. Pytest-Marker `word` registrieren und in CI standardmäßig ausschließen.

**Acceptance criteria:**

- [x] Dokument mit Änderungsverfolgung + Kommentar → PDF-Text enthält nur die Endfassung, keinen Kommentartext
- [x] Kennwortgeschützte Datei → `PasswordProtectedError` ohne Dialog/Hänger; kein verbleibender eigener WINWORD-Prozess
- [x] Quelldatei-`mtime` unverändert; bereits offenes Nutzer-Word bleibt offen

**Verification:**

- [x] `uv run pytest -v` (CI/Linux: Word-Tests übersprungen)
- [x] Daniel lokal: `uv run pytest -v -m word`
- [x] Manuell: Word mit eigenem Dokument offen lassen, Test laufen lassen → Dokument noch offen

**Dependencies:** Task 1
**Files:** `src/core/word_to_pdf.py`, `tests/test_word_to_pdf.py`, `tests/test_word_to_pdf_integration.py`, `tests/fixtures/markup.docx`, `tests/fixtures/password.docx`, `pyproject.toml` (pytest-Marker)
**Scope:** M

---

### ✅ Checkpoint 1 (Daniel, Windows)

- [x] `uv run pytest -v -m word` grün
- [x] PDF eines Markup-Dokuments manuell angesehen: nur Endfassung
- [x] Review mit Daniel vor Phase 2

---

## Phase 2: Orchestrierung

### Task 4: `pipeline.process_document` – Ausgabeordner, Temp-PDF, Aufräumen

**Description:** `process_document(src, options, on_page, is_cancelled) -> Path` prüft die
Endung, legt `<name>_pages` bzw. `<name>_pages (n)` an, erzeugt das PDF in einem
`TemporaryDirectory`, ruft `render_pages` auf und räumt immer auf. Zusätzlich
`python -m src.core.pipeline <datei>` als Smoke-Test-Einstieg ohne GUI.

**Acceptance criteria:**

- [x] Nicht unterstützte Endung → `UnsupportedFileError`, kein Ordner angelegt
- [x] Vorhandener Ausgabeordner → `(2)`, `(3)` …; bestehender Ordner unverändert
- [x] Temp-PDF ist nach Erfolg, Fehler (gemocktes `word_to_pdf` wirft) und Abbruch gelöscht

**Verification:**

- [x] `uv run pytest tests/test_pipeline.py tests/test_output_dir.py -v`
- [x] Daniel lokal: `uv run python -m src.core.pipeline <test.docx>` → Bilder vorhanden

**Dependencies:** Task 2, Task 3
**Files:** `src/core/pipeline.py`, `tests/test_pipeline.py`, `tests/test_output_dir.py`
**Scope:** S

---

### Task 5: Word-Timeout (120 s) mit Beenden der eigenen Word-Instanz

**Description:** Watchdog um den Word-Export: PID der eigenen Instanz über das Fenster-Handle
ermitteln; überschreitet der Export 120 s, wird genau dieser Prozess beendet und
`WordTimeoutError` geworfen. Ist die PID nicht ermittelbar, wird nichts beendet und nur der
Fehler gemeldet. Timeout ist als Parameter injizierbar (Tests mit kurzer Zeit).

**Acceptance criteria:**

- [x] Simulierter Hänger (Fake-Exporter, Timeout 1 s) → `WordTimeoutError`, Kill-Funktion mit korrekter PID aufgerufen
- [x] PID unbekannt → kein Kill-Aufruf, trotzdem `WordTimeoutError`
- [x] Nie Beenden per Prozessname; Nutzer-Word bleibt bei Timeout unberührt (manuell)

**Verification:**

- [x] `uv run pytest tests/test_word_timeout.py -v`
- [x] Daniel lokal: Word-Export mit künstlich kurzem Timeout → eigenes Word bleibt offen

**Dependencies:** Task 3
**Files:** `src/core/word_to_pdf.py`, `tests/test_word_timeout.py`
**Scope:** S

---

### ✅ Checkpoint 2

- [x] `uv run pytest -v` grün, lokal zusätzlich `-m word`
- [x] Smoke-Test über `python -m src.core.pipeline` mit echtem Dokument erfolgreich

---

## Phase 3: GUI

### Task 6: GUI-Scheibe – Drop-Zone → Export im Worker → Ordner öffnen

**Description:** Erste durchgängige Bedienung mit Standardoptionen: Drop-Zone-Widget
(Drag & Drop, Klick öffnet Dateidialog), `ExportWorker` als QObject im QThread
(`CoInitialize` im Thread), Signale `file_done`/`failed`/`finished`; nach Abschluss wird der
Ausgabeordner im Explorer geöffnet. `main.py` startet das neue `MainWindow`.

**Acceptance criteria:**

- [x] Drop einer .docx → Bilder entstehen, Ordner öffnet sich; Fenster bleibt währenddessen verschiebbar
- [x] Mehrere Dateien werden nacheinander verarbeitet; Klick auf Drop-Zone öffnet Dateidialog mit Word-Filter
- [x] `src/gui/` enthält keine Fachlogik, `src/core/` keinen Qt-Import (per Test geprüft: `grep`-Test auf `PySide6` in `src/core`)

**Verification:**

- [x] `uv run pytest -v`
- [x] Daniel lokal: `uv run main`, Datei droppen

**Dependencies:** Task 4
**Files:** `src/main.py`, `src/gui/__init__.py`, `src/gui/main_window.py`, `src/gui/drop_zone.py`, `src/gui/worker.py`, `tests/test_architecture.py`, `tests/test_worker.py`
**Scope:** M

---

### Task 7: Optionsleiste (Skalierung, Format, Text) + Persistenz

**Description:** Über der Drop-Zone: Spinbox „Skalierung (%)“ (10–400), Auswahl PNG/JPG,
Checkbox „Text pro Seite speichern“. Werte gehen als `ExportOptions` an den Worker und
werden per `QSettings` gespeichert und beim Start geladen.

**Acceptance criteria:**

- [x] Gewählte Optionen wirken sich auf den Export aus (50 % → halbe Pixelmaße, JPG, Textdateien)
- [x] Nach Neustart sind die zuletzt gewählten Optionen wieder eingestellt
- [x] Ungültige gespeicherte Werte fallen auf Standard zurück

**Verification:**

- [x] `uv run pytest -v`
- [x] Daniel lokal: Optionen ändern, App neu starten, prüfen

**Dependencies:** Task 6
**Files:** `src/gui/main_window.py`, `src/gui/options_bar.py`, `src/gui/settings.py`, `tests/test_settings.py`, `tests/test_options_bar.py`
**Scope:** S

---

### Task 8: Fortschritt, Abbrechen, Statusliste mit Fehlern

**Description:** Fortschrittsanzeige „Datei x/y – Seite a/b“, Button „Abbrechen“ (setzt
Flag, das `is_cancelled` liefert), Statusliste mit einer Zeile pro Datei
(✓ Ausgabeordner / ✗ deutsche Fehlermeldung). Drop-Zone ist während eines Laufs gesperrt.

**Acceptance criteria:**

- [x] Fortschritt aktualisiert sich pro Seite; Abbrechen stoppt nach der aktuellen Seite, bereits erzeugte Bilder bleiben
- [x] Fehlerhafte Datei (z. B. kennwortgeschützt) → ✗ mit Meldung, nächste Datei wird verarbeitet
- [x] Während eines Laufs keine zweite Verarbeitung startbar

**Verification:**

- [x] `uv run pytest -v`
- [x] Daniel lokal: 3 Dateien droppen (eine mit Kennwort), einmal abbrechen

**Dependencies:** Task 6
**Files:** `src/gui/main_window.py`, `src/gui/status_list.py`, `src/gui/progress.py`, `tests/test_progress.py`, `tests/test_status_list.py`
**Scope:** S

---

### Task 9: Dark/Light-Theme, F11, Fenstergeometrie

**Description:** QSS für Dark und Light (System-Standard, umschaltbar über Menü), F11 für
Vollbild, Fenstergröße/-position per `QSettings` gespeichert. Konsistent für alle Widgets aus
Task 6–8, inkl. Hover-/Drag-Over-Zustand der Drop-Zone.

**Acceptance criteria:**

- [x] Theme umschaltbar, Auswahl wird gespeichert; Kontraste gut lesbar in beiden Themes
- [x] F11 wechselt Vollbild ↔ Fenster ohne Layoutfehler
- [x] Fenstergeometrie bleibt über Neustart erhalten

**Verification:**

- [x] `uv run pytest -v`
- [x] Daniel lokal: Sichtprüfung beider Themes, F11, Neustart

**Dependencies:** Task 6
**Files:** `src/gui/theme.py`, `src/gui/main_window.py`, `src/gui/settings.py`, `src/gui/drop_zone.py`, `src/main.py`, `tests/test_theme.py`
**Scope:** S

---

### ✅ Checkpoint 3 (Daniel, Windows)

- [x] Manuelle Prüfung aller GUI-bezogenen Success Criteria aus `SPEC.md`
- [x] Review mit Daniel vor Phase 4

---

## Phase 4: Auslieferung

### Task 10: CI-Testschritt, PyInstaller-Build, README

**Description:** `ci.yml` um `uv run pytest -v` ergänzen (Word-Tests per Marker
ausgeschlossen). PyInstaller-Build so anpassen, dass pypdfium2- und pywin32-Binaries
enthalten sind. README um Nutzung, Optionen und Hinweis auf Word-Voraussetzung ergänzen,
CHANGELOG-Eintrag 0.1.0.

**Acceptance criteria:**

- [x] CI führt Lint + Tests aus und ist grün
- [x] `uv run build` → `dist/py-document-processor/py-document-processor.exe` startet und exportiert ein Dokument auf einem Rechner ohne Python
- [x] README beschreibt Bedienung, Optionen, Voraussetzungen; CHANGELOG aktualisiert *(CHANGELOG pflegt der post-commit-Hook automatisch)*

**Verification:**

- [x] CI-Lauf auf GitHub grün
- [x] Daniel lokal: Build + Exe-Test

**Dependencies:** Task 7, Task 8, Task 9
**Files:** `.github/workflows/ci.yml`, `src/build.py`, `README.md`, `tests/test_build.py`
**Scope:** S

---

### ✅ Checkpoint: Complete

- [x] Alle Success Criteria aus `SPEC.md` abgehakt
- [x] CI grün, Exe funktioniert
- [x] Abschluss-Review mit Daniel
