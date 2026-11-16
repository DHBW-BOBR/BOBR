"""SQLite-Persistenz – ein Ausschnitt aus Lukas' Datenbankschema.

Umgesetzt sind die Tabellen ``project``, ``upload``, ``reference`` und ``finding``
(das Nötige für den aktuellen Ablauf: Datei hochladen → Quellen speichern → prüfen →
Findings annehmen/ablehnen). Nicht umgesetzt sind vorerst ``publication``,
``publication_citation``, ``suggestion``, ``finding_reference``, ``rule_setting`` und
``involved_person``.

Gegenüber dem vollen Schema bewusst vereinfacht:
* Es gibt genau ein Default-Projekt; keine Projektverwaltung.
* Welche Quelle ein Finding betrifft, steht (noch) nur im Text, nicht als
  ``finding_reference``-Verknüpfung.

Die bibliografischen Daten werden als **CSL-JSON** in ``reference.data_original`` und
``reference.data_current`` abgelegt (Umwandlung aus dem bibtexparser-Dict hier in
diesem Modul). Zeitstempel sind UTC-Text ``YYYY-MM-DD HH:MM:SS``.
"""

import json
import re
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    citation_style  TEXT
);

CREATE TABLE IF NOT EXISTS upload (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    file_name   TEXT NOT NULL,
    file_hash   TEXT NOT NULL,
    file_content BLOB NOT NULL,
    format      TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    last_check_started_at  TEXT,
    last_check_finished_at TEXT
);

