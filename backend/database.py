"""SQLite-Persistenz auf Basis von Lukas' Datenbankschema.

Was:
    Speichert jeden Upload als eigene Prüfung dauerhaft in einer SQLite-Datei:
    ``project`` (ein Standard-Projekt), ``upload`` (inkl. Originaldatei),
    ``reference`` (je Quelle) sowie je Prüfung ``finding``, ``finding_reference``
    (betroffene Quelle) und ``suggestion`` (Korrekturvorschlag). Die übrigen
    Tabellen (``publication`` usw.) existieren, werden aber noch nicht befüllt.

Warum:
    Prüfungen sollen einen Neustart des Backends überstehen und später weiter
    bearbeitet werden können (Teamentscheidung: jeder Upload ist eine eigene,
    gespeicherte Prüfung; Uploads werden nicht zusammengeführt).

Entscheidungen im Überblick (Details in den Docstrings der Funktionen):
    * Schema-Quelle: Die Struktur wird nicht hier im Code definiert, sondern per
      SQLite-``backup`` aus der Vorlage ``bobr.sqlite`` kopiert. So gibt es nur
      eine Schema-Quelle. Alternative wäre ein ``CREATE TABLE``-Skript im Code
      gewesen; verworfen, weil es doppelt gepflegt werden müsste und von der
      Vorlage abweichen könnte.
    * Speicherort: Datei im Benutzerordner für Anwendungsdaten, nicht im Repo
      (siehe ``default_db_path``).
    * Kein Zustand im Arbeitsspeicher: Alles, was für eine Prüfung gebraucht wird
      (Originaldatei, Zuordnung Eintrag -> Quelle), wird aus der Datenbank
      gelesen (siehe ``_reference_resolver``).
    * Datenformat: Bibliografische Daten gehen als CSL-JSON in
      ``reference.data_original``/``data_current`` (Vorgabe aus dem Schema; CSL
      ist das Austauschformat von Crossref/OpenAlex und Zitierprogrammen).
      Zeitstempel sind UTC-Text ``YYYY-MM-DD HH:MM:SS`` (Vorgabe aus dem Schema).
    * Keine ORM-Bibliothek (z. B. SQLAlchemy): ``sqlite3`` ist in Python
      enthalten, das Schema ist klein und die Abfragen bleiben gut lesbar.
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

# Version der Prüfregeln; wandert in jedes Finding (Schema: finding.rule_version).
RULE_VERSION = 1


def now():
    """Aktueller Zeitpunkt als Text.

    Was: UTC-Zeit im Format ``YYYY-MM-DD HH:MM:SS``.
    Warum: Vorgabe aus dem Schema; UTC vermeidet Probleme mit Zeitzonen und
        Sommerzeit, das Textformat ist in SQLite sortier- und vergleichbar.
    Alternativen: SQLite-Default ``CURRENT_TIMESTAMP`` (liefert dasselbe Format),
        aber ein Wert aus Python lässt sich innerhalb eines Uploads für mehrere
        Zeilen identisch setzen und ist in Tests leichter nachzuvollziehen.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def default_db_path():
    """Speicherort der Datenbankdatei; der Ordner wird bei Bedarf angelegt.

    Was: Reihenfolge ``BOBR_DB_PATH``, sonst der übliche Ordner für
        Anwendungsdaten des Betriebssystems: Windows
        ``%LOCALAPPDATA%\\BOBR\\bobr.db``, macOS
        ``~/Library/Application Support/BOBR/bobr.db``, sonst
        ``$XDG_DATA_HOME/bobr/bobr.db`` bzw. ``~/.local/share/bobr/bobr.db``.
    Warum: Der Nutzer muss nichts einrichten; die Datei liegt dort, wo das
        Betriebssystem Programmdaten erwartet. ``LOCALAPPDATA`` (nicht
        ``APPDATA``) wird nicht mit OneDrive/Roaming-Profilen synchronisiert,
        das vermeidet Sync-Konflikte an einer offenen SQLite-Datei. Über
        ``BOBR_DB_PATH`` lässt sich der Ort für Tests, Demos oder mehrere
        Datenbanken umstellen.
    Alternativen:
        * Datei im Repo/Arbeitsverzeichnis: verworfen, weil sie dann je nach
          Startordner woanders landet, versehentlich committet werden kann und
          bei einer installierten Version nicht beschreibbar sein muss.
        * Bibliothek ``platformdirs``: liefert dieselben Ordner, wäre aber eine
          neue Abhängigkeit für wenige Zeilen Code.
        * Fester Pfad in einer Konfigurationsdatei: mehr Aufwand für den
          Nutzer ohne Vorteil im aktuellen Stand.
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
    """Prüft, ob ``path`` auf die Schema-Vorlage zeigt.

    Was: Vergleicht die aufgelösten Pfade (``:memory:`` ist nie die Vorlage).
    Warum: Würde jemand ``BOBR_DB_PATH`` auf ``backend/bobr.sqlite`` setzen,
        landeten echte Daten in der Vorlage und damit im Repo.
    Alternativen: Vorlage im Dateisystem schreibgeschützt markieren; verworfen,
        weil das bei jedem Checkout neu gesetzt werden müsste und unter Git/Windows
        nicht zuverlässig erhalten bleibt.
    """
    if str(path) == ":memory:":
        return False
    try:
        return Path(path).resolve() == TEMPLATE_PATH.resolve()
    except OSError:
        return False


class Database:
    """Dünne SQLite-Schicht auf Lukas' Schema.

    Was: Öffnet (oder erzeugt) eine Datenbank und bietet Methoden zum
        Speichern und Lesen von Uploads, Quellen und Findings. Standard ist eine
        In-Memory-DB; ``Database(default_db_path())`` schreibt in eine Datei.
    Warum: Alle SQL-Befehle an einer Stelle; ``app.py`` kennt nur Methoden.
        Der Standard ``:memory:`` bleibt, damit Unit-Tests ohne Datei
        auskommen; das Backend übergibt den Dateipfad ausdrücklich.
    Alternativen: Eine Verbindung pro Request öffnen; verworfen, weil SQLite
        lokal sehr schnell ist, die App nur einen Nutzer hat und eine geteilte
        Verbindung einfacher bleibt (``check_same_thread=False``, da FastAPI die
        Endpunkte auf seinem Event-Loop-Thread ausführt).
    """

    def __init__(self, path=":memory:"):
        """Öffnet die Datenbank und stellt Schema und Projekt sicher.

        Was: Lehnt die Vorlage als Ziel ab, öffnet die Verbindung, kopiert bei
            einer leeren Datei das Schema aus der Vorlage, schaltet
            Fremdschlüssel ein und legt bei Bedarf das Standard-Projekt an.
        Warum: ``PRAGMA foreign_keys = ON`` ist laut Schema-Doku auf jeder
            Verbindung Pflicht, sonst greifen die ``ON DELETE CASCADE``-Regeln
            nicht. Eine bestehende Datei wird nicht erneut aus der Vorlage
            überschrieben, damit gespeicherte Prüfungen erhalten bleiben.
        Alternativen: Schema bei jedem Start neu anlegen (``CREATE TABLE IF NOT
            EXISTS``); verworfen, siehe Modul-Docstring (eine Schema-Quelle).
        """
        if _is_template(path):
            raise ValueError(
                f"{TEMPLATE_PATH} ist die Schema-Vorlage "
                "und darf nicht beschrieben werden."
            )
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if not self._has_schema():
            self._load_template()  # leere DB -> Struktur aus Lukas' Vorlage holen
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.project_id = self._ensure_project()

    def _has_schema(self):
        """Prüft, ob die Datenbank schon Tabellen hat.

        Was: Sucht die Tabelle ``upload`` in ``sqlite_master``.
        Warum: Unterscheidet eine neue, leere Datei von einer bestehenden
            Datenbank, die nicht überschrieben werden darf.
        Alternativen: ``PRAGMA user_version`` als Schema-Version; sinnvoll, sobald
            es Migrationen gibt, aktuell aber noch nicht nötig.
        """
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='upload'"
        ).fetchone()
        return row is not None

    def _load_template(self):
        """Kopiert die Struktur der Vorlage in die neue Datenbank.

        Was: Öffnet ``bobr.sqlite`` schreibgeschützt (``mode=ro``) und kopiert sie
            per ``backup`` in die eigene Verbindung.
        Warum: ``backup`` übernimmt Tabellen, Indizes, CHECKs und generierte
            Spalten exakt. ``mode=ro`` stellt sicher, dass die Vorlage selbst
            dabei nie verändert wird.
        Alternativen: Datei kopieren (``shutil.copy``); geht nicht für
            ``:memory:`` und braucht Sonderfälle für bestehende Dateien.
        """
        template = sqlite3.connect(
            TEMPLATE_PATH.resolve().as_uri() + "?mode=ro", uri=True
        )
        try:
            template.backup(self.conn)
        finally:
            template.close()

    def _ensure_project(self):
        """Liefert die ID des Standard-Projekts und legt es bei Bedarf an.

        Was: Nimmt das erste vorhandene Projekt, sonst wird ``BOBR-Projekt``
            angelegt.
        Warum: Das Schema verlangt ``upload.project_id``; eine Projektverwaltung
            in der Oberfläche gibt es noch nicht. Laut Schema-Doku ist eine
            Datenbankdatei ein Projekt.
        Alternativen: Projekt bei jedem Upload neu anlegen; verworfen, weil dann
            Uploads derselben Arbeit nicht zusammen auffindbar wären.
        """
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
        """Speichert einen Upload samt Originaldatei und einer Zeile je Quelle.

        Was: Legt eine ``upload``-Zeile an (inkl. ``file_content`` und
            ``file_hash``) und je Eintrag eine ``reference``-Zeile mit
            ``position`` (1, 2, 3 … in Reihenfolge der Datei), CSL-JSON und den
            abgeleiteten Spalten. Gibt die neue ``upload.id`` zurück.
        Warum: Die Originaldatei wird gespeichert, damit eine Prüfung nach einem
            Neustart die Einträge erneut einlesen kann und später ein
            korrigiertes .bib exportiert werden kann. ``position`` ist die
            eindeutige Zuordnung Eintrag -> Quelle, weil citekeys doppelt sein
            dürfen und .txt/.pdf gar keinen haben.
        Alternativen: Nur die geparsten Einträge speichern und die Datei
            verwerfen; verworfen, weil dann ``@string``, Kommentare und die
            Reihenfolge für den späteren Export verloren gingen.
        """
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
                   (upload_id, position, citekey, raw_text, data_original,
                    data_current, reference_type, doi_norm, title_norm, year,
                    first_author_norm, updated_at)
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
        """Speichert die Findings einer Prüfung und gibt die neuen mit DB-``id`` zurück.

        Was: Setzt die Prüf-Zeitpunkte am Upload, löscht offene Findings der
            letzten Prüfung und legt je Finding eine ``finding``-Zeile, die
            Verknüpfung zur Quelle (``finding_reference``) und den Vorschlag
            (``suggestion``) an. Der Fingerprint ist ``Regel:Feld:reference.id``.
        Warum:
            * Offene Findings werden verworfen, angenommene/abgelehnte bleiben
              (Vorgabe aus der Schema-Doku). Über ``UNIQUE(upload_id,
              fingerprint)`` wird ein schon entschiedenes Finding bei einer
              erneuten Prüfung nicht noch einmal angelegt.
            * ``reference.id`` im Fingerprint (statt citekey) ist stabil über
              Neustarts und eindeutig, auch bei doppelten citekeys. So steht es
              auch als Beispiel in der Schema-Doku (``K05:year:17``).
            * ``last_check_started_at``/``finished_at`` zeigen in der Übersicht,
              wann zuletzt geprüft wurde und ob eine Prüfung abgebrochen ist.
        Alternativen: Alle Findings einer Prüfung löschen und neu anlegen;
            verworfen, weil dann die Entscheidungen des Nutzers verloren gingen.
        """
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
            # Nur wenn keine Quelle gefunden wird, steht die entry_id im Fingerprint.
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
                    "INSERT OR IGNORE INTO finding_reference "
                    "(finding_id, reference_id) VALUES (?, ?)",
                    (finding_id, ref_id),
                )

            # Korrekturvorschlag als eigene Zeile (Schema trennt finding/suggestion)
            suggestion = f.get("suggestion")
            if suggestion:
                self.conn.execute(
                    """INSERT INTO suggestion
                           (finding_id, rank, changes, label, is_chosen)
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
        """Liefert eine Funktion Finding -> ``reference.id`` (oder ``None``).

        Was: Liest die Quellen des Uploads aus der Tabelle ``reference`` und ordnet
            ein Finding über ``position`` zu; fehlt die, über citekey bzw. ``refN``
            (erster Treffer).
        Warum: Die Zuordnung wird aus der Datenbank hergeleitet statt im
            Arbeitsspeicher gehalten, damit sie einen Neustart übersteht.
            ``position`` ist eindeutig, auch wenn citekeys doppelt vorkommen (das
            Schema erlaubt das). Der Rückfall auf den citekey bedient Aufrufer,
            die keine Position mitgeben (z. B. ältere Tests).
        Alternativen:
            * Dict ``citekey -> reference.id`` im Speicher (bisherige Lösung):
              geht beim Neustart verloren und überschreibt sich bei doppelten
              citekeys.
            * Eigene Spalte für eine interne Eintrags-ID: bräuchte eine
              Schema-Änderung; ``position`` leistet dasselbe.
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
        """Setzt den Status eines Findings (``accepted``/``rejected``).

        Was: Speichert Status und Entscheidungszeitpunkt; gibt ``False`` zurück,
            wenn es die ID nicht gibt.
        Warum: Der Rückgabewert erlaubt der API, bei unbekannter ID 404 zu liefern,
            statt stillschweigend Erfolg zu melden.
        Alternativen: Exception werfen; verworfen, weil ein ``bool`` für den
            einzigen Aufrufer einfacher auszuwerten ist.
        """
        cur = self.conn.execute(
            "UPDATE finding SET status = ?, decided_at = ? WHERE id = ?",
            (status, now(), finding_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ Lesen

    def get_upload(self, upload_id):
        """Liefert einen Upload (inkl. ``file_content``) als Dict oder ``None``.

        Was: Liest die ``upload``-Zeile des aktuellen Projekts.
        Warum: Die Prüfung braucht Dateiname und Originaldatei, um die Einträge
            nach einem Neustart neu einzulesen.
        Alternativen: Geparste Einträge zwischenspeichern; verworfen, siehe
            ``save_upload`` (Originaldatei ist die eine Quelle der Wahrheit).
        """
        row = self.conn.execute(
            "SELECT * FROM upload WHERE id = ? AND project_id = ?",
            (upload_id, self.project_id),
        ).fetchone()
        return dict(row) if row else None

    def latest_upload_id(self):
        """ID des zuletzt gespeicherten Uploads oder ``None``.

        Was: Höchste ``upload.id`` im Projekt.
        Warum: ``POST /api/validate/`` ohne Parameter prüft den neuesten Upload;
            so bleibt das bisherige Frontend unverändert lauffähig.
        Alternativen: Nach ``uploaded_at`` sortieren; verworfen, weil der
            Zeitstempel nur sekundengenau ist und die ID streng steigt.
        """
        row = self.conn.execute(
            "SELECT MAX(id) AS id FROM upload WHERE project_id = ?",
            (self.project_id,),
        ).fetchone()
        return row["id"]

    def reference_count(self, upload_id):
        """Anzahl der gespeicherten Quellen eines Uploads.

        Was: Zählt die ``reference``-Zeilen.
        Warum: Die API vergleicht damit, ob das erneute Einlesen genauso viele
            Einträge ergibt wie beim Upload. Weicht das ab (z. B. weil der
            Importer geändert wurde), wäre die Zuordnung über ``position`` falsch.
        Alternativen: Abweichung ignorieren; verworfen, weil Findings dann an
            falschen Quellen hängen könnten.
        """
        return self.conn.execute(
            "SELECT COUNT(*) FROM reference WHERE upload_id = ?", (upload_id,)
        ).fetchone()[0]

    def find_uploads_by_hash(self, digest):
        """Frühere Uploads mit demselben Datei-Hash.

        Was: Liefert ``id``, ``file_name`` und ``uploaded_at`` aller Uploads im
            Projekt mit diesem ``file_hash``.
        Warum: Vorgabe aus der Schema-Doku: Beim erneuten Hochladen derselben
            Datei einen Hinweis zeigen. Gespeichert wird trotzdem neu, weil jeder
            Upload eine eigene Prüfung ist.
        Alternativen: Doppelten Upload ablehnen oder den alten wiederverwenden;
            verworfen wegen der Teamentscheidung „Uploads nicht zusammenführen“.
        """
        rows = self.conn.execute(
            "SELECT id, file_name, uploaded_at FROM upload "
            "WHERE project_id = ? AND file_hash = ? ORDER BY id",
            (self.project_id, digest),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_uploads(self, upload_id=None):
        """Übersicht der Uploads, neueste zuerst (optional nur einer).

        Was: Je Upload Metadaten, Anzahl Quellen, Findings je Status
            (``finding_counts``) und Zeitpunkte der letzten Prüfung.
        Warum: Grundlage für eine Liste „gespeicherte Prüfungen“ im Frontend, ohne
            dass dafür alle Findings geladen werden müssen.
        Alternativen: Zähler in Python aus allen Findings berechnen; verworfen,
            weil SQL das in einer Abfrage erledigt und weniger Daten lädt.
        """
        sql = """
            SELECT u.id, u.file_name, u.format, u.uploaded_at,
                   u.last_check_started_at, u.last_check_finished_at,
                   (SELECT COUNT(*) FROM reference r WHERE r.upload_id = u.id)
                       AS reference_count,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'open') AS n_open,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'accepted')
                       AS n_accepted,
                   (SELECT COUNT(*) FROM finding f
                     WHERE f.upload_id = u.id AND f.status = 'rejected')
                       AS n_rejected
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
        """Alle Findings eines Uploads inkl. Status, erstem Vorschlag und Quellen.

        Was: Liest ``finding``, den Vorschlag mit dem kleinsten ``rank`` aus
            ``suggestion`` und je Finding die IDs der betroffenen Quellen
            (``reference_ids`` aus ``finding_reference``, aufsteigend sortiert).
        Warum: Damit lässt sich eine gespeicherte Prüfung im bisherigen
            Frontend-Format wieder anzeigen; der Status zeigt, was schon
            entschieden ist. ``reference_ids`` verbindet ein Finding mit den
            Quellen aus ``get_references``, damit das Frontend je Quelle ihre
            Findings zeigen kann.
        Alternativen:
            * Alle Vorschläge als Liste liefern; aktuell gibt es nur einen
              Vorschlag je Finding, das Frontend zeigt auch nur einen.
            * Eine einzelne ``reference_id`` statt einer Liste; das Schema
              erlaubt aber mehrere Quellen je Finding (z. B. bei Duplikaten).
        """
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
        links = {}
        for link in self.conn.execute(
            """SELECT fr.finding_id, fr.reference_id
               FROM finding_reference fr JOIN finding f ON f.id = fr.finding_id
               WHERE f.upload_id = ?
               ORDER BY fr.reference_id""",
            (upload_id,),
        ):
            links.setdefault(link["finding_id"], []).append(link["reference_id"])
        return [{**dict(r), "reference_ids": links.get(r["id"], [])} for r in rows]

    def get_references(self, upload_id):
        """Die erkannten Quellen eines Uploads in Dateireihenfolge.

        Was: Je ``reference``-Zeile ``id``, ``position``, ``citekey``, ``type``
            (BibTeX-Typ), dazu aus dem CSL-JSON in ``data_current`` ``title``,
            ``authors`` (als „Nachname, Vorname“), ``container`` (Zeitschrift
            bzw. Tagungsband), ``publisher``, ``doi``, ``isbn``, ``url`` und das
            Jahr aus der abgeleiteten Spalte ``year``. ``raw_text`` ist der
            Originaltext der Quelle bei .txt/.pdf, bei .bib ``None``.
        Warum: Der Nutzer soll sehen, was der Importer aus seiner Datei erkannt
            hat, auch Quellen ohne Finding. Gerade bei .txt/.pdf ist die
            Erkennung heuristisch; nur so fällt auf, wenn eine Quelle falsch
            zerlegt wurde. ``data_current`` statt ``data_original``, damit später
            übernommene Korrekturen sichtbar sind. ``raw_text`` ist bei .bib
            ``None``, weil dort (mangels Originaltext je Eintrag) nur das
            CSL-JSON in der Spalte steht, was für Nutzer nichts aussagt.
        Alternativen: Das CSL-JSON unverändert ausliefern; verworfen, weil das
            Frontend dann CSL kennen müsste (z. B. ``issued.date-parts``).
        """
        rows = self.conn.execute(
            """SELECT id, position, citekey, reference_type, raw_text,
                      data_original, data_current, year
               FROM reference WHERE upload_id = ? ORDER BY position""",
            (upload_id,),
        ).fetchall()
        result = []
        for r in rows:
            csl = json.loads(r["data_current"])
            result.append(
                {
                    "id": r["id"],
                    "position": r["position"],
                    "citekey": r["citekey"],
                    "type": r["reference_type"],
                    "title": csl.get("title"),
                    "authors": [format_author(a) for a in csl.get("author", [])],
                    "year": r["year"],
                    "container": csl.get("container-title"),
                    "publisher": csl.get("publisher"),
                    "doi": csl.get("DOI"),
                    "isbn": csl.get("ISBN"),
                    "url": csl.get("URL"),
                    "raw_text": (
                        None if r["raw_text"] == r["data_original"] else r["raw_text"]
                    ),
                }
            )
        return result

    def delete_upload(self, upload_id):
        """Löscht einen Upload samt Quellen, Findings und Vorschlägen.

        Was: Löscht die ``upload``-Zeile; die abhängigen Zeilen entfernt SQLite
            über ``ON DELETE CASCADE``. Danach ``VACUUM``, damit die Datei wieder
            schrumpft. Gibt ``False`` zurück, wenn es die ID nicht gibt.
        Warum: Nutzer sollen einzelne Prüfungen entfernen können, ohne andere zu
            verlieren; die Datei soll durch gelöschte Prüfungen nicht dauerhaft
            wachsen. Die Lösch-Kette ist im Schema festgelegt, deshalb genügt
            ein ``DELETE``.
        Alternativen:
            * Abhängige Tabellen einzeln löschen: doppelt zur Schema-Regel und
              fehleranfällig.
            * Ohne ``VACUUM``: SQLite verwendet freie Seiten wieder, die Datei
              wird aber nie kleiner. Bei den kleinen Datenmengen hier kostet
              ``VACUUM`` kaum Zeit.
            * ``PRAGMA auto_vacuum``: müsste in der Vorlage gesetzt werden, also
              eine Änderung am Schema-Artefakt.
        """
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
    """SHA-256 einer Datei als Hex-Text.

    Was: Prüfsumme über die Bytes der hochgeladenen Datei (``upload.file_hash``).
    Warum: Erkennt, ob genau dieselbe Datei schon einmal hochgeladen wurde.
        SHA-256 ist in Python enthalten und praktisch kollisionsfrei.
    Alternativen: MD5/SHA-1 (schneller, aber veraltet) oder Vergleich über
        Dateiname/Größe (unzuverlässig, gleiche Namen bei anderem Inhalt).
    """
    return hashlib.sha256(content).hexdigest()


