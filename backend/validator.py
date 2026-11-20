"""Prüft Literatureinträge auf Vollständigkeit, Format, Crossref-Abgleich und Duplikate.

Jede Prüfung liefert ein "Finding" – ein Dict mit den Feldern aus Lukas'
Datenbankschema: category, severity, rule_id, confidence, field, message, suggestion.
Die fortlaufende id wird in check() vergeben.
"""

import re
import time

import requests
from rapidfuzz import fuzz

HEADERS = {"User-Agent": "BOBR-Prototype/0.1"}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
URL_RE = re.compile(r"^https?://\S+$")

# Pflichtfelder je BibTeX-Typ (Standard, falls Typ unbekannt).
REQUIRED = {
    "article": {"author", "title", "journal", "year"},
    "book": {"author", "title", "publisher", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
}


def valid_isbn13(number):
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) != 13:
        return False
    total = 0
    for i, digit in enumerate(digits):
        # Stellen abwechselnd mit 1 und 3 gewichten.
        total += digit if i % 2 == 0 else digit * 3
    return total % 10 == 0


def valid_isbn10(number):
    if not re.match(r"^\d{9}[\dXx]$", number):
        return False
    total = 0
    for i in range(9):
        total += (10 - i) * int(number[i])
    total += 10 if number[9] in "Xx" else int(number[9])
    return total % 11 == 0


def check_formats(entry):
    """Prüft DOI-, ISBN- und URL-Format; gibt eine Liste von Problemtexten zurück."""
    problems = []

    doi = entry.get("doi")
    if doi and not DOI_RE.match(doi.strip()):
        problems.append("DOI-Format ungültig")

    isbn = entry.get("isbn")
    if isbn:
        clean = re.sub(r"[-\s]", "", isbn)
        if not (valid_isbn13(clean) or valid_isbn10(clean)):
            problems.append("ISBN Prüfsumme falsch")

    url = entry.get("url")
    if url and not URL_RE.match(url.strip()):
        problems.append("URL Format ungültig")

    return problems


def duplicate_map(entries, threshold=90):
    """Ordnet jeder Eintrags-ID die IDs ähnlicher (evtl. doppelter) Einträge zu."""
    partners = {entry.get("ID"): [] for entry in entries}
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            title1 = entries[i].get("title", "")
            title2 = entries[j].get("title", "")
            if title1 and title2 and fuzz.token_sort_ratio(title1, title2) >= threshold:
                id1 = entries[i].get("ID")
                id2 = entries[j].get("ID")
                partners[id1].append(id2)
                partners[id2].append(id1)
    return partners


class Validator:
    """Führt alle Prüfungen über eine Liste von Einträgen aus."""

    def __init__(self, use_crossref=True, rate_limit=0.2):
        # use_crossref=False schaltet den Netzwerkabgleich ab (z. B. in Tests).
        self.use_crossref = use_crossref
        self.rate_limit = rate_limit

    def check(self, entries):
        duplicates = duplicate_map(entries)
        findings = []
        next_id = 1

        for position, entry in enumerate(entries, start=1):
            entry_id = entry.get("ID", "?")

            found = self._completeness(entry, entry_id)
            found += self._formats(entry, entry_id)
            if self.use_crossref:
                found += self._crossref(entry, entry_id)
            found += self._duplicates(entry_id, duplicates)

            for finding in found:
                finding["id"] = next_id
                # Position des Eintrags (1-basiert) -> eindeutig, auch bei doppelten citekeys
                finding["position"] = position
                next_id += 1
                findings.append(finding)

            if self.use_crossref:
                time.sleep(self.rate_limit)  # Crossref-Rate-Limit

        return findings

    def _completeness(self, entry, entry_id):
        needed = REQUIRED.get(
            entry.get("ENTRYTYPE", "").lower(), {"author", "title", "year"}
        )
        missing = needed - set(entry.keys())
        if not missing:
            return []
        fields = ", ".join(sorted(missing))
        return [
            {
                "category": "completeness",
                "severity": "error",
                "rule_id": "V01_required_fields",
                "confidence": "confirmed",
                "entry_id": entry_id,
                "field": "Vollständigkeit",
                "message": f"Pflichtfelder fehlen bei {entry_id}: {fields}",
                "suggestion": "Fehlende Felder ergänzen",
            }
        ]

    def _formats(self, entry, entry_id):
        findings = []
        for problem in check_formats(entry):
            findings.append(
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
        return findings

    def _crossref(self, entry, entry_id):
        status, detail, suggestion = self._check_crossref(entry)
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

    def _duplicates(self, entry_id, duplicates):
        partners = duplicates.get(entry_id, [])
        if not partners:
            return []
        return [
            {
                "category": "consistency",
                "severity": "warning",
                "rule_id": "K10_duplicate",
                "confidence": "possible",
                "entry_id": entry_id,
                "field": "Duplikat",
                "message": f"{entry_id} ähnelt: {', '.join(partners)}",
                "suggestion": "Eintrag auf Duplikat prüfen und ggf. entfernen",
            }
        ]

    def _check_crossref(self, entry):
        doi = entry.get("doi")
        if not doi:
            return "kein DOI", "", ""
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{doi.strip()}",
                headers=HEADERS,
                timeout=10,
            )
        except requests.RequestException:
            return "Netzwerkfehler", "", ""
        if response.status_code != 200:
            return "DOI nicht auflösbar", "", ""

        message = response.json()["message"]
        cr_year = message.get("issued", {}).get("date-parts", [[None]])[0][0]
        cr_title = (message.get("title") or [""])[0]

        year = entry.get("year")
        if year and cr_year and str(year) != str(cr_year):
            return "Jahr weicht ab", f"{year} ≠ {cr_year}", f"year = {cr_year}"

        title = entry.get("title")
        if title and cr_title and fuzz.token_sort_ratio(title, cr_title) < 85:
            return "Titel weicht ab", "", f"title = {cr_title}"

        return "ok", "", ""
