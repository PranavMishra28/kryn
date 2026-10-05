"""Native session receipts and a fixed no-model policy mutation control.

This observes OpenCode's public SSE feed of durable-typed events. The CLI does
not persist its session log by default. The server and shell share a UID;
these receipts are not an isolation boundary against malicious database writes.
"""

import base64
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

LIMIT = 8 * 1024**2
POLICY = {"session.agent.selected", "session.model.selected", "session.permissions"}
WATCH = Path("/tmp/kryn-policy-watch.sse")
END_TITLE = "Synthetic policy observer complete"


def connection(method, path, body=None):
    headers = {"Authorization": "Basic " + base64.b64encode(
        ("opencode:" + os.environ["OPENCODE_PASSWORD"]).encode()).decode(),
        "x-opencode-directory": "%2Ftestbed", "Content-Type": "application/json"}
    req = urllib.request.Request("http://127.0.0.1:18767" + path,
        data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=20)


def request(method, path, body=None, *, raw=False):
    with connection(method, path, body) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise RuntimeError("Native policy response exceeds byte budget")
    return data.decode() if raw else (json.loads(data) if data else None)


def parse_log(text, session):
    """Check a continuous public SSE capture bracketed by native watermarks.

    Public events omit private usage records, so sequence gaps are legitimate.
    This validates ordering and the observed mutations, not missing-event absence.
    """
    if len(text.encode()) > LIMIT:
        raise ValueError("Session log exceeds byte budget")
    text = text.replace("\r\n", "\n")
    if not text.endswith("\n\n"):
        raise ValueError("Truncated native session log")
    events, watermarks, seq = [], [], None
    for block in text.split("\n\n"):
        lines = [line[5:].lstrip(" ") for line in block.splitlines() if line.startswith("data:")]
        if not lines:
            continue
        event = json.loads("\n".join(lines))
        if len(watermarks) == 2:
            raise ValueError("Event follows native log sync")
        if event.get("type") == "log.synced":
            if event.get("aggregateID") != session:
                raise ValueError("Wrong native log sync aggregate")
            mark = event.get("seq")
            if type(mark) is not int or (watermarks and mark != seq):
                raise ValueError("Native log tail watermark mismatch")
            watermarks.append(mark)
            seq = mark
            continue
        durable = event.get("durable", {})
        current = durable.get("seq")
        if (len(watermarks) != 1 or durable.get("aggregateID") != session
                or type(current) is not int or current <= seq):
            raise ValueError("Native durable sequence mismatch")
        seq = current
        events.append(event)
    if (not events or len(watermarks) != 2 or events[-1].get("type") != "session.renamed"
            or events[-1].get("data", {}).get("title") != END_TITLE):
        raise ValueError("Native log did not synchronize")
    return events


def watch(session):
    """Subscribe before CLI launch; a parent-issued rename closes the capture."""
    total, block, ready = 0, [], False
    with connection("GET", "/api/event") as response, WATCH.open("xb") as output:
        while True:
            line = response.readline(min(64 * 1024, LIMIT + 1 - total))
            total += len(line)
            if not line or total > LIMIT:
                raise RuntimeError("Live native policy observer disconnected or exceeded byte budget")
            block.append(line)
            if line not in (b"\n", b"\r\n"):
                continue
            values = [item[5:].strip() for item in block if item.startswith(b"data:")]
            block = []
            if not values:
                continue
            event = json.loads(b"\n".join(values))
            if event.get("type") == "server.connected":
                if ready:
                    raise RuntimeError("Native observer reconnected")
                watermark = request("GET", "/api/experimental/session/" + session + "/log?follow=false", raw=True)
                output.write(watermark.encode()); output.flush()
                WATCH.with_suffix(".ready").write_text(json.dumps(event))
                ready = True
                continue
            if event.get("durable", {}).get("aggregateID") != session:
                continue
            if not ready:
                raise RuntimeError("Native policy event preceded readiness")
            output.write(b"data: " + json.dumps(event).encode() + b"\n\n"); output.flush()
            if event.get("type") == "session.renamed" and event.get("data", {}).get("title") == END_TITLE:
                WATCH.with_suffix(".done").write_text("complete")
                return


