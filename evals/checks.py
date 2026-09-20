"""External deterministic graders. Execute against one disposable workspace only."""
import argparse
import ast
import csv
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent


class Checks(unittest.TestCase):
    workspace = None

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(cls.workspace))
        cls.parse = importlib.import_module("taskboard_lite.parse")
        cls.report = importlib.import_module("taskboard_lite.report")
        cls.rows = cls.parse.parse_rows((cls.workspace / "data/entries.csv").read_text())

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", "-m", "taskboard_lite.cli", *map(str, args)], cwd=self.workspace, text=True, capture_output=True, timeout=10)
        return result.returncode, json.loads(result.stdout)

    def test_original(self):
        self.assertEqual(self.report.summarize(self.rows), {"count": 3, "minutes": 75})
        self.assertEqual(len(self.rows), 3)
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_existing"], cwd=self.workspace, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_comprehension(self):
        result = json.loads((self.workspace / "answer.json").read_text())
        expected = {"cli": "taskboard_lite.cli:main", "store": "taskboard_lite.store:Store",
                    "validator": "taskboard_lite.parse:parse_rows", "summary": "taskboard_lite.report:summarize",
                    "http_chain": ["taskboard_lite.server:Handler.do_POST", "taskboard_lite.parse:validate", "taskboard_lite.store:Store.add"],
                    "all": {"count": 3, "minutes": 75}, "day_one": {"count": 2, "minutes": 30}, "alpha": {"count": 2, "minutes": 75}}
        self.assertEqual(result, expected)

    def test_ranges(self):
        self.assertEqual(self.report.summarize(self.rows, "2026-09-01", "2026-09-02"), {"count": 2, "minutes": 30})
        self.assertEqual(self.report.summarize(self.rows, "2026-09-02", "2026-09-03"), {"count": 1, "minutes": 45})
        self.assertEqual(self.report.summarize(self.rows, "2026-09-02", "2026-09-02"), {"count": 0, "minutes": 0})
        self.assertEqual(self.report.summarize(self.rows, end="2026-09-01"), {"count": 0, "minutes": 0})
        with self.assertRaises(ValueError):
            self.report.summarize(self.rows, start="2026-02-30")

    def test_filter(self):
        rows = self.rows + [{"id": "x", "project": "a, Ω", "minutes": 7, "date": "2026-09-01"}]
        for project, count, total in [("beta", 1, 0), ("alpha", 2, 75), ("Alpha", 0, 0), ("missing", 0, 0), ("a, Ω", 1, 7)]:
            self.assertEqual(self.report.summarize(rows, project=project), {"count": count, "minutes": total})
        code, result = self.cli("summary", "data/entries.csv", "--project", "beta")
        self.assertEqual((code, result), (0, {"count": 1, "minutes": 0}))

    def test_csv(self):
        for prefix in ("", "\ufeff"):
            text = prefix + 'id,project,minutes,date\r\nx,"a, Ω",0,2026-09-01\r\n'
            self.assertEqual(self.parse.parse_rows(text), [{"id": "x", "project": "a, Ω", "minutes": 0, "date": "2026-09-01"}])
        for bad in ("-1", "1.5", "", "NaN"):
            with self.assertRaises(ValueError):
                self.parse.parse_rows(f"id,project,minutes,date\nx,a,{bad},2026-09-01\n")
        with self.assertRaises(ValueError):
            self.parse.parse_rows("id,project,minutes,date\nx,a,1,2026-09-01\nx,b,2,2026-09-01\n")
        code, result = self.cli("validate", "data/bom.csv")
        self.assertEqual(code, 0, result)
        self.assertEqual(result[0]["project"], "café, Ω")

    def test_shared_validation(self):
        for name in ("cli.py", "server.py"):
            tree = ast.parse((self.workspace / "taskboard_lite" / name).read_text())
            self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == "parse" and any(a.name == "parse_rows" for a in n.names) for n in ast.walk(tree)), name)
            self.assertFalse(any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ("parse_rows", "validate") for n in ast.walk(tree)), name)

    def test_context_constraints(self):
        self.assertEqual(json.loads((self.workspace / "context-summary.json").read_text()), {"report_label": "September review", "zero_minutes": "include", "project_match": "exact"})

    def test_vision_answer(self):
        result = json.loads((self.workspace / "vision-answer.json").read_text())
        self.assertEqual(set(result), {"status", "pending", "clipped_control"})
        self.assertEqual(str(result["status"]).strip().casefold(), "offline")
        self.assertEqual(result["pending"], 7)
        self.assertIn(str(result["clipped_control"]).strip().casefold(), ("save", "save button"))

    def test_http(self):
        with tempfile.TemporaryDirectory(prefix="http-", dir=self.workspace.parent) as tmp:
            tmp = Path(tmp)
            port_file, db = tmp / "port", tmp / "test.db"
            with (tmp / "server.log").open("w") as log:
                proc = subprocess.Popen([sys.executable, "-B", "-m", "taskboard_lite.server", "--db", str(db), "--seed", "data/entries.csv", "--port", "0", "--port-file", str(port_file)], cwd=self.workspace, stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 10
                    while not port_file.exists() and proc.poll() is None and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(port_file.exists(), (tmp / "server.log").read_text())
                    base = "http://127.0.0.1:" + port_file.read_text()
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

                    def request(path, body=None, method=None, raw=False):
                        data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
                        req = urllib.request.Request(base + path, data=data, method=method)
                        try:
                            response = opener.open(req, timeout=5)
                        except urllib.error.HTTPError as exc:
                            response = exc
                        with response:
                            content = response.read().decode()
                            return response.status, content if raw else json.loads(content)

                    self.assertEqual(request("/api/summary"), (200, {"count": 3, "minutes": 75}))
                    if self.task in ("03", "10", "12"):
                        self.assertEqual(request("/api/summary?project=beta"), (200, {"count": 1, "minutes": 0}))
                    if self.task in ("04", "05", "12"):
                        bad = "id,project,minutes,date\nx,a,1,2026-09-01\ny,b,-1,2026-09-01\n"
                        self.assertEqual(request("/api/import", bad)[0], 400)
                        self.assertEqual(len(request("/api/entries")[1]), 3)
                        self.assertEqual(request("/api/import", "id,project,minutes,date\nx,a,1,2026-09-01\nt1,a,1,2026-09-01\n")[0], 400)
                        self.assertEqual(len(request("/api/entries")[1]), 3)
                    if self.task in ("06", "12"):
                        row = {"id": "new", "project": "z", "minutes": 6, "date": "2026-09-03"}
                        db.with_suffix(".fail-next").touch()
                        self.assertEqual(request("/api/entries", row)[0], 503)
                        self.assertEqual(len(request("/api/entries")[1]), 3)
                        self.assertEqual(request("/api/entries", row)[0], 201)
                        self.assertEqual(len(request("/api/entries")[1]), 4)
                        self.assertEqual(request("/api/entries", dict(row, id="invalid", minutes=-1))[0], 400)
                    if self.task == "12":
                        imported = 'id,project,minutes,date\nu,"café, Ω",9,2026-09-04\n'
                        self.assertEqual(request("/api/import", imported)[0], 201)
                        self.assertEqual(request("/api/import", imported)[0], 400)
                        self.assertEqual(request("/api/entries/new", dict(row, minutes=11), "PATCH")[0], 200)
                        code, exported = request("/api/export", raw=True)
                        self.assertEqual(code, 200)
                        exported_rows = self.parse.parse_rows(exported)
                        self.assertEqual(len(exported_rows), 5)
                        self.assertEqual(next(r for r in exported_rows if r["id"] == "new")["minutes"], 11)
                        self.assertEqual(next(r for r in exported_rows if r["id"] == "t1")["minutes"], 30)
                finally:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)


TESTS = {
    "01": ["test_original", "test_comprehension"],
    "02": ["test_original", "test_ranges"],
    "03": ["test_original", "test_filter", "test_http"],
    "04": ["test_original", "test_csv", "test_shared_validation", "test_http"],
    "05": ["test_original", "test_csv", "test_http"],
    "06": ["test_original", "test_http"],
    "07": [], "08": ["test_vision_answer"], "09": ["test_original"],
    "10": ["test_original", "test_ranges", "test_filter", "test_http", "test_context_constraints"],
    "11": [], "12": ["test_original", "test_http"],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=TESTS)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    Checks.workspace, Checks.task = args.workspace.resolve(), args.task
    suite = unittest.TestSuite(Checks(name) for name in TESTS[args.task])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful()}))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
