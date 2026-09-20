import csv
import datetime
import io

FIELDS = ("id", "project", "minutes", "date")


def validate(row):
    if set(row) != set(FIELDS) or not row["id"] or not row["project"]:
        raise ValueError("invalid fields")
    minutes = str(row["minutes"])
    if not minutes.isascii() or not minutes.isdecimal():
        raise ValueError("invalid minutes")
    date = str(row["date"])
    if datetime.date.fromisoformat(date).isoformat() != date:
        raise ValueError("invalid date")
    return dict(row, minutes=int(minutes))


def parse_rows(text):
    """Validate a CSV batch completely before a caller writes any rows."""
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames != list(FIELDS):
        raise ValueError("invalid fields")
    rows = [validate(row) for row in reader]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate id")
    return rows
