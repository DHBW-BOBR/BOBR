"""Tests für Formatprüfungen und den Korrektheits-Validator (Issue 3)."""

from model.literature import LiteratureEntry
from model.validator.correctness import CorrectnessValidator
from model.validator import format_checks as fc

# --- DOI -------------------------------------------------------------------


def test_doi_valid():
    assert fc.is_valid_doi("10.1000/xyz123")
    assert fc.is_valid_doi("https://doi.org/10.1000/xyz123")
    assert fc.is_valid_doi("doi:10.1109/5.771073")


def test_doi_invalid():
    assert not fc.is_valid_doi("not-a-doi")
    assert not fc.is_valid_doi("10.12/x")  # Registrant zu kurz
    assert not fc.is_valid_doi("11.1000/xyz123")  # falsches Präfix
    assert not fc.is_valid_doi("10.1000/")  # kein Suffix


# --- ISBN ------------------------------------------------------------------


def test_isbn10_valid():
    assert fc.is_valid_isbn10("0-306-40615-2")
    assert fc.is_valid_isbn10("080442957X")  # Prüfziffer X


def test_isbn10_invalid():
    assert not fc.is_valid_isbn10("0306406153")  # falsche Prüfziffer
    assert not fc.is_valid_isbn10("030640615")  # zu kurz


def test_isbn13_valid():
    assert fc.is_valid_isbn13("978-3-16-148410-0")


def test_isbn13_invalid():
    assert not fc.is_valid_isbn13("978-3-16-148410-1")  # falsche Prüfziffer
    assert not fc.is_valid_isbn13("978316148410")  # zu kurz


def test_isbn_dispatch():
    assert fc.is_valid_isbn("0-306-40615-2")
    assert fc.is_valid_isbn("978-3-16-148410-0")
    assert not fc.is_valid_isbn("12345")


# --- URL -------------------------------------------------------------------


def test_url_valid():
    assert fc.is_valid_url("https://example.org/pfad")
    assert fc.is_valid_url("http://localhost")


def test_url_invalid():
    assert not fc.is_valid_url("htp:/broken")
    assert not fc.is_valid_url("ftp://example.org")
    assert not fc.is_valid_url("https://")
    assert not fc.is_valid_url("kein link")


# --- CorrectnessValidator --------------------------------------------------


def test_validator_flags_bad_fields_per_entry():
    bad = LiteratureEntry(
        "book",
        {"doi": "not-a-doi", "isbn": "978-3-16-148410-1", "url": "htp:/broken"},
    )
    good = LiteratureEntry(
        "article",
        {
            "doi": "10.1000/xyz123",
            "isbn": "978-3-16-148410-0",
            "url": "https://example.org/x",
        },
    )

    findings = CorrectnessValidator().validate([bad, good])

    assert len(findings) == 3  # 3 fehlerhafte Felder, alle im "bad"-Eintrag
    assert len(bad.issues) == 3  # Befunde pro Eintrag angehängt
    assert len(good.issues) == 0
    assert {f.field for f in bad.issues} == {"doi", "isbn", "url"}


def test_validator_ignores_empty_fields():
    entry = LiteratureEntry("misc", {"doi": "", "title": "ohne ids"})
    findings = CorrectnessValidator().validate([entry])
    assert findings == []
    assert entry.issues == []
