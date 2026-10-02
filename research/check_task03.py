#!/usr/bin/env python3
"""Development-only Task03 probe across report, CLI and HTTP project filters."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request


CASES = (("space name", 1, 4), ("a, Ω", 1, 7), ("Alpha", 1, 3),
         ("alpha", 1, 2), ("missing", 0, 0))
ROWS = [{"id": key, "project": project, "minutes": minutes, "date": "2026-09-01"}
        for key, project, minutes in (("s", "space name", 4), ("c", "a, Ω", 7),
                                      ("u", "Alpha", 3), ("a", "alpha", 2))]


def check(workspace):
    workspace = Path(workspace).resolve()
    if not (workspace / "taskboard_lite/report.py").is_file():
        raise ValueError("Missing candidate report module")
    sys.path.insert(0, str(workspace))
    from taskboard_lite.report import summarize
    for project, count, minutes in CASES:
        expected = {"count": count, "minutes": minutes}
        if summarize(ROWS, project=project) != expected:
            raise AssertionError(f"report filter failed: {project!r}")
    if summarize(ROWS) != {"count": 4, "minutes": 16}:
        raise AssertionError("unfiltered report changed")
    with tempfile.TemporaryDirectory(prefix="kryn-task03-") as tmp:
        temp = Path(tmp)
        csv_path = temp / "rows.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=("id", "project", "minutes", "date"))
            writer.writeheader()
            writer.writerows(ROWS)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
        for project, count, minutes in CASES:
            result = subprocess.run([sys.executable, "-B", "-m", "taskboard_lite.cli", "summary",
                                     str(csv_path), "--project", project], cwd=workspace, env=env,
                                    capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or json.loads(result.stdout) != {"count": count, "minutes": minutes}:
                raise AssertionError(f"CLI filter failed: {project!r}")
        db, port_file = temp / "rows.db", temp / "port"
        server = subprocess.Popen([sys.executable, "-B", "-m", "taskboard_lite.server",
                                   "--db", str(db), "--seed", str(csv_path), "--port", "0",
                                   "--port-file", str(port_file)], cwd=workspace, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not port_file.exists() and server.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            if not port_file.exists():
                raise AssertionError("candidate HTTP server did not start")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            base = "http://127.0.0.1:" + port_file.read_text().strip()
            for project, count, minutes in CASES:
                url = base + "/api/summary?project=" + urllib.parse.quote(project)
                with opener.open(url, timeout=5) as response:
                    if response.status != 200 or json.load(response) != {"count": count, "minutes": minutes}:
                        raise AssertionError(f"HTTP filter failed: {project!r}")
        finally:
            server.terminate()
            try:
                server.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
                server.communicate(timeout=3)


if __name__ == "__main__":
    try:
        check(sys.argv[1])
    except Exception as error:
        print(json.dumps({"task": "03", "passed": False, "error": str(error)}))
        raise SystemExit(1)
    print(json.dumps({"task": "03", "passed": True}))
