class LiteratureEntry:
    def __init__(self, entry_type: str, fields: dict):
        self.entry_type = entry_type
        self.fields = fields
        self.issues = []
