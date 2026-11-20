"""BOBR-Backend – FastAPI-Server.

Was:
    Verbindet Importer, Validator und die SQLite-Datenbank über eine REST-API.
    Jeder Upload ist eine eigene, gespeicherte Prüfung; alles liegt in der
    Datenbankdatei (siehe ``database.default_db_path``), nichts nur im
    Arbeitsspeicher.

Warum:
    Prüfungen sollen einen Neustart überstehen und später weiter bearbeitet
    werden können. Früher lagen der aktuelle Upload und die Zuordnung
    Eintrag -> Quelle nur im Arbeitsspeicher (``_entries``/``_upload_id``) und
    gingen beim Neustart verloren; außerdem gab es immer nur *einen* aktuellen
    Upload.

Alternativen:
    * Geparste Einträge zusätzlich als JSON speichern statt die Originaldatei
      neu einzulesen: verworfen, weil die Originaldatei laut Schema ohnehin
      gespeichert wird (eine Quelle der Wahrheit) und der Validator auf dem
      bibtexparser-Format arbeitet, das so direkt wieder entsteht.
    * Die Struktur unter ``backend/api``/``controller``/``model`` (Stubs) nutzen:
      Entscheidung des Teams steht noch aus; bis dahin bleibt alles in dieser
      Datei, damit nichts doppelt gepflegt wird.

Endpunkte: siehe README, Abschnitt „Backend-API“.

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
# CORS: Das Vue-Frontend läuft im Dev-Server auf einem anderen Port (5173/5174);
# ohne diese Freigabe blockiert der Browser die Anfragen.
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


async def get_db():
    """Liefert die Datenbank und öffnet sie beim ersten Aufruf.

    Was: FastAPI-Abhängigkeit (``Depends``); legt beim ersten Request
        ``Database(default_db_path())`` an und gibt danach immer dieselbe
        Instanz zurück.
    Warum:
        * Erst beim ersten Request statt beim Import des Moduls: Tests, die
          ``backend.app`` importieren, legen so keine Datei im Benutzerordner an
          und können ``app_module.db`` vorher durch eine Test-DB ersetzen.
        * ``async``: läuft auf dem Event-Loop statt im Threadpool, dadurch können
          zwei gleichzeitige erste Requests nicht zwei Verbindungen öffnen.
    Alternativen: FastAPI-``lifespan``-Hook beim Start; funktioniert auch, aber
        Tests müssten dann den Hook auslösen bzw. umgehen.
    """
    global db
    if db is None:
        db = Database(default_db_path())
    return db


def to_frontend(f):
    """Übersetzt ein Finding in das Format des Frontends.

    Was: ``{id, type, field, message, suggestion}`` mit ``type`` = ``fehler``
        (severity ``error``) oder ``warnung`` (alles andere).
    Warum: Das Vue-Frontend (Branch ``Marieke-2``) erwartet genau diese Felder;
        intern gelten die Bezeichnungen aus dem Schema (``severity`` usw.).
    Alternativen: Das Frontend auf die Schema-Felder umstellen; verworfen, weil
        das Frontend nicht Teil dieser Änderung ist.
    """
    return {
        "id": f["id"],
        "type": "fehler" if f["severity"] == "error" else "warnung",
        "field": f["field"],
        "message": f["message"],
        "suggestion": f["suggestion"],
    }


def load_entries(upload):
    """Liest die gespeicherte Originaldatei eines Uploads erneut ein.

    Was: Ruft den Importer mit ``file_name`` und ``file_content`` aus der
        Datenbank auf; Fehler werden zu HTTP 409.
    Warum: So braucht die Prüfung keinen Zustand im Arbeitsspeicher. Der Importer
        ist deterministisch, die Einträge entstehen also in derselben
        Reihenfolge wie beim Upload (Zuordnung über ``reference.position``).
        409 (Konflikt), weil die Anfrage korrekt ist, aber der gespeicherte
        Stand nicht mehr zum aktuellen Importer passt.
    Alternativen: Siehe Modul-Docstring (geparste Einträge speichern).
    """
    try:
        return importer.load(upload["file_name"], upload["file_content"])
    except ValueError as err:
        raise HTTPException(
            status_code=409, detail=f"Gespeicherte Datei nicht lesbar: {err}"
        )


# ---------------------------------------------------------------------- Import


@app.post("/api/import/")
async def import_file(file: UploadFile = File(...), db: Database = Depends(get_db)):
    """Datei einlesen und als neue Prüfung speichern.

    Was: Parst die Datei, speichert sie als neuen Upload und liefert ``count``,
        ``filename``, ``upload_id``, ``notice`` und ``duplicate_of``. Bei
        nicht lesbaren Dateien 422, dann wird nichts gespeichert.
    Warum: ``count``/``filename`` bleiben für das bestehende Frontend gleich;
        ``upload_id`` braucht das Frontend, um später genau diese Prüfung
        wieder aufzurufen. ``notice`` weist auf eine schon gespeicherte,
        identische Datei hin (gleicher ``file_hash``), gespeichert wird trotzdem
        neu, weil jeder Upload eine eigene Prüfung ist.
    Alternativen: Doppelte Datei ablehnen oder mit der alten zusammenführen;
        verworfen wegen der Teamentscheidung „Uploads nicht zusammenführen“.
    """
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
            f"Diese Datei wurde bereits am {first['uploaded_at']} (UTC) "
            f"hochgeladen (Prüfung #{first['id']}). Sie wurde trotzdem als neue "
            "Prüfung gespeichert."
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
    """Einen gespeicherten Upload prüfen.

    Was: Ohne Parameter wird der zuletzt gespeicherte Upload geprüft, mit
        ``?upload_id=`` ein bestimmter. Die Einträge werden aus der
        Originaldatei neu eingelesen, geprüft und die Findings gespeichert.
        Antwort: die neu angelegten Findings im Frontend-Format.
        400 ohne Upload, 404 bei unbekannter ID, 409 wenn die Datei heute eine
        andere Anzahl an Quellen ergibt als beim Upload.
    Warum: Das bestehende Frontend ruft den Endpunkt ohne Parameter auf und
        funktioniert so unverändert weiter; der Parameter erlaubt, ältere
        Prüfungen nach einem Neustart erneut zu prüfen. Die 409-Prüfung
        verhindert, dass Findings an falschen Quellen hängen, falls sich der
        Importer seit dem Upload geändert hat.
    Alternativen: Query-Parameter statt eigener Route
        (``/api/uploads/{id}/validate``); die Route wäre sauberer REST, der
        Parameter hält aber den bisherigen Endpunkt kompatibel und vermeidet
        zwei Wege für dieselbe Aktion.
    """
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
    """Gemeinsame Logik für Annehmen/Ablehnen.

    Was: Setzt den Status; bei unbekannter ID 404.
    Warum: Früher meldete der Endpunkt auch bei unbekannter ID Erfolg; das
        Frontend konnte so nicht merken, dass z. B. eine gelöschte Prüfung
        angezeigt wird.
    Alternativen: Zwei getrennte, fast gleiche Funktionen; verworfen, um die
        Logik nur einmal zu pflegen.
    """
    if not db.set_status(issue_id, status):
        raise HTTPException(
            status_code=404, detail=f"Finding {issue_id} nicht gefunden"
        )
    return {"status": status, "id": issue_id}


@app.post("/api/corrections/{issue_id}/accept")
async def accept_correction(issue_id: int, db: Database = Depends(get_db)):
    """Korrekturvorschlag annehmen (Status ``accepted``, 404 bei unbekannter ID).

    Hinweis: Die Übernahme der Änderung in ``reference.data_current`` ist ein
    eigener, späterer Schritt; aktuell wird nur die Entscheidung gespeichert.
    """
    return _decide(db, issue_id, "accepted")


@app.post("/api/corrections/{issue_id}/reject")
async def reject_correction(issue_id: int, db: Database = Depends(get_db)):
    """Korrekturvorschlag ablehnen (Status ``rejected``, 404 bei unbekannter ID)."""
    return _decide(db, issue_id, "rejected")


# ---------------------------------------------------------------------- Uploads


@app.get("/api/uploads")
async def list_uploads(db: Database = Depends(get_db)):
    """Alle gespeicherten Prüfungen, neueste zuerst.

    Was: Je Upload ``id``, ``file_name``, ``format``, ``uploaded_at``,
        ``reference_count``, ``finding_counts`` (open/accepted/rejected),
        ``last_check_started_at`` und ``last_check_finished_at``.
    Warum: Damit kann das Frontend nach einem Neustart eine Liste anzeigen und
        eine Prüfung zum Weiterarbeiten auswählen.
    Alternativen: Findings direkt mitliefern; verworfen, weil die Liste dann
        bei vielen Prüfungen unnötig groß würde (Details über
        ``GET /api/uploads/{id}``).
    """
    return db.list_uploads()


@app.get("/api/uploads/{upload_id}")
async def get_upload(upload_id: int, db: Database = Depends(get_db)):
    """Eine gespeicherte Prüfung mit allen Findings.

    Was: Dieselben Metadaten wie in der Liste plus ``findings`` im bisherigen
        Frontend-Format, ergänzt um ``status``. 404 bei unbekannter ID.
    Warum: Das Frontend kann die Ergebnisansicht ohne erneute Prüfung wieder
        aufbauen; ``status`` zeigt, was bereits angenommen/abgelehnt ist.
    Alternativen: Nur offene Findings liefern; verworfen, weil der Nutzer auch
        seine bisherigen Entscheidungen sehen soll.
    """
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
    """Eine gespeicherte Prüfung löschen.

    Was: Löscht den Upload samt Quellen, Findings und Vorschlägen; andere
        Prüfungen bleiben. Antwort ``{"deleted": id}``, 404 bei unbekannter ID.
    Warum: Grundlage für einen Lösch-Button im Frontend; die Datenbankdatei
        soll nicht unbegrenzt wachsen (siehe ``Database.delete_upload``).
    Alternativen: Status 204 ohne Inhalt (üblicher REST-Stil); verworfen, weil
        eine JSON-Antwort im Frontend einheitlich mit den anderen Endpunkten
        ausgewertet werden kann.
    """
    if not db.delete_upload(upload_id):
        raise HTTPException(
            status_code=404, detail=f"Upload {upload_id} nicht gefunden"
        )
    return {"deleted": upload_id}
