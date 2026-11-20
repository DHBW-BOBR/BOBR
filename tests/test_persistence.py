"""Tests für die dauerhafte Speicherung: Datenbankdatei, Neustart, Schutz der
Vorlage, Zuordnung Eintrag -> reference auch bei doppelten citekeys."""

import hashlib
import sqlite3

import pytest

from backend import database
from backend.database import TEMPLATE_PATH, Database, default_db_path
from backend.importer import Importer
from backend.validator import Validator

BIB = (
    b"@article{a1, author={Smith, John}, title={First}, year={2020}}\n"
    b"@book{b1, title={Second}, author={Doe, Jane}}"
)


def finding_links(db, upload_id):
    """finding.id -> reference.id für alle Findings eines Uploads."""
    rows = db.conn.execute(
        """SELECT fr.finding_id, fr.reference_id FROM finding_reference fr
           JOIN finding f ON f.id = fr.finding_id WHERE f.upload_id = ?""",
        (upload_id,),
    ).fetchall()
    return {r["finding_id"]: r["reference_id"] for r in rows}


# ---------------------------------------------------------------- Speicherort


def test_default_db_path_uses_env(monkeypatch, tmp_path):
    target = tmp_path / "neu" / "ordner" / "bobr.db"
    monkeypatch.setenv("BOBR_DB_PATH", str(target))
    assert default_db_path() == target
    assert target.parent.is_dir()  # Ordner wurde angelegt


