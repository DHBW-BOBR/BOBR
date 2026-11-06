"""Führt die Prüfungen über die importierten Einträge aus.

Aktuell ist die Korrektheitsprüfung (Formatfehler) umgesetzt; Vollständigkeits-
und Konsistenzprüfung folgen in eigenen Issues.
"""

from model.validator.correctness import CorrectnessValidator


class ValidatorController:
    def __init__(self):
        self._validators = [CorrectnessValidator()]

    def run_validation(self, entries: list) -> list:
        """Lässt alle aktiven Validatoren laufen und sammelt die Befunde.

        Befunde werden zusätzlich an ``entry.issues`` angehängt (siehe Validatoren).
        """
        findings = []
        for validator in self._validators:
            findings.extend(validator.validate(entries))
        return findings
