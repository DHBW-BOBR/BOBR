"""Liest Literaturdateien ein und liefert eine Liste von Einträgen.

Was:
    Ein Eintrag ist ein Dict wie von bibtexparser v1: ``ENTRYTYPE`` (z. B.
    ``article``), ``ID`` (der BibTeX-Key) und die Felder in Kleinschreibung
    (``author``, ``title`` …). ``.bib`` ist strukturiert und wird exakt geparst.
    ``.txt`` und ``.pdf`` sind unstrukturiert: Der Text wird in einzelne Quellen
    zerlegt und je Quelle per Heuristik (DOI, Jahr, ISBN, URL, Autor/Titel)
    befüllt. Bei ``.pdf`` wird der Textlayer gebraucht; reine Scans ohne Text
    ergeben einen klaren Fehler.

Warum:
    Ein gemeinsames Eintragsformat für alle Dateitypen, damit der Validator nur
    eine Eingabe kennen muss. Das bibtexparser-Format wurde gewählt, weil .bib
    das wichtigste Eingabeformat ist und es dort ohne Umwandlung entsteht. Die
    Heuristik für .txt/.pdf ist bewusst einfach: Unvollständige Treffer meldet
    der Validator als Vollständigkeits-Findings, der Nutzer sieht also, was
    nicht erkannt wurde.

Alternativen:
    * GROBID oder anystyle (trainierte Modelle für Literaturangaben): deutlich
      bessere Erkennung bei .txt/.pdf, brauchen aber einen eigenen Dienst bzw.
      Ruby/Java; für den Prototyp zu schwergewichtig (siehe README).
    * bibtexparser v2: andere API (``parse_string``, Blöcke statt Dicts); das
      Projekt bleibt bei ``bibtexparser<2``, weil Importer, Validator und
      ``database.to_csl`` auf dem v1-Dict-Format aufbauen.
    * CSL-JSON als internes Format: wäre näher am Schema, hätte aber Validator
      und Tests komplett verändert; umgewandelt wird deshalb erst an der
      Datenbank-Grenze (``database.to_csl``).

Wichtig für die Persistenz: Der Importer muss deterministisch sein (gleiche
Datei -> gleiche Einträge in gleicher Reihenfolge). Die Prüfung liest die
gespeicherte Originaldatei erneut ein und ordnet Findings über die Position der
Einträge den gespeicherten Quellen zu.
"""

import io
import os
import re

import bibtexparser
import pdfplumber

# Muster für die Heuristik. Bewusst tolerant: lieber einen Wert zu viel finden
# und vom Validator prüfen lassen, als einen vorhandenen Wert zu übersehen.
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
    """Wählt anhand der Dateiendung den passenden Parser.

    Was: ``load(filename, content)`` liefert die Einträge oder wirft
        ``ValueError`` mit einer verständlichen Meldung.
    Warum: Eine Einstiegsstelle für alle Formate; die API muss nur einen Aufruf
        kennen. ``ValueError`` wird in der API zu HTTP 422.
    Alternativen: Format am Inhalt erkennen (MIME-Sniffing); unnötig, solange
        Nutzer Dateien mit korrekter Endung hochladen, und bei .txt vs. .bib
        nicht eindeutig.
    """

    def load(self, filename, content):
        """Parst ``content`` (Bytes) passend zur Endung von ``filename``."""
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
    """Parst eine .bib-Datei mit bibtexparser.

    Was: Gibt alle Einträge in Dateireihenfolge zurück, doppelte citekeys
        bleiben erhalten; ohne Einträge ``ValueError``.
    Warum: bibtexparser ist die etablierte Python-Bibliothek für BibTeX und
        liefert direkt das interne Eintragsformat.
    Alternativen: ``pybtex``; ebenfalls verbreitet, aber mit eigenem
        Datenmodell, das erst umgewandelt werden müsste.
    """
    entries = bibtexparser.loads(content.decode("utf-8")).entries
    if not entries:
        raise ValueError("Keine Einträge gefunden.")
    return entries