def test_default_db_path_windows(monkeypatch, tmp_path):
    monkeypatch.delenv("BOBR_DB_PATH", raising=False)
    monkeypatch.setattr(database.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_db_path() == tmp_path / "BOBR" / "bobr.db"


def test_default_db_path_linux(monkeypatch, tmp_path):
    monkeypatch.delenv("BOBR_DB_PATH", raising=False)
    monkeypatch.setattr(database.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert default_db_path() == tmp_path / "bobr" / "bobr.db"


def test_template_is_never_written(tmp_path):
    before = hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()

    db = Database(tmp_path / "bobr.db")
    db.save_upload("r.bib", BIB, "bib", Importer().load("r.bib", BIB))
    db.conn.close()

    with pytest.raises(ValueError):
        Database(TEMPLATE_PATH)
    assert hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest() == before


# ---------------------------------------------------------------- Neustart


def test_data_survives_restart(tmp_path):
    path = tmp_path / "bobr.db"
    entries = Importer().load("r.bib", BIB)

    first = Database(path)
    upload_id = first.save_upload("r.bib", BIB, "bib", entries)
    saved = first.save_findings(upload_id, Validator(use_crossref=False).check(entries))
    assert first.set_status(saved[0]["id"], "accepted")
    first.conn.close()

    # "Neustart": neue Instanz auf derselben Datei
    second = Database(path)
    upload = second.get_upload(upload_id)
    assert upload["file_content"] == BIB
    assert second.reference_count(upload_id) == 2
    assert second.project_id == first.project_id
    counts = second.list_uploads()[0]["finding_counts"]
    assert counts["accepted"] == 1
    assert counts["open"] == len(saved) - 1


def test_check_after_restart_links_references(tmp_path):
    path = tmp_path / "bobr.db"
    first = Database(path)
    upload_id = first.save_upload("r.bib", BIB, "bib", Importer().load("r.bib", BIB))
    first.conn.close()

    second = Database(path)
    upload = second.get_upload(upload_id)
    entries = Importer().load(upload["file_name"], upload["file_content"])
    saved = second.save_findings(
        upload_id, Validator(use_crossref=False).check(entries)
    )
    assert saved

    links = finding_links(second, upload_id)
    assert set(links) == {f["id"] for f in saved}  # jedes Finding hat eine Quelle
    refs = {
        r["citekey"]: r["id"]
        for r in second.conn.execute(
            "SELECT id, citekey FROM reference WHERE upload_id = ?", (upload_id,)
        )
    }
    # b1 fehlt der publisher -> Finding hängt an der Quelle b1
    missing = [f for f in saved if f["entry_id"] == "b1"]
    assert missing and links[missing[0]["id"]] == refs["b1"]


def test_recheck_keeps_decisions(tmp_path):
    path = tmp_path / "bobr.db"
    entries = Importer().load("r.bib", BIB)
    db = Database(path)
    upload_id = db.save_upload("r.bib", BIB, "bib", entries)
    saved = db.save_findings(upload_id, Validator(use_crossref=False).check(entries))
    db.set_status(saved[0]["id"], "rejected")
    db.conn.close()

    db = Database(path)
    again = db.save_findings(upload_id, Validator(use_crossref=False).check(entries))
    # Gleiche Fingerprints nach dem Neustart: abgelehntes Finding kommt nicht wieder
    assert saved[0]["id"] not in {f["id"] for f in again}
    assert len(again) == len(saved) - 1
    statuses = [f["status"] for f in db.get_findings(upload_id)]
    assert statuses.count("rejected") == 1


# ---------------------------------------------------------------- doppelte citekeys


def test_duplicate_citekeys_get_separate_findings():
    bib = (
        b"@article{a1, title={Erster Titel}, year={2020}}\n"
        b"@article{a1, title={Ganz anderer Titel}, year={2021}}"
    )
    entries = Importer().load("r.bib", bib)
    assert [e["ID"] for e in entries] == ["a1", "a1"]

    db = Database()
    upload_id = db.save_upload("r.bib", bib, "bib", entries)
    saved = db.save_findings(upload_id, Validator(use_crossref=False).check(entries))

    # Beide Einträge haben fehlende Pflichtfelder -> zwei getrennte Findings
    completeness = [f for f in saved if f["rule_id"] == "V01_required_fields"]
    assert len(completeness) == 2

    links = finding_links(db, upload_id)
    linked = {links[f["id"]] for f in completeness}
    refs = {
        r["position"]: r["id"]
        for r in db.conn.execute(
            "SELECT id, position FROM reference WHERE upload_id = ?", (upload_id,)
        )
    }
    assert linked == {refs[1], refs[2]}


# ---------------------------------------------------------------- Löschen


def test_delete_upload_cascades(tmp_path):
    db = Database(tmp_path / "bobr.db")
    entries = Importer().load("r.bib", BIB)
    keep = db.save_upload("r.bib", BIB, "bib", entries)
    drop = db.save_upload("r.bib", BIB, "bib", entries)
    db.save_findings(drop, Validator(use_crossref=False).check(entries))

    assert db.delete_upload(drop)
    assert not db.delete_upload(drop)  # zweites Mal: nichts mehr da
    assert db.get_upload(drop) is None
    assert db.get_upload(keep) is not None
    for table in ("reference", "finding"):
        n = db.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE upload_id = ?", (drop,)
        ).fetchone()[0]
        assert n == 0
    for table in ("finding_reference", "suggestion"):
        assert db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_file_is_valid_sqlite_after_writes(tmp_path):
    path = tmp_path / "bobr.db"
    Database(path).save_upload("r.bib", BIB, "bib", Importer().load("r.bib", BIB))
    conn = sqlite3.connect(path)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()


# ---------------------------------------------------------------- Quellen lesen


def test_get_references_survives_restart(tmp_path):
    path = tmp_path / "bobr.db"
    first = Database(path)
    upload_id = first.save_upload("r.bib", BIB, "bib", Importer().load("r.bib", BIB))
    first.conn.close()

    refs = Database(path).get_references(upload_id)
    assert [(r["position"], r["citekey"], r["title"]) for r in refs] == [
        (1, "a1", "First"),
        (2, "b1", "Second"),
    ]
    assert refs[1]["authors"] == ["Doe, Jane"]
    assert refs[1]["year"] is None


def test_duplicate_citekeys_have_separate_references():
    bib = (
        b"@misc{a1, title={Erster}, author={X}, year={2020}}\n"
        b"@misc{a1, title={Zweiter}, author={Y}}"
    )
    db = Database()
    entries = Importer().load("r.bib", bib)
    upload_id = db.save_upload("r.bib", bib, "bib", entries)
    db.save_findings(upload_id, Validator(use_crossref=False).check(entries))

    refs = db.get_references(upload_id)
    assert [r["title"] for r in refs] == ["Erster", "Zweiter"]
    findings = db.get_findings(upload_id)
    # Nur der zweite Eintrag hat kein Jahr -> genau ein Finding an Quelle 2
    assert [f["reference_ids"] for f in findings] == [[refs[1]["id"]]]
