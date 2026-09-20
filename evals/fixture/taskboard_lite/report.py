import datetime


def summarize(rows, start=None, end=None, project=None):
    for boundary in (start, end):
        if boundary is not None:
            if datetime.date.fromisoformat(boundary).isoformat() != boundary:
                raise ValueError("invalid date")
    selected = [r for r in rows if (start is None or r["date"] >= start)
                and (end is None or r["date"] < end)
                and (project is None or r["project"] == project)]
    return {"count": len(selected), "minutes": sum(r["minutes"] for r in selected)}
