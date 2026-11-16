"""Tests für die SQLite-Schicht auf Lukas' Schema:
CSL-JSON, abgeleitete Spalten, Findings mit finding_reference + suggestion, Status."""

import json

from backend.database import Database


def test_schema_has_all_tables():
    db = Database()
    tables = {
        r["name"]
        for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {
        "project",
        "upload",
        "reference",
        "finding",
        "finding_reference",
        "suggestion",
        "publication",
    } <= tables


def test_save_upload_creates_reference_with_csl_and_norms():
    db = Database()
    entries = [
        {
            "ENTRYTYPE": "article",
            "ID": "a1",
            "author": "Smith, John and Doe, Jane",
            "title": "A Great Paper",
            "year": "2020",
            "doi": "10.1000/XYZ",
        }
    ]
    up = db.save_upload("r.bib", b"...", "bib", entries)

    row = db.conn.execute("SELECT * FROM reference WHERE upload_id=?", (up,)).fetchone()
    assert row["citekey"] == "a1"
    assert row["year"] == 2020
    assert row["doi_norm"] == "10.1000/xyz"
    assert row["first_author_norm"] == "smith"

    csl = json.loads(row["data_current"])
    assert csl["type"] == "article-journal"
    assert csl["author"][0]["family"] == "Smith"
    assert csl["issued"] == {"date-parts": [[2020]]}


def test_finding_links_reference_and_suggestion():
    db = Database()
    up = db.save_upload(
        "r.bib",
        b"x",
        "bib",
        [{"ENTRYTYPE": "article", "ID": "a1", "title": "T", "year": "2020"}],
    )
    finding = {
        "rule_id": "K20_crossref_match",
        "category": "consistency",
        "severity": "warning",
        "field": "Crossref",
        "message": "Jahr weicht ab bei a1",
        "suggestion": "year = 2021",
        "confidence": "likely",
        "entry_id": "a1",
    }

    saved = db.save_findings(up, [finding])
    fid = saved[0]["id"]

    # rule_version wurde ergänzt (Schema: NOT NULL)
    assert (
        db.conn.execute(
            "SELECT rule_version FROM finding WHERE id=?", (fid,)
        ).fetchone()["rule_version"]
        == 1
    )

    # finding_reference verknüpft das Finding mit der Quelle a1
    link = db.conn.execute(
        "SELECT reference_id FROM finding_reference WHERE finding_id=?", (fid,)
    ).fetchone()
    ref_id = db.conn.execute("SELECT id FROM reference WHERE citekey='a1'").fetchone()[
        "id"
    ]
    assert link["reference_id"] == ref_id

    # suggestion-Zeile: "year = 2021" -> strukturierte changes
    sug = db.conn.execute(
        "SELECT changes, label FROM suggestion WHERE finding_id=?", (fid,)
    ).fetchone()
    assert json.loads(sug["changes"]) == {"year": "2021"}
    assert sug["label"] == "year = 2021"


def test_findings_status_and_idempotency():
    db = Database()
    up = db.save_upload(
        "r.bib",
        b"x",
        "bib",
        [{"ENTRYTYPE": "article", "ID": "a1", "title": "T", "year": "2020"}],
    )
    finding = {
        "rule_id": "V01",
        "category": "completeness",
        "severity": "error",
        "field": "Vollständigkeit",
        "message": "m",
        "suggestion": "s",
        "confidence": "confirmed",
        "entry_id": "a1",
    }

    s1 = db.save_findings(up, [finding])
    assert len(s1) == 1

    db.set_status(s1[0]["id"], "accepted")
    s2 = db.save_findings(up, [finding])  # gleicher fingerprint
    assert len(s2) == 0  # kein Duplikat
    assert db.conn.execute("SELECT COUNT(*) c FROM finding").fetchone()["c"] == 1
    assert (
        db.conn.execute(
            "SELECT status FROM finding WHERE id=?", (s1[0]["id"],)
        ).fetchone()["status"]
        == "accepted"
    )


def test_txt_reference_has_no_citekey():
    db = Database()
    up = db.save_upload(
        "r.txt",
        b"x",
        "txt",
        [
            {
                "ENTRYTYPE": "",
                "ID": "ref1",
                "raw_text": "Some ref 2020",
                "title": "Some ref",
                "year": "2020",
            }
        ],
    )
    row = db.conn.execute(
        "SELECT citekey, raw_text FROM reference WHERE upload_id=?", (up,)
    ).fetchone()
    assert row["citekey"] is None  # Schema: citekey leer für .txt/.pdf
    assert row["raw_text"] == "Some ref 2020"


def test_foreign_keys_enabled():
    db = Database()
    assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
