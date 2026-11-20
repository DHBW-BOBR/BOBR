"""Prüft Literatureinträge auf Vollständigkeit, Format, Crossref-Abgleich und Duplikate.

Was:
    Jede Prüfung liefert ein „Finding“: ein Dict mit den Feldern aus Lukas'
    Datenbankschema (``category``, ``severity``, ``rule_id``, ``confidence``,
    ``field``, ``message``, ``suggestion``) plus ``entry_id`` und ``position``
    des betroffenen Eintrags. Die fortlaufende ``id`` wird in ``check()``
    vergeben und beim Speichern durch die Datenbank-ID ersetzt.

Warum:
    Der Validator kennt keine Datenbank und keine API; er bekommt Einträge und
    gibt Findings zurück. Dadurch lässt er sich ohne Server und ohne Netz testen
    (``use_crossref=False``), und die Regeln können unabhängig von der
    Speicherung wachsen.

Alternativen:
    * Je Regel eine eigene Klasse/Datei (vorbereitet in
      ``backend/model/validator/``): übersichtlicher bei vielen Regeln; die
      Entscheidung über die Struktur trifft das Team, bis dahin bleiben die
      wenigen Regeln in einer Datei.
    * Findings direkt in die Datenbank schreiben: koppelt Prüflogik an die
      Speicherung und erschwert Tests.
"""

import re
import time

import requests
from rapidfuzz import fuzz

# Crossref bittet um einen aussagekräftigen User-Agent („polite pool“).
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
    """Prüft die Prüfziffer einer ISBN-13.

    Was: Gewichtet die Ziffern abwechselnd mit 1 und 3; die Summe muss durch 10
        teilbar sein.
    Warum: Tippfehler in ISBNs fallen so ohne Netzabfrage auf.
    Alternativen: Bibliothek ``isbnlib``; neue Abhängigkeit für wenige Zeilen.
    """
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) != 13:
        return False
    total = 0
    for i, digit in enumerate(digits):
        # Stellen abwechselnd mit 1 und 3 gewichten.
        total += digit if i % 2 == 0 else digit * 3
    return total % 10 == 0


def valid_isbn10(number):
    """Prüft die Prüfziffer einer ISBN-10 (letzte Stelle darf ``X`` = 10 sein).

    Was: Gewichtet die Ziffern mit 10 bis 1; die Summe muss durch 11 teilbar sein.
    Warum: Ältere Bücher haben nur eine ISBN-10.
    Alternativen: Siehe ``valid_isbn13``.
    """
    if not re.match(r"^\d{9}[\dXx]$", number):
        return False
    total = 0
    for i in range(9):
        total += (10 - i) * int(number[i])
    total += 10 if number[9] in "Xx" else int(number[9])
    return total % 11 == 0


