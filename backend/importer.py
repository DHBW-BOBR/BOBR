"""Liest Literaturdateien ein und liefert eine Liste von Einträgen.

Ein Eintrag ist ein Dict wie von bibtexparser v1: ``ENTRYTYPE`` (z. B. ``article``),
``ID`` (der BibTeX-Key) und die Felder in Kleinschreibung (``author``, ``title`` …).
Dieses Format erwartet auch der Validator.

``.bib`` ist strukturiert und wird exakt geparst. ``.txt`` und ``.pdf`` sind
unstrukturiert: Der Text wird in einzelne Quellen zerlegt und je Quelle per Heuristik
(DOI, Jahr, ISBN, URL, Autor/Titel) befüllt. Die Treffer sind oft unvollständig – das
meldet der Validator dann als Vollständigkeits-Findings. Bei ``.pdf`` wird der Textlayer
gebraucht; reine Scans ohne Text ergeben einen klaren Fehler.
"""

import io
import os
import re

import bibtexparser
import pdfplumber

DOI_FIND = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
URL_FIND = re.compile(r"https?://\S+")
YEAR_FIND = re.compile(r"\b(?:19|20)\d{2}\b")
ISBN_FIND = re.compile(r"ISBN[:\s]*([0-9Xx][0-9Xx\-\s]{8,})", re.IGNORECASE)

# Übliche Überschriften, ab denen das Literaturverzeichnis beginnt.
REF_HEADINGS = {
    "references",
    "reference",
    "bibliography",
    "bibliografie",
    "literatur",
    "literaturverzeichnis",
    "quellen",
    "quellenverzeichnis",
}


class Importer:
    """Wählt anhand der Dateiendung den passenden Parser."""

    def load(self, filename, content):
        ext = os.path.splitext(filename or "")[1].lower()
        if ext == ".bib":
            return load_bib(content)
        if ext == ".txt":
            return parse_text(content.decode("utf-8", errors="replace"))
        if ext == ".pdf":
            return parse_text(references_section(pdf_text(content)))
        raise ValueError(
            f"Format '{ext or '?'}' wird nicht unterstützt (nur .bib, .txt, .pdf)"
        )


def load_bib(content):
    entries = bibtexparser.loads(content.decode("utf-8")).entries
    if not entries:
        raise ValueError("Keine Einträge gefunden.")
    return entries


def parse_text(text):
    """Zerlegt Freitext in Quellen und parst jede davon."""
    entries = []
    position = 1
    for chunk in split_references(text):
        if chunk:
            entries.append(parse_reference(chunk, position))
            position += 1
    if not entries:
        raise ValueError("Keine Einträge gefunden.")
    return entries


def pdf_text(content):
    """Holt den Text aus einem PDF (braucht einen Textlayer)."""
    try:
        parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
    except Exception as err:
        raise ValueError(f"PDF konnte nicht gelesen werden: {err}")
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("PDF enthält keinen extrahierbaren Text.")
    return text


def references_section(text):
    """Schneidet alles vor der (letzten) Literaturverzeichnis-Überschrift ab."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower().strip(":. ") in REF_HEADINGS:
            start = i + 1
    if start is None:
        return text
    return "\n".join(lines[start:])


def split_references(text):
    """Zerlegt einen Textblock in einzelne Quellen (drei Strategien)."""
    text = text.strip()
    if not text:
        return []
    # 1) Nummeriert: "[1] …" oder "1. …" am Zeilenanfang
    numbered = re.split(r"\n(?=\s*(?:\[\d+\]|\d+\.\s))", text)
    if len(numbered) > 1:
        return [clean(block) for block in numbered if block.strip()]
    # 2) Einträge durch Leerzeilen getrennt
    blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    if len(blocks) > 1:
        return [clean(block) for block in blocks]
    # 3) Fallback: eine Quelle pro Zeile
    return [clean(line) for line in text.splitlines() if line.strip()]


def clean(block):
    """Entfernt die Nummerierung und fasst Umbrüche zu einer Zeile zusammen."""
    block = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", block.strip())
    return re.sub(r"\s+", " ", block)


def parse_reference(raw, position):
    """Erkennt per Heuristik die Felder in einem Referenz-String."""
    # ENTRYTYPE bleibt leer (Typ unbekannt) -> Validator verlangt author/title/year.
    # ID ist nur ein interner Handle; einen echten citekey gibt es hier nicht.
    entry = {"ENTRYTYPE": "", "ID": f"ref{position}", "raw_text": raw}

    doi = DOI_FIND.search(raw)
    if doi:
        entry["doi"] = doi.group(0).rstrip(".,;)")

    url = URL_FIND.search(raw)
    if url:
        entry["url"] = url.group(0).rstrip(".,;)")

    year = YEAR_FIND.search(raw)
    if year:
        entry["year"] = year.group(0)

    isbn = ISBN_FIND.search(raw)
    if isbn:
        entry["isbn"] = isbn.group(1).strip()

    author, title = guess_author_title(raw)
    if author:
        entry["author"] = author
    if title:
        entry["title"] = title
    return entry


def guess_author_title(raw):
    """Heuristik: Autoren stehen meist vor dem Jahr, der Titel ist der Satz danach."""
    year = YEAR_FIND.search(raw)
    if year:
        author = raw[: year.start()].strip(" .,()")
        rest = raw[year.end() :].strip(" .,()")
        title = re.split(r"(?<=[.?!])\s", rest, maxsplit=1)[0].strip()
        return author, title

    parts = re.split(r"(?<=[.?!])\s", raw, maxsplit=1)
    author = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""
    return author, title
