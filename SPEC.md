# Spec: Word-Seiten als Bilder (MVP)

> Grundlage: [`docs/ideas/word-pages-to-images.md`](docs/ideas/word-pages-to-images.md)
> Status: **Entwurf – wartet auf Freigabe**

## Objective

Daniel (einziger Nutzer, Entwickler) bekommt 2–3× pro Woche Word-Dokumente von Kunden
oder Kollegen und braucht deren Seiten als einzelne Bilder (für Confluence, Slides,
Vorschau, KI/OCR). Heute geschieht das per Screenshot oder Umweg über PDF-Tools.

**Wir bauen:** eine PySide6-Desktop-App mit einer Drop-Zone. Word-Dateien hineinziehen →
jede Seite wird als Bild neben der Quelldatei gespeichert.

**Pipeline (zwei getrennte Schritte):**

1. `word_to_pdf` – Microsoft Word (per COM, eigene unsichtbare Instanz) exportiert das
   Dokument als temporäres PDF – **ohne Markup** (keine Änderungsverfolgung, keine Kommentare).
2. `pdf_to_images` – pypdfium2 rendert jede PDF-Seite als PNG oder JPG, optional plus
   Textdatei pro Seite.

Das PDF als Zwischenformat ist der Erweiterungspunkt für spätere Quellen (PPTX, XLSX, PDF)
und Ziele (Text, Merge/Split) – realisiert durch Funktionstrennung, **nicht** durch ein
Plugin-Framework.

### User Stories / Akzeptanzkriterien

1. **Seiten exportieren** – Als Nutzer ziehe ich eine oder mehrere Word-Dateien auf die
   Drop-Zone; für jede entsteht `<name>_pages/page_01.png … page_NN.png` neben der Quelle.
   - Seitenanzahl der Bilder == Seitenanzahl in Word.
   - Dateinamen sind nullgepolstert passend zur Seitenzahl (`page_01` bei < 100 Seiten,
     `page_001` ab 100).
   - Nach Abschluss öffnet sich der Ausgabeordner im Explorer (bei mehreren Dateien: der
     Ordner der letzten erfolgreich verarbeiteten).
2. **Originalgröße** – Standard ist 100 % = **150 DPI** (A4 → 1240 × 1754 px, ±1 px).
3. **Skalierung** – Ein Eingabefeld „Skalierung (%)“ (10–400 %, Standard 100 %) skaliert
   relativ zur Originalgröße. Effektive DPI = 150 × Skalierung / 100 (50 % → A4 620 × 877 px).
4. **Format** – Auswahl PNG (Standard) oder JPG (Qualität 90, fest).
5. **Text pro Seite** – Checkbox „Text pro Seite speichern“ (Standard: aus). Wenn aktiv,
   entsteht zusätzlich `page_NN.txt` (UTF-8) mit dem aus dem PDF extrahierten Text der Seite.
6. **Ohne Markup** – Änderungsverfolgung und Kommentare erscheinen nie im Bild; das Bild
   zeigt die Endfassung.
7. **Quelle unangetastet** – Die Quelldatei wird schreibgeschützt geöffnet und nie
   gespeichert; Änderungsdatum bleibt gleich.
8. **Kein Überschreiben** – Existiert `<name>_pages` bereits, wird `<name>_pages (2)`,
   `(3)` … angelegt.
9. **Fortschritt & Abbruch** – Fortschrittsanzeige (Datei x/y, Seite a/b) und Button
   „Abbrechen“; Abbruch greift nach der aktuellen Seite (Rendering) bzw. nach dem aktuellen
   Word-Export. Bereits erzeugte Bilder bleiben erhalten.
10. **Fehlerrobustheit** – Kennwortgeschützte, beschädigte oder nicht unterstützte Dateien
    erzeugen eine deutsche Fehlermeldung in der Statusliste; die übrigen Dateien werden
    weiter verarbeitet. Kein Word-Dialog bleibt hängen.
11. **Parallel zu eigenem Word** – Offene Word-Dokumente des Nutzers bleiben während und
    nach dem Export unberührt (eigene Instanz via `DispatchEx`, nur diese wird beendet).
12. **Nur lokal** – Keine Netzwerkzugriffe. Temporäres PDF liegt in einem `tempfile`-Ordner
    und wird immer gelöscht (auch bei Fehler/Abbruch). Keine Dokumentinhalte in Logs.

**Unterstützte Eingaben:** `.docx`, `.docm`, `.doc`, `.rtf` (alles, was Word öffnet;
andere Endungen → Hinweis „Dateityp wird nicht unterstützt“).

## Tech Stack

