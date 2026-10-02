#!/usr/bin/env python3
"""Independent Task02 boundary probe; the frozen grader omits compact ISO dates."""
import json
from pathlib import Path
import sys


def check(workspace):
    sys.path.insert(0, str(workspace))
    from taskboard_lite.report import summarize

    rows = [
        {"date": "2026-09-01", "minutes": 0, "project": "alpha"},
        {"date": "2026-09-02", "minutes": 7, "project": "alpha"},
    ]
    assert summarize(rows, start="2026-09-01", end="2026-09-02") == {"count": 1, "minutes": 0}
    assert summarize(rows, start="2026-09-02", end="2026-09-02") == {"count": 0, "minutes": 0}
    for boundary in ("20260901", "2026-W36-2", "2026-9-01", "2026-09-32", ""):
        for name in ("start", "end"):
            try:
                summarize(rows, **{name: boundary})
            except ValueError:
                continue
            raise AssertionError(f"accepted noncanonical or invalid {name}: {boundary!r}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: supervised_task02.py WORKSPACE")
    workspace = Path(sys.argv[1]).resolve()
    try:
        check(workspace)
    except Exception as error:
        print(json.dumps({"task": "02", "passed": False, "error": str(error)}))
        raise SystemExit(1)
    print(json.dumps({"task": "02", "passed": True}))
