"""Steuert den Import und wählt anhand der Dateiendung den passenden Importer."""

import os

from model.importer.bib_importer import BibImporter
from model.importer.txt_importer import TxtImporter
from model.importer.pdf_importer import PdfImporter
from model.importer.base import FileImportError


class ImportController:
    def __init__(self):
        self._importers = {
            ".bib": BibImporter(),
            ".txt": TxtImporter(),
            ".pdf": PdfImporter(),
        }

    def handle_import(self, path: str):
        """Importiert eine Datei und liefert ein ``ImportResult``.

        Unbekannte Dateiendungen führen zu ``FileImportError``.
        """
        ext = os.path.splitext(path)[1].lower()
        importer = self._importers.get(ext)
        if importer is None:
            supported = ", ".join(sorted(self._importers))
            raise FileImportError(
                f"Nicht unterstütztes Dateiformat: '{ext or path}'. "
                f"Unterstützt werden: {supported}."
            )
        return importer.import_file(path)
