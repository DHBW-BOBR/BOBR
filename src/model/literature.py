class LiteratureEntry:
    """Ein einzelner Literatureintrag, unabhängig vom Quellformat (.bib/.txt/.pdf).

    Die Felder werden bewusst mit BibTeX-Feldnamen (author, title, year, doi,
    isbn, url, ...) in ``fields`` gehalten. Das hält den Import einfach und lässt
    sich später verlustarm auf das ``reference``-Schema (data_original/data_current
    als CSL-JSON) abbilden:

    - ``citekey``    -> reference.citekey
    - ``raw_text``   -> reference.raw_text
    - ``position``   -> reference.position
    - ``entry_type`` -> reference.reference_type
    """

    def __init__(
        self,
        entry_type: str,
        fields: dict,
        citekey: str = None,
        raw_text: str = "",
        position: int = None,
        source_path: str = None,
    ):
        self.entry_type = entry_type
        self.fields = fields
        self.citekey = citekey
        self.raw_text = raw_text
        self.position = position
        self.source_path = source_path
        # Befunde (Findings) der Validatoren, pro Eintrag gesammelt.
        self.issues = []

    def __repr__(self) -> str:
        label = self.citekey or self.fields.get("title", "")
        return f"LiteratureEntry({self.entry_type!r}, {label!r}, issues={len(self.issues)})"
