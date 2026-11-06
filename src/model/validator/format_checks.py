"""Formatprüfungen für strukturierte Felder – ohne externe API.

Reine Funktionen (keine Seiteneffekte), damit sie einzeln testbar sind und von
mehreren Validatoren genutzt werden können.
"""

import re
from urllib.parse import urlsplit

# DOI: Präfix "10." + Registrant (4–9 Ziffern) + "/" + Suffix.
# https://www.crossref.org/blog/dois-and-matching-regular-expressions/
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

# Häufige DOI-Präfixe, die vor der Prüfung entfernt werden.
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
    "doi ",
)


def normalize_doi(value: str) -> str:
    """Entfernt gängige Präfixe/Whitespace und liefert die reine DOI."""
    doi = (value or "").strip()
    low = doi.lower()
    for prefix in _DOI_PREFIXES:
        if low.startswith(prefix):
            doi = doi[len(prefix) :].strip()
            break
    return doi


def is_valid_doi(value: str) -> bool:
    """Prüft das DOI-Format gegen das Schema ``10.XXXX/...``."""
    return bool(_DOI_RE.match(normalize_doi(value)))


def _clean_isbn(value: str) -> str:
    """Entfernt Bindestriche, Leerzeichen und ein evtl. ``ISBN``-Präfix."""
    s = (value or "").strip()
    if s.lower().startswith("isbn"):
        s = s[4:]
    return re.sub(r"[\s\-]", "", s).upper()


def is_valid_isbn10(value: str) -> bool:
    """ISBN-10: gewichtete Quersumme (10..1) muss durch 11 teilbar sein."""
    s = _clean_isbn(value)
    if len(s) != 10 or not re.match(r"^\d{9}[\dX]$", s):
        return False
    total = 0
    for i, ch in enumerate(s):
        digit = 10 if ch == "X" else int(ch)  # 'X' nur an letzter Stelle (=10)
        total += digit * (10 - i)
    return total % 11 == 0


def is_valid_isbn13(value: str) -> bool:
    """ISBN-13: Gewichte 1/3 alternierend, Summe muss durch 10 teilbar sein."""
    s = _clean_isbn(value)
    if len(s) != 13 or not s.isdigit():
        return False
    total = 0
    for i, ch in enumerate(s):
        weight = 1 if i % 2 == 0 else 3
        total += int(ch) * weight
    return total % 10 == 0


def is_valid_isbn(value: str) -> bool:
    """Akzeptiert gültige ISBN-10 oder ISBN-13 (nach Länge unterschieden)."""
    s = _clean_isbn(value)
    if len(s) == 10:
        return is_valid_isbn10(s)
    if len(s) == 13:
        return is_valid_isbn13(s)
    return False


def is_valid_url(value: str) -> bool:
    """Gültiges http(s)-URL-Format: Schema + Host vorhanden, keine Leerzeichen."""
    s = (value or "").strip()
    if not s or re.search(r"\s", s):
        return False
    parts = urlsplit(s)
    if parts.scheme not in ("http", "https"):
        return False
    # Host muss vorhanden sein und mindestens einen Punkt oder 'localhost' haben.
    host = parts.hostname or ""
    return bool(host) and ("." in host or host == "localhost")