def parse_changes(suggestion):
    """Wandelt einen Vorschlagstext in die Spalte ``suggestion.changes``.

    Was: ``"year = 2021"`` wird zu ``{"year": "2021"}``; rein beratende Texte
        (z. B. „Fehlende Felder ergänzen“) ergeben ``{}``.
    Warum: Das Schema verlangt ``changes`` als JSON (NOT NULL), damit ein
        angenommener Vorschlag später automatisch in ``data_current``
        übernommen werden kann. Der Validator liefert Vorschläge aber als Text.
    Alternativen: Den Validator direkt strukturierte Änderungen liefern lassen;
        sinnvoll, sobald die Übernahme in ``data_current`` gebaut wird, aktuell
        hätte das die Validator-Schnittstelle stärker verändert.
    """
    match = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", suggestion)
    if match:
        return {match.group(1): match.group(2).strip()}
    return {}


# ---------------------------------------------------------------------------
# bibtexparser-Dict  ->  CSL-JSON  (nur an der DB-Grenze)
# ---------------------------------------------------------------------------

# Zuordnung BibTeX-Typ -> CSL-Typ; unbekannte Typen werden "document".
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
    """Wandelt einen bibtexparser-Eintrag in ein (minimales) CSL-JSON-Objekt.

    Was: Übernimmt Typ, ID, Titel, Autoren, Jahr, Zeitschrift/Tagungsband,
        Verlag, DOI, ISBN und URL in die CSL-Feldnamen.
    Warum: Das Schema speichert Quellen als CSL-JSON; Importer und Validator
        arbeiten intern aber mit dem bibtexparser-Format. Die Umwandlung passiert
        deshalb nur hier an der Datenbank-Grenze, der Rest des Codes bleibt
        unverändert.
    Alternativen: Bibliothek wie ``citeproc-py`` oder ``pybtex``; verworfen,
        weil eine neue Abhängigkeit für die wenigen Felder, die BOBR prüft, nicht
        nötig ist.
    """
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
    """Zerlegt ein BibTeX-Autorenfeld in CSL-Autoren.

    Was: ``"Nachname, Vorname and Vorname Nachname"`` wird zu einer Liste von
        ``{"family": …, "given": …}``.
    Warum: CSL trennt Nach- und Vornamen; das braucht der spätere Abgleich mit
        Crossref/OpenAlex. BibTeX erlaubt beide Schreibweisen (mit und ohne
        Komma), deshalb werden beide behandelt.
    Alternativen: ``bibtexparser.customization.splitname``; deckt Sonderfälle
        (``von``, ``Jr.``) besser ab, ist aber an bibtexparser v1 gebunden und
        für den aktuellen Bedarf mehr als nötig.
    """
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


