"""Gemeinsame Typen für die Importer-Schicht."""

from dataclasses import dataclass, field


class FileImportError(Exception):
    """Fataler Importfehler: Datei nicht lesbar, falsches Format o. Ä.

    Wird von den Importern geworfen, wenn der Import komplett abgebrochen werden
    muss (Akzeptanzkriterium: „mit einer Meldung abgebrochen"). Nicht für einzelne
    fehlerhafte Einträge verwenden – die landen als Warnung in ``ImportResult``.
    """


@dataclass
class ImportResult:
    """Ergebnis eines Imports.

    ``entries``  -- erfolgreich erkannte Literatureinträge.
    ``warnings`` -- nicht-fatale Hinweise (z. B. fehlerhafte .bib-Blöcke).
    ``unparsed`` -- Rohtext-Abschnitte, die nicht als Literaturangabe erkannt
                    wurden (Akzeptanzkriterium: „Nicht erkannte Inhalte werden
                    dem Nutzer gemeldet").
    """

    entries: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    unparsed: list = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)
