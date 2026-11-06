"""Import von Literaturangaben aus PDF-Dateien (.pdf).

Textextraktion via pdfplumber; die eigentliche Erkennung übernimmt der gemeinsame
Referenz-Parser. Funktioniert am besten mit maschinell erzeugten (nicht
gescannten) PDFs.
"""

import pdfplumber

from .base import ImportResult, FileImportError
from .reference_parser import parse_references_from_text


class PdfImporter:
    def import_file(self, path: str) -> ImportResult:
        try:
            pages_text = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    pages_text.append(page.extract_text() or "")
        except FileNotFoundError as exc:
            raise FileImportError(
                f"Die PDF-Datei wurde nicht gefunden: {path}"
            ) from exc
        except Exception as exc:  # defekte/unlesbare PDF
            raise FileImportError(
                f"Die PDF-Datei konnte nicht gelesen werden: {path} ({exc})"
            ) from exc

        text = "\n".join(pages_text)
        entries, unparsed = parse_references_from_text(text, source_path=path)
        result = ImportResult(entries=entries, unparsed=unparsed)

        if not text.strip():
            result.warnings.append(
                "Aus der PDF konnte kein Text extrahiert werden "
                "(evtl. ein gescanntes Dokument ohne Textebene)."
            )
        if unparsed:
            result.warnings.append(
                f"{len(unparsed)} Abschnitt(e) konnten nicht als Literaturangabe "
                f"erkannt werden."
            )
        if not entries:
            result.warnings.append("Keine Literaturangaben in der PDF erkannt.")
        return result
