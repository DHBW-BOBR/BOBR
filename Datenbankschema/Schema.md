
# BOBR – Datenbankschema (ER-Diagramm, Version 0.8)

Entspricht `bobr_schema.sql` mit `PRAGMA user_version = 8`. GitHub stellt den Mermaid-Block direkt als Diagramm dar.

## Begriffe

| Tabelle | Bedeutung |
|---|---|
| `project` | eine geprüfte Arbeit (Paper, Abschlussarbeit, Antrag) = eine `.bobr`-Datei |
| `involved_person` | an der geprüften Arbeit beteiligte Person: Autor, Betreuer, Gutachter, Herausgeber (für Interessenkonflikt-Hinweise) |
| `rule_setting` | Prüfregel im Projekt an- oder abgeschaltet (keine Zeile = Standard der Regel) |
| `upload` | eine hochgeladene Literaturliste samt Originaldatei; jeder Upload ist eine eigene, gespeicherte Prüfung |
| `reference` | eine Quelle aus der Literaturliste, so wie der Autor sie angegeben hat |
| `publication` | die tatsächliche Veröffentlichung, so wie Crossref, OpenAlex usw. sie kennen |
| `publication_citation` | Veröffentlichung A zitiert Veröffentlichung B (Kante im Zitationsgraphen) |
| `finding` | ein Befund |
| `finding_reference` | welche Quellen ein Befund betrifft (meist eine, bei Dubletten oder Zyklen mehrere) |
| `suggestion` | ein Korrekturvorschlag; kann mehrere Felder ändern und lässt sich rückgängig machen |

erDiagram
  project ||--o{ involved_person : "involves"
  project ||--o{ rule_setting : "configures"
  project ||--o{ upload : "has"
  upload ||--o{ reference : "contains"
  upload ||--o{ finding : "has"
  reference }o--o| publication : "matched to"
  publication ||--o{ publication_citation : "cites"
  publication ||--o{ publication_citation : "is cited"
  finding ||--|{ finding_reference : "affects"
  reference ||--o{ finding_reference : "has finding"
  finding ||--o{ suggestion : "offers"
  publication |o--o{ suggestion : "candidate"
  project {
    int id PK
    text name "NOT NULL"
    text created_at "NOT NULL"
    text citation_style
  }
  involved_person {
    int id PK
    int project_id FK "NOT NULL"
    text name "NOT NULL"
    text orcid
    text role "NOT NULL; author, supervisor, reviewer, editor"
  }
  rule_setting {
    int project_id PK, FK "NOT NULL"
    text rule_id PK "NOT NULL"
    int enabled "NOT NULL; 0 or 1"
  }
  upload {
    int id PK
    int project_id FK "NOT NULL"
    text file_name "NOT NULL"
    text file_hash "NOT NULL"
    blob file_content "NOT NULL; original file"
    text format "NOT NULL; bib, txt, pdf"
    text uploaded_at "NOT NULL"
    text last_check_started_at
    text last_check_finished_at
    text last_check_app_version
  }
  reference {
    int id PK
    int upload_id FK "NOT NULL"
    int position "NOT NULL"
    text citekey
    text raw_text "NOT NULL; original entry"
    json data_original "NOT NULL; incl. authors as in the work"
    json data_current "NOT NULL; incl. corrections"
    text reference_type "BibTeX type"
    text doi_norm
    text title_norm
    int year
    text first_author_norm
    int publication_id FK
    text match_method
    real match_score
    text updated_at "NOT NULL"
  }
  publication {
    int id PK
    text doi_norm UK
    text openalex_id UK
    json data "merged, incl. authors"
    text title "generated from data"
    int year "generated from data"
    json sources "NOT NULL; e.g. crossref, openalex"
    text fetched_at
  }
  publication_citation {
    int citing_publication_id PK, FK "NOT NULL"
    int cited_publication_id PK, FK "NOT NULL"
    text source_api PK "NOT NULL"
    text fetched_at "NOT NULL"
  }
  finding {
    int id PK
    int upload_id FK "NOT NULL"
    text rule_id "NOT NULL"
    int rule_version "NOT NULL"
    text category "NOT NULL"
    text severity "NOT NULL"
    text field
    text message "NOT NULL"
    text old_value
    text confidence "NOT NULL; confirmed, likely, possible"
    json evidence
    text fingerprint UK "NOT NULL; unique per upload"
    text status "NOT NULL; open, accepted, rejected"
    text decided_at
  }
  finding_reference {
    int finding_id PK, FK "NOT NULL"
    int reference_id PK, FK "NOT NULL"
  }
  suggestion {
    int id PK
    int finding_id FK "NOT NULL"
    int rank "NOT NULL"
    json changes "NOT NULL; field and new value, null = remove"
    json previous_values "for undo"
    int publication_id FK
    text label
    real score
    int is_chosen "NOT NULL; max. one per finding"
  }
