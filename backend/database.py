"""SQLite-Persistenz auf Basis von Lukas' Datenbankschema.

Die Struktur wird **nicht** hier definiert: Eine frische DB übernimmt sie direkt
aus Lukas' ``bobr.sqlite`` (liegt als Vorlage neben diesem Modul) per SQLite-
``backup``. Dadurch verwenden backend/ und Lukas' Schema garantiert dieselben
Tabellen/Constraints, ohne das Schema doppelt zu pflegen.

Geschrieben wird in den für den aktuellen Ablauf nötigen Teil:
``project`` (ein Default-Projekt), ``upload``, ``reference`` sowie je Prüfung
``finding`` + ``finding_reference`` (betroffene Quelle) + ``suggestion``
(Korrekturvorschlag). Die übrigen Tabellen (``publication`` usw.) existieren,
werden aber noch nicht befüllt.

Bibliografische Daten gehen als **CSL-JSON** in ``reference.data_original`` /
``data_current`` (Umwandlung hier). Zeitstempel sind UTC-Text.
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Lukas' leere DB; ihre Struktur wird in neue Datenbanken kopiert. Wird nur
# gelesen, nie beschrieben.
TEMPLATE_PATH = Path(__file__).with_name("bobr.sqlite")

# Umgebungsvariable, mit der sich der Speicherort der Datenbank überschreiben lässt.
DB_PATH_ENV = "BOBR_DB_PATH"

# Version der Prüfregeln; wandert mit in jedes Finding (Schema: finding.rule_version).
RULE_VERSION = 1


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def default_db_path():
    """Speicherort der Datenbankdatei; der Ordner wird bei Bedarf angelegt.

    Reihenfolge: ``BOBR_DB_PATH``, sonst der übliche Ordner für Anwendungsdaten
    des Betriebssystems (Windows ``%LOCALAPPDATA%\\BOBR\\bobr.db``, macOS
    ``~/Library/Application Support/BOBR/bobr.db``, sonst
    ``$XDG_DATA_HOME/bobr/bobr.db`` bzw. ``~/.local/share/bobr/bobr.db``).
    """
    override = os.environ.get(DB_PATH_ENV)
    if override:
        path = Path(override).expanduser()
    elif sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        path = Path(os.environ["LOCALAPPDATA"]) / "BOBR" / "bobr.db"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "BOBR" / "bobr.db"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        path = Path(base) / "bobr" / "bobr.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _is_template(path):
    """True, wenn ``path`` auf die Schema-Vorlage zeigt."""
    if str(path) == ":memory:":
        return False
    try:
        return Path(path).resolve() == TEMPLATE_PATH.resolve()
    except OSError:
        return False


class Database:
    """Dünne SQLite-Schicht auf Lukas' Schema. Standard ist eine In-Memory-DB
    (nichts wird persistiert); ``Database(default_db_path())`` schreibt in eine Datei.
    """

    def __init__(self, path=":memory:"):
        if _is_template(path):
            raise ValueError(
                f"{TEMPLATE_PATH} ist die Schema-Vorlage und darf nicht beschrieben werden."
            )
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if not self._has_schema():
            self._load_template()  # leere DB -> Struktur aus Lukas' Vorlage holen
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.project_id = self._ensure_project()

    def _has_schema(self):
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='upload'"
        ).fetchone()
        return row is not None

    def _load_template(self):
        # Vorlage nur lesen und ihre Struktur in die neue DB kopieren.
        template = sqlite3.connect(
            TEMPLATE_PATH.resolve().as_uri() + "?mode=ro", uri=True
        )
        try:
            template.backup(self.conn)
        finally:
            template.close()

    def _ensure_project(self):
        row = self.conn.execute("SELECT id FROM project LIMIT 1").fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO project (name, created_at) VALUES (?, ?)",
            ("BOBR-Projekt", now()),
        )
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------ Upload

    def save_upload(self, file_name, content, fmt, entries):
        created = now()
        cur = self.conn.execute(
            """INSERT INTO upload
                   (project_id, file_name, file_hash, file_content, format, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.project_id,
                file_name,
                file_hash(content),
                content,
                fmt,
                created,
            ),
        )
        upload_id = cur.lastrowid

        position = 1
        for entry in entries:
            data = json.dumps(to_csl(entry), ensure_ascii=False)
            citekey = entry.get("ID") if fmt == "bib" else None
            self.conn.execute(
                """INSERT INTO reference
                   (upload_id, position, citekey, raw_text, data_original, data_current,
                    reference_type, doi_norm, title_norm, year, first_author_norm, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    upload_id,
                    position,
                    citekey,
                    entry.get("raw_text") or data,
                    data,
                    data,
                    entry.get("ENTRYTYPE") or None,
                    norm_doi(entry.get("doi")),
                    norm_text(entry.get("title")),
                    norm_year(entry.get("year")),
                    norm_author(entry.get("author")),
                    created,
                ),
            )
            position += 1

        self.conn.commit()
        return upload_id

    # ------------------------------------------------------------------ Findings

    def save_findings(self, upload_id, findings):
        """Speichert die Findings einer Prüfung (+ betroffene Quelle + Vorschlag)
        und gibt sie mit DB-``id`` zurück."""
        self.conn.execute(
            "UPDATE upload SET last_check_started_at = ? WHERE id = ?",
            (now(), upload_id),
        )
        # Offene (noch nicht entschiedene) Findings der letzten Prüfung verwerfen;
        # akzeptierte/abgelehnte bleiben erhalten.
        self.conn.execute(
            "DELETE FROM finding WHERE upload_id = ? AND status = 'open'", (upload_id,)
        )
        resolve = self._reference_resolver(upload_id)
        saved = []

        for f in findings:
            ref_id = resolve(f)
            # Schema: Regel + Feld + IDs der betroffenen Quellen, z. B. "K05:year:17".
            # reference.id ist stabil (auch nach Neustart) und eindeutig, auch bei
            # doppelten citekeys; nur wenn keine Quelle gefunden wird, die entry_id.
            source = ref_id if ref_id is not None else f.get("entry_id", "")
            fingerprint = f"{f['rule_id']}:{f.get('field', '')}:{source}"
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO finding
                   (upload_id, rule_id, rule_version, category, severity, field,
                    message, confidence, fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    upload_id,
                    f["rule_id"],
                    f.get("rule_version", RULE_VERSION),
                    f["category"],
                    f["severity"],
                    f.get("field"),
                    f["message"],
                    f["confidence"],
                    fingerprint,
                ),
            )
            if not cur.rowcount:  # wegen UNIQUE(upload_id, fingerprint) ignoriert
                continue
            finding_id = cur.lastrowid

            # Betroffene Quelle verknüpfen (n:m über finding_reference)
            if ref_id is not None:
                self.conn.execute(
                    "INSERT OR IGNORE INTO finding_reference (finding_id, reference_id) "
                    "VALUES (?, ?)",
                    (finding_id, ref_id),
                )

            # Korrekturvorschlag als eigene Zeile (Schema trennt finding/suggestion)
            suggestion = f.get("suggestion")
            if suggestion:
                self.conn.execute(
                    """INSERT INTO suggestion (finding_id, rank, changes, label, is_chosen)
                       VALUES (?, 1, ?, ?, 0)""",
                    (finding_id, json.dumps(parse_changes(suggestion)), suggestion),
                )

            saved.append({**f, "id": finding_id})

        self.conn.execute(
            "UPDATE upload SET last_check_finished_at = ? WHERE id = ?",
            (now(), upload_id),
        )
        self.conn.commit()
        return saved

    def _reference_resolver(self, upload_id):
        """Liefert eine Funktion Finding -> reference.id (oder None).

        Die Zuordnung kommt aus der Tabelle ``reference``: bevorzugt über
        ``position`` (eindeutig), sonst über citekey bzw. ``refN`` (erster Treffer).
        """
        rows = self.conn.execute(
            "SELECT id, position, citekey FROM reference WHERE upload_id = ? "
            "ORDER BY position",
            (upload_id,),
        ).fetchall()
        by_position = {r["position"]: r["id"] for r in rows}
        by_key = {}
        for r in rows:
            by_key.setdefault(r["citekey"] or f"ref{r['position']}", r["id"])

        def resolve(finding):
            if finding.get("position") is not None:
                return by_position.get(finding["position"])
            return by_key.get(finding.get("entry_id"))

        return resolve

    def set_status(self, finding_id, status):
        cur = self.conn.execute(
            "UPDATE finding SET status = ?, decided_at = ? WHERE id = ?",
            (status, now(), finding_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ Lesen

    def get_upload(self, upload_id):
        row = self.conn.execute(
            "SELECT * FROM upload WHERE id = ? AND project_id = ?",
            (upload_id, self.project_id),
        ).fetchone()
        return dict(row) if row else None

    def latest_upload_id(self):
        row = self.conn.execute(
            "SELECT MAX(id) AS id FROM upload WHERE project_id = ?",
            (self.project_id,),
        ).fetchone()
        return row["id"]

    def reference_count(self, upload_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM reference WHERE upload_id = ?", (upload_id,)
        ).fetchone()[0]

    def find_uploads_by_hash(self, digest):
        rows = self.conn.execute(
            "SELECT id, file_name, uploaded_at FROM upload "
            "WHERE project_id = ? AND file_hash = ? ORDER BY id",
            (self.project_id, digest),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_uploads(self, upload_id=None):
        """Übersicht der Uploads, neueste zuerst (optional nur einer)."""
        sql = """
            SELECT u.id, u.file_name, u.format, u.uploaded_at,
                   u.last_check_started_at, u.last_check_finished_at,
                   (SELECT COUNT(*) FROM reference r WHERE r.upload_id = u.id)
                       AS reference_count,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'open') AS n_open,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'accepted') AS n_accepted,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'rejected') AS n_rejected
            FROM upload u
            WHERE u.project_id = ?"""
        params = [self.project_id]
        if upload_id is not None:
            sql += " AND u.id = ?"
            params.append(upload_id)
        sql += " ORDER BY u.id DESC"

        result = []
        for r in self.conn.execute(sql, params).fetchall():
            row = dict(r)
            row["finding_counts"] = {
                "open": row.pop("n_open"),
                "accepted": row.pop("n_accepted"),
                "rejected": row.pop("n_rejected"),
            }
            result.append(row)
        return result

    def get_findings(self, upload_id):
        """Alle Findings eines Uploads inkl. Status und erstem Vorschlag."""
        rows = self.conn.execute(
            """SELECT f.id, f.rule_id, f.category, f.severity, f.field, f.message,
                      f.status, f.decided_at,
                      (SELECT s.label FROM suggestion s WHERE s.finding_id = f.id
                        ORDER BY s.rank, s.id LIMIT 1) AS suggestion
               FROM finding f
               WHERE f.upload_id = ?
               ORDER BY f.id""",
            (upload_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_upload(self, upload_id):
        """Löscht einen Upload samt Quellen, Findings und Vorschlägen."""
        cur = self.conn.execute(
            "DELETE FROM upload WHERE id = ? AND project_id = ?",
            (upload_id, self.project_id),
        )
        self.conn.commit()
        if cur.rowcount:
            # Freien Platz an das Dateisystem zurückgeben.
            self.conn.execute("VACUUM")
        return cur.rowcount > 0


def file_hash(content):
    return hashlib.sha256(content).hexdigest()


def parse_changes(suggestion):
    """Macht aus einem Vorschlag wie ``"year = 2021"`` die Änderung
    ``{"year": "2021"}``; rein beratende Texte ergeben ``{}`` (changes ist NOT NULL)."""
    match = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", suggestion)
    if match:
        return {match.group(1): match.group(2).strip()}
    return {}


# ---------------------------------------------------------------------------
# bibtexparser-Dict  ->  CSL-JSON  (nur an der DB-Grenze)
# ---------------------------------------------------------------------------

CSL_TYPE = {
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


def to_csl(entry):
    """Wandelt einen bibtexparser-Eintrag in ein (minimales) CSL-JSON-Objekt."""
    entry_type = (entry.get("ENTRYTYPE") or "").lower()
    csl = {"type": CSL_TYPE.get(entry_type, "document")}

    if entry.get("ID"):
        csl["id"] = entry["ID"]
    if entry.get("title"):
        csl["title"] = entry["title"]

    authors = csl_authors(entry.get("author"))
    if authors:
        csl["author"] = authors

    year = norm_year(entry.get("year"))
    if year:
        csl["issued"] = {"date-parts": [[year]]}

    container = entry.get("journal") or entry.get("booktitle")
    if container:
        csl["container-title"] = container

    for source_key, csl_key in (
        ("publisher", "publisher"),
        ("doi", "DOI"),
        ("isbn", "ISBN"),
        ("url", "URL"),
    ):
        value = entry.get(source_key)
        if value:
            csl[csl_key] = value

    return csl


def csl_authors(author):
    """ "Nachname, Vorname and …" -> Liste von {family, given}."""
    if not author:
        return []
    authors = []
    for name in re.split(r"\s+and\s+", author):
        name = name.strip()
        if not name:
            continue
        if "," in name:
            family, given = name.split(",", 1)
            authors.append({"family": family.strip(), "given": given.strip()})
        else:
            parts = name.split()
            if len(parts) > 1:
                authors.append({"family": parts[-1], "given": " ".join(parts[:-1])})
            else:
                authors.append({"family": name})
    return authors


# ---------------------------------------------------------------------------
# Abgeleitete (normalisierte) Spalten der reference-Tabelle
# ---------------------------------------------------------------------------


def norm_doi(doi):
    if not doi:
        return None
    return doi.strip().lower()


def norm_text(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip().lower()


def norm_year(year):
    if year is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(year))
    if match:
        return int(match.group(0))
    return None


def norm_author(author):
    """Nachname des ersten Autors, kleingeschrieben."""
    if not author:
        return None
    first = re.split(r"\s+and\s+", author.strip())[0]
    if "," in first:
        family = first.split(",")[0].strip()
    else:
        family = first.split()[-1]
    return family.lower() or None