- Python ≥ 3.11 (wie `pyproject.toml`), Paketverwaltung ausschließlich **uv**
- **PySide6** – GUI (vorhanden)
- **pywin32** – Word-Automation per COM *(neu; Marker `sys_platform == 'win32'`)*
- **pypdfium2** – PDF-Seiten rendern + Text extrahieren *(neu; Apache-2.0/BSD – bewusst
  statt PyMuPDF wegen AGPL)*
- **Pillow** – Bild speichern (PNG/JPG); kommt als Abhängigkeit für `to_pil()` *(neu)*
- Dev: pytest, ruff, pyinstaller (vorhanden)

## Commands

```bash
uv sync --all-groups                 # Abhängigkeiten installieren
uv add pypdfium2 pillow "pywin32; sys_platform == 'win32'"   # einmalig (nach Freigabe)
uv run main                          # GUI starten
uv run pytest -v                     # Tests
uv run pytest -v -m word             # zusätzlich echte Word-Integrationstests (nur Windows+Word)
uv run ruff check .                  # Lint
uv run ruff format .                 # Formatieren
uv run build                         # PyInstaller-Build (dist/py-document-processor/)
```

## Project Structure

```text
src/
├── main.py                 → Einstiegspunkt: QApplication + MainWindow starten
├── core/                   → Fachlogik, keinerlei Qt-Import
│   ├── __init__.py
│   ├── options.py          → ExportOptions (Dataclass: scale_percent, image_format, save_text)
│   ├── word_to_pdf.py      → word_to_pdf(src: Path, dst_pdf: Path) -> None  (COM)
│   ├── pdf_to_images.py    → render_pages(pdf: Path, out_dir: Path, options, on_page, is_cancelled) -> list[Path]
│   ├── pipeline.py         → process_document(src, options, ...) -> Path (Temp-PDF, Ausgabeordner, Aufräumen)
│   └── errors.py           → DocumentError + Unterklassen mit deutscher Nutzer-Meldung
├── gui/
│   ├── __init__.py
│   ├── main_window.py      → Fenster, Optionen-Leiste, Statusliste, F11, QSettings
│   ├── drop_zone.py        → Drop-Zone-Widget (Drag & Drop + Klick → Dateidialog)
│   ├── worker.py           → QObject-Worker im QThread; Signale progress/file_done/failed/finished
│   └── theme.py            → Dark/Light-QSS
├── build.py, tools.py      → unverändert
tests/
├── fixtures/               → kleines Test-PDF mit Text (2 Seiten, A4)
├── test_pdf_to_images.py
├── test_pipeline.py        → word_to_pdf gemockt
├── test_output_dir.py      → Ordnerbenennung / Kein-Überschreiben
└── test_word_to_pdf.py     → @pytest.mark.word, nur Windows + Word
docs/ideas/                 → Ideen-One-Pager
SPEC.md                     → diese Datei
```

**Regel:** `src/core/` importiert nie Qt; `src/gui/` enthält keine Fachlogik.

## Code Style

Englischer Code/Kommentare, deutsche Nutzertexte, `pathlib`, Typ-Annotationen, Ruff (Zeilen­länge 100).

```python
BASE_DPI = 150
PDF_POINTS_PER_INCH = 72


class PasswordProtectedError(DocumentError):
    user_message = "Das Dokument ist kennwortgeschützt und kann nicht verarbeitet werden."


def render_pages(
    pdf_path: Path,
    out_dir: Path,
    options: ExportOptions,
    on_page: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] = lambda: False,
) -> list[Path]:
    """Render every page of a PDF to an image file and return the written paths."""
    scale = BASE_DPI * options.scale_percent / 100 / PDF_POINTS_PER_INCH
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        width = max(2, len(str(len(pdf))))
        written: list[Path] = []
        for index, page in enumerate(pdf, start=1):
            if is_cancelled():
                break
            target = out_dir / f"page_{index:0{width}d}.{options.image_format.extension}"
            page.render(scale=scale).to_pil().save(target, **options.image_format.save_kwargs)
            written.append(target)
            if on_page:
                on_page(index, len(pdf))
        return written
    finally:
        pdf.close()
```

## Testing Strategy

- **Framework:** pytest, Tests in `tests/`, Dateien `test_*.py`.
- **Unit (läuft überall, auch CI/Ubuntu):**
  - `pdf_to_images`: Seitenanzahl, Pixelmaße bei 100 % und 50 %, PNG vs. JPG, Textdateien,
    Nullpolsterung, Abbruch nach Seite n.
  - Ausgabeordner-Benennung inkl. `(2)`, `(3)`.
  - `pipeline`: mit gemocktem `word_to_pdf` (kopiert Fixture-PDF) → Temp-PDF wird in Erfolg,
    Fehler und Abbruch gelöscht; Fehler werden als `DocumentError` weitergereicht.
  - `ExportOptions`: Validierung 10–400 %.
