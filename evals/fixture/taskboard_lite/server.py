import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, unquote
from .parse import parse_rows, validate, FIELDS
from .report import summarize
from .store import Store

WEB = Path(__file__).parent.parent / "web"


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type="application/json"):
        payload = json.dumps(body).encode() if content_type == "application/json" else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        url = urlsplit(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
        try:
            if url.path == "/api/entries":
                return self.reply(200, self.server.store.entries())
            if url.path == "/api/summary":
                return self.reply(200, summarize(self.server.store.entries(), query.get("start"), query.get("end"), query.get("project")))
            if url.path == "/api/export":
                output = io.StringIO(newline="")
                writer = csv.DictWriter(output, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(self.server.store.entries())
                return self.reply(200, output.getvalue(), "text/csv")
            files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
            if url.path in files:
                name, kind = files[url.path]
                return self.reply(200, (WEB / name).read_text(), kind)
            return self.reply(404, {"error": "not found"})
        except ValueError as exc:
            return self.reply(400, {"error": str(exc)})

    def do_POST(self):
        # The evaluator controls this disposable marker to inject exactly one failure.
        if self.server.fail_next.exists():
            self.server.fail_next.unlink()
            return self.reply(503, {"error": "temporary failure"})
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8")
            if self.path == "/api/import":
                rows = parse_rows(body)
            elif self.path == "/api/entries":
                rows = [validate(json.loads(body))]
            else:
                return self.reply(404, {"error": "not found"})
            self.server.store.add(rows)
            return self.reply(201, {"count": len(rows)})
        except (ValueError, TypeError, KeyError) as exc:
            return self.reply(400, {"error": str(exc)})

    def do_PATCH(self):
        try:
            row = validate(json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0")))))
            if self.path != "/api/entries/" + row["id"]:
                return self.reply(400, {"error": "id mismatch"})
            self.server.store.update(row)
            return self.reply(200, row)
        except (ValueError, TypeError, KeyError) as exc:
            return self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--port-file", type=Path)
    parser.add_argument("--seed", type=Path)
    args = parser.parse_args()
    store = Store(args.db)
    if args.seed and not store.entries():
        store.add(parse_rows(args.seed.read_text(encoding="utf-8")))
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    server.store = store
    server.fail_next = args.db.with_suffix(".fail-next")
    if args.port_file:
        args.port_file.write_text(str(server.server_port))
    print(f"http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
