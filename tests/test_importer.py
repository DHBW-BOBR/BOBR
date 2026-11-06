"""Tests für die Importer-Schicht (.bib, .txt, .pdf) und den Referenz-Parser."""

from pathlib import Path

import pytest

from model.importer.bib_importer import BibImporter
from model.importer.txt_importer import TxtImporter
from model.importer.pdf_importer import PdfImporter
from model.importer.base import FileImportError
from model.importer.reference_parser import parse_references_from_text

FIXTURES = Path(__file__).parent / "fixtures"


# --- BibImporter -----------------------------------------------------------


def test_bib_import_valid():
    result = BibImporter().import_file(str(FIXTURES / "sample.bib"))
    assert len(result.entries) == 2

    by_key = {e.citekey: e for e in result.entries}
    smith = by_key["smith2020"]
    assert smith.entry_type == "article"
    assert smith.fields["doi"] == "10.1000/xyz123"
    assert smith.fields["year"] == "2020"
    assert smith.position == 0
    assert smith.raw_text.startswith("@article")


def test_bib_import_malformed_reports_but_continues():
    result = BibImporter().import_file(str(FIXTURES / "sample_malformed.bib"))
    # Der gültige Eintrag wird erkannt ...
    assert len(result.entries) == 1
    assert result.entries[0].citekey == "good2021"
    # ... der fehlerhafte Block wird gemeldet, nicht als Abbruch behandelt.
    assert result.warnings
    assert result.unparsed


def test_bib_import_missing_file_raises():
    with pytest.raises(FileImportError):
        BibImporter().import_file(str(FIXTURES / "does_not_exist.bib"))


# --- Referenz-Parser (rein, ohne Datei) ------------------------------------


def test_reference_parser_numbered_list():
    text = (
        "References\n"
        "[1] Smith, J. (2020). A study. Journal, 1(2), 3-4. "
        "https://doi.org/10.1000/xyz123\n"
        "[2] Doe, J. (2019). Another work. Publisher. https://example.org/x\n"
        "[3] kurzer hinweis ohne jahr\n"
    )
    entries, unparsed = parse_references_from_text(text)
    assert len(entries) == 2

    first = entries[0]
    assert first.fields["doi"] == "10.1000/xyz123"
    assert first.fields["year"] == "2020"
    assert first.raw_text  # Rohtext bleibt immer erhalten
    # Der dritte Block ist keine erkennbare Literaturangabe -> gemeldet.
    assert len(unparsed) == 1


def test_reference_parser_extracts_url_and_year():
    text = "Mustermann, M. (2021). Titel. https://example.com/artikel"
    entries, _ = parse_references_from_text(text)
    assert len(entries) == 1
    assert entries[0].fields["url"] == "https://example.com/artikel"
    assert entries[0].fields["year"] == "2021"


# --- TxtImporter -----------------------------------------------------------


def test_txt_import():
    result = TxtImporter().import_file(str(FIXTURES / "references.txt"))
    assert len(result.entries) == 2
    assert len(result.unparsed) == 1
    assert result.warnings  # Hinweis auf nicht erkannten Abschnitt


def test_txt_import_missing_file_raises():
    with pytest.raises(FileImportError):
        TxtImporter().import_file(str(FIXTURES / "nope.txt"))


# --- PdfImporter -----------------------------------------------------------


def test_pdf_import():
    result = PdfImporter().import_file(str(FIXTURES / "references.pdf"))
    assert len(result.entries) >= 2
    dois = [e.fields.get("doi") for e in result.entries]
    assert "10.1000/xyz123" in dois


def test_pdf_import_missing_file_raises():
    with pytest.raises(FileImportError):
        PdfImporter().import_file(str(FIXTURES / "nope.pdf"))