- **Integration (`@pytest.mark.word`, nur lokal unter Windows mit Word, in CI übersprungen):**
  echte .docx mit Änderungsverfolgung + Kommentar → Bild ohne Markup (Textprüfung über
  Sidecar), kennwortgeschützte .docx → `PasswordProtectedError` ohne Hängen, Quelldatei-
  `mtime` unverändert.
- **GUI:** kein automatisierter Test im MVP; manuelle Checkliste (siehe Success Criteria).
- **Abdeckung:** `src/core/` ohne `word_to_pdf.py` ≥ 80 % Zeilenabdeckung (Richtwert,
  kein CI-Gate).
- CI (`ci.yml`) bekommt zusätzlich `uv run pytest -v` (Word-Tests per Marker ausgeschlossen).

## Boundaries

- **Always:**
  - Word nur über `DispatchEx` starten, `Visible = False`, `DisplayAlerts = 0`,
    Dokument `ReadOnly=True`, `AddToRecentFiles=False`; `Close(SaveChanges=0)` und `Quit()`
    stets im `finally`.
  - Makros in der Word-Instanz deaktivieren (`AutomationSecurity = msoAutomationSecurityForceDisable`),
    da die Dokumente von Kunden stammen.
  - `pythoncom.CoInitialize()` / `CoUninitialize()` im Worker-Thread.
  - Lange Arbeit nur im QThread-Worker; GUI-Updates nur über Signale.
  - Temp-Dateien über `tempfile`, Aufräumen im `finally`.
  - `uv run ruff check .` und `uv run pytest` grün vor jedem Commit.
- **Ask first:**
  - Weitere Abhängigkeiten über die drei oben genannten hinaus.
  - Änderungen an `ci.yml` über das Hinzufügen des Testschritts hinaus.
  - Neue Eingabeformate (PPTX, XLSX, PDF) oder neue Ausgabeziele.
  - Abweichung von der Ordner-/Dateinamenskonvention.
- **Never:**
  - Quelldokumente verändern oder speichern.
  - Die Word-Instanz des Nutzers (`Dispatch`/`GetActiveObject`) verwenden oder beenden.
  - Dokumentinhalte oder -texte loggen; Netzwerkzugriffe.
  - PyMuPDF oder andere AGPL-Bibliotheken einbinden.
  - Testdokumente mit echten Kunden-/Patientendaten ins Repo einchecken.

## Success Criteria

- [ ] 10-seitige A4-.docx → genau 10 PNGs à 1240 × 1754 px (±1 px) in `<name>_pages/`.
- [ ] Skalierung 50 % → 620 × 877 px; 200 % → 2480 × 3508 px.
- [ ] JPG-Auswahl erzeugt `.jpg`; Checkbox Text erzeugt `page_NN.txt` mit Seitentext.
- [ ] Dokument mit Änderungsverfolgung + Kommentaren → Bilder zeigen nur die Endfassung.
- [ ] Zweiter Export desselben Dokuments → `<name>_pages (2)`, erster Ordner unverändert.
- [ ] Während des Exports bleibt das Fenster bedienbar (verschiebbar, Abbrechen klickbar).
- [ ] Eigene offene Word-Dokumente bleiben offen und unverändert.
- [ ] Kennwortgeschützte Datei → deutsche Fehlermeldung, kein hängender WINWORD-Prozess,
      nächste Datei wird verarbeitet.
- [ ] Nach Lauf (Erfolg, Fehler, Abbruch) liegt kein Temp-PDF mehr im Temp-Ordner.
- [ ] Quelldatei: Änderungsdatum unverändert.
- [ ] Dark/Light-Theme, F11-Vollbild, Fenstergeometrie wird über Neustart gemerkt.
- [ ] `uv run ruff check .` und `uv run pytest` grün; CI grün.
- [ ] `uv run build` erzeugt eine lauffähige .exe, die einen Export durchführt.

## Open Questions

1. **Hängende Word-Instanz:** Ein blockierender COM-Aufruf lässt sich nicht sauber
   abbrechen. Vorschlag: Timeout von 120 s pro Dokument; danach wird der von uns gestartete
   `WINWORD.EXE`-Prozess (PID per Fenster-Handle ermittelt) beendet. Akzeptabel, oder reicht
   im MVP „Abbrechen greift nach dem Word-Export“ ohne Timeout?
2. **Text-Checkbox:** Standard „aus“ angenommen – passt das?
3. **Einstellungen merken:** Sollen Skalierung, Format und Text-Checkbox über Neustarts
   hinweg gespeichert werden (QSettings)? Angenommen: ja.
