import sqlite3


class Database:
    def __init__(self, db_path: str = "bobr.db"):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def close(self):
        if self.connection:
            self.connection.close()
