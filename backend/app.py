"""BOBR-Backend – FastAPI-Server.

Verbindet Importer, Validator und die SQLite-Datenbank mit den vier Endpunkten,
die Mariekes Vue-Frontend erwartet. Die Datenbank läuft In-Memory; die geparsten
Einträge bleiben zusätzlich im Speicher, weil der Validator auf dem
bibtexparser-Format arbeitet.

Starten:
    uvicorn backend.app:app --reload --port 8000
"""

import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Database
from backend.importer import Importer
from backend.validator import Validator

app = FastAPI(title="BOBR Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

importer = Importer()
validator = Validator()
db = Database()  # In-Memory-SQLite

# Aktueller Datensatz
_entries = []
_upload_id = None


def to_frontend(f):
    """Übersetzt ein internes Finding in das Format des Frontends."""
    return {
        "id": f["id"],
        "type": "fehler" if f["severity"] == "error" else "warnung",
        "field": f["field"],
        "message": f["message"],
        "suggestion": f["suggestion"],
    }


@app.post("/api/import/")
async def import_file(file: UploadFile = File(...)):
    global _entries, _upload_id
    content = await file.read()
    try:
        _entries = importer.load(file.filename or "", content)
    except ValueError as err:
        _entries = []
        _upload_id = None
        raise HTTPException(status_code=422, detail=str(err))

    fmt = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    _upload_id = db.save_upload(file.filename or "", content, fmt, _entries)
    return {"count": len(_entries), "filename": file.filename}


@app.post("/api/validate/")
async def validate():
    if not _entries or _upload_id is None:
        raise HTTPException(status_code=400, detail="zuerst eine Datei importieren")
    findings = validator.check(_entries)
    saved = db.save_findings(_upload_id, findings)
    return [to_frontend(f) for f in saved]


@app.post("/api/corrections/{issue_id}/accept")
async def accept_correction(issue_id: int):
    db.set_status(issue_id, "accepted")
    return {"status": "accepted", "id": issue_id}


@app.post("/api/corrections/{issue_id}/reject")
async def reject_correction(issue_id: int):
    db.set_status(issue_id, "rejected")
    return {"status": "rejected", "id": issue_id}
