"""End-to-End-Tests über die FastAPI-Endpunkte (Crossref abgeschaltet)."""

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.database import Database
from backend.validator import Validator


@pytest.fixture
def client():
    # Für jeden Test frische In-Memory-DB und ein Validator ohne Netz.
    app_module.db = Database()
    app_module.validator = Validator(use_crossref=False)
    app_module._entries = []
    app_module._upload_id = None
    return TestClient(app_module.app)


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
