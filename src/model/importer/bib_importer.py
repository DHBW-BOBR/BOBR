"""Import von BibTeX-Dateien (.bib) mit bibtexparser v2."""

import logging

import bibtexparser

from ..literature import LiteratureEntry
from .base import ImportResult, FileImportError

# Fehlerhafte Blöcke werden sauber als Warnung gemeldet; die zusätzliche
# bibtexparser-Log-Meldung auf stderr unterdrücken wir.
logging.getLogger("bibtexparser").setLevel(logging.ERROR)


class BibImporter:
    def import_file(self, path: str) -> ImportResult:
        """Liest eine .bib-Datei und liefert strukturierte Einträge.

        - Nicht lesbare/dekodierbare Dateien -> ``FileImportError`` (Abbruch).
        - Einzelne syntaktisch fehlerhafte Blöcke werden gemeldet (``warnings``/
          ``unparsed``), brechen den Import aber nicht ab.
        """
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise FileImportError(
                f"Die Datei konnte nicht gelesen werden: {path} ({exc})"
            ) from exc

        try:
            library = bibtexparser.parse_string(text)
        except Exception as exc:  # defensiv: bibtexparser-interne Fehler
            raise FileImportError(
                f"Die BibTeX-Datei konnte nicht verarbeitet werden: {path} ({exc})"
            ) from exc

        result = ImportResult()
        for position, raw_entry in enumerate(library.entries):
            fields = {f.key: f.value for f in raw_entry.fields}
            result.entries.append(
                LiteratureEntry(
                    entry_type=raw_entry.entry_type,
                    fields=fields,
                    citekey=raw_entry.key,
                    raw_text=raw_entry.raw or "",
                    position=position,
                    source_path=path,
                )
            )

        for block in library.failed_blocks:
            snippet = (block.raw or "").strip().splitlines()
            head = snippet[0] if snippet else "(leer)"
            result.warnings.append(f"Fehlerhafter BibTeX-Block übersprungen: {head}")
            result.unparsed.append(block.raw or "")

        if not result.entries and not result.warnings:
            result.warnings.append("Keine BibTeX-Einträge in der Datei gefunden.")

        return result
