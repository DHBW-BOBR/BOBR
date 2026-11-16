"""Tests für die vier Prüfungen. Crossref wird abgeschaltet oder gemockt (kein Netz)."""

from backend.validator import Validator


def check(entries):
    return Validator(use_crossref=False).check(entries)


def test_completeness_missing_fields():
    findings = check(
        [{"ENTRYTYPE": "article", "ID": "a", "title": "T", "year": "2020"}]
    )
    comp = [f for f in findings if f["category"] == "completeness"]
    assert comp and "author" in comp[0]["message"]


def test_doi_format_invalid():
    findings = check(
        [
            {
                "ENTRYTYPE": "misc",
                "ID": "a",
                "author": "X",
                "title": "T",
                "year": "2020",
                "doi": "not-a-doi",
            }
        ]
    )
    assert any(f["category"] == "correctness" and "DOI" in f["field"] for f in findings)


def test_isbn_checksum():
    base = {
        "ENTRYTYPE": "book",
        "ID": "a",
        "author": "X",
        "title": "T",
        "year": "2020",
        "publisher": "P",
    }
    bad = check([{**base, "isbn": "978-3-16-148410-1"}])  # falsche Prüfziffer
    good = check([{**base, "isbn": "978-3-16-148410-0"}])  # korrekt
    assert any("ISBN" in f["message"] for f in bad)
    assert not any("ISBN" in f["message"] for f in good)


def test_duplicates():
    entries = [
        {
            "ENTRYTYPE": "article",
            "ID": "a",
            "author": "X",
            "title": "Deep Learning for Cats",
            "journal": "J",
            "year": "2020",
        },
        {
            "ENTRYTYPE": "article",
            "ID": "b",
            "author": "Y",
            "title": "Deep Learning for Cats",
            "journal": "J",
            "year": "2021",
        },
    ]
    assert any(f["field"] == "Duplikat" for f in check(entries))


def test_crossref_mocked(monkeypatch):
    monkeypatch.setattr(
        Validator,
        "_check_crossref",
        lambda self, e: ("Jahr weicht ab", "2020 ≠ 2021", "year = 2021"),
    )
    v = Validator(use_crossref=True, rate_limit=0)
    findings = v.check(
        [
            {
                "ENTRYTYPE": "article",
                "ID": "a",
                "author": "X",
                "title": "T",
                "journal": "J",
                "year": "2020",
                "doi": "10.1/x",
            }
        ]
    )
    hit = [
        f
        for f in findings
        if f["category"] == "consistency" and f["field"] == "Crossref"
    ]
    assert hit and hit[0]["suggestion"] == "year = 2021"
