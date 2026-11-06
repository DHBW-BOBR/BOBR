"""Befund (Finding) der Validatoren.

Bildet eine Teilmenge des ``finding``-Schemas (v0.8) ab
"""

from dataclasses import dataclass


@dataclass
class Finding:
    rule_id: str  # auslösende Regel, z. B. "K01_doi_format"
    field: str  # betroffenes Feld, z. B. "doi"
    message: str  # verständliche Meldung für den Nutzer
    value: str = None  # geprüfter Wert (zur Anzeige)
    category: str = "correctness"  # completeness | consistency | correctness | network
    severity: str = "error"  # info | warning | error
    confidence: str = "confirmed"  # confirmed | likely | possible

    def __str__(self) -> str:
        return f"[{self.severity}] {self.field}: {self.message}"
