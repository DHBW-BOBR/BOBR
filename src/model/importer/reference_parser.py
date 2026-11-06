"""Heuristische Erkennung von Literaturangaben aus Freitext (.txt und .pdf).

Bewusst ein MVP: zuverlässig erkannt werden DOI, URL und Jahr; der Rohtext bleibt
immer erhalten. Autor und Titel sind best-effort. Für eine robustere Erkennung
wäre später ein spezialisiertes Werkzeug (GROBID, anystyle) sinnvoll.

Rückgabe: ``(entries, unparsed)`` – erkannte ``LiteratureEntry`` und die Rohtexte
von Abschnitten, die nicht sicher als Literaturangabe erkannt wurden.
"""

import re

from ..literature import LiteratureEntry

# DOI / URL / Jahr im Freitext (stoppen an Whitespace bzw. typischer Satzzeichen).
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;)\]}>]+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s,;)\]}>]+", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")

# Zeilenanfang mit Nummerierung: [1]  (1)  1.  1)
_NUM_MARKER_RE = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s+")

# Überschrift des Literaturverzeichnisses (optional, zum Abschneiden von Fließtext davor).
_HEADING_RE = re.compile(
    r"^\s*(references|bibliography|literatur(?:verzeichnis)?|quellen(?:verzeichnis)?|"
    r"literaturverzeichnis)\s*:?\s*$",
    re.IGNORECASE,
)

_MIN_BLOCK_CHARS = 20  # kürzere Fragmente (Seitenzahlen, Kopfzeilen) ignorieren


def _strip_trailing_punct(value: str) -> str:
    return value.rstrip(".,;)]}>")


def _isolate_reference_section(text: str) -> str:
    """Schneidet – falls vorhanden – alles vor der Literatur-Überschrift ab."""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if _HEADING_RE.match(line):
            return "\n".join(lines[idx + 1 :])
    return text


def _split_blocks(text: str) -> list:
    """Teilt den Text in Referenzblöcke (nummeriert oder durch Leerzeilen)."""
    lines = text.splitlines()
    marker_lines = [ln for ln in lines if _NUM_MARKER_RE.match(ln)]

    if len(marker_lines) >= 2:
        blocks, current = [], []
        for line in lines:
            if _NUM_MARKER_RE.match(line):
                if current:
                    blocks.append("\n".join(current))
                current = [_NUM_MARKER_RE.sub("", line, count=1)]
            elif current:
                current.append(line)
        if current:
            blocks.append("\n".join(current))
        return blocks

    # Fallback: Absätze durch Leerzeilen trennen.
    return re.split(r"\n\s*\n", text)


def _normalize_block(block: str) -> str:
    """Zeilenumbrüche innerhalb eines Eintrags zu einem Fließtext zusammenfügen."""
    return re.sub(r"\s+", " ", block.replace("\n", " ")).strip()


def _looks_like_reference(text: str, has_doi: bool, has_year: bool) -> bool:
    if has_doi or has_year:
        return True
    # Ohne Jahr/DOI nur akzeptieren, wenn es nach Autorenliste aussieht
    # (Komma + ausreichend Länge).
    return len(text) >= 40 and "," in text


def _guess_authors_and_title(text: str, year: str):
    """Best-effort: Autoren = Text vor dem Jahr, Titel = Abschnitt danach."""
    authors = None
    title = None

    # Titel in Anführungszeichen hat Vorrang.
    m = re.search(r'[“"„]([^”"“]{4,})[”"“]', text)
    if m:
        title = m.group(1).strip()

    if year:
        before = text.split(year, 1)[0].strip(" ,.();[]")
        if before:
            authors = before
        if title is None:
            after = text.split(year, 1)[1].strip(" ,.();[]")
            # erster „Satz" nach dem Jahr als Titel
            title_candidate = re.split(r"[.]\s", after, 1)[0].strip()
            if 4 <= len(title_candidate) <= 300:
                title = title_candidate

    return authors, title


def parse_references_from_text(text: str, source_path: str = None):
    entries = []
    unparsed = []

    section = _isolate_reference_section(text or "")
    for position, raw_block in enumerate(_split_blocks(section)):
        normalized = _normalize_block(raw_block)
        if len(normalized) < _MIN_BLOCK_CHARS:
            continue  # Rauschen (Seitenzahlen, Kopf-/Fußzeilen)

        doi_match = _DOI_RE.search(normalized)
        url_match = _URL_RE.search(normalized)
        year_match = _YEAR_RE.search(normalized)
        year = year_match.group(0) if year_match else None

        if not _looks_like_reference(normalized, bool(doi_match), bool(year)):
            unparsed.append(normalized)
            continue

        fields = {}
        if doi_match:
            fields["doi"] = _strip_trailing_punct(doi_match.group(0))
        if url_match:
            fields["url"] = _strip_trailing_punct(url_match.group(0))
        if year:
            fields["year"] = year

        authors, title = _guess_authors_and_title(normalized, year)
        if authors:
            fields["author"] = authors
        if title:
            fields["title"] = title

        entries.append(
            LiteratureEntry(
                entry_type="misc",
                fields=fields,
                raw_text=normalized,
                position=position,
                source_path=source_path,
            )
        )

    return entries, unparsed
