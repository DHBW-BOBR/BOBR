"""Liest Literaturdateien ein und liefert eine Liste von Einträgen (bibtexparser-Dicts).

Ein Eintrag ist ein Dict wie von bibtexparser v1: Schlüssel ``ENTRYTYPE`` (z. B.
``article``), ``ID`` (der BibTeX-Key) sowie die Felder in Kleinschreibung
(``author``, ``title``, ``year`` …). Dieses Format erwartet auch der Validator.

``.bib`` ist strukturiert und wird exakt geparst. ``.txt`` und ``.pdf`` sind
unstrukturiert: Dort wird der Text in einzelne Quellen zerlegt und je Quelle per
Heuristik (DOI, Jahr, ISBN, URL, Autor/Titel) befüllt. Das ist absichtlich einfach
gehalten – die Treffer sind oft unvollständig, was der Validator dann korrekt als
Vollständigkeits-Findings meldet. Bei ``.pdf`` wird zusätzlich der Textlayer gebraucht;
reine Scans ohne Text führen zu einem klaren Fehler.
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

    def load(self, filename: str, content: bytes) -> list[dict]:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext == ".bib":
            return self._load_bib(content)
        if ext == ".txt":
            return self._load_txt(content)
        if ext == ".pdf":
            return self._load_pdf(content)
        raise ValueError(
            f"Format '{ext or '?'}' wird nicht unterstützt (nur .bib, .txt, .pdf)"
        )

    # ------------------------------------------------------------------ .bib

    def _load_bib(self, content: bytes) -> list[dict]:
        entries = bibtexparser.loads(content.decode("utf-8")).entries
        if not entries:
            raise ValueError("Keine Einträge gefunden.")
        return entries

    # ------------------------------------------------------------------ .txt / .pdf

    def _load_txt(self, content: bytes) -> list[dict]:
        text = content.decode("utf-8", errors="replace")
        return self._parse_references(self._split_references(text))

    def _load_pdf(self, content: bytes) -> list[dict]:
        text = self._pdf_text(content)
        section = self._references_section(text)
        return self._parse_references(self._split_references(section))

    @staticmethod
    def _pdf_text(content: bytes) -> str:
        try:
            parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
        except Exception as err:
            raise ValueError(f"PDF konnte nicht gelesen werden: {err}")
        text = "\n".join(parts).strip()
        if not text:
            raise ValueError(
                "PDF enthält keinen extrahierbaren Text (vermutlich ein Scan ohne Textschicht)."
            )
        return text

    @staticmethod
    def _references_section(text: str) -> str:
        """Schneidet ab der (letzten) Literaturverzeichnis-Überschrift ab."""
        lines = text.splitlines()
        start = None
        for i, line in enumerate(lines):
            if line.strip().lower().strip(":. ") in REF_HEADINGS:
                start = i + 1
        return "\n".join(lines[start:]) if start is not None else text

    @staticmethod
    def _split_references(text: str) -> list[str]:
        """Zerlegt einen Textblock in einzelne Quellen – drei Strategien, fallend."""
        text = text.strip()
        if not text:
            return []
        # 1) Nummeriert: "[1] …" oder "1. …" am Zeilenanfang
        numbered = re.split(r"\n(?=\s*(?:\[\d+\]|\d+\.\s))", text)
        if len(numbered) > 1:
            return [Importer._clean(b) for b in numbered if b.strip()]
        # 2) Einträge durch Leerzeilen getrennt
        blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
        if len(blocks) > 1:
            return [Importer._clean(b) for b in blocks]
        # 3) Fallback: eine Quelle pro Zeile
        return [Importer._clean(line) for line in text.splitlines() if line.strip()]

    @staticmethod
    def _clean(block: str) -> str:
        """Entfernt die Nummerierung und fasst Umbrüche zu einer Zeile zusammen."""
        block = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", block.strip())
        return re.sub(r"\s+", " ", block)

    def _parse_references(self, chunks: list[str]) -> list[dict]:
        entries = [
            self._parse_one(raw, n) for n, raw in enumerate(chunks, start=1) if raw
        ]
        if not entries:
            raise ValueError("Keine Einträge gefunden.")
        return entries

    @staticmethod
    def _parse_one(raw: str, position: int) -> dict:
        # ENTRYTYPE bleibt leer (Typ unbekannt) -> Validator verlangt author/title/year.
        # ID ist nur ein interner Handle; ein echter citekey existiert hier nicht.
        entry = {"ENTRYTYPE": "", "ID": f"ref{position}", "raw_text": raw}
        if m := DOI_FIND.search(raw):
            entry["doi"] = m.group(0).rstrip(".,;)")
        if m := URL_FIND.search(raw):
            entry["url"] = m.group(0).rstrip(".,;)")
        if m := YEAR_FIND.search(raw):
            entry["year"] = m.group(0)
        if m := ISBN_FIND.search(raw):
            entry["isbn"] = m.group(1).strip()
        author, title = Importer._guess_author_title(raw)
        if author:
            entry["author"] = author
        if title:
            entry["title"] = title
        return entry

    @staticmethod
    def _guess_author_title(raw: str) -> tuple[str, str]:
        """Heuristik: Autoren stehen meist vor dem Jahr, der Titel ist der Satz danach."""
        m = YEAR_FIND.search(raw)
        if m:
            author = raw[: m.start()].strip(" .,()")
            rest = raw[m.end() :].strip(" .,()")
            title = re.split(r"(?<=[.?!])\s", rest, maxsplit=1)[0].strip()
        else:
            parts = re.split(r"(?<=[.?!])\s", raw, maxsplit=1)
            author = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
        return author, title
