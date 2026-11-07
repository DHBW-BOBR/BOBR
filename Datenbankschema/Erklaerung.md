# BOBR – Data Model Explanation
  
## Principles

- **One `.bobr` file = one project = one work under review.** No user management.
- **Each upload is a separate, saved check.** Uploads are not merged.
- **`reference`** = a source as the author cited it. **`publication`** = a publication as Crossref, OpenAlex etc. know it.
- **JSON columns:** `reference.data_original`, `reference.data_current` and `publication.data` hold bibliographic data in CSL-JSON format; the other JSON columns (e.g. `sources`, `evidence`, `changes`) hold simple lists or objects. SQLite only checks that the JSON is valid (`CHECK (json_valid(column))`); Python checks the content.
- **Derived columns** in `reference` are set by the code in exactly one place (repository layer) whenever `data_current` changes. **Generated columns** in `publication` are computed by SQLite itself; they cannot be written directly.
- **Timestamps** are text in the format `YYYY-MM-DD HH:MM:SS`, in UTC.
- **Required on every connection:** `PRAGMA foreign_keys = ON`; otherwise SQLite does not check foreign keys.
- **Not stored in the project file:** API cache, API usage counters, Crossref e-mail address and OpenAlex key (user folder or the operating system's credential store).

Legend: **PK** primary key, **FK** foreign key, **UK** unique, **NOT NULL** required field.
 
---
 
## project – the work under review
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| name | TEXT | NOT NULL | Project name |
| created_at | TEXT | NOT NULL | Creation timestamp (set automatically) |
| citation_style | TEXT | | Expected citation style, e.g. `apa`; NULL = no style check |
 
## involved_person – people involved in the work under review
 
Entered by the user; basis for the conflict-of-interest notes. Not the authors of the cited sources.
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| project_id | INTEGER | FK, NOT NULL | → `project` |
| name | TEXT | NOT NULL | e.g. `Müller, Hans`; normalization for comparisons is done in Python |
| orcid | TEXT | | Optional; only with an ORCID can matches count as `confirmed`, otherwise at most `possible` |
| role | TEXT | NOT NULL | `author`, `supervisor`, `reviewer`, `editor` |
 
## rule_setting – check rules switched on/off per project
 
Only deviations from the default. No row = the rule's default applies.
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| project_id | INTEGER | PK, FK, NOT NULL | → `project` |
| rule_id | TEXT | PK, NOT NULL | e.g. `V01_required_fields`; valid IDs are checked in Python |
| enabled | INTEGER | NOT NULL | `1` on, `0` off |
 
## upload – an uploaded reference list
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| project_id | INTEGER | FK, NOT NULL | → `project` |
| file_name | TEXT | NOT NULL | Original file name |
| file_hash | TEXT | NOT NULL | Hash of the file; shows a notice if the same file has already been uploaded |
| file_content | BLOB | NOT NULL | Original file; basis for exporting the corrected .bib (keeps `@string`, comments, order) and for re-parsing PDFs |
| format | TEXT | NOT NULL | `bib`, `txt`, `pdf` |
| uploaded_at | TEXT | NOT NULL | Upload timestamp (set automatically) |
| last_check_started_at | TEXT | | Start of the last check; NULL = never checked |
| last_check_finished_at | TEXT | | End of the last check; NULL while the start is set = aborted |
| last_check_app_version | TEXT | | BOBR version used for the last check |
 
## reference – a source from the reference list
 
As given by the author; may contain errors.
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| upload_id | INTEGER | FK, NOT NULL | → `upload` |
| position | INTEGER | NOT NULL | Order in the file |
| citekey | TEXT | | BibTeX key; empty for .txt/.pdf; duplicate keys allowed (reported as a finding) |
| raw_text | TEXT | NOT NULL | Original text of the entry, never changed |
| data_original | JSON | NOT NULL | Entry as parsed at upload, never changed |
| data_current | JSON | NOT NULL | Current state incl. accepted corrections |
| reference_type | TEXT | | BibTeX type as in the file (`article`, `book` …); unknown types are a finding |
| doi_norm | TEXT | | Normalized DOI (derived) |
| title_norm | TEXT | | Normalized title (derived) |
| year | INTEGER | | Year as a number (derived); `2015a` → 2015, `in press` → NULL |
| first_author_norm | TEXT | | Normalized surname of the first author (derived) |
| publication_id | INTEGER | FK | → `publication`; NULL = not matched |
| match_method | TEXT | | How it was matched: `doi`, `search`, `manual` |
| match_score | REAL | | Similarity when matched via search (0–1) |
| updated_at | TEXT | NOT NULL | Last change |
 
## publication – publication according to the databases
 
Reference record for the correctness check and node in the citation graph, also for publications outside the list. Written only by the code when fetching data.
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| doi_norm | TEXT | UK | Normalized DOI; multiple NULLs allowed |
| openalex_id | TEXT | UK | OpenAlex ID of the publication |
| data | JSON | | Record merged from all sources incl. authors with ORCID/OpenAlex author ID; conflicts are resolved by a fixed rule in the code |
| title | TEXT | | **Generated** from `data` |
| year | INTEGER | | **Generated** from `data` |
| sources | JSON | NOT NULL | List of data sources, e.g. `["crossref","openalex"]` |
| fetched_at | TEXT | | Last fetch |
 
## publication_citation – edge in the citation graph
 
Publication A cites publication B, one row per data source. A → A is blocked (a data error from the API; not to be confused with self-citation A → B by the same author).
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| citing_publication_id | INTEGER | PK, FK, NOT NULL | → `publication` (citing) |
| cited_publication_id | INTEGER | PK, FK, NOT NULL | → `publication` (cited) |
| source_api | TEXT | PK, NOT NULL | `crossref`, `openalex`, `opencitations` |
| fetched_at | TEXT | NOT NULL | Fetch timestamp |
 
## finding – a finding
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| upload_id | INTEGER | FK, NOT NULL | → `upload` |
| rule_id | TEXT | NOT NULL | Rule that raised the finding |
| rule_version | INTEGER | NOT NULL | Version of the rule |
| category | TEXT | NOT NULL | `completeness`, `consistency`, `correctness`, `network` |
| severity | TEXT | NOT NULL | `info`, `warning`, `error` |
| field | TEXT | | Main field affected, e.g. `year` |
| message | TEXT | NOT NULL | Message text |
| old_value | TEXT | | Value of the main field at check time (for display) |
| confidence | TEXT | NOT NULL | `confirmed`, `likely`, `possible` (default `confirmed`) |
| evidence | JSON | | Evidence: data source, score, URL … |
| fingerprint | TEXT | NOT NULL, UK per upload | Rule + field + IDs of the affected sources, e.g. `K05:year:17`; recognizes the same finding when checking again |
| status | TEXT | NOT NULL | `open`, `accepted`, `rejected` (default `open`) |
| decided_at | TEXT | | Time of the decision |
 
When checking again, the code deletes open findings that no longer occur; accepted and rejected findings are kept.
 
## finding_reference – sources affected by a finding
 
Usually one source; several for duplicates, cycles or mutual citations.
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| finding_id | INTEGER | PK, FK, NOT NULL | → `finding` |
| reference_id | INTEGER | PK, FK, NOT NULL | → `reference` |
 
## suggestion – correction suggestion
 
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | |
| finding_id | INTEGER | FK, NOT NULL | → `finding` |
| rank | INTEGER | NOT NULL | Order in the GUI, `1` = recommended |
| changes | JSON | NOT NULL | Field → new value, e.g. `{"year":"2015"}`; several fields possible; `null` = remove field |
| previous_values | JSON | | Set on acceptance: overwritten values per source, e.g. `{"17":{"year":"in press"}}`; for undo and before/after view |
| publication_id | INTEGER | FK | → `publication`; for "Did you mean publication A or B?" |
| label | TEXT | | Short explanation, e.g. `print year` |
| score | REAL | | Similarity for search hits |
| is_chosen | INTEGER | NOT NULL | `1` = chosen; at most one per finding |
 
 
## Relationships

| From | To | Cardinality | On delete of target |
|---|---|---|---|
| `involved_person.project_id` | `project` | n : 1 | `CASCADE` |
| `rule_setting.project_id` | `project` | n : 1 | `CASCADE` |
| `upload.project_id` | `project` | n : 1 | `CASCADE` |
| `reference.upload_id` | `upload` | n : 1 | `CASCADE` |
| `finding.upload_id` | `upload` | n : 1 | `CASCADE` |
| `reference.publication_id` | `publication` | n : 0..1 | `SET NULL` |
| `publication_citation.citing_publication_id` | `publication` | n : 1 | `CASCADE` |
| `publication_citation.cited_publication_id` | `publication` | n : 1 | `CASCADE` |
| `finding_reference.finding_id` | `finding` | n : 1 | `CASCADE` |
| `finding_reference.reference_id` | `reference` | n : 1 | `CASCADE` |
| `suggestion.finding_id` | `finding` | n : 1 | `CASCADE` |
| `suggestion.publication_id` | `publication` | n : 0..1 | `SET NULL` |

`finding` ↔ `reference` is an n : m relationship via `finding_reference`. The code ensures that every finding affects at least one reference (SQLite cannot enforce this).

**Delete chains:** Deleting a project → everything in the project. Deleting an upload → its references, findings, finding–reference links and suggestions; other uploads and all `publication` rows remain.