CREATE TABLE IF NOT EXISTS reference (
    id            INTEGER PRIMARY KEY,
    upload_id     INTEGER NOT NULL REFERENCES upload(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    citekey       TEXT,
    raw_text      TEXT NOT NULL,
    data_original TEXT NOT NULL CHECK (json_valid(data_original)),
    data_current  TEXT NOT NULL CHECK (json_valid(data_current)),
    reference_type    TEXT,
    doi_norm          TEXT,
    title_norm        TEXT,
    year              INTEGER,
    first_author_norm TEXT,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finding (
    id          INTEGER PRIMARY KEY,
    upload_id   INTEGER NOT NULL REFERENCES upload(id) ON DELETE CASCADE,
    rule_id     TEXT NOT NULL,
    category    TEXT NOT NULL,
    severity    TEXT NOT NULL,
    field       TEXT,
    message     TEXT NOT NULL,
    suggestion  TEXT,
    confidence  TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    decided_at  TEXT,
    UNIQUE (upload_id, fingerprint)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Database:
    """Dünne SQLite-Schicht. Standard ist eine In-Memory-DB (nichts wird persistiert);
    mit ``Database("bobr.db")`` wird in eine Datei geschrieben."""

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.project_id = self._ensure_project()

    def _ensure_project(self) -> int:
        row = self.conn.execute("SELECT id FROM project LIMIT 1").fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO project (name, created_at) VALUES (?, ?)",
            ("BOBR-Projekt", _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------ Upload

    def save_upload(
        self, file_name: str, content: bytes, fmt: str, entries: list[dict]
    ) -> int:
        import hashlib

        now = _now()
        cur = self.conn.execute(
            """INSERT INTO upload
                   (project_id, file_name, file_hash, file_content, format, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.project_id,
                file_name,
                hashlib.sha256(content).hexdigest(),
                content,
                fmt,
                now,
            ),
        )
        upload_id = cur.lastrowid

        for position, e in enumerate(entries, start=1):
            csl = to_csl(e)
            data = json.dumps(csl, ensure_ascii=False)
            self.conn.execute(
                """INSERT INTO reference
                   (upload_id, position, citekey, raw_text, data_original, data_current,
                    reference_type, doi_norm, title_norm, year, first_author_norm, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    upload_id,
                    position,
                    e.get("ID") if fmt == "bib" else None,
                    e.get("raw_text") or data,
                    data,
                    data,
                    e.get("ENTRYTYPE") or None,
                    _norm_doi(e.get("doi")),
                    _norm_text(e.get("title")),
                    _norm_year(e.get("year")),
                    _norm_author(e.get("author")),
                    now,
                ),
            )
        self.conn.commit()
        return upload_id

    # ------------------------------------------------------------------ Findings

    def save_findings(self, upload_id: int, findings: list[dict]) -> list[dict]:
        """Speichert die Findings einer Prüfung und gibt sie mit DB-``id`` zurück."""
        self.conn.execute(
            "UPDATE upload SET last_check_started_at = ? WHERE id = ?",
            (_now(), upload_id),
        )
        # Offene (noch nicht entschiedene) Findings der letzten Prüfung verwerfen.
        self.conn.execute(
            "DELETE FROM finding WHERE upload_id = ? AND status = 'open'", (upload_id,)
        )

        saved = []
        for f in findings:
            fingerprint = f"{f['rule_id']}:{f.get('field', '')}:{f.get('entry_id', '')}"
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO finding
                   (upload_id, rule_id, category, severity, field, message, suggestion,
                    confidence, fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    upload_id,
                    f["rule_id"],
                    f["category"],
                    f["severity"],
                    f.get("field"),
                    f["message"],
                    f.get("suggestion"),
                    f["confidence"],
                    fingerprint,
                ),
            )
            if cur.rowcount:  # 1 = eingefügt, 0 = wegen UNIQUE ignoriert
                saved.append({**f, "id": cur.lastrowid})

        self.conn.execute(
            "UPDATE upload SET last_check_finished_at = ? WHERE id = ?",
            (_now(), upload_id),
        )
        self.conn.commit()
        return saved

    def set_status(self, finding_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE finding SET status = ?, decided_at = ? WHERE id = ?",
            (status, _now(), finding_id),
        )
        self.conn.commit()


# ---------------------------------------------------------------------------
# bibtexparser-Dict  ->  CSL-JSON  (nur an der DB-Grenze)
# ---------------------------------------------------------------------------

_CSL_TYPE = {
    "article": "article-journal",
    "book": "book",
    "inbook": "chapter",
    "incollection": "chapter",
    "inproceedings": "paper-conference",
    "conference": "paper-conference",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "misc": "document",
}


def to_csl(e: dict) -> dict:
    """Wandelt einen bibtexparser-Eintrag in ein (minimales) CSL-JSON-Objekt."""
    csl: dict = {"type": _CSL_TYPE.get((e.get("ENTRYTYPE") or "").lower(), "document")}
    if e.get("ID"):
        csl["id"] = e["ID"]
    if title := e.get("title"):
        csl["title"] = title
    if authors := _csl_authors(e.get("author")):
        csl["author"] = authors
    if year := _norm_year(e.get("year")):
        csl["issued"] = {"date-parts": [[year]]}
    if container := (e.get("journal") or e.get("booktitle")):
        csl["container-title"] = container
    for src, dst in (
        ("publisher", "publisher"),
        ("doi", "DOI"),
        ("isbn", "ISBN"),
        ("url", "URL"),
    ):
        if val := e.get(src):
            csl[dst] = val
    return csl


def _csl_authors(author: str | None) -> list[dict]:
    if not author:
        return []
    out = []
    for name in re.split(r"\s+and\s+", author):
        name = name.strip()
        if not name:
            continue
        if "," in name:
            family, given = (p.strip() for p in name.split(",", 1))
            out.append({"family": family, "given": given})
        else:
            parts = name.split()
            out.append(
                {"family": parts[-1], "given": " ".join(parts[:-1])}
                if len(parts) > 1
                else {"family": name}
            )
    return out


# ---------------------------------------------------------------------------
# Abgeleitete (normalisierte) Spalten der reference-Tabelle
# ---------------------------------------------------------------------------


def _norm_doi(doi: str | None) -> str | None:
    return doi.strip().lower() if doi else None


def _norm_text(text: str | None) -> str | None:
    return re.sub(r"\s+", " ", text).strip().lower() if text else None


def _norm_year(year) -> int | None:
    if year is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(year))
    return int(m.group(0)) if m else None


def _norm_author(author: str | None) -> str | None:
    """Nachname des ersten Autors, kleingeschrieben."""
    if not author:
        return None
    first = re.split(r"\s+and\s+", author.strip())[0]
    family = first.split(",")[0].strip() if "," in first else first.split()[-1]
    return family.lower() or None