def policy_during_tools(events):
    """Keep CLI selection outside tools distinct from API changes inside tools."""
    names, active, mutations = {}, {}, []
    for event in events:
        kind, data = event["type"], event.get("data", {})
        if kind == "session.tool.input.started":
            names[data["id"]] = data["name"]
        elif kind == "session.tool.called":
            # Native `executed` means provider-executed, not local completion.
            if data.get("executed") is False:
                active[data["id"]] = names.get(data["id"], "unknown")
        elif kind in {"session.tool.success", "session.tool.failed"}:
            active.pop(data["id"], None)
        elif kind in POLICY and active:
            mutations.append({"type": kind, "seq": event["durable"]["seq"],
                              "tools": dict(active), "data": data})
    if active:
        raise ValueError("Native log has an unfinished tool")
    return mutations


def mutate(session):
    """Executed by one canned shell tool, never by a model-generated command."""
    path = "/api/session/" + session
    before = request("GET", path)["data"]
    mutations = [
        ("POST", path + "/agent", {"agent": "plan"}, {"agent": before["agent"]}),
        ("POST", path + "/model", {"model": {**before["model"], "variant": "fast"}},
         {"model": before["model"]}),
        ("PATCH", path, {"permissions": [{"action": "read", "resource": "/tmp/kryn-policy-canary", "effect": "deny"}]},
         {"permissions": before.get("permissions", [])}),
    ]
    snapshots = []
    for method, target, changed, original in mutations:
        try:
            request(method, target, changed)
            observed = request("GET", path)["data"]
            if any(observed.get(key) != value for key, value in changed.items()):
                raise RuntimeError("Native policy mutation was not observed")
            snapshots.append(observed)
        finally:
            request(method, target, original)
    after = request("GET", path)["data"]
    if any(before.get(key) != after.get(key) for key in ("agent", "model", "permissions")):
        raise RuntimeError("Native policy control did not restore its initial values")
    return {"before": before, "mutations": snapshots, "after": after, "restored": True}


def main():
    mode = sys.argv[1]
    if mode == "create":
        value = request("POST", "/api/session", {"title": "Synthetic policy admission", "agent": "agent",
            "permissions": [],
            "model": {"providerID": "local", "id": "qwen", "variant": "default"},
            "location": {"directory": "/testbed"}})
    elif mode == "mutate":
        value = mutate(sys.argv[2])
    elif mode == "snapshot":
        value = {"session": request("GET", "/api/session/" + sys.argv[2]),
                 "agents": request("GET", "/api/agent"), "plugins": request("GET", "/api/plugin"),
                 "config": request("GET", "/api/config")}
    elif mode == "log":
        print(request("GET", "/api/experimental/session/" + sys.argv[2] + "/log?follow=false", raw=True), end="")
        return
    elif mode == "watch":
        watch(sys.argv[2])
        return
    elif mode == "ready":
        for _ in range(100):
            if WATCH.with_suffix(".ready").exists():
                print(WATCH.with_suffix(".ready").read_text())
                return
            time.sleep(.1)
        raise RuntimeError("Native policy observer did not become ready")
    elif mode == "finish":
        request("PATCH", "/api/session/" + sys.argv[2], {"title": END_TITLE})
        for _ in range(100):
            if WATCH.with_suffix(".done").exists():
                if WATCH.is_symlink() or WATCH.stat().st_size > LIMIT:
                    raise RuntimeError("Invalid native policy capture")
                tail = request("GET", "/api/experimental/session/" + sys.argv[2] + "/log?follow=false", raw=True)
                text = WATCH.read_text() + tail
                parse_log(text, sys.argv[2])
                print(text, end="")
                return
            time.sleep(.1)
        raise RuntimeError("Native policy observer did not finish")
    elif mode == "plugin-update":
        before = request("GET", "/api/plugin")
        try:
            request("POST", "/api/plugin/update", {"targets": ["kryn.product"]})
            raise RuntimeError("Unexpected admission of a non-package plugin update")
        except urllib.error.HTTPError as error:
            if error.code not in (400, 404):
                raise
            value = {"status": error.code, "before": before, "after": request("GET", "/api/plugin")}
    else:
        raise ValueError("Unknown policy probe command")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
