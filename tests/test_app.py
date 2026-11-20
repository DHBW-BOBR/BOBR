"""End-to-End-Tests über die FastAPI-Endpunkte (Crossref abgeschaltet)."""

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.database import Database
from backend.validator import Validator

BIB = (
    b"@article{a1, author={Smith, John}, title={T}, year={2020}}\n"
    b"@book{b1, title={B}, author={M, M}}"
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "bobr.db"


@pytest.fixture
def client(db_path):
    # Für jeden Test eine frische DB-Datei in tmp_path und ein Validator ohne Netz.
    app_module.db = Database(db_path)
    app_module.validator = Validator(use_crossref=False)
    return TestClient(app_module.app)


def upload(client, content=BIB, name="r.bib"):
    r = client.post("/api/import/", files={"file": (name, content, "text/plain")})
    assert r.status_code == 200, r.text
    return r.json()


def restart(db_path):
    """Simuliert einen Neustart des Backends: neue DB-Instanz auf derselben Datei."""
    app_module.db.conn.close()
    app_module.db = Database(db_path)


def test_import_validate_accept(client):
    bib = (
        b"@article{a1, author={Smith, John}, title={T}, year={2020}}\n"
        b"@book{b1, title={B}, author={M, M}}"
    )
    r = client.post(
        "/api/import/", files={"file": ("r.bib", bib, "application/x-bibtex")}
    )
    assert r.status_code == 200
    assert r.json()["count"] == 2

    r = client.post("/api/validate/")
    assert r.status_code == 200
    findings = r.json()
    assert findings
    assert {"id", "type", "field", "message", "suggestion"} <= set(findings[0])
    assert findings[0]["type"] in ("fehler", "warnung")

    fid = findings[0]["id"]
    r = client.post(f"/api/corrections/{fid}/accept")
    assert r.status_code == 200 and r.json()["status"] == "accepted"


def test_validate_without_import(client):
    assert client.post("/api/validate/").status_code == 400


def test_import_unsupported_format(client):
    r = client.post(
        "/api/import/", files={"file": ("x.docx", b"...", "application/octet-stream")}
    )
    assert r.status_code == 422


# ---------------------------------------------------------------- Import


def test_import_returns_upload_id_without_notice(client):
    body = upload(client)
    assert body["count"] == 2 and body["filename"] == "r.bib"
    assert isinstance(body["upload_id"], int)
    assert body["notice"] is None and body["duplicate_of"] == []


def test_same_file_twice_gives_notice_and_new_upload(client):
    first = upload(client)
    second = upload(client, name="kopie.bib")
    assert second["upload_id"] != first["upload_id"]
    assert second["duplicate_of"] == [first["upload_id"]]
    assert f"#{first['upload_id']}" in second["notice"]
    assert len(client.get("/api/uploads").json()) == 2


def test_db_opened_lazily_at_env_path(monkeypatch, tmp_path):
    target = tmp_path / "env" / "bobr.db"
    monkeypatch.setenv("BOBR_DB_PATH", str(target))
    app_module.db = None
    app_module.validator = Validator(use_crossref=False)
    assert not target.exists()
    upload(TestClient(app_module.app))
    assert target.exists()
    app_module.db.conn.close()


# ---------------------------------------------------------------- Prüfung


def test_validate_after_restart(client, db_path):
    upload_id = upload(client)["upload_id"]
    restart(db_path)

    r = client.post("/api/validate/")
    assert r.status_code == 200
    findings = r.json()
    assert findings

    # Jedes Finding ist über finding_reference mit einer Quelle dieses Uploads verknüpft
    db = app_module.db
    linked = db.conn.execute(
        """SELECT COUNT(DISTINCT fr.finding_id) FROM finding_reference fr
           JOIN reference r ON r.id = fr.reference_id WHERE r.upload_id = ?""",
        (upload_id,),
    ).fetchone()[0]
    assert linked == len(findings)


def test_validate_specific_and_unknown_upload(client):
    first = upload(client)["upload_id"]
    upload(client, content=b"@misc{x, title={Nur Titel}}")

    r = client.post(f"/api/validate/?upload_id={first}")
    assert r.status_code == 200
    detail = client.get(f"/api/uploads/{first}").json()
    assert len(detail["findings"]) == len(r.json())
    assert detail["last_check_finished_at"] is not None

    assert client.post("/api/validate/?upload_id=9999").status_code == 404


def test_validate_conflict_when_references_mismatch(client):
    upload_id = upload(client)["upload_id"]
    app_module.db.conn.execute(
        "DELETE FROM reference WHERE upload_id = ? AND position = 2", (upload_id,)
    )
    app_module.db.conn.commit()
    assert client.post("/api/validate/").status_code == 409


# ---------------------------------------------------------------- Korrekturen


def test_accept_reject_unknown_finding(client):
    assert client.post("/api/corrections/9999/accept").status_code == 404
    assert client.post("/api/corrections/9999/reject").status_code == 404


def test_decision_survives_restart(client, db_path):
    upload_id = upload(client)["upload_id"]
    fid = client.post("/api/validate/").json()[0]["id"]
    assert client.post(f"/api/corrections/{fid}/reject").status_code == 200
    restart(db_path)

    detail = client.get(f"/api/uploads/{upload_id}").json()
    status = {f["id"]: f["status"] for f in detail["findings"]}
    assert status[fid] == "rejected"


# ---------------------------------------------------------------- Uploads


def test_list_uploads(client):
    assert client.get("/api/uploads").json() == []
    first = upload(client)["upload_id"]
    second = upload(client, content=b"@misc{x, title={Nur Titel}}")["upload_id"]
    findings = client.post(f"/api/validate/?upload_id={first}").json()
    client.post(f"/api/corrections/{findings[0]['id']}/accept")

    items = client.get("/api/uploads").json()
    assert [i["id"] for i in items] == [second, first]  # neueste zuerst
    item = items[1]
    assert {
        "id",
        "file_name",
        "format",
        "uploaded_at",
        "reference_count",
        "finding_counts",
        "last_check_started_at",
        "last_check_finished_at",
    } <= set(item)
    assert item["format"] == "bib" and item["reference_count"] == 2
    assert item["finding_counts"] == {
        "open": len(findings) - 1,
        "accepted": 1,
        "rejected": 0,
    }
    assert items[0]["last_check_started_at"] is None  # nie geprüft


def test_get_upload_detail(client):
    upload_id = upload(client)["upload_id"]
    client.post("/api/validate/")

    r = client.get(f"/api/uploads/{upload_id}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["file_name"] == "r.bib"
    assert detail["findings"]
    assert {"id", "type", "field", "message", "suggestion", "status"} == set(
        detail["findings"][0]
    )
    assert client.get("/api/uploads/9999").status_code == 404


def test_delete_upload(client):
    keep = upload(client)["upload_id"]
    drop = upload(client)["upload_id"]
    client.post(f"/api/validate/?upload_id={drop}")

    r = client.delete(f"/api/uploads/{drop}")
    assert r.status_code == 200 and r.json() == {"deleted": drop}
    assert client.get(f"/api/uploads/{drop}").status_code == 404
    assert client.delete(f"/api/uploads/{drop}").status_code == 404
    assert [i["id"] for i in client.get("/api/uploads").json()] == [keep]
    # ohne Parameter wird jetzt wieder der verbleibende Upload geprüft
    assert client.post("/api/validate/").status_code == 200
