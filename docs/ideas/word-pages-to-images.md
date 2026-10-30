# py-document-processor: Word-Seiten als Bilder (MVP)

## Problem Statement

Wie könnten wir die Seiten eines Word-Dokuments mit einem Drag & Drop in genau
das Bildformat bringen, das das Ziel (Confluence, Slides, Vorschau, KI) braucht,
ohne Screenshots, manuelles Konvertieren oder Online-Tools?

## Recommended Direction

Eine PySide6-App mit einer einzigen Drop-Zone und einer Preset-Auswahl darüber.
Intern läuft eine zweistufige Pipeline: (1) Word rendert per COM (DispatchEx,
unsichtbare eigene Instanz) die .docx zu einem temporären PDF, das garantiert
layouttreu ist. (2) pypdfium2 rendert jede PDF-Seite gemäß Preset zu PNG/JPG.

Das PDF ist der Dreh- und Angelpunkt: Jede spätere Quelle (PPTX, XLSX, PDF selbst)
braucht nur einen neuen `to_pdf`-Schritt, jedes spätere Ziel (Text, Merge/Split)
nur einen neuen Schritt danach. Diese Erweiterbarkeit entsteht durch saubere
Funktionstrennung, nicht durch ein Plugin-Framework.

Presets ersetzen Optionen: Der Nutzer wählt *wofür*, nicht *wie*. Die
Preset-Werte liegen in einer kleinen, editierbaren Config.

## Decisions

- **Export immer ohne Markup:** Änderungsverfolgung und Kommentare werden beim
  PDF-Export ausgeblendet (`ExportAsFixedFormat` mit `wdExportDocumentContent`,
  Revisionen nicht angezeigt). Ergebnis ist stets die saubere Endfassung. Die
  Quelldatei wird schreibgeschützt geöffnet und nie verändert. Eine Option
  „mit Markup“ kommt erst bei konkretem Bedarf.

## Key Assumptions to Validate

- [ ] Word-COM läuft stabil unsichtbar im QThread, auch neben einer offenen
      Word-Instanz. Test: Export starten, während eigene Dokumente in Word offen sind.
- [ ] Problemdokumente blockieren nicht. Test: geschützte Ansicht, Kennwort-Doc,
      beschädigte .docx mit Timeout → saubere deutsche Fehlermeldung.
- [ ] Preset-Werte passen zu den echten Zielen. Test: je ein Export in
      Confluence/Slides einfügen und Schärfe/Größe beurteilen.
- [ ] pypdfium2 + pywin32 lassen sich mit PyInstaller bündeln. Test: `uv run build`
      früh im Projekt, nicht am Ende.

## MVP Scope

**Drin:**

- Drop-Zone (eine oder mehrere .docx), Preset-Dropdown, Fortschrittsanzeige
- 4 Presets: Confluence, Slides, Thumbnail, KI (PNG + `page_XX.txt`)
- Ausgabe in `<dokument>_pages/page_01.png …` neben der Quelle, danach Ordner öffnen
- Worker-Thread, Dark/Light, F11, Fenstergeometrie in QSettings (Repo-Regeln)
- Tests für den Render-Schritt (PDF → Bilder) mit einem Fixture-PDF; der COM-Schritt
  wird hinter einer Funktion gekapselt und im Test gemockt

**Draußen:** siehe unten.

## Not Doing (and Why)

- **Weitere Quellformate (PPTX, XLSX, PDF-Input)**: Die Pipeline ist dafür vorbereitet,
  aber erst bauen, wenn der Bedarf echt auftritt.
- **Inhalte extrahieren, Merge/Split**: eigene Anwendungsfälle mit eigener UX, kommen
  nach dem MVP.
- **Plugin-/Registry-Architektur**: YAGNI bei einer Quelle und einem Ziel.
- **LibreOffice-Fallback**: Word ist überall vorhanden, also bringt das nur
  Komplexität und schlechteres Layout.
- **Seitenauswahl, Zuschneiden, Viewer**: der größte Scope-Creep-Magnet.
- **Explorer-Kontextmenü, Ordner-Watcher**: erst wenn die Häufigkeit es rechtfertigt.
- **PyMuPDF**: wegen der AGPL-Lizenz, pypdfium2 leistet dasselbe.

## Open Questions

- Wie oft tritt der Fall auf (täglich / wöchentlich / selten)? Davon hängt ab, ob
  Batch und Kontextmenü später Priorität bekommen.
- Woher stammen die Word-Dokumente (Handbücher, Release Notes, Schulungsunterlagen)?
  Sie könnten konkretere Presets liefern.
- Was sind die tatsächlichen Zielmaße für Confluence und Slides bei euch?
