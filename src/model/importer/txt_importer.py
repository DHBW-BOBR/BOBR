"""Import von Literaturangaben aus reinen Textdateien (.txt)."""

from .base import ImportResult, FileImportError
from .reference_parser import parse_references_from_text


class TxtImporter:
    def import_file(self, path: str) -> ImportResult:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise FileImportError(
                f"Die Textdatei konnte nicht gelesen werden: {path} ({exc})"
            ) from exc

        entries, unparsed = parse_references_from_text(text, source_path=path)
        result = ImportResult(entries=entries, unparsed=unparsed)
        if unparsed:
            result.warnings.append(
                f"{len(unparsed)} Abschnitt(e) konnten nicht als Literaturangabe "
                f"erkannt werden."
            )
        if not entries:
            result.warnings.append("Keine Literaturangaben im Text erkannt.")
        return result
