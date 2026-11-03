# BOBR – Datenmodell (Schema v0.8)
 
Gilt für `bobr_schema.sql` mit `PRAGMA user_version = 8`. Diagramm: `bobr_erd_v08.md`.
 
## Grundsätze
 
- **Eine `.bobr`-Datei = ein Projekt = eine geprüfte Arbeit.** Keine Nutzerverwaltung.
- **Jeder Upload ist eine eigene, gespeicherte Prüfung.** Uploads werden nicht zusammengeführt.
- **`reference`** = Quelle, wie der Autor sie angegeben hat. **`publication`** = Veröffentlichung, wie Crossref, OpenAlex usw. sie kennen.
- **JSON-Spalten** enthalten Literaturdaten im Format CSL-JSON. SQLite prüft nur, ob gültiges JSON vorliegt; den Inhalt prüft Python.
- **Abgeleitete Spalten** in `reference` setzt der Code an genau einer Stelle (Repository-Schicht) bei jeder Änderung von `data_current`. **Generierte Spalten** in `publication` berechnet SQLite selbst; sie sind nicht direkt beschreibbar.
- **Zeitstempel** sind Text im Format `YYYY-MM-DD HH:MM:SS` in UTC.
- **Pflicht bei jeder Verbindung:** `PRAGMA foreign_keys = ON`, sonst prüft SQLite keine Fremdschlüssel.
- **Nicht in der Projektdatei:** API-Cache, API-Nutzungszähler, Crossref-E-Mail und OpenAlex-Schlüssel (Nutzerordner bzw. Schlüsselspeicher des Systems).
Legende: **PK** Primärschlüssel, **FK** Fremdschlüssel, **UK** eindeutig, **✓** Pflichtfeld (NOT NULL).
 
---
 
## project – die geprüfte Arbeit
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| name | TEXT | ✓ | Projektname |
| created_at | TEXT | ✓ | Anlagezeitpunkt (automatisch) |
| citation_style | TEXT | | erwarteter Zitierstil, z. B. `apa`; NULL = keine Stilprüfung |
 
## involved_person – Beteiligte der geprüften Arbeit
 
Vom Nutzer eingegeben; Grundlage der Interessenkonflikt-Hinweise. Nicht die Autoren der zitierten Quellen.
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| project_id | INTEGER | FK ✓ | → `project` |
| name | TEXT | ✓ | z. B. `Müller, Hans`; Normalisierung für Vergleiche macht Python |
| orcid | TEXT | | optional; nur damit gelten Treffer als `confirmed`, sonst höchstens `possible` |
| role | TEXT | ✓ | `author`, `supervisor`, `reviewer`, `editor` |
 
## rule_setting – Prüfregeln pro Projekt an/aus
 
Nur Abweichungen vom Standard. Keine Zeile = Standard der Regel.
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| project_id | INTEGER | PK, FK | → `project` |
| rule_id | TEXT | PK | z. B. `V01_pflichtfelder`; gültige IDs prüft Python |
| enabled | INTEGER | ✓ | `1` an, `0` aus |
 
## upload – eine hochgeladene Literaturliste
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| project_id | INTEGER | FK ✓ | → `project` |
| file_name | TEXT | ✓ | ursprünglicher Dateiname |
| file_hash | TEXT | ✓ | Hash der Datei; Hinweis, wenn dieselbe Datei schon hochgeladen wurde |
| file_content | BLOB | ✓ | Originaldatei; Basis für den Export der korrigierten .bib (behält `@string`, Kommentare, Reihenfolge) und für erneutes Auslesen von PDFs |
| format | TEXT | ✓ | `bib`, `txt`, `pdf` |
| uploaded_at | TEXT | ✓ | Zeitpunkt des Uploads (automatisch) |
| last_check_started_at | TEXT | | Start der letzten Prüfung; NULL = nie geprüft |
| last_check_finished_at | TEXT | | Ende der letzten Prüfung; NULL bei gesetztem Start = abgebrochen |
| last_check_app_version | TEXT | | BOBR-Version der letzten Prüfung |
 
## reference – eine Quelle aus der Literaturliste
 
So, wie der Autor sie angegeben hat; kann Fehler enthalten.
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| upload_id | INTEGER | FK ✓ | → `upload` |
| position | INTEGER | ✓ | Reihenfolge in der Datei |
| citekey | TEXT | | BibTeX-Schlüssel; bei .txt/.pdf leer; doppelte Schlüssel erlaubt (werden als Befund gemeldet) |
| raw_text | TEXT | ✓ | Originaltext des Eintrags, nie verändert |
| data_original | JSON | ✓ | geparster Eintrag beim Upload, nie verändert |
| data_current | JSON | ✓ | aktueller Stand inkl. angenommener Korrekturen |
| reference_type | TEXT | | BibTeX-Typ wie in der Datei (`article`, `book` …); unbekannte Typen sind ein Befund |
| doi_norm | TEXT | | normalisierte DOI (abgeleitet) |
| title_norm | TEXT | | normalisierter Titel (abgeleitet) |
| year | INTEGER | | Jahr als Zahl (abgeleitet); `2015a` → 2015, `im Druck` → NULL |
| first_author_norm | TEXT | | normalisierter Nachname des Erstautors (abgeleitet) |
| publication_id | INTEGER | FK | → `publication`; NULL = keine Zuordnung |
| match_method | TEXT | | Art der Zuordnung: `doi`, `search`, `manual` |
| match_score | REAL | | Ähnlichkeit bei Zuordnung über Suche (0–1) |
| updated_at | TEXT | ✓ | letzte Änderung |
 
## publication – Veröffentlichung laut Datenbanken
 
