# Implementation Plan: Word-Seiten als Bilder (MVP)

> Grundlage: [`SPEC.md`](../SPEC.md) (freigegeben 2026-10-30) · Tasks: [`tasks/todo.md`](todo.md)
> Status: **Abgeschlossen (2026-10-30)** – alle Tasks und Checkpoints erledigt

## Overview

PySide6-App mit Drop-Zone: Word-Dateien → temporäres PDF (Word per COM, ohne Markup) →
Seitenbilder (pypdfium2) neben der Quelle. Umsetzung in vier Phasen: zuerst die beiden
Pipeline-Schritte einzeln (inkl. des riskantesten Teils, Word-COM), dann deren
Orchestrierung samt Timeout, dann die GUI als vertikale Scheibe, zuletzt CI und Build.

## Architecture Decisions

- **`src/core/` ist Qt-frei.** Fortschritt und Abbruch laufen über einfache Callbacks
  (`on_page`, `is_cancelled`); der GUI-Worker übersetzt sie in Qt-Signale. Damit ist die
  gesamte Fachlogik ohne GUI testbar.
- **Word-Risiko zuerst.** `word_to_pdf` kommt direkt nach dem Fundament, damit
  COM-Überraschungen (Dialoge, Markup-Einstellungen, Kennwortdateien) früh auffallen.
- **Word-Tests nur lokal.** COM-Code wird in CI nicht ausgeführt (Ubuntu); echte Tests
  laufen mit `-m word` auf Daniels Rechner. Die Pipeline wird mit gemocktem `word_to_pdf`
  getestet.
- **Timeout als eigener Task.** Watchdog + gezieltes Beenden des eigenen `WINWORD.EXE` ist
  die heikelste Logik und wird getrennt vom Grund-Export gebaut, damit dieser zuerst stabil
  ist.
- **Test-Fixture-PDF wird einmalig generiert und eingecheckt** (2 Seiten A4 mit bekanntem
  Text, keine echten Daten). Generator-Skript liegt daneben, damit es reproduzierbar bleibt.
- **Ein Worker-Thread pro Lauf**, Dateien sequenziell. Keine Parallelisierung im MVP.

## Dependency Graph

```text
T1 Fundament (deps, options, errors)
 ├── T2 pdf_to_images ───────────┐
 └── T3 word_to_pdf (COM) ──┐    │
                            ├── T4 pipeline (Ordner, Temp-PDF)
                            └── T5 Word-Timeout
                                     │
                     T6 GUI-Scheibe: Drop → Export → Ordner öffnen
                      ├── T7 Optionen + Persistenz
                      ├── T8 Fortschritt, Abbruch, Statusliste
                      └── T9 Theme, F11, Fenstergeometrie
                                     │
                     T10 CI-Tests, PyInstaller-Build, README
```

## Task List

### Phase 1: Pipeline-Bausteine

- [x] Task 1: Fundament – Abhängigkeiten, `ExportOptions`, Fehlerklassen
- [x] Task 2: `pdf_to_images` – Seiten rendern, Text extrahieren, Abbruch
- [x] Task 3: `word_to_pdf` – Word-COM-Export ohne Markup

### Checkpoint 1 (Daniel, Windows)

- [x] `uv run pytest -v -m word` grün auf Daniels Rechner
- [x] Markup-Dokument → PDF zeigt nur Endfassung; eigenes offenes Word unberührt

### Phase 2: Orchestrierung

- [x] Task 4: `pipeline.process_document` – Ausgabeordner, Temp-PDF, Aufräumen
- [x] Task 5: Word-Timeout (120 s) mit Beenden der eigenen Word-Instanz

### Checkpoint 2

- [x] `uv run pytest -v` grün (inkl. `-m word` lokal)
- [x] Smoke-Test ohne GUI: `uv run python -m src.core.pipeline <datei.docx>` erzeugt Bilder

### Phase 3: GUI

- [x] Task 6: GUI-Scheibe – Drop-Zone → Export im Worker → Ordner öffnen
- [x] Task 7: Optionsleiste (Skalierung, Format, Text) + Persistenz
- [x] Task 8: Fortschritt, Abbrechen, Statusliste mit Fehlern
- [x] Task 9: Dark/Light-Theme, F11, Fenstergeometrie

### Checkpoint 3 (Daniel, Windows)

- [x] Manuelle GUI-Checkliste aus SPEC → Success Criteria vollständig abgehakt

### Phase 4: Auslieferung

- [x] Task 10: CI-Testschritt, PyInstaller-Build, README

### Checkpoint: Complete

- [x] Alle Success Criteria aus `SPEC.md` erfüllt
- [x] CI grün, `.exe` führt einen Export durch
- [x] Review mit Daniel

## Parallelisierung

T2 und T3 sind unabhängig (nach T1). T7, T8 und T9 sind nach T6 weitgehend unabhängig,
berühren aber alle `main_window.py` – daher sequenziell umsetzen, um Konflikte zu vermeiden.

## Risks and Mitigations

| Risiko | Impact | Mitigation |
| --- | --- | --- |
| Word zeigt trotz `DisplayAlerts=0` modale Dialoge (Konvertierung, Reparatur, Kennwort) und blockiert | Hoch | `ConfirmConversions=False`, `OpenAndRepair=False`, `NoEncodingDialog=True`, `PasswordDocument="#invalid#"` (Kennwortdatei wirft Fehler statt Dialog); als letzte Linie T5-Timeout |
| Markup-Ausblendung greift nicht zuverlässig (Ansichtseinstellungen pro Dokument) | Hoch | `ShowRevisionsAndComments=False`, `RevisionsView=wdRevisionsViewFinal` auf dem Fenster der eigenen Instanz setzen; Integrationstest mit Markup-Dokument + Textprüfung |
| PID der eigenen Word-Instanz nicht ermittelbar → falscher Prozess beendet | Hoch | PID über Fenster-Handle (`win32process.GetWindowThreadProcessId`); wenn nicht ermittelbar: **nicht** beenden, nur Fehler melden. Nie per Prozessname killen |
| CI ohne Windows/Word | Mittel | `word`-Marker, Import von `win32com` lazy innerhalb der Funktion |
| PyInstaller findet pywin32/pypdfium2-Binaries nicht | Mittel | Build früh in T10 prüfen; ggf. `--collect-all pypdfium2`, `--hidden-import win32timezone` |
| Große Dokumente / hohe Skalierung → Speicher | Niedrig | Seiten einzeln rendern und sofort speichern (kein Sammeln im RAM); Obergrenze 400 % |
| Seitenzahl PDF ≠ Seitenzahl Word | Niedrig | Word erzeugt das PDF selbst – identische Paginierung; Integrationstest vergleicht mit `ComputeStatistics(wdStatisticPages)` |

## Open Questions

– keine –
