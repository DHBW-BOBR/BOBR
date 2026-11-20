"""BOBR-Backend – FastAPI-Server.

Verbindet Importer, Validator und die SQLite-Datenbank. Jeder Upload ist eine
eigene, gespeicherte Prüfung; alles liegt in der Datenbankdatei (siehe
``database.default_db_path``), nichts nur im Arbeitsspeicher.

Starten (aus dem Repo-Root):
    uvicorn backend.app:app --reload --port 8000
"""

import os
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Database, default_db_path, file_hash
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

# Wird erst beim ersten Request geöffnet (siehe get_db).
db: Optional[Database] = None


def get_db():
    global db
    if db is None:
        db = Database(default_db_path())
    return db


def to_frontend(f):
    """Übersetzt ein internes Finding in das Format des Frontends."""
    return {
        "id": f["id"],
        "type": "fehler" if f["severity"] == "error" else "warnung",
        "field": f["field"],
        "message": f["message"],
        "suggestion": f["suggestion"],
    }


def load_entries(upload):
    """Liest die gespeicherte Originaldatei eines Uploads erneut ein."""
    try:
        return importer.load(upload["file_name"], upload["file_content"])
    except ValueError as err:
        raise HTTPException(
            status_code=409, detail=f"Gespeicherte Datei nicht lesbar: {err}"
        )


# ---------------------------------------------------------------------- Import


@app.post("/api/import/")
async def import_file(file: UploadFile = File(...), db: Database = Depends(get_db)):
    content = await file.read()
    filename = file.filename or ""
    try:
        entries = importer.load(filename, content)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))

    previous = db.find_uploads_by_hash(file_hash(content))
    fmt = os.path.splitext(filename)[1].lower().lstrip(".")
    upload_id = db.save_upload(filename, content, fmt, entries)

    notice = None
    if previous:
        first = previous[0]
        notice = (
            f"Diese Datei wurde bereits am {first['uploaded_at']} (UTC) hochgeladen "
            f"(Prüfung #{first['id']}). Sie wurde trotzdem als neue Prüfung gespeichert."
        )
    return {
        "count": len(entries),
        "filename": file.filename,
        "upload_id": upload_id,
        "notice": notice,
        "duplicate_of": [p["id"] for p in previous],
    }


# ---------------------------------------------------------------------- Prüfung


@app.post("/api/validate/")
async def validate(upload_id: Optional[int] = None, db: Database = Depends(get_db)):
    if upload_id is None:
        upload_id = db.latest_upload_id()
        if upload_id is None:
            raise HTTPException(status_code=400, detail="zuerst eine Datei importieren")

    upload = db.get_upload(upload_id)
    if upload is None:
        raise HTTPException(
            status_code=404, detail=f"Upload {upload_id} nicht gefunden"
        )

    entries = load_entries(upload)
    if len(entries) != db.reference_count(upload_id):
        # Importer liest die Datei anders als beim Upload -> Zuordnung wäre falsch.
        raise HTTPException(
            status_code=409,
            detail="Die gespeicherte Datei ergibt eine andere Anzahl an Quellen als "
            "beim Upload. Bitte die Datei neu hochladen.",
        )

    findings = validator.check(entries)
    saved = db.save_findings(upload_id, findings)
    return [to_frontend(f) for f in saved]


# ---------------------------------------------------------------------- Korrekturen


def _decide(db, issue_id, status):
    if not db.set_status(issue_id, status):
        raise HTTPException(
            status_code=404, detail=f"Finding {issue_id} nicht gefunden"
        )
    return {"status": status, "id": issue_id}


@app.post("/api/corrections/{issue_id}/accept")
async def accept_correction(issue_id: int, db: Database = Depends(get_db)):
    return _decide(db, issue_id, "accepted")


@app.post("/api/corrections/{issue_id}/reject")
async def reject_correction(issue_id: int, db: Database = Depends(get_db)):
    return _decide(db, issue_id, "rejected")


# ---------------------------------------------------------------------- Uploads


@app.get("/api/uploads")
async def list_uploads(db: Database = Depends(get_db)):
    return db.list_uploads()


@app.get("/api/uploads/{upload_id}")
async def get_upload(upload_id: int, db: Database = Depends(get_db)):
    summary = db.list_uploads(upload_id)
    if not summary:
        raise HTTPException(
            status_code=404, detail=f"Upload {upload_id} nicht gefunden"
        )
    result = summary[0]
    result["findings"] = [
        {**to_frontend(f), "status": f["status"]} for f in db.get_findings(upload_id)
    ]
    return result


@app.delete("/api/uploads/{upload_id}")
async def delete_upload(upload_id: int, db: Database = Depends(get_db)):
    if not db.delete_upload(upload_id):
        raise HTTPException(
            status_code=404, detail=f"Upload {upload_id} nicht gefunden"
        )
    return {"deleted": upload_id}