Vergleichsdatensatz für die Korrektheitsprüfung und Knoten im Zitationsgraphen, auch für Veröffentlichungen außerhalb der Liste. Wird nur vom Code beim Abruf geschrieben.
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| doi_norm | TEXT | UK | normalisierte DOI; mehrfach NULL erlaubt |
| openalex_id | TEXT | UK | OpenAlex-ID der Veröffentlichung |
| data | JSON | | aus allen Quellen zusammengeführter Datensatz inkl. Autoren mit ORCID/OpenAlex-Autor-ID; bei Widersprüchen entscheidet eine feste Regel im Code |
| title | TEXT | | **generiert** aus `data` |
| year | INTEGER | | **generiert** aus `data` |
| sources | JSON | ✓ | Liste der Datenquellen, z. B. `["crossref","openalex"]` |
| fetched_at | TEXT | | letzter Abruf |
 
## publication_citation – Kante im Zitationsgraphen
 
Veröffentlichung A zitiert Veröffentlichung B, je Datenquelle eine Zeile. A → A ist gesperrt (Datenfehler der API; nicht zu verwechseln mit Selbstzitation A → B mit gleichem Autor).
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| citing_publication_id | INTEGER | PK, FK | → `publication` (zitierend) |
| cited_publication_id | INTEGER | PK, FK | → `publication` (zitiert) |
| source_api | TEXT | PK | `crossref`, `openalex`, `opencitations` |
| fetched_at | TEXT | ✓ | Abrufzeitpunkt |
 
## finding – ein Befund
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| upload_id | INTEGER | FK ✓ | → `upload` |
| rule_id | TEXT | ✓ | auslösende Regel |
| rule_version | INTEGER | ✓ | Version der Regel |
| category | TEXT | ✓ | `completeness`, `consistency`, `correctness`, `network` |
| severity | TEXT | ✓ | `info`, `warning`, `error` |
| field | TEXT | | betroffenes Hauptfeld, z. B. `year` |
| message | TEXT | ✓ | Meldungstext |
| old_value | TEXT | | Wert des Hauptfelds bei der Prüfung (Anzeige) |
| confidence | TEXT | ✓ | `confirmed`, `likely`, `possible` (Standard `confirmed`) |
| evidence | JSON | | Belege: Datenquelle, Score, URL … |
| fingerprint | TEXT | ✓, UK je Upload | Regel + Feld + IDs der betroffenen Quellen, z. B. `K05:year:17`; erkennt denselben Befund bei erneuter Prüfung |
| status | TEXT | ✓ | `open`, `accepted`, `rejected` (Standard `open`) |
| decided_at | TEXT | | Zeitpunkt der Entscheidung |
 
Bei erneuter Prüfung löscht der Code offene Befunde, die nicht mehr entstehen; angenommene und abgelehnte bleiben.
 
## finding_reference – betroffene Quellen eines Befunds
 
Meist eine Quelle; bei Dublette, Zyklus oder gegenseitiger Zitation mehrere.
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| finding_id | INTEGER | PK, FK | → `finding` |
| reference_id | INTEGER | PK, FK | → `reference` |
 
## suggestion – Korrekturvorschlag
 
| Spalte | Typ | | Bedeutung |
|---|---|---|---|
| id | INTEGER | PK | |
| finding_id | INTEGER | FK ✓ | → `finding` |
| rank | INTEGER | ✓ | Reihenfolge in der GUI, `1` = Empfehlung |
| changes | JSON | ✓ | Feld → neuer Wert, z. B. `{"year":"2015"}`; mehrere Felder möglich; `null` = Feld entfernen |
| previous_values | JSON | | beim Annehmen gesetzt: überschriebene Werte je Quelle, z. B. `{"17":{"year":"im Druck"}}`; für Rückgängig und „vorher/nachher“ |
| publication_id | INTEGER | FK | → `publication`; bei „Meinst du Veröffentlichung A oder B?“ |
| label | TEXT | | kurze Erklärung, z. B. `Druckjahr` |
| score | REAL | | Ähnlichkeit bei Suchtreffern |
| is_chosen | INTEGER | ✓ | `1` = gewählt; höchstens einer je Befund |
 
---
 
## Verknüpfungen
 
| Von | Nach | Kardinalität | Beim Löschen des Ziels |
|---|---|---|---|
| `involved_person.project_id` | `project` | n : 1 | wird mitgelöscht |
| `rule_setting.project_id` | `project` | n : 1 | wird mitgelöscht |
| `upload.project_id` | `project` | n : 1 | wird mitgelöscht |
| `reference.upload_id` | `upload` | n : 1 | wird mitgelöscht |
| `finding.upload_id` | `upload` | n : 1 | wird mitgelöscht |
| `reference.publication_id` | `publication` | n : 0..1 | wird NULL |
| `publication_citation.citing_publication_id` | `publication` | n : 1 | wird mitgelöscht |
| `publication_citation.cited_publication_id` | `publication` | n : 1 | wird mitgelöscht |
| `finding_reference.finding_id` | `finding` | n : 1 | wird mitgelöscht |
| `finding_reference.reference_id` | `reference` | n : 1 | wird mitgelöscht |
| `suggestion.finding_id` | `finding` | n : 1 | wird mitgelöscht |
| `suggestion.publication_id` | `publication` | n : 0..1 | wird NULL |
 
`finding` ↔ `reference` ist eine n : m-Beziehung über `finding_reference`. Dass jeder Befund mindestens eine Quelle betrifft, stellt der Code sicher (SQLite kann das nicht erzwingen).
 
**Löschketten:** Projekt löschen → alles im Projekt. Upload löschen → dessen Quellen, Befunde, Zuordnungen und Vorschläge; andere Uploads und alle `publication`-Zeilen bleiben.
