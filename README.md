# BOBR – Back-check Of Bibliographic Records

> Open-Source-Werkzeug mit grafischer Oberfläche, das Literaturverzeichnisse auf formale Vollständigkeit, Konsistenz und Korrektheit prüft und Korrekturvorschläge macht.

**Status:** Konzeptionsphase

---

## Problemstellung

In Forschungsprojekten, wissenschaftlichen und studentischen Arbeiten sowie Forschungsanträgen kommen durch manuelle und (teil-)automatisierte Recherche schnell große Mengen an Quellen zusammen. Editoren, Gutachter und Autoren stehen dann vor der Frage, wie sich solche Literaturlisten effizient auf formale Vollständigkeit, Konsistenz und Korrektheit prüfen und korrigieren lassen.

Bestehende Tools wie [GROBID](https://github.com/kermitt2/grobid) decken nur Teile dieses Prozesses ab. Andere Lösungen sind kostenpflichtig oder für nicht-technische Anwender zu komplex.

## Ziel

BOBR soll bibliographische Daten einlesen, prüfen und dem Nutzer verständliche Korrekturvorschläge liefern, und zwar über eine einfache grafische Oberfläche.

## Funktionsumfang (geplant)

**Kernfunktionen**

- Import von Literaturdaten aus `.txt`, `.pdf` und `.bib`
- Prüfung auf **Vollständigkeit**, z. B. fehlende Pflichtangaben
- Prüfung auf **Konsistenz**, z. B. einheitliche Schreibweisen und Formate
- Prüfung auf **Korrektheit** der Angaben
- Korrekturvorschläge, übersichtlich für den Nutzer aufbereitet
- Grafische Oberfläche, die auch ohne technische Vorkenntnisse bedienbar ist

**Erweiterungen (wenn möglich)**

- Erkennen, welche der verwendeten Quellen sich gegenseitig zitieren
- Verknüpfungen zwischen Quellen, Autoren und Gutachtern prüfen und mögliche Interessenkonflikte aufzeigen

**Nicht Teil des Projekts**

- Inhaltliche Prüfung, also ob eine Aussage tatsächlich durch die zitierte Quelle belegt wird

## Ablauf (Konzept)

```mermaid
flowchart LR
    A["Import<br/>.txt / .pdf / .bib"] --> B["Einträge erkennen<br/>und strukturieren"]
    B --> C["Prüfung<br/>Vollständigkeit · Konsistenz · Korrektheit"]
    C --> D["Korrekturvorschläge"]
    D --> E["Ausgabe an<br/>den Nutzer"]
```

## Installation

Folgt mit dem ersten Release. Geplant sind fertige Programme für **Windows** und **macOS** zum Download unter [Releases](../../releases).

## Technologie

| Bereich | Technologie | Begründung |
|---------|-------------|------------|
| Sprache | Python | Vorgabe (RB4) |
| GUI | PyQt6 | Plattformübergreifend (Windows + macOS), aktiv gepflegt |
| Datenbank | Neo4j Community Edition (GPL v3) | Graphdatenbank für Zitiernetzwerk und Beziehungen zwischen Quellen |
| BibTeX-Import | bibtexparser | Etablierte Python-Bibliothek für .bib-Dateien |
| PDF-Import | pdfplumber | Zuverlässige Textextraktion aus PDFs |
| Tests | pytest | Standard-Testframework für Python |
| Linting | black + flake8 | Einheitliche Codeformatierung im Team |

> **Voraussetzung:** Neo4j Community Edition muss lokal installiert sein bevor die Anwendung gestartet wird. Download unter [neo4j.com/download](https://neo4j.com/download/).

## Projektstruktur

```
BOBR/
├── src/
│   ├── main.py                  # Einstiegspunkt der Anwendung
│   ├── model/                   # Daten, Importlogik, Validierung, Datenbankzugriff
│   │   ├── literature.py        # Datenmodell für Literatureinträge
│   │   ├── importer/            # Datei-Import (.bib, .txt, .pdf)
│   │   │   ├── bib_importer.py
│   │   │   ├── txt_importer.py
│   │   │   └── pdf_importer.py
│   │   ├── validator/           # Prüflogik (Vollständigkeit, Konsistenz, Korrektheit)
│   │   │   ├── completeness.py
│   │   │   ├── consistency.py
│   │   │   └── correctness.py
│   │   └── database/            # Neo4j-Datenbankanbindung
│   │       └── db.py
│   ├── view/                    # GUI-Komponenten (PyQt6)
│   │   ├── main_window.py
│   │   ├── import_view.py
│   │   └── results_view.py
│   └── controller/              # Steuerung des Ablaufs zwischen Model und View
│       ├── app_controller.py
│       ├── import_controller.py
│       ├── validator_controller.py
│       └── correction_controller.py
├── tests/                       # Unit- und Integrationstests (pytest)
├── docs/                        # Anforderungen und Architekturdokumente
├── .gitignore
└── requirements.txt
```

## Projektorganisation

- **Aufgaben und Fortschritt:** GitHub Projects → [Projektboard](LINK-ZUM-BOARD)
- **Fehler, Ideen, Fragen:** über [Issues](../../issues)

## Meilensteine

| Zeitpunkt | Meilenstein |
|---|---|
| Ende 5. Semester | Zwischenpräsentation |
| Ende 6. Semester | Abschlusspräsentation und Abgabe der schriftlichen Ausarbeitung |

## Projektkontext

Studentisches Projekt im Studiengang Wirtschaftsinformatik – Business Engineering an der [DHBW Ravensburg](https://www.dhbw-ravensburg.de) (Kurse WWIBE124 und WWIBE224).

- **Auftraggeber:** Prof. Dr. Martin Zaefferer

## Lizenz

BOBR wird als Open-Source-Software veröffentlicht. Die konkrete Lizenz wird mit dem Auftraggeber abgestimmt.


---

# Gefundene Tools

Für den Graphen:
https://networkx.org/documentation/stable/auto_examples/index.html



---

Vereinfachungen im Bild: `fingerprint` ist nur innerhalb eines Projekts eindeutig (Index auf `project_id` + `fingerprint`); die Beziehung `import_file` → `entry` steht für die beiden Spalten `first_import_id` und `last_import_id`.
 
```mermaid
erDiagram
  project ||--o{ import_file : "hat"
  project ||--o{ entry : "enthaelt"
  import_file ||--o{ entry : "erstmals / zuletzt"
  entry }o--o| work : "abgeglichen mit"
  work ||--o{ work_author : "hat"
  person ||--o{ work_author : "ist"
  work ||--o{ citation : "zitiert"
  work ||--o{ citation : "wird zitiert"
  project ||--o{ project_person : "kennt"
  person ||--o{ project_person : "hat Rolle"
  project ||--o{ check_run : "hat"
  entry ||--o{ check_state : "geprueft durch"
  project ||--o{ finding : "hat"
  check_run |o--o{ finding : "erzeugt"
  finding ||--|{ finding_entry : "betrifft"
  entry ||--o{ finding_entry : "hat Befund"
  finding ||--o{ suggestion : "bietet an"
  work |o--o{ suggestion : "Kandidat"
  project {
    int id PK
    text name
    json settings
  }
  import_file {
    int id PK
    int project_id FK
    text file_name
    text file_hash
    text format "bib, txt, pdf"
  }
  entry {
    int id PK
    int project_id FK
    int first_import_id FK
    int last_import_id FK
    text removed_at "nicht mehr in Datei"
    text citekey
    text raw_text "Original"
    json data_original
    json data_current
    text doi_norm
    text title_norm
    int year
    text first_author_norm
    text content_hash
    int work_id FK
    text match_method
  }
  work {
    int id PK
    text doi_norm UK
    text openalex_id UK
    text title
    int year
    json data "Referenzdatensatz"
    text fetched_from
  }
  person {
    int id PK
    text display_name
    text name_norm
    text orcid UK
    text openalex_id UK
  }
  work_author {
    int work_id PK, FK
    int position PK
    int person_id FK
  }
  citation {
    int citing_work_id PK, FK
    int cited_work_id PK, FK
    text source_api PK
  }
  project_person {
    int project_id PK, FK
    int person_id PK, FK
    text role PK "Autor, Gutachter, Editor"
  }
  check_run {
    int id PK
    int project_id FK
    text app_version
  }
  check_state {
    int entry_id PK, FK
    text rule_id PK
    int rule_version
    text input_hash
  }
  finding {
    int id PK
    int project_id FK
    int check_run_id FK
    text rule_id
    text category
    text severity
    text confidence "confirmed, likely, possible"
    text field
    text old_value
    json evidence
    text fingerprint UK
    text status
  }
  finding_entry {
    int finding_id PK, FK
    int entry_id PK, FK
  }
  suggestion {
    int id PK
    int finding_id FK
    int rank
    text new_value
    int work_id FK
    text label
    real score
    int is_chosen "max. einer je Befund"
  }
```
 