def format_author(author):
    """Ein CSL-Autor als Anzeigetext.

    Was: ``{"family": "Smith", "given": "John"}`` -> ``"Smith, John"``; ohne
        Vornamen nur der Nachname.
    Warum: Das Frontend soll Autoren nur anzeigen, nicht CSL zerlegen müssen.
        „Nachname, Vorname“ ist die übliche Schreibweise in Literaturlisten.
    Alternativen: Das CSL-Objekt durchreichen; verschiebt die Formatierung in
        jede Oberfläche, die die Daten anzeigt.
    """
    family = author.get("family", "")
    given = author.get("given")
    return f"{family}, {given}" if given else family


# ---------------------------------------------------------------------------
# Abgeleitete (normalisierte) Spalten der reference-Tabelle
#
# Was:   doi_norm, title_norm, year, first_author_norm.
# Warum: Laut Schema-Doku werden sie an genau einer Stelle im Code gesetzt und
#        dienen dem schnellen Vergleich (Duplikate, Abgleich mit Datenbanken)
#        per Index, ohne jedes Mal das JSON zu zerlegen.
# Alternativen: Generierte Spalten in SQLite (wie bei ``publication``); hier
#        nicht möglich, weil die Normalisierung (Regex, Namenslogik) über das
#        hinausgeht, was SQL-Ausdrücke gut abbilden.
# ---------------------------------------------------------------------------