def check_formats(entry):
    """Prüft DOI-, ISBN- und URL-Format; gibt eine Liste von Problemtexten zurück.

    Was: DOI und URL per Regex, ISBN per Prüfziffer (ISBN-13 oder ISBN-10).
    Warum: Formatfehler sind sicher erkennbar (``confidence = confirmed``) und
        brauchen keine Netzabfrage.
    Alternativen: DOI/URL zusätzlich auflösen (HTTP-Abfrage); passiert für DOIs
        im Crossref-Abgleich, für URLs wäre es langsam und unzuverlässig.
    """
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
    """Ordnet jeder Eintrags-ID die IDs ähnlicher (evtl. doppelter) Einträge zu.

    Was: Vergleicht alle Titel paarweise mit ``rapidfuzz.token_sort_ratio``;
        ab ``threshold`` gelten zwei Einträge als mögliche Duplikate.
    Warum: Doppelte Quellen haben oft leicht unterschiedliche Titel
        (Groß-/Kleinschreibung, Wortreihenfolge, Tippfehler); ein exakter
        Vergleich fände sie nicht. ``token_sort_ratio`` ignoriert die
        Wortreihenfolge.
    Alternativen: Vergleich über DOI oder ``title_norm`` in der Datenbank;
        schneller bei großen Listen, findet aber keine Tippfehler. Paarweise
        ist O(n²), bei üblichen Verzeichnissen (unter 500 Quellen) aber schnell.
    Hinweis: Bei doppelten citekeys fallen die Einträge hier auf denselben
        Schlüssel; der Duplikat-Hinweis erscheint trotzdem.
    """
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
    """Führt alle Prüfungen über eine Liste von Einträgen aus.

    Was: ``check(entries)`` liefert alle Findings; ``use_crossref`` schaltet den
        Netzabgleich ein/aus, ``rate_limit`` ist die Pause zwischen
        Crossref-Abfragen.
    Warum: Tests und Offline-Betrieb brauchen eine Prüfung ohne Netz; Crossref
        bittet um zurückhaltende Abfrageraten.
    Alternativen: Crossref-Abfragen parallel ausführen; schneller, riskiert aber
        Sperren durch das Rate-Limit.
    """

    def __init__(self, use_crossref=True, rate_limit=0.2):
        # use_crossref=False schaltet den Netzwerkabgleich ab (z. B. in Tests).
        self.use_crossref = use_crossref
        self.rate_limit = rate_limit

    def check(self, entries):
        """Prüft alle Einträge und gibt die Findings zurück.

        Was: Je Eintrag Vollständigkeit, Formate, optional Crossref und
            Duplikate. Jedes Finding bekommt eine fortlaufende ``id`` und die
            ``position`` des Eintrags (1-basiert, Reihenfolge in ``entries``).
        Warum: ``position`` ordnet ein Finding eindeutig der gespeicherten
            Quelle zu (``reference.position``), auch wenn citekeys doppelt
            vorkommen oder ganz fehlen (.txt/.pdf). ``entry_id`` (citekey) allein
            reicht dafür nicht.
        Alternativen: Einträge vorher mit einer internen eindeutigen ID
            versehen; verworfen, weil sich dann die ``ID`` in Meldungstexten
            ändern würde. ``position`` ist eine kleine Ergänzung ohne Einfluss
            auf bestehende Felder.
        """
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
                # Position des Eintrags (1-basiert) -> eindeutig, auch bei
                # doppelten citekeys
                finding["position"] = position
                next_id += 1
                findings.append(finding)

            if self.use_crossref:
                time.sleep(self.rate_limit)  # Crossref-Rate-Limit

        return findings

    def _completeness(self, entry, entry_id):
        """Regel V01: Pflichtfelder je Eintragstyp.

        Was: Fehlen Felder aus ``REQUIRED`` (unbekannter Typ: author, title,
            year), entsteht ein Finding mit allen fehlenden Feldern.
        Warum: Ein Finding je Eintrag statt je Feld hält die Liste für den Nutzer
            kurz.
        Alternativen: Ein Finding je fehlendem Feld; genauer für spätere
            automatische Korrekturen, aber unübersichtlicher in der Oberfläche.
        """
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
        """Regel K01: Formatfehler in DOI, ISBN und URL (je Problem ein Finding).

        Was: Wandelt die Problemtexte aus ``check_formats`` in Findings um.
        Warum: Jedes Format kann getrennt korrigiert werden.
        Alternativen: Ein Sammel-Finding; erschwert die Zuordnung zum Feld.
        """
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
        """Regel K20: Abweichung zu Crossref (Jahr oder Titel).

        Was: Nur echte Abweichungen werden zu Findings (``severity = warning``,
            ``confidence = likely``); kein DOI, Netzfehler oder nicht auflösbare
            DOI ergeben kein Finding.
        Warum: Eine Abweichung kann auch an Crossref liegen (z. B. Online- vs.
            Druckjahr), deshalb nur Warnung. Netzprobleme sind kein Fehler der
            Arbeit und sollen den Nutzer nicht verunsichern.
        Alternativen: Auch „DOI nicht auflösbar“ melden; sinnvoll, sobald
            zwischen Netzfehler und falscher DOI sicher unterschieden wird.
        """
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
        """Regel K10: mögliches Duplikat.

        Was: Ein Finding je Eintrag, der ähnliche Partner hat
            (``confidence = possible``).
        Warum: Ähnliche Titel sind nur ein Hinweis, die Entscheidung trifft der
            Nutzer.
        Alternativen: Ein Finding je Duplikat-Paar, verknüpft mit beiden Quellen
            (das Schema erlaubt das über ``finding_reference``); möglicher
            Folgeschritt.
        """
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
        """Fragt Crossref zur DOI ab und vergleicht Jahr und Titel.

        Was: Gibt ``(status, detail, suggestion)`` zurück; ``suggestion`` hat die
            Form ``"feld = wert"`` (wird in ``database.parse_changes`` zerlegt).
        Warum: Crossref ist die zentrale DOI-Registrierung und ohne API-Schlüssel
            nutzbar. Titel werden unscharf verglichen (unter 85 % Ähnlichkeit gilt
            als Abweichung), weil Groß-/Kleinschreibung und Untertitel oft
            unterschiedlich sind.
        Alternativen: OpenAlex (mehr Metadaten, Zitationsgraph); im Schema über
            ``publication`` vorgesehen, aber noch nicht angebunden.
        """
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
