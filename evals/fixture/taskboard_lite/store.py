import sqlite3


class Store:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, project TEXT NOT NULL, minutes INTEGER NOT NULL, date TEXT NOT NULL)")

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def entries(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM entries ORDER BY id")]

    def add(self, rows):
        try:
            with self.connect() as db:
                db.executemany("INSERT INTO entries VALUES (:id, :project, :minutes, :date)", rows)
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate id") from exc

    def update(self, row):
        with self.connect() as db:
            result = db.execute("UPDATE entries SET project=:project, minutes=:minutes, date=:date WHERE id=:id", row)
            if result.rowcount != 1:
                raise ValueError("unknown id")
