"""Schlanker Kommandozeilen-Einstieg zum Durchspielen des Ablaufs ohne GUI.

    python src/cli.py <datei.bib|.txt|.pdf>

Importiert die Datei, führt die Korrektheitsprüfung aus und gibt Einträge,
Befunde und nicht erkannte Inhalte aus.
"""

import sys

from controller.import_controller import ImportController
from controller.validator_controller import ValidatorController
from model.importer.base import FileImportError


def run(path: str) -> int:
    import_controller = ImportController()
    validator_controller = ValidatorController()

    try:
        result = import_controller.handle_import(path)
    except FileImportError as exc:
        print(f"Import abgebrochen: {exc}", file=sys.stderr)
        return 1

    print(f"Import aus: {path}")
    print(f"Erkannte Einträge: {len(result.entries)}")

    for warning in result.warnings:
        print(f"  ! {warning}")

    findings = validator_controller.run_validation(result.entries)

    print("\n--- Einträge ---")
    for entry in result.entries:
        label = entry.citekey or entry.fields.get("title") or "(ohne Titel)"
        print(f"[{entry.position}] {entry.entry_type}: {label}")
        for key, value in entry.fields.items():
            print(f"      {key}: {value}")
        for issue in entry.issues:
            print(f"      ✗ {issue}")

    print(f"\n--- Befunde (Korrektheit): {len(findings)} ---")
    for finding in findings:
        print(f"  {finding.rule_id}  {finding}  (Wert: {finding.value})")

    if result.unparsed:
        print(f"\n--- Nicht erkannte Inhalte: {len(result.unparsed)} ---")
        for chunk in result.unparsed:
            preview = chunk[:120] + ("…" if len(chunk) > 120 else "")
            print(f"  ? {preview}")

    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Verwendung: python src/cli.py <datei.bib|.txt|.pdf>", file=sys.stderr)
        return 2
    return run(argv[0])


if __name__ == "__main__":
    raise SystemExit(main())
