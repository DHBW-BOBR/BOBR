"""Tests für die SQLite-Schicht: CSL-JSON, abgeleitete Spalten, Status, Idempotenz."""

import json

from backend.database import Database


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