def norm_doi(doi):
    """DOI ohne Leerzeichen und in Kleinbuchstaben.

    Was: ``" 10.1000/XYZ "`` -> ``"10.1000/xyz"``.
    Warum: DOIs sind laut Standard unabhängig von Groß-/Kleinschreibung;
        so findet ein Vergleich auch unterschiedlich geschriebene DOIs.
    Alternativen: Präfixe wie ``https://doi.org/`` entfernen; sinnvolle
        Erweiterung, sobald der Importer solche Werte liefert.
    """
    if not doi:
        return None
    return doi.strip().lower()


def norm_text(text):
    """Text mit einfachen Leerzeichen und in Kleinbuchstaben.

    Was: Fasst Leerraum zusammen und schreibt klein.
    Warum: Titel aus verschiedenen Quellen unterscheiden sich oft nur in
        Zeilenumbrüchen und Großschreibung.
    Alternativen: Satzzeichen und Akzente entfernen; macht Vergleiche noch
        robuster, kann aber verschiedene Titel zusammenfallen lassen. Für den
        unscharfen Vergleich nutzt der Validator ohnehin ``rapidfuzz``.
    """
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip().lower()


def norm_year(year):
    """Jahr als Zahl oder ``None``.

    Was: Sucht die erste vierstellige Jahreszahl 19xx/20xx (``"2015a"`` -> 2015,
        ``"in press"`` -> ``None``).
    Warum: Vorgabe aus der Schema-Doku; Jahreszahlen mit Zusätzen sollen
        trotzdem vergleichbar sein.
    Alternativen: ``int(year)``; scheitert an Zusätzen wie ``2015a``.
    """
    if year is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(year))
    if match:
        return int(match.group(0))
    return None


def norm_author(author):
    """Nachname des ersten Autors, kleingeschrieben.

    Was: Nimmt den ersten Namen vor ``and`` und davon den Nachnamen.
    Warum: Erstautor + Jahr + Titel sind die üblichen Merkmale, um dieselbe
        Publikation zu erkennen, wenn keine DOI vorhanden ist.
    Alternativen: Alle Autoren normalisieren; für den Abgleich reicht laut
        Schema der Erstautor.
    """
    if not author:
        return None
    first = re.split(r"\s+and\s+", author.strip())[0]
    if "," in first:
        family = first.split(",")[0].strip()
    else:
        family = first.split()[-1]
    return family.lower() or None
