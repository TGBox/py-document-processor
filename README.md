# py-document-processor

Desktop-App (PySide6), die die Seiten von Word-Dokumenten als einzelne Bilder exportiert –
z. B. für Confluence, Präsentationen, Vorschauen oder die Weitergabe an KI/OCR.

Word-Datei ins Fenster ziehen → neben der Datei entsteht `<name>_pages/` mit
`page_01.png`, `page_02.png`, … Die Verarbeitung läuft vollständig lokal.

## Voraussetzungen

- Windows mit installiertem **Microsoft Word** (übernimmt das seitengenaue Rendern)
- Für die Entwicklung: Python 3.11+ und [uv](https://docs.astral.sh/uv/)

## Bedienung

1. App starten (`uv run main` oder `py-document-processor.exe`).
2. Optionen wählen:
   - **Skalierung** (10–400 %) – 100 % entspricht 150 DPI, eine A4-Seite wird 1240 × 1754 Pixel groß.
   - **Format** – PNG (verlustfrei) oder JPG (Qualität 90, kleinere Dateien).
   - **Text pro Seite speichern** – legt zusätzlich `page_NN.txt` (UTF-8) mit dem Seitentext an.
3. Eine oder mehrere Dateien (`.docx`, `.docm`, `.doc`, `.rtf`) auf die Fläche ziehen oder
   die Fläche anklicken und Dateien auswählen.
4. Fortschritt verfolgen; **Abbrechen** stoppt nach der aktuellen Seite bzw. dem aktuellen
   Word-Export – bereits erzeugte Bilder bleiben erhalten.
5. Nach Abschluss öffnet sich der Ausgabeordner. In der Statusliste öffnet ein Doppelklick auf
   eine erfolgreiche Zeile den jeweiligen Ordner.

**Ansicht-Menü:** Design (System / Hell / Dunkel), Vollbild mit **F11** (verlassen mit F11 oder Esc).
Optionen, Design sowie Fenstergröße und -position werden beim nächsten Start wiederhergestellt.

### Verhalten im Detail

- Änderungsverfolgung und Kommentare erscheinen **nie** im Bild – exportiert wird die Endfassung.
- Die Quelldatei wird schreibgeschützt geöffnet und nie verändert; Makros sind deaktiviert.
- Für den Export startet die App eine **eigene, unsichtbare** Word-Instanz – eigene offene
  Word-Dokumente bleiben unberührt.
- Existiert `<name>_pages/` bereits, wird `<name>_pages (2)`, `(3)` … angelegt; nichts wird überschrieben.
- Kennwortgeschützte oder beschädigte Dateien werden mit einer Meldung übersprungen, die
  übrigen Dateien weiter verarbeitet.
- Reagiert Word 120 Sekunden lang nicht, wird nur die von der App gestartete Word-Instanz
  beendet und die Datei als fehlgeschlagen markiert.

## Entwicklung

```bash
uv sync --all-groups

uv run main                                   # GUI starten
uv run python -m src.core.pipeline <datei>    # Export ohne GUI (Smoke-Test)

uv run pytest -v                              # Tests (ohne Word)
uv run pytest -v -m word                      # zusätzlich echte Word-Tests (nur Windows + Word)

uv run ruff check .                           # Lint
uv run ruff format .                          # Formatieren

uv run build                                  # Standalone-App → dist/py-document-processor/
```

Die CI (GitHub Actions, Ubuntu) führt Lint und alle Tests außer den Word-Integrationstests aus.
Das Test-PDF `tests/fixtures/sample.pdf` lässt sich mit
`uv run --with reportlab python tests/fixtures/make_sample_pdf.py` neu erzeugen.

## Projektstruktur

```
src/
├── main.py              Einstiegspunkt der GUI
├── build.py             PyInstaller-Build
├── core/                Fachlogik, ohne Qt
│   ├── options.py       ExportOptions (Skalierung, Format, Text)
│   ├── errors.py        Fehlerklassen mit deutschen Meldungen
│   ├── word_to_pdf.py   Word (COM) → PDF ohne Markup, mit Timeout
│   ├── pdf_to_images.py PDF-Seiten → PNG/JPG (+ Text) mit pypdfium2
│   └── pipeline.py      Ablauf pro Dokument, Ausgabeordner, Aufräumen
└── gui/                 PySide6-Oberfläche, ohne Fachlogik
    ├── main_window.py   Hauptfenster, Ansicht-Menü
    ├── drop_zone.py     Drag-&-Drop-Fläche
    ├── options_bar.py   Optionsleiste
    ├── worker.py        Hintergrundverarbeitung im QThread
    ├── progress.py      Fortschrittsberechnung
    ├── status_list.py   Ergebnis pro Datei
    ├── settings.py      Persistenz über QSettings
    └── theme.py         Hell/Dunkel-Paletten und Stylesheet
tests/                   pytest; fixtures/ enthält nur synthetische Testdokumente
SPEC.md                  Spezifikation
tasks/                   Umsetzungsplan und Aufgabenliste
docs/ideas/              Ideen-One-Pager
```

## Lizenzen der Abhängigkeiten

PySide6 (LGPL), pypdfium2 (Apache-2.0 / BSD-3), Pillow (MIT-CMU), pywin32 (PSF). Bewusst
**kein** PyMuPDF (AGPL).
