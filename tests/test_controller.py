"""Tests für die Controller-Verdrahtung (Import-Dispatch + Validierung)."""

from pathlib import Path

import pytest

from controller.import_controller import ImportController
from controller.validator_controller import ValidatorController
from model.importer.base import FileImportError

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_controller_dispatches_by_extension():
    result = ImportController().handle_import(str(FIXTURES / "sample.bib"))
    assert len(result.entries) == 2


def test_import_controller_rejects_unknown_extension():
    with pytest.raises(FileImportError):
        ImportController().handle_import("irgendwas.csv")


def test_validator_controller_runs_correctness():
    result = ImportController().handle_import(str(FIXTURES / "sample.bib"))
    findings = ValidatorController().run_validation(result.entries)
    # mueller2019 hat eine ungültige DOI und eine ungültige URL.
    fields = sorted(f.field for f in findings)
    assert fields == ["doi", "url"]