def parse_text(text):
    """Zerlegt Freitext in Quellen und parst jede davon.

    Was: ``split_references`` + ``parse_reference`` je Abschnitt; die Position
        (1, 2, 3 …) wird zur internen ID ``refN``.
    Warum: Trennung von „wo endet eine Quelle“ und „was steht in einer Quelle“
        hält beide Heuristiken einzeln test- und austauschbar.
    Alternativen: Eine einzige Regex für das ganze Verzeichnis; scheitert an der
        Vielfalt der Zitierstile.
    """
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
    """Holt den Text aus einem PDF (braucht einen Textlayer).

    Was: Text aller Seiten mit pdfplumber; Lesefehler und leere PDFs werden zu
        ``ValueError``.
    Warum: pdfplumber extrahiert Text zuverlässig und ist reines Python.
    Alternativen: OCR (z. B. Tesseract) für gescannte PDFs; braucht ein
        externes Programm und ist nicht Teil des aktuellen Umfangs. PyPDF2/pypdf
        liefert bei mehrspaltigen Layouts oft schlechtere Reihenfolgen.
    """
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
    """Schneidet alles vor der (letzten) Literaturverzeichnis-Überschrift ab.

    Was: Sucht Zeilen wie „Literaturverzeichnis“ oder „References“ und gibt den
        Text danach zurück; ohne Überschrift den ganzen Text.
    Warum: Bei einer ganzen Arbeit als PDF sollen nur die Quellen geprüft
        werden. Die *letzte* Überschrift, weil der Begriff auch im
        Inhaltsverzeichnis vorkommt.
    Alternativen: Nutzer markiert den Bereich selbst; mehr Aufwand in der
        Oberfläche.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower().strip(":. ") in REF_HEADINGS:
            start = i + 1
    if start is None:
        return text
    return "\n".join(lines[start:])


def split_references(text):
    """Zerlegt einen Textblock in einzelne Quellen (drei Strategien).

    Was: 1) nummeriert (``[1]`` / ``1.``), 2) durch Leerzeilen getrennt,
        3) eine Quelle pro Zeile. Die erste Strategie, die mehr als einen
        Abschnitt ergibt, gewinnt.
    Warum: Das sind die häufigsten Formen von Literaturverzeichnissen; die
        Reihenfolge geht vom eindeutigsten zum unsichersten Merkmal.
    Alternativen: Trennung an Autorennamen/Jahreszahlen (wie GROBID); deutlich
        aufwendiger und ohne trainiertes Modell fehleranfällig.
    """
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
    """Entfernt die Nummerierung und fasst Umbrüche zu einer Zeile zusammen.

    Was: ``"[3] Müller,\\n H. 2020 …"`` -> ``"Müller, H. 2020 …"``.
    Warum: Die Heuristiken in ``parse_reference`` arbeiten auf einer Zeile;
        die Nummer gehört nicht zur Quelle.
    Alternativen: Keine sinnvolle; Zeilenumbrüche im PDF sind Layout, kein Inhalt.
    """
    block = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", block.strip())
    return re.sub(r"\s+", " ", block)


def parse_reference(raw, position):
    """Erkennt per Heuristik die Felder in einem Referenz-String.

    Was: Sucht DOI, URL, Jahr, ISBN sowie Autor und Titel; ``ENTRYTYPE`` bleibt
        leer, ``ID`` ist ``ref<position>``, ``raw_text`` der Originaltext.
    Warum: ``ENTRYTYPE`` leer, weil der Typ aus Freitext nicht sicher erkennbar
        ist; der Validator verlangt dann die Grundfelder author/title/year.
        ``ref<position>`` ist nur ein interner Handle (einen echten citekey gibt
        es nicht, in der Datenbank bleibt ``citekey`` deshalb leer).
        ``raw_text`` landet unverändert in ``reference.raw_text``.
    Alternativen: Siehe Modul-Docstring (GROBID/anystyle).
    """
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
    """Heuristik für Autor und Titel.

    Was: Mit Jahreszahl: Autoren = Text vor dem Jahr, Titel = erster Satz danach
        (APA-ähnlich). Ohne Jahr: erster Satz = Autoren, Rest = Titel.
    Warum: Deckt die verbreiteten Autor-Jahr-Stile (APA, Harvard) ab, die in
        studentischen Arbeiten am häufigsten sind.
    Alternativen: Je Zitierstil eigene Regeln; erst sinnvoll, wenn der Stil
        bekannt ist (``project.citation_style`` im Schema ist dafür vorgesehen).
    """
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
