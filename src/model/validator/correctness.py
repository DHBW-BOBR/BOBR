"""Korrektheitsprüfung: Formatfehler in strukturierten Feldern (ohne externe API).

Deckt Anforderung F5 ab: DOI-Format, ISBN-10/13-Checksumme, URL-Format.
"""

from .finding import Finding
from . import format_checks


class CorrectnessValidator:
    # (Feldname, Prüffunktion, rule_id, Beschreibung des erwarteten Formats)
    _CHECKS = [
        (
            "doi",
            format_checks.is_valid_doi,
            "K01_doi_format",
            "DOI entspricht nicht dem Schema 10.XXXX/...",
        ),
        (
            "isbn",
            format_checks.is_valid_isbn,
            "K02_isbn_checksum",
            "ISBN ist ungültig (Prüfziffer/Länge stimmt nicht).",
        ),
        (
            "url",
            format_checks.is_valid_url,
            "K03_url_format",
            "URL hat kein gültiges Format (erwartet: http(s)://host/...).",
        ),
    ]

    def validate(self, entries: list) -> list:
        """Prüft alle Einträge und liefert eine flache Liste aller Befunde.

        Zusätzlich wird jeder Befund an ``entry.issues`` angehängt, damit die GUI
        Fehler pro Eintrag anzeigen kann.
        """
        findings = []
        for entry in entries:
            for field_name, check, rule_id, message in self._CHECKS:
                value = entry.fields.get(field_name)
                if value is None or str(value).strip() == "":
                    continue  # leere/fehlende Felder sind Sache der Vollständigkeitsprüfung
                if not check(value):
                    finding = Finding(
                        rule_id=rule_id,
                        field=field_name,
                        message=message,
                        value=str(value),
                        category="correctness",
                        severity="error",
                    )
                    entry.issues.append(finding)
                    findings.append(finding)
        return findings
