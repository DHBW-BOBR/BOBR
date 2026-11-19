"""Tests für den Importer (.bib strukturiert, .txt/.pdf heuristisch)."""

import pytest

from backend.importer import Importer

imp = Importer()


def test_bib_import():
    entries = imp.load(
        "r.bib", b"@article{a1, author={Smith, John}, title={T}, year={2020}}"
    )
    assert len(entries) == 1
    assert entries[0]["ID"] == "a1"
    assert entries[0]["ENTRYTYPE"] == "article"


def test_bib_empty_raises():
    with pytest.raises(ValueError):
        imp.load("r.bib", b"% nur ein Kommentar")


def test_txt_numbered():
    txt = (
        b"[1] Smith, John. 2020. A Great Paper. doi:10.1000/abc\n"
        b"[2] Doe, Jane. 2019. Another One."
    )
    entries = imp.load("r.txt", txt)
    assert len(entries) == 2
    assert entries[0]["doi"] == "10.1000/abc"
    assert entries[0]["year"] == "2020"
    assert entries[0]["author"] == "Smith, John"


def test_txt_isbn_and_url():
    txt = b"Mustermann, Max. 2018. Buch. ISBN 978-3-16-148410-0 https://example.org/x"
    e = imp.load("r.txt", txt)[0]
    assert e["isbn"].startswith("978")
    assert e["url"].startswith("https://")


def test_unsupported_format():
    with pytest.raises(ValueError):
        imp.load("x.docx", b"...")


def test_pdf_import(make_pdf):
    pdf = make_pdf(
        [
            "A Paper About Things",
            "Some intro paragraph.",
            "",
            "References",
            "[1] Smith, John. 2020. A Great Paper. doi:10.1000/abc",
            "[2] Doe, Jane. 2019. Another Study.",
        ]
    )
    entries = imp.load("r.pdf", pdf)
    assert len(entries) == 2  # Intro vor der Überschrift wird verworfen
    assert entries[0]["doi"] == "10.1000/abc"


def test_pdf_broken_raises():
    with pytest.raises(ValueError):
        imp.load("r.pdf", b"not a pdf at all")
