"""Prüft Literatureinträge auf Vollständigkeit, Format, Crossref-Abgleich und Duplikate.

Die Prüflogik stammt 1:1 aus dem BOBR-Notebook und ist hier nur in einer Klasse
gebündelt. Jede Prüfung liefert sogenannte *Findings* – Dicts mit den Feldern, die
Lukas' Datenbankschema vorsieht:

    category   completeness | correctness | consistency
    severity   error | warning
    field      betroffenes Feld / Prüfung
    message    Beschreibung
    suggestion Korrekturvorschlag (kann leer sein)

Die ID wird beim Zusammenbauen der Gesamtliste vergeben.
"""

import re
import time

import requests
from rapidfuzz import fuzz

HEADERS = {"User-Agent": "BOBR-Prototype/0.1"}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
URL_RE = re.compile(r"^https?://\S+$")

REQUIRED = {
    "article": {"author", "title", "journal", "year"},
    "book": {"author", "title", "publisher", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
}


class Validator:
    """Führt alle Prüfungen über eine Liste von Einträgen aus."""

    def __init__(self, use_crossref: bool = True, rate_limit: float = 0.2):
        # use_crossref=False schaltet den Netzwerkabgleich ab (nützlich für Tests).
        self.use_crossref = use_crossref
        self.rate_limit = rate_limit

    def check(self, entries: list[dict]) -> list[dict]:
        dup_map = self._duplicate_map(entries)
        findings: list[dict] = []
        next_id = 1

        for e in entries:
            entry_id = e.get("ID", "?")

            raw = self._completeness(e, entry_id)
            raw += self._formats(e, entry_id)
            if self.use_crossref:
                raw += self._crossref(e, entry_id)
            raw += self._duplicates(entry_id, dup_map)

            for finding in raw:
                finding["id"] = next_id
                next_id += 1
                findings.append(finding)

            if self.use_crossref:
                time.sleep(self.rate_limit)  # Crossref-Rate-Limit

        return findings

    # ------------------------------------------------------------------ Prüfungen

    def _completeness(self, e: dict, entry_id: str) -> list[dict]:
        needed = REQUIRED.get(
            e.get("ENTRYTYPE", "").lower(), {"author", "title", "year"}
        )
        missing = needed - set(e.keys())
        if not missing:
            return []
        return [
            {
                "category": "completeness",
                "severity": "error",
                "rule_id": "V01_required_fields",
                "confidence": "confirmed",
                "entry_id": entry_id,
                "field": "Vollständigkeit",
                "message": f"Pflichtfelder fehlen bei {entry_id}: {', '.join(sorted(missing))}",
                "suggestion": "Fehlende Felder ergänzen",
            }
        ]

    def _formats(self, e: dict, entry_id: str) -> list[dict]:
        out = []
        for problem in self._check_formats(e):
            out.append(
                {
                    "category": "correctness",
                    "severity": "error",
                    "rule_id": "K01_field_format",
                    "confidence": "confirmed",
                    "entry_id": entry_id,
                    "field": problem.split("-")[0].strip(),
                    "message": f"{problem} bei {entry_id}",
                    "suggestion": "Format gemäß Standard korrigieren",
                }
            )
        return out

    def _crossref(self, e: dict, entry_id: str) -> list[dict]:
        status, detail, suggestion = self._check_crossref(e)
        if status in ("ok", "kein DOI", "Netzwerkfehler", "DOI nicht auflösbar"):
            return []
        return [
            {
                "category": "consistency",
                "severity": "warning",
                "rule_id": "K20_crossref_match",
                "confidence": "likely",
                "entry_id": entry_id,
                "field": "Crossref",
                "message": f"{status} bei {entry_id}: {detail}",
                "suggestion": suggestion,
            }
        ]

    def _duplicates(self, entry_id: str, dup_map: dict) -> list[dict]:
        partner = dup_map.get(entry_id, [])
        if not partner:
            return []
        return [
            {
                "category": "consistency",
                "severity": "warning",
                "rule_id": "K10_duplicate",
                "confidence": "possible",
                "entry_id": entry_id,
                "field": "Duplikat",
                "message": f"{entry_id} ähnelt: {', '.join(partner)}",
                "suggestion": "Eintrag auf Duplikat prüfen und ggf. entfernen",
            }
        ]

    # ------------------------------------------------------------------ Helfer

    @staticmethod
    def _check_formats(e: dict) -> list[str]:
        probleme = []
        if (doi := e.get("doi")) and not DOI_RE.match(doi.strip()):
            probleme.append("DOI-Format ungültig")
        if isbn := e.get("isbn"):
            clean = re.sub(r"[-\s]", "", isbn)
            if not (Validator._valid_isbn13(clean) or Validator._valid_isbn10(clean)):
                probleme.append("ISBN Prüfsumme falsch")
        if (url := e.get("url")) and not URL_RE.match(url.strip()):
            probleme.append("URL Format ungültig")
        return probleme

    @staticmethod
    def _valid_isbn13(s: str) -> bool:
        d = [int(c) for c in s if c.isdigit()]
        if len(d) != 13:
            return False
        return sum(x * (1 if i % 2 == 0 else 3) for i, x in enumerate(d)) % 10 == 0

    @staticmethod
    def _valid_isbn10(s: str) -> bool:
        if not re.match(r"^\d{9}[\dXx]$", s):
            return False
        total = sum((10 - i) * int(c) for i, c in enumerate(s[:9]))
        total += 10 if s[9] in "Xx" else int(s[9])
        return total % 11 == 0

    def _check_crossref(self, e: dict) -> tuple[str, str, str]:
        doi = e.get("doi")
        if not doi:
            return "kein DOI", "", ""
        try:
            r = requests.get(
                f"https://api.crossref.org/works/{doi.strip()}",
                headers=HEADERS,
                timeout=10,
            )
        except requests.RequestException:
            return "Netzwerkfehler", "", ""
        if r.status_code != 200:
            return "DOI nicht auflösbar", "", ""

        msg = r.json()["message"]
        cr_year = msg.get("issued", {}).get("date-parts", [[None]])[0][0]
        cr_title = (msg.get("title") or [""])[0]

        if (y := e.get("year")) and cr_year and str(y) != str(cr_year):
            return "Jahr weicht ab", f"{y} ≠ {cr_year}", f"year = {cr_year}"

        if (
            e.get("title")
            and cr_title
            and fuzz.token_sort_ratio(e["title"], cr_title) < 85
        ):
            return "Titel weicht ab", "", f"title = {cr_title}"

        return "ok", "", ""

    @staticmethod
    def _duplicate_map(entries: list[dict], threshold: int = 90) -> dict:
        """Ordnet jeder Eintrags-ID die IDs ähnlicher (evtl. doppelter) Einträge zu."""
        dup: dict = {e.get("ID"): [] for e in entries}
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                t1 = entries[i].get("title", "")
                t2 = entries[j].get("title", "")
                if t1 and t2 and fuzz.token_sort_ratio(t1, t2) >= threshold:
                    id1, id2 = entries[i].get("ID"), entries[j].get("ID")
                    dup[id1].append(id2)
                    dup[id2].append(id1)
        return dup
