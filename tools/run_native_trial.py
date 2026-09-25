#!/usr/bin/env python3
"""Record one native OpenCode turn on an already prepared disposable fixture.

This is a CLI test driver, not an agent loop. It never edits candidate code or grades it.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.parse import quote

from native_client import BINARY, MODEL_ID, ROOT, NativeServer, owned_config
from protocol_probe import memory_snapshot, request as protocol_request
from context_probe import ResourceGuard, resources, summarize_resources


def power_source():
    try:
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5)
        match = re.search(r"Now drawing from '([^']+)'", result.stdout) if result.returncode == 0 else None
        return match.group(1) if match else None
    except (OSError, subprocess.TimeoutExpired):
        return None


EXA_TOOLS = {"search_web_fetch_exa", "search_web_search_advanced_exa", "search_web_search_exa"}


class NativeResourceGuard:
    """Resource sampling only; the main thread owns all native HTTP/control calls."""
    def __init__(self, folder, samples):
        self.samples = samples
        self.guard = ResourceGuard(512 * 1024**2, 2)
        self.cancel, self.stop = threading.Event(), threading.Event()
        self.log = (folder / "resources.jsonl").open("x")
        self.watcher = None
        self.preflight_passed = False

    def sample(self):
        try:
            item = resources("http://127.0.0.1:8000")
        except Exception as error:
            item = {"unavailable": type(error).__name__}
        reason = self.guard.check(item)
        if reason:
            item["guard_reason"] = reason
            self.cancel.set()
        self.samples.append(item)
        try:
            self.log.write(json.dumps(item) + "\n")
            self.log.flush()
        except Exception:
            self.guard.reason = "resource evidence write failed"
            self.cancel.set()
            raise

    def start(self):
        for index in range(3):
            self.sample()
            if self.cancel.is_set() or self.samples[-1].get("pressure_level") != 1:
                self.guard.reason = self.guard.reason or "resource preflight was not green; no prompt sent"
                self.cancel.set()
                raise RuntimeError(self.guard.reason)
            if index < 2:
                time.sleep(2)
        def poll():
            while not self.stop.wait(2):
                try:
                    self.sample()
                except Exception:
                    return  # sample() has already signalled main-thread cancellation.
        self.watcher = threading.Thread(target=poll, daemon=True, name="native-resource-guard")
        self.preflight_passed = True
        self.watcher.start()

    def close(self):
        self.stop.set()
        if self.watcher is not None:
            self.watcher.join()  # resources() uses individually bounded local commands.
        try:
            self.sample()
        finally:
            self.log.close()


def guarded_communicate(child, prompt, timeout, cancel):
    """Retry communicate safely: supply stdin once, never resend after a timeout."""
    deadline, first = time.monotonic() + timeout, True
    while True:
        if cancel.is_set():
            return "resource_guard"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "timeout"
        try:
            child.communicate(input=prompt if first else None, timeout=min(.5, remaining))
            return "resource_guard" if cancel.is_set() else None
        except subprocess.TimeoutExpired:
            first = False


def runtime_is_idle(folder, label, timeout=3):
    response = protocol_request("http://127.0.0.1:8000", folder, label, "/api/status", timeout=timeout)
    state = response.get("json") or {}
    return (response.get("http_status") == 200 and not response.get("transport_error")
            and state.get("default_model") == MODEL_ID
            and all(type(state.get(k)) is int and state[k] == 0 for k in ("active_requests", "waiting_requests")))


def manual_compaction(server, session_id, workspace, folder, cancel=None):
    """Request one native checkpoint, then wait for its persisted result."""
    route = "/api/experimental/session/" + session_id + "/export"
    def owned_export():
        exported = server.request("GET", route, timeout=5)
        info = exported.get("data", {}).get("info", {})
        if (info.get("id") != session_id or
                Path(info.get("location", {}).get("directory", "")).resolve() != workspace.resolve() or
                info.get("model", {}).get("providerID") != "local" or
                info.get("model", {}).get("id") != "qwen"):
            raise RuntimeError("Refused compaction export outside the owned local fixture")
        return exported
    previous = {m.get("id") for m in owned_export()["data"]["messages"] if m.get("type") == "compaction"}
    admitted = server.request("POST", "/api/session/" + session_id + "/compact", {}, timeout=5)
    if admitted.get("data", {}).get("type") != "compaction":
        raise RuntimeError("Native manual compaction was not admitted")
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if cancel is not None and cancel.is_set():
            break
        exported = owned_export()
        rows = [m for m in exported["data"]["messages"]
                if m.get("type") == "compaction" and m.get("id") not in previous]
        if rows and rows[-1].get("status") in {"completed", "failed"}:
            row = rows[-1]
            summary = row.get("summary", "")
            contradiction = bool((workspace / "TASK.md").is_file() and (workspace / "TASK.md").read_text().strip() and
                re.search(r"\b(?:no user (?:conversation|input|task)|no active task|no task (?:objective|context))\b", summary, re.I))
            result = {"admitted": True, "message_id": row.get("id"),
                      "status": row.get("status"), "completed": row.get("status") == "completed",
                      "summary_headings": re.findall(r"^## .+$", summary, re.M),
                      "obvious_task_contradiction": contradiction,
                      "semantic_qualification": "FAIL" if contradiction else "NOT_ESTABLISHED"}
            (folder / "manual-compaction.json").write_text(json.dumps(result, indent=2) + "\n")
            return result
        time.sleep(1)
    settlement = settle_owned_sessions(server, session_id, workspace, folder, interrupt=True, cancel=cancel)
    result = {"admitted": True, "completed": False, "status": "resource_abort" if cancel and cancel.is_set() else "timeout",
              "owned_settlement": settlement}
    (folder / "manual-compaction.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def settle_owned_sessions(server, root_id, workspace, folder, interrupt=False, cancel=None):
    """Metadata-first bounded traversal. Never interrupt unrelated native sessions."""
    result = {"interrupt_requested": interrupt, "verified_sessions": [], "interrupts": [], "idle": False}
    deadline, quiet, sent, previous = time.monotonic() + 30, 0, set(), None
    label = "guard-idle-" + str(time.monotonic_ns())
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise RuntimeError("Owned-session settlement exceeded 30 seconds")
        return min(3, value)
    def request(method, path, body=None):
        return server.request(method, path, body, timeout=remaining())
    try:
        for attempt in range(60):
            if cancel is not None and cancel.is_set():
                interrupt = result["resource_abort"] = result["interrupt_requested"] = True
            pending, found = [(root_id, None)], set()
            while pending:
                sid, parent = pending.pop(0)
                if sid in found or len(found) >= 64 or not re.fullmatch(r"ses_[A-Za-z0-9]+", sid):
                    raise RuntimeError("Invalid, cyclic or excessive native descendant metadata")
                info = request("GET", "/api/session/" + sid)["data"]
                model = info.get("model", {})
                if (info.get("id") != sid or (parent is not None and info.get("parentID") != parent)
                        or Path(info.get("location", {}).get("directory", "")).resolve() != workspace.resolve()
                        or model.get("providerID") != "local" or model.get("id") != "qwen"):
                    raise RuntimeError("Refused control of a session outside the owned local fixture")
                found.add(sid)
                result["verified_sessions"] = sorted(set(result["verified_sessions"]) | found)
                # Stop each verified ancestor before discovering its children.
                if interrupt and sid not in sent:
                    response = request("POST", "/api/session/" + sid + "/interrupt", {})
                    if type(response.get("interrupted")) is not bool:
                        raise RuntimeError("Unexpected native interrupt response")
                    sent.add(sid)
                    result["interrupts"].append({"session_id": sid, "interrupted": response["interrupted"]})
                endpoint, cursors = f"/api/session?parentID={sid}&limit=100", set()
                while True:
                    children = request("GET", endpoint)
                    page = children.get("data")
                    if not isinstance(page, list) or len(found) + len(pending) + len(page) > 64:
                        raise RuntimeError("Native descendant list is unavailable or excessive")
                    for child in page:
                        if child.get("parentID") != sid:
                            raise RuntimeError("Native descendant list contains an unrelated session")
                        pending.append((child["id"], sid))
                    cursor = children.get("cursor", {}).get("next")
                    # Native 2.0.10 returns a next cursor on every nonempty page,
                    # including the final one. Follow it to prove exhaustion.
                    if not page or not cursor:
                        break
                    if not isinstance(cursor, str) or len(cursor) > 4096 or cursor in cursors:
                        raise RuntimeError("Invalid or cyclic native descendant cursor")
                    cursors.add(cursor)
                    endpoint = f"/api/session?parentID={sid}&limit=100&cursor=" + quote(cursor, safe="")
            active = request("GET", "/api/session/active")["data"]
            if not isinstance(active, dict):
                raise RuntimeError("Unexpected native active-session response")
            runtime_idle = runtime_is_idle(folder, f"{label}-{attempt:03}", remaining())
            good = not found.intersection(active) and runtime_idle and found == previous
            quiet = quiet + 1 if good else 0
            result["active_owned_sessions"] = sorted(found.intersection(active))
            result["runtime_idle"] = runtime_idle
            if quiet >= 2:
                result["idle"] = True
                break
            previous = found
            time.sleep(min(.5, remaining()))
        if not result["idle"]:
            raise RuntimeError("Owned native sessions or model runtime did not settle")
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    return result


def run_guarded_cli(child, prompt, timeout, monitor, server, session_id, workspace, folder, report):
    def intervention(cause):
        report["intervention_cause"] = cause
        events = report.setdefault("intervention_events", [])
        events.append({"cause": cause, "utc": dt.datetime.now(dt.timezone.utc).isoformat()})
        report["interventions"] = len(events)
        report["operator_interventions"] = sum(e["cause"] == "operator_interrupt" for e in events)
        report["automatic_interventions"] = len(events) - report["operator_interventions"]
        report["timed_out"] = cause == "timeout"
        report["resource_aborted"] = cause == "resource_guard"
    cause = None
    try:
        cause = guarded_communicate(child, prompt, timeout, monitor.cancel)
        if cause:
            intervention(cause)
    except BaseException as error:
        cause = "operator_interrupt" if isinstance(error, KeyboardInterrupt) else "driver_exception"
        intervention(cause)
        raise
    finally:
        try:
            report["owned_settlement"] = settle_owned_sessions(
                server, session_id, workspace, folder, interrupt=cause is not None, cancel=monitor.cancel)
            if cause is None and report["owned_settlement"].get("resource_abort"):
                intervention("resource_guard")
        except KeyboardInterrupt:
            intervention("operator_interrupt")
            report["owned_settlement"] = settle_owned_sessions(server, session_id, workspace, folder, interrupt=True)
            raise
        finally:
            # This handle belongs to this invocation's native CLI, never the model runtime.
            try:
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    report["owned_cli_termination_required"] = True
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
            except Exception as error:
                report["owned_cli_cleanup_error"] = type(error).__name__ + ": " + str(error)
            report["owned_cli_exited"] = child.poll() is not None


def snapshot_audit_plugin(folder):
    source = Path(__file__).resolve().parent / "inference-audit"
    target = folder / "audit-plugin"
    target.mkdir()
    hashes = {}
    for name in ("server.js", "package.json"):
        raw = (source / name).read_bytes()
        (target / name).write_bytes(raw)
        (target / name).chmod(0o444)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    target.chmod(0o555)
    return target, hashes


def plugin_active(inventory, plugin_id, snapshot):
    entries = [p for p in inventory.get("data", []) if p.get("id") == plugin_id]
    return (len(entries) == 1 and entries[0].get("state", {}).get("status") == "active"
            and entries[0].get("source", {}).get("type") == "local"
            and Path(entries[0].get("source", {}).get("path", "")).resolve() == snapshot / "server.js")


def hashes_match(folder, hashes):
    try:
        return all(hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
                   for name, digest in hashes.items())
    except OSError:
        return False


def allow_fixture_browser(config):
    # Agent rules override globals. Auto-approve only the already-qualified
    # named Browse actions in disposable tests; retain every explicit denial.
    for rule in config.get("agents", {}).get("browse", {}).get("permissions", []):
        if rule.get("effect") == "ask" and rule.get("action", "").startswith("browser_browser_"):
            rule["effect"] = "allow"


def isolate_trial_config(config, target, managed):
    """Freeze trial inputs without merging the incumbent product plugin back in.

    OpenCode merges plugin packages by path, so an inline config cannot replace a
    same-ID plugin at another path. Override only its native config directory;
    leave project discovery and the session database at their ordinary locations.
    """
    allowed = {"AGENTS.md", "cli.json", "opencode.json"}
    if set(p.name for p in managed.iterdir()) - allowed:
        raise RuntimeError("Trial isolation refuses unsupported managed config entries")
    products = [p for p in config.get("plugins", [])
                if isinstance(p, dict) and "profileId" in p.get("options", {})]
    if len(products) != 1:
        raise RuntimeError("Expected exactly one requested KRYN product plugin")
    source = Path(products[0]["package"]).resolve()
    product_names = ("server.js", "tui.tsx", "permission_display.mjs", "package.json")
    if (source / "context_capsule.mjs").is_file():
        product_names += ("context_capsule.mjs",)
    fresh = not target.exists()
    target.mkdir(parents=True, mode=0o700, exist_ok=True)
    config_root, product = target / "config", target / "product"
    if fresh:
        config_root.mkdir(mode=0o700)
        product.mkdir(mode=0o700)
    hashes = {"config": {}, "product": {}}
    for origin, destination, names, key in (
        (managed, config_root, ("AGENTS.md", "cli.json"), "config"),
        (source, product, product_names, "product"),
    ):
        for name in names:
            if name == "cli.json" and not (origin / name).exists():
                continue
            raw = (origin / name).read_bytes()
            if fresh:
                (destination / name).write_bytes(raw)
                (destination / name).chmod(0o444)
            hashes[key][name] = hashlib.sha256(raw).hexdigest()
        if set(p.name for p in destination.iterdir()) != set(hashes[key]) or not hashes_match(destination, hashes[key]):
            raise RuntimeError("Frozen trial inputs changed; prepare a new run for a different candidate")
    products[0]["package"] = str(product)
    return config_root, product, hashes


def audit_session_ids(audit):
    return {r["sessionID"] for r in audit if r.get("sessionID")
            and r.get("kind") in {"primary", "compaction"}}


def audit_rejections(audit):
    return [{k: r.get(k) for k in ("time", "event", "sessionID", "kind", "ok")}
            for r in audit if r.get("ok") is False or r.get("event") == "unexpected.websocket"]


def export_owned_sessions(server, session_ids, root_id, workspace, folder):
    """Establish ownership from metadata before reading any session transcript."""
    pending, found = set(session_ids) | {root_id}, {}
    deadline = time.monotonic() + 30
    def request(path):
        if time.monotonic() >= deadline:
            raise RuntimeError("Native session exports exceeded the 30-second metadata bound")
        return server.request("GET", path, timeout=min(5, max(.01, deadline - time.monotonic())))
    while pending:
        sid = pending.pop()
        if sid in found:
            continue
        if len(found) >= 64 or not re.fullmatch(r"ses_[A-Za-z0-9]+", sid):
            raise RuntimeError("Invalid or excessive native session ancestry")
        info = request("/api/session/" + sid)["data"]
        if info.get("id") != sid:
            raise RuntimeError("Native metadata identity differs from requested session")
        found[sid] = {"data": {"info": info}}
        model = info.get("model", {})
        if (Path(info.get("location", {}).get("directory", "")).resolve() != workspace.resolve()
                or model.get("providerID") != "local" or model.get("id") != "qwen"):
            return [], session_ownership(list(found.values()), root_id, workspace)
        if sid != root_id and info.get("parentID") not in found:
            parent = info.get("parentID")
            if parent:
                pending.add(parent)
    ownership = session_ownership(list(found.values()), root_id, workspace)
    if not ownership["verified"]:
        return [], ownership
    exports = []
    for sid, metadata in found.items():
        exported = request("/api/experimental/session/" + sid + "/export")
        info = exported["data"]["info"]
        if any(info.get(k) != metadata["data"]["info"].get(k) for k in ("id", "parentID", "model", "location")):
            raise RuntimeError("Native session ownership changed between metadata and export")
        (folder / (sid + ".export.json")).write_text(json.dumps(exported, indent=2) + "\n")
        exports.append(exported)
    return exports, ownership


def session_ownership(exports, root_id, workspace):
    infos = {e["data"]["info"]["id"]: e["data"]["info"] for e in exports}
    rows = []
    for sid, info in infos.items():
        chain, current = [], sid
        while current in infos and current not in chain:
            chain.append(current)
            if current == root_id:
                break
            current = infos[current].get("parentID")
        model = info.get("model", {})
        same_directory = Path(info.get("location", {}).get("directory", "")).resolve() == workspace.resolve()
        rows.append({"session_id": sid, "parent_chain": chain,
                     "owned": bool(chain) and chain[-1] == root_id and same_directory
                     and model.get("providerID") == "local" and model.get("id") == "qwen"})
    return {"verified": root_id in infos and all(r["owned"] for r in rows), "sessions": rows}


def generation_completion(exports, started_ms, root_id, required_ids):
    """Only this invocation's generations count; previous successful turns do not."""
    rows, seen, root_answer = [], set(), False
    for export in exports:
        info = export["data"]["info"]
        sid = info["id"]
        new = [m for m in export["data"]["messages"] if m.get("time", {}).get("created", 0) >= started_ms]
        generations = [m for m in new if m.get("type") in {"assistant", "compaction"}]
        if not generations:
            continue
        seen.add(sid)
        assistants = [m for m in generations if m["type"] == "assistant"]
        root_answer |= sid == root_id and bool(assistants)
        details = []
        for message in generations:
            clock = message.get("time", {})
            model = message.get("model", {})
            local = model.get("providerID") == "local" and model.get("id") == "qwen"
            if message["type"] == "assistant":
                complete = (isinstance(clock.get("completed"), (int, float))
                            and clock["completed"] >= clock["created"]
                            and message.get("finish") in {"stop", "tool-calls"})
                complete &= all(p.get("state", {}).get("status") in {"completed", "error"}
                                for p in message.get("content", []) if p.get("type") == "tool")
            else:
                complete = message.get("status") == "completed"
            details.append({"message_id": message.get("id"), "type": message["type"],
                            "finish": message.get("finish"), "status": message.get("status"),
                            "complete": bool(complete and local and not message.get("error"))})
        last_end = max(m.get("time", {}).get("completed") or m["time"]["created"] for m in generations)
        idle = [m for m in new if m.get("type") == "idle" and m["time"]["created"] >= last_end]
        settled = (bool(idle) and idle[-1].get("outcome") == "succeeded"
                   and info.get("outcome") == "succeeded" and info.get("time", {}).get("idle", 0) >= last_end)
        terminal = not assistants or assistants[-1].get("finish") == "stop"
        rows.append({"session_id": sid, "settled_successfully": settled, "terminal_stop": terminal,
                     "generations": details, "complete": settled and terminal and all(r["complete"] for r in details)})
    missing = sorted(set(required_ids) - seen)
    return {"verified": root_answer and not missing and all(r["complete"] for r in rows),
            "missing_new_generations": missing, "sessions": rows}


def route_coverage(audit, exports, started_ms, finished_ms):
    """Cross-check persisted native generations, not just a nonempty audit prefix."""
    def millis(record):
        return dt.datetime.fromisoformat(record["time"].replace("Z", "+00:00")).timestamp() * 1000
    ready = [millis(r) for r in audit if r.get("event") == "ready"]
    closed = [millis(r) for r in audit if r.get("event") == "closed"]
    bracketed = len(ready) == len(closed) == 1 and ready[0] <= started_ms and closed[0] >= finished_ms
    rows, used_requests = [], set()
    for export in exports:
        sid = export["data"]["info"]["id"]
        messages = export["data"]["messages"]
        previous_completion = started_ms
        for message in messages:
            kind = {"assistant": "primary", "compaction": "compaction"}.get(message.get("type"))
            created = message.get("time", {}).get("created", 0)
            if kind is None or created < started_ms:
                continue
            completed = message.get("time", {}).get("completed")
            upper = completed or finished_ms
            if kind == "compaction":
                upper = min([m.get("time", {}).get("created", finished_ms) for m in messages
                             if m.get("type") in {"assistant", "compaction"}
                             and m.get("time", {}).get("created", 0) > created] + [upper])
            # Native preparation can precede assistant row creation. Match in
            # order after the previous completion, not against created alone.
            lower = previous_completion if kind == "primary" else created
            scoped = [(i, r) for i, r in enumerate(audit) if r.get("sessionID") == sid and r.get("kind") == kind
                      and lower <= millis(r) <= upper]
            requests = [i for i, r in scoped if r.get("event") == "http.request" and r.get("ok") is True
                        and i not in used_requests]
            covered = bool(requests) and any(r.get("event") == "wire.options" for _, r in scoped) and any(
                r.get("event") == "http.response" and r.get("status") == 200 for _, r in scoped)
            if covered:
                used_requests.update(requests)
            rows.append({"session_id": sid, "message_id": message.get("id"), "kind": kind,
                         "created_ms": created, "completed_ms": completed, "coverage_window_ms": [lower, upper],
                         "covered": covered})
            if kind == "primary":
                previous_completion = upper
    last_completion = max([finished_ms] + [r["completed_ms"] or r["coverage_window_ms"][1] for r in rows])
    bracketed = bracketed and closed[0] >= last_completion
    rejected = audit_rejections(audit)
    uncovered = [{"session_id": r.get("sessionID"), "kind": r.get("kind"), "time": r.get("time")}
                 for i, r in enumerate(audit) if r.get("event") == "http.request"
                 and r.get("kind") in {"primary", "compaction"} and i not in used_requests]
    return {"verified": bool(rows) and bracketed and not rejected and not uncovered and all(r["covered"] for r in rows),
            "rejected_audit_events": rejected,
            "uncovered_generation_requests": uncovered,
            "lifecycle_brackets_prompt": bracketed, "ready_count": len(ready), "closed_count": len(closed),
            "native_generations": rows, "last_completion_ms": last_completion,
            "scope": "Persisted assistant/compaction messages from this invocation; non-persisted helpers cannot be independently enumerated from these exports. This is not OS-wide network proof."}


def canonical_tool_ids(value):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("Tool catalog must be a JSON array of nonempty IDs")
    if len(set(value)) != len(value):
        raise ValueError("Tool catalog contains duplicate IDs")
    return sorted(value)


def catalog_sha(ids):
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()


def catalog_problem(ids, expected=None):
    if not EXA_TOOLS.issubset(ids) or not any(x.startswith("browser_") for x in ids):
        return "Missing expected Exa/browser tool namespace"
    if expected is not None and ids != expected:
        return "Registered tool catalog differs from expected baseline"
    return None


def wait_ready_tools(server, config, folder, expected=None):
    """Metadata-only startup gate. Never creates a session, prompts, or executes a tool."""
    required = {name for name, item in config.get("mcp", {}).get("servers", {}).items()
                if not item.get("disabled", False) and item.get("enabled", True)}
    started = time.monotonic()
    deadline = started + 30
    evidence = {"required_servers": sorted(required), "snapshots": [], "ready": False,
                "expected_catalog_sha256": catalog_sha(expected) if expected is not None else None}
    previous = None
    try:
        if not {"search", "browser"}.issubset(required):
            raise RuntimeError("Readiness requires configured search and browser MCP servers")
        while time.monotonic() < deadline:
            response = server.request("GET", "/api/mcp", timeout=min(2, max(.01, deadline - time.monotonic())))
            states = {item["name"]: item["status"]["status"] for item in response["data"]}
            if time.monotonic() >= deadline:
                break
            response = server.request("POST", "/api/rpc/localai.inference-audit/tools", {"input": {}},
                                      timeout=min(2, max(.01, deadline - time.monotonic())))
            ids = canonical_tool_ids(response["output"])
            snapshot = {"elapsed_seconds": round(time.monotonic() - started, 3),
                        "servers": states, "tools": ids, "catalog_sha256": catalog_sha(ids)}
            evidence["snapshots"].append(snapshot)
            failed = [name for name in required if name in states and states[name] not in {"pending", "connected"}]
            if failed:
                raise RuntimeError("MCP server not connected: " + ", ".join(sorted(failed)))
            connected = all(states.get(name) == "connected" for name in required)
            if connected and not catalog_problem(ids):
                if previous is not None and previous["tools"] == ids:
                    problem = catalog_problem(ids, expected)
                    if problem:
                        raise RuntimeError(problem)
                    if time.monotonic() >= deadline:
                        break
                    evidence.update(ready=True, catalog_sha256=catalog_sha(ids))
                    (folder / "tool-catalog.json").write_text(json.dumps(ids, indent=2) + "\n")
                    return evidence
                previous = snapshot
            else:
                previous = None
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(.5, remaining))
        raise RuntimeError("MCP/tool readiness timed out after 30s; no prompt was sent")
    except Exception as error:
        evidence["error"] = type(error).__name__ if not isinstance(error, (RuntimeError, ValueError)) else str(error)
        raise
    finally:
        evidence["wall_seconds"] = round(time.monotonic() - started, 3)
        (folder / "tool-readiness.json").write_text(json.dumps(evidence, indent=2) + "\n")


def budget_value(value):
    value = int(value)
    if not 0 <= value <= 8192:
        raise argparse.ArgumentTypeError("thinking budget must be 0..8192")
    return value


def apply_budget(config, variant, budget):
    if budget is None:
        return
    model = config["providers"]["local"]["models"]["qwen"]
    selected = [model] if variant == "default" else [v for v in model["variants"] if v["id"] == variant]
    if len(selected) != 1:
        raise ValueError("Expected exactly one selected variant")
    selected[0].setdefault("body", {})["thinking_budget"] = budget


def attachment_info(workspace, given):
    if given is None:
        return None, None
    path = (workspace / given).resolve()
    mime = mimetypes.guess_type(path.name)[0]
    if not path.is_relative_to(workspace.resolve()) or not path.is_file():
        raise ValueError("Attachment must resolve to a file inside the prepared workspace")
    if not mime or not mime.startswith("image/") or not 0 < path.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError("Attachment must be an image file of at most 10 MiB (native CLI limit)")
    raw = path.read_bytes()
    return path, {"path": str(path.relative_to(workspace.resolve())), "mime": mime,
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def acceptance_checks(audit, session_id, no_tools, attachment, budget, tool_parts, exports):
    primary = [r for r in audit if r.get("sessionID") == session_id and r.get("kind") == "primary"]
    wires = [r for r in primary if r.get("event") == "wire.options"]
    requests = [r for r in primary if r.get("event") == "http.request"]
    responses = [r for r in primary if r.get("event") == "http.response" and r.get("status") == 200]
    checks = {"primary_wire_evidence": bool(wires) and len(wires) == len(requests)
              and all(r.get("captureOnly") is False for r in wires) and bool(responses)}
    if budget is not None:
        checks["selected_budget_on_wire"] = bool(wires) and all(
            r.get("numeric", {}).get("thinking_budget") == budget for r in wires)
    if no_tools:
        all_wires = [r for r in audit if r.get("event") == "wire.options"]
        checks["no_tools_exposed"] = bool(all_wires) and all(
            r.get("toolCount") == 0 and r.get("tools") == [] for r in all_wires)
        exported_tools = [p for e in exports for m in e["data"]["messages"]
                          if m.get("type") == "assistant" for p in m.get("content", []) if p.get("type") == "tool"]
        checks["no_tools_called"] = bool(exports) and not tool_parts and not exported_tools
    if attachment:
        checks["matching_embedded_image_on_wire"] = bool(wires) and all(
            r.get("imageCount", 0) > 0 and r.get("imagePartCount") == r.get("imageCount")
            and r.get("imageCount") == len(r.get("images", [])) and any(
                all(image.get(k) == attachment[k] for k in ("sha256", "bytes", "mime"))
                for image in r.get("images", [])) for r in wires)
    return checks


def guard_self_check():
    import tempfile
    from unittest.mock import patch
    class Child:
        def __init__(self):
            self.inputs, self.returncode = [], 0
        def communicate(self, input=None, timeout=None):
            self.inputs.append(input)
            if len(self.inputs) < 3:
                raise subprocess.TimeoutExpired("offline", timeout)
        def wait(self, timeout=None):
            return self.returncode
        def poll(self):
            return self.returncode
    cancel, child = threading.Event(), Child()
    assert guarded_communicate(child, b"only once", 10, cancel) is None
    assert child.inputs == [b"only once", None, None]
    cancel.set()
    child = Child()
    assert guarded_communicate(child, b"never", 10, cancel) == "resource_guard" and not child.inputs
    assert guarded_communicate(child, b"never", 0, threading.Event()) == "timeout"
    # Exercise actual stdlib retry state with a disposable stdin-only process.
    payload = b"x" * (256 * 1024)
    with subprocess.Popen([sys.executable, "-c", "import sys,time; time.sleep(.65); print(len(sys.stdin.buffer.read()))"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
        assert guarded_communicate(child, payload, 5, threading.Event()) is None
        assert child.communicate()[0].strip() == str(len(payload)).encode()
    green = {"swap_used_bytes": 100, "pressure_level": 1,
             "listener_processes": [{"pid": 42, "phys_footprint_bytes": 100}]}
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        monitor = NativeResourceGuard(folder, [])
        with patch(__name__ + ".resources", return_value=green), patch.object(time, "sleep", lambda _: None):
            monitor.start()
            assert monitor.preflight_passed and len(monitor.samples) == 3
            with patch(__name__ + ".resources", return_value={**green, "pressure_level": 2}):
                monitor.sample()
                assert not monitor.cancel.is_set()
                monitor.sample()
                assert monitor.cancel.is_set()
            monitor.close()
        assert not monitor.watcher.is_alive() and monitor.log.closed
        assert summarize_resources(monitor.samples)["warning_or_critical_observed"]
        class Server:
            def __init__(self, foreign=False, busy=False, paginated=False, cyclic=False):
                self.paths, self.foreign, self.busy = [], foreign, busy
                self.paginated, self.cyclic = paginated, cyclic
            def request(self, method, path, body=None, timeout=None):
                assert threading.current_thread() is threading.main_thread() and 0 < timeout <= 3
                self.paths.append((method, path))
                if path == "/api/session/active":
                    return {"data": {"ses_foreign": {}, **({"ses_root": {}} if self.busy else {})}}
                if "parentID=" in path:
                    sid = path.split("parentID=")[1].split("&")[0]
                    kids = {"ses_root": "ses_child", "ses_child": "ses_grand"}
                    if "&cursor=" in path and not self.cyclic:
                        return {"data": [], "cursor": {}}
                    return {"data": [{"id": kids[sid], "parentID": sid}] if sid in kids else [],
                            "cursor": {"next": "last-page"} if self.paginated and sid in kids else {}}
                if path.endswith("/interrupt"):
                    return {"interrupted": True}
                sid = path.rsplit("/", 1)[1]
                return {"data": {"id": sid, "parentID": {"ses_child": "ses_root", "ses_grand": "ses_child"}.get(sid),
                    "location": {"directory": str(folder / "foreign") if self.foreign and sid == "ses_child" else str(folder)},
                    "model": {"providerID": "local", "id": "qwen"}}}
        clock = [0.]
        def tick(value):
            clock[0] += value
        with patch(__name__ + ".runtime_is_idle", return_value=True), patch.object(time, "sleep", tick), \
                patch.object(time, "monotonic", lambda: clock[0]):
            server = Server()
            result = settle_owned_sessions(server, "ses_root", folder, folder, interrupt=True)
            assert result["idle"] and len(result["interrupts"]) == 3
            posts = [path for method, path in server.paths if method == "POST"]
            assert posts == [f"/api/session/{sid}/interrupt" for sid in ("ses_root", "ses_child", "ses_grand")]
            paginated = Server(paginated=True)
            assert settle_owned_sessions(paginated, "ses_root", folder, folder)["idle"]
            assert any("&cursor=" in path for _, path in paginated.paths)
            cyclic = settle_owned_sessions(Server(paginated=True, cyclic=True), "ses_root", folder, folder)
            assert not cyclic["idle"] and "cursor" in cyclic["error"]
            bad = Server(foreign=True)
            assert not settle_owned_sessions(bad, "ses_root", folder, folder, interrupt=True)["idle"]
            assert [p for m, p in bad.paths if m == "POST"] == ["/api/session/ses_root/interrupt"]
            busy = Server(busy=True)
            start = clock[0]
            assert not settle_owned_sessions(busy, "ses_root", folder, folder, interrupt=True)["idle"]
            assert clock[0] - start <= 30
        monitor.cancel.clear()
        for outcome in ("resource_guard", "timeout", KeyboardInterrupt("offline operator")):
            report = {"interventions": 0}
            with patch(__name__ + ".guarded_communicate", side_effect=outcome if isinstance(outcome, BaseException) else None,
                       return_value=outcome), patch(__name__ + ".settle_owned_sessions", return_value={"idle": True}) as settle:
                try:
                    run_guarded_cli(Child(), b"x", 10, monitor, Server(), "ses_root", folder, folder, report)
                except KeyboardInterrupt as error:
                    assert str(error) == "offline operator"
                assert settle.call_args.kwargs["interrupt"] and report["owned_cli_exited"]
                assert report["operator_interventions"] == int(isinstance(outcome, KeyboardInterrupt))
                assert report["automatic_interventions"] == int(not isinstance(outcome, KeyboardInterrupt))
                assert not report.get("completed")


def self_check():
    import tempfile
    guard_self_check()
    browser = {"agents": {"browse": {"permissions": [
        {"action": "browser_*", "effect": "deny"},
        {"action": "browser_browser_navigate", "effect": "ask"},
        {"action": "browser_browser_run_code_unsafe", "effect": "deny"},
        {"action": "external_directory", "effect": "ask"}]}}}
    allow_fixture_browser(browser)
    assert [r["effect"] for r in browser["agents"]["browse"]["permissions"]] == ["deny", "allow", "deny", "ask"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        managed, original = root / "managed", root / "original"
        managed.mkdir()
        original.mkdir()
        for name in ("AGENTS.md", "cli.json", "opencode.json"):
            (managed / name).write_text(name)
        for name in ("server.js", "tui.tsx", "permission_display.mjs", "context_capsule.mjs", "package.json"):
            (original / name).write_text(name)
        config = {"plugins": [{"package": str(original), "options": {"profileId": "test"}}]}
        isolated, product, hashes = isolate_trial_config(config, root / "frozen", managed)
        assert hashes_match(isolated, hashes["config"]) and hashes_match(product, hashes["product"])
        assert not (isolated / "opencode.json").exists()
        assert config["plugins"][0]["package"] == str(product)
        resumed = {"plugins": [{"package": str(original), "options": {"profileId": "test"}}]}
        assert isolate_trial_config(resumed, root / "frozen", managed) == (isolated, product, hashes)
        entry = {"id": "kryn.product", "state": {"status": "active"},
                 "source": {"type": "local", "path": str(product / "server.js")}}
        assert plugin_active({"data": [entry]}, "kryn.product", product)
        assert not plugin_active({"data": []}, "kryn.product", product)
        (original / "context_capsule.mjs").unlink()
        legacy = {"plugins": [{"package": str(original), "options": {"profileId": "test"}}]}
        _, old_product, old_hashes = isolate_trial_config(legacy, root / "legacy", managed)
        assert "context_capsule.mjs" not in old_hashes["product"] and hashes_match(old_product, old_hashes["product"])
        assert not plugin_active({"data": [entry]}, "kryn.product", original)
        failed = copy.deepcopy(entry)
        failed["state"] = {"status": "failed", "error": "Duplicate plugin ID: kryn.product"}
        assert not plugin_active({"data": [entry, failed]}, "kryn.product", product)
        assert not plugin_active({"data": [failed]}, "kryn.product", product)
        (product / "server.js").chmod(0o600)
        (product / "server.js").write_text("changed")
        assert not hashes_match(product, hashes["product"])
        resumed["plugins"][0]["package"] = str(original)
        try:
            isolate_trial_config(resumed, root / "frozen", managed)
        except RuntimeError:
            pass
        else:
            raise AssertionError("changed snapshot reused")
        (managed / "agents").mkdir()
        try:
            isolate_trial_config(config, root / "unsupported", managed)
        except RuntimeError:
            pass
        else:
            raise AssertionError("custom managed instructions silently omitted")
    def audit_row(event, milliseconds, **extra):
        return {"event": event, "time": dt.datetime.fromtimestamp(milliseconds / 1000, dt.timezone.utc).isoformat(), **extra}
    scope = {"sessionID": "test", "kind": "primary"}
    trace = [audit_row("ready", 500), audit_row("http.request", 1100, ok=True, **scope),
             audit_row("wire.options", 1101, **scope), audit_row("http.response", 1102, status=200, **scope),
             audit_row("closed", 2600)]
    exported = [{"data": {"info": {"id": "test"}, "messages": [
        {"id": "one", "type": "assistant", "time": {"created": 1000, "completed": 2000}}]}}]
    assert route_coverage(trace, exported, 900, 2500)["verified"]
    assert not route_coverage(trace[:-1] + [audit_row("model.request", 2300, ok=False)] + trace[-1:], exported, 900, 2500)["verified"]
    assert not route_coverage(trace[:-1] + [audit_row("unexpected.websocket", 2300)] + trace[-1:], exported, 900, 2500)["verified"]
    assert not route_coverage(trace[:-1] + [audit_row("http.request", 2300, ok=True, **scope)] + trace[-1:], exported, 900, 2500)["verified"]
    assert not route_coverage(trace[:-1] + [audit_row("closed", 1800)], exported, 900, 2500)["verified"]
    assert not route_coverage([trace[0], trace[-1]], exported, 900, 2500)["verified"]
    extra = copy.deepcopy(exported)
    extra[0]["data"]["messages"].append({"id": "two", "type": "assistant", "time": {"created": 2100, "completed": 2400}})
    assert not route_coverage(trace, extra, 900, 2500)["verified"]
    compacted = copy.deepcopy(exported)
    compacted[0]["data"]["messages"].append({"id": "compact", "type": "compaction", "status": "completed", "time": {"created": 2100}})
    assert not route_coverage(trace, compacted, 900, 2500)["verified"]
    compact_trace = [audit_row(event, stamp, sessionID="test", kind="compaction", **details) for event, stamp, details in (
        ("http.request", 2200, {"ok": True}), ("wire.options", 2201, {}), ("http.response", 2202, {"status": 200}))]
    assert route_coverage(trace[:-1] + compact_trace + trace[-1:], compacted, 900, 2500)["verified"]
    ids = canonical_tool_ids([*EXA_TOOLS, "browser_browser_navigate", "read"])
    assert catalog_problem(ids) is None and catalog_problem(ids, ids) is None
    assert catalog_problem(["read"]) and catalog_problem(ids, ids + ["write"])
    assert canonical_tool_ids(list(reversed(ids))) == ids
    for invalid in (None, {}, ["same", "same"], [1], [""]):
        try:
            canonical_tool_ids(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid tool catalog accepted")
    config = {"providers": {"local": {"models": {"qwen": {
        "body": {"max_tokens": 8192}, "variants": [{"id": "low", "body": {"x": 1}}, {"id": "xhigh"}]}}}}}
    original = copy.deepcopy(config)
    apply_budget(config, "low", None)
    assert config == original
    apply_budget(config, "low", budget_value("0"))
    assert config["providers"]["local"]["models"]["qwen"]["variants"] == [
        {"id": "low", "body": {"x": 1, "thinking_budget": 0}}, {"id": "xhigh"}]
    assert config["providers"]["local"]["models"]["qwen"]["body"] == {"max_tokens": 8192}
    apply_budget(config, "default", 3072)
    assert config["providers"]["local"]["models"]["qwen"]["body"]["thinking_budget"] == 3072
    assert budget_value("8192") == 8192
    for value in ("-1", "8193"):
        try:
            budget_value(value)
        except argparse.ArgumentTypeError:
            pass
        else:
            raise AssertionError("invalid budget accepted")
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        local = {"providerID": "local", "id": "qwen"}
        def fixture(sid, parent=None):
            return {"data": {"info": {"id": sid, "parentID": parent, "model": local,
                "location": {"directory": str(workspace)}, "outcome": "succeeded", "time": {"idle": 2100}},
                "messages": [{"id": "old", "type": "assistant", "error": {"type": "old failure"}, "time": {"created": 100}},
                    {"id": "answer", "type": "assistant", "model": local, "finish": "stop", "time": {"created": 1000, "completed": 2000}},
                    {"id": "idle", "type": "idle", "outcome": "succeeded", "time": {"created": 2100}}]}}
        root = fixture("ses_root")
        class CompactServer:
            def __init__(self, summary="## Objective\n- Continue task"):
                self.started = False
                self.summary = summary
            def request(self, method, path, body=None, timeout=5):
                if method == "POST":
                    assert path == "/api/session/ses_root/compact" and body == {}
                    self.started = True
                    return {"data": {"type": "compaction"}}
                assert method == "GET" and path == "/api/experimental/session/ses_root/export"
                data = copy.deepcopy(root)
                if self.started:
                    data["data"]["messages"].append({"id": "cmp_1", "type": "compaction",
                        "status": "completed", "summary": self.summary})
                return data
        compacted = manual_compaction(CompactServer(), "ses_root", workspace, Path(tmp))
        assert compacted["completed"] and compacted["summary_headings"] == ["## Objective"]
        assert compacted["semantic_qualification"] == "NOT_ESTABLISHED"
        (workspace / "TASK.md").write_text("Build an application.\n")
        false = manual_compaction(CompactServer("## Objective\n- No user conversation or task was provided"),
                                  "ses_root", workspace, Path(tmp))
        assert false["completed"] and false["obvious_task_contradiction"]
        assert false["semantic_qualification"] == "FAIL"
        assert generation_completion([root], 900, "ses_root", {"ses_root"})["verified"]
        for key, value in (("finish", "length"), ("finish", None), ("error", {"type": "new failure"})):
            bad = copy.deepcopy(root)
            bad["data"]["messages"][1][key] = value
            assert not generation_completion([bad], 900, "ses_root", {"ses_root"})["verified"]
        bad = copy.deepcopy(root)
        del bad["data"]["messages"][1]["time"]["completed"]
        assert not generation_completion([bad], 900, "ses_root", {"ses_root"})["verified"]
        for status in ("running", "failed", "completed"):
            bad = copy.deepcopy(root)
            bad["data"]["messages"].insert(1, {"id": "compact", "type": "compaction", "status": status,
                                                 "model": local, "time": {"created": 950}})
            assert generation_completion([bad], 900, "ses_root", {"ses_root"})["verified"] == (status == "completed")
        child_export = fixture("ses_child", "ses_root")
        pair = [root, child_export]
        assert session_ownership(pair, "ses_root", workspace)["verified"]
        assert generation_completion(pair, 900, "ses_root", {"ses_root", "ses_child"})["verified"]
        assert not generation_completion([root], 900, "ses_root", {"ses_root", "ses_child"})["verified"]
        bad = copy.deepcopy(pair)
        bad[1]["data"]["messages"].pop()
        assert not generation_completion(bad, 900, "ses_root", {"ses_child"})["verified"]
        for key, value in (("parentID", "ses_foreign"), ("parentID", "ses_child"),
                           ("location", {"directory": str(Path(tmp))}), ("model", {"providerID": "cloud", "id": "qwen"})):
            bad = copy.deepcopy(pair)
            bad[1]["data"]["info"][key] = value
            assert not session_ownership(bad, "ses_root", workspace)["verified"]
        class ExportServer:
            def __init__(self, data):
                self.data, self.paths = data, []
            def request(self, method, path, timeout):
                assert method == "GET"
                assert 0 < timeout <= 5
                self.paths.append(path)
                if path.startswith("/api/session/"):
                    return {"data": self.data[path.split("/")[-1]]["data"]["info"]}
                assert path.startswith("/api/experimental/session/")
                return self.data[path.split("/")[-2]]
        discovered = audit_session_ids([{"sessionID": "ses_child", "kind": "primary"}])
        fake = ExportServer({"ses_root": root, "ses_child": child_export})
        saved, ownership = export_owned_sessions(fake, discovered, "ses_root", workspace, Path(tmp))
        assert len(saved) == 2 and ownership["verified"] and (Path(tmp) / "ses_child.export.json").is_file()
        assert all(p.startswith("/api/session/") for p in fake.paths[:2])
        foreign = copy.deepcopy(child_export)
        foreign["data"]["info"]["location"]["directory"] = str(Path(tmp))
        fake = ExportServer({"ses_root": root, "ses_child": foreign})
        saved, ownership = export_owned_sessions(fake, discovered, "ses_root", workspace, Path(tmp))
        assert not saved and not ownership["verified"] and all(p.startswith("/api/session/") for p in fake.paths)
        (workspace / "test.png").write_bytes(b"test image bytes")
        _, image = attachment_info(workspace, Path("test.png"))
        (workspace / "escape.png").symlink_to(Path(tmp) / "outside.png")
        (Path(tmp) / "outside.png").write_bytes(b"outside")
        try:
            attachment_info(workspace, Path("escape.png"))
        except ValueError:
            pass
        else:
            raise AssertionError("attachment escaped workspace")
        scope = {"sessionID": "test", "kind": "primary"}
        wire = {**scope, "event": "wire.options", "captureOnly": False, "numeric": {"thinking_budget": 0},
                "tools": [], "toolCount": 0, "imageCount": 1, "imagePartCount": 1, "images": [image]}
        audit = [{**scope, "event": "http.request"}, wire, {**scope, "event": "http.response", "status": 200}]
        exports = [{"data": {"messages": [{"type": "assistant", "content": [{"type": "text"}]}]}}]
        check = lambda a, tools, ex: acceptance_checks(a, "test", True, image, 0, tools, ex)
        assert all(check(audit, [], exports).values())
        assert not all(check([], [], exports).values())
        assert not check(audit, [{"tool": "read"}], exports)["no_tools_called"]
        used = [{"data": {"messages": [{"type": "assistant", "content": [{"type": "tool"}]}]}}]
        assert not check(audit, [], used)["no_tools_called"]
        bad = copy.deepcopy(audit)
        bad[1]["toolCount"] = 1
        assert not check(bad, [], exports)["no_tools_exposed"]
        bad = copy.deepcopy(audit)
        bad[1]["images"][0]["sha256"] = "wrong"
        assert not check(bad, [], exports)["matching_embedded_image_on_wire"]
        bad = copy.deepcopy(audit)
        bad[1]["numeric"] = {}
        assert not check(bad, [], exports)["selected_budget_on_wire"]
    print(json.dumps({"self_check": "PASS", "inference": "not run"}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path, nargs="?")
    ap.add_argument("--stage", default="attempt1")
    ap.add_argument("--agent", default="build")
    ap.add_argument("--variant", default="default", choices=("default", "fast"))
    ap.add_argument("--prompt", type=Path)
    ap.add_argument("--session")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--thinking-budget", type=budget_value)
    ap.add_argument("--attachment", type=Path, help="image path relative to, or resolving inside, the prepared workspace")
    ap.add_argument("--no-tools", action="store_true", help="deny all tools on a fresh native session; verify wire/transcript evidence")
    ap.add_argument("--ready-tools", action="store_true", help="wait up to 30s for connected MCP servers and a stable tool catalog before prompting")
    ap.add_argument("--expected-tools", type=Path, help="require exact equality with baseline tool-catalog.json; implies --ready-tools")
    ap.add_argument("--guard-resources", action="store_true", help="require green/idle preflight; cancel only owned sessions on sustained pressure, missing telemetry or >512 MiB swap growth")
    ap.add_argument("--compact-after", action="store_true", help="after the turn, request and verify one native checkpoint in this disposable session; requires --guard-resources")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return 0
    if args.run is None or (args.no_tools and args.session):
        ap.error("A prepared run is required; --no-tools requires a fresh session (omit --session)")
    if args.compact_after and not args.guard_resources:
        ap.error("--compact-after requires --guard-resources")
    ready_tools = args.ready_tools or args.expected_tools is not None
    try:
        expected_tools = canonical_tool_ids(json.loads(args.expected_tools.read_text())) if args.expected_tools else None
    except (OSError, ValueError) as error:
        ap.error("Invalid expected tool catalog: " + str(error))
    run = args.run.resolve()
    workspace = run / "workspace"
    if not (run / "run.json").is_file() or not (workspace / ".git").is_dir():
        ap.error("Expected a disposable run prepared by evals/bench.py")
    try:
        attachment, image_info = attachment_info(workspace, args.attachment)
    except ValueError as error:
        ap.error(str(error))
    folder = run / "evidence" / args.stage
    folder.mkdir(parents=True, exist_ok=False)
    config = copy.deepcopy(owned_config())
    apply_budget(config, args.variant, args.thinking_budget)
    # Outside the workspace and shell's writable evidence/log directory.
    config_root, product_plugin, input_hashes = isolate_trial_config(
        config, run / "trial-inputs" / "frozen", ROOT / "xdg/config/opencode")
    # These eval-only permissions remove interactive waiting in the disposable repo.
    # Ordinary daily launches retain ask. They are not an OS filesystem sandbox.
    config["permissions"] += [
        {"action": "shell", "resource": "*", "effect": "allow"},
        {"action": "browser_*", "resource": "*", "effect": "allow"},
        {"action": "browser", "resource": "*", "effect": "allow"},
        {"action": "browser_browser_run_code_unsafe", "resource": "*", "effect": "deny"},
        {"action": "webfetch", "resource": "*", "effect": "allow"},
        {"action": "external_directory", "resource": "*", "effect": "deny"},
    ]
    allow_fixture_browser(config)
    audit_options = {"log": str(folder / "inference.jsonl"), "expectedModelID": MODEL_ID}
    if ready_tools:
        audit_options["readyTools"] = True
    audit_plugin, audit_hashes = snapshot_audit_plugin(folder)
    config["plugins"].append({"package": str(audit_plugin),
                              "options": audit_options})
    config_bytes = (json.dumps(config, indent=2) + "\n").encode()
    (folder / "requested-config.json").write_bytes(config_bytes)
    prompt = (args.prompt or workspace / "TASK.md").read_text()
    (folder / "prompt.txt").write_text(prompt)
    report = {"agent": args.agent, "variant": args.variant, "expected_model_id": MODEL_ID,
              "thinking_budget_override": args.thinking_budget, "no_tools": args.no_tools,
              "attachment": image_info,
              "audit_plugin_sha256": audit_hashes,
              "trial_input_sha256": input_hashes,
              "ready_tools": ready_tools, "expected_tools": str(args.expected_tools.resolve()) if args.expected_tools else None,
              "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "memory_before": memory_snapshot(), "power_before": power_source(), "interventions": 0,
              "fixture_only_permissions": True, "completed": False, "model_completed": False}
    started = time.monotonic()
    samples, sampling_stop = [], threading.Event()
    def sample_resources():
        with (folder / "resources.jsonl").open("x") as resource_log:
            while True:
                item = resources("http://127.0.0.1:8000")
                samples.append(item)
                resource_log.write(json.dumps(item) + "\n")
                resource_log.flush()
                if sampling_stop.wait(5):
                    break
    sampler = threading.Thread(target=sample_resources, daemon=True)
    monitor = NativeResourceGuard(folder, samples) if args.guard_resources else None
    if monitor is None:
        sampler.start()
    else:
        report["resource_guard"] = {"green_samples_before_prompt": 3, "sample_interval_seconds": 2,
            "warning_samples_to_abort": 2, "max_swap_growth_bytes": 512 * 1024**2,
            "any_warning_fails_acceptance": True, "missing_telemetry_aborts": True}
        report.update(operator_interventions=0, automatic_interventions=0)
    exports, server = [], None
    try:
        server = NativeServer(workspace, config, folder / "native-server.log")
        server.env["OPENCODE_CONFIG_DIR"] = str(config_root)
        with server:
            providers, models = server.inventory()
            if [p["id"] for p in providers["data"]] != ["local"] or [m["id"] for m in models["data"]] != ["qwen"]:
                raise RuntimeError("Unexpected provider/model inventory")
            (folder / "inventory.json").write_text(json.dumps({"providers": providers, "models": models}, indent=2))
            for domain in ("config", "plugin", "agent", "command", "skill"):
                value = server.request("GET", "/api/" + domain)
                (folder / (domain + "-inventory.json")).write_text(json.dumps(value, indent=2))
            audit_path = folder / "inference.jsonl"
            if not audit_path.is_file() or '"event":"ready"' not in audit_path.read_text():
                raise RuntimeError("Native inference audit hook did not initialize")
            plugin_before = server.request("GET", "/api/plugin")
            report["product_plugin_active_before"] = plugin_active(plugin_before, "kryn.product", product_plugin)
            if not (report["product_plugin_active_before"] and hashes_match(product_plugin, input_hashes["product"])
                    and hashes_match(config_root, input_hashes["config"])):
                raise RuntimeError("Frozen KRYN product plugin/config is not active and unchanged; no prompt sent")
            report["audit_plugin_active_before"] = plugin_active(plugin_before, "localai.inference-audit", audit_plugin)
            if not report["audit_plugin_active_before"]:
                raise RuntimeError("Frozen audit plugin is not active before prompting")
            if ready_tools:
                report["tool_readiness"] = wait_ready_tools(server, config, folder, expected_tools)
            if args.session:
                session = server.request("GET", "/api/session/" + args.session)["data"]
            else:
                create = {
                    "title": run.name + "-" + args.stage, "agent": args.agent,
                    "model": {"providerID": "local", "id": "qwen", "variant": args.variant},
                    "location": {"directory": str(workspace)}}
                if args.no_tools:
                    create["permissions"] = [{"action": "*", "resource": "*", "effect": "deny"}]
                session = server.request("POST", "/api/session", create)["data"]
            (folder / "session-before.json").write_text(json.dumps(session, indent=2))
            if Path(session["location"]["directory"]).resolve() != workspace:
                raise RuntimeError("Session directory differs from prepared fixture before prompting")
            if monitor is not None:
                model = session.get("model", {})
                if model.get("providerID") != "local" or model.get("id") != "qwen":
                    raise RuntimeError("Guarded session must use the owned local model")
                if session["id"] in server.request("GET", "/api/session/active", timeout=3)["data"]:
                    raise RuntimeError("Owned session is already active; no prompt sent")
                if not runtime_is_idle(folder, "guard-idle-before"):
                    raise RuntimeError("Expected model runtime is not idle; no prompt sent")
                monitor.start()
                if not runtime_is_idle(folder, "guard-idle-after-preflight"):
                    raise RuntimeError("Expected runtime became busy during resource preflight; no prompt sent")
            command = [str(BINARY), "run", "--server", server.url, "--agent", args.agent,
                       "--model", "local/qwen" + ("#fast" if args.variant == "fast" else ""), "--format", "json", "--thinking",
                       "--session", session["id"], "--title", run.name + "-" + args.stage]
            if attachment:
                command += ["--file", str(attachment)]
            report["command"] = command
            report["prompt_started_unix_ms"] = time.time() * 1000
            with (folder / "events.jsonl").open("wb") as out, (folder / "stderr.log").open("wb") as err:
                child = subprocess.Popen(command, cwd=workspace, env=server.env, stdin=subprocess.PIPE, stdout=out, stderr=err)
                try:
                    if monitor is not None:
                        run_guarded_cli(child, prompt.encode(), args.timeout, monitor, server,
                                        session["id"], workspace, folder, report)
                    else:
                        child.communicate(prompt.encode(), timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    try:
                        server.request("POST", "/api/session/" + session["id"] + "/interrupt", {})
                        report["native_interrupt_sent"] = True
                    except Exception as interrupt_error:
                        report["native_interrupt_error"] = str(interrupt_error)
                    child.terminate()
                    child.wait(timeout=10)
                    report["timed_out"] = True
                finally:
                    if monitor is None and child.poll() is None:
                        child.kill()
                        child.wait()
            report["prompt_finished_unix_ms"] = time.time() * 1000
            report["exit_code"] = child.returncode
            cli_completed = child.returncode == 0 and not report.get("timed_out") and not report.get("resource_aborted")
            if monitor is not None:
                cli_completed &= report.get("owned_settlement", {}).get("idle", False) and report.get("owned_cli_exited", False)
            if args.compact_after and cli_completed:
                try:
                    report["manual_compaction"] = manual_compaction(server, session["id"], workspace, folder,
                                                                     monitor.cancel if monitor else None)
                except BaseException:
                    report["owned_settlement"] = settle_owned_sessions(server, session["id"], workspace, folder,
                        interrupt=True, cancel=monitor.cancel if monitor else None)
                    raise
                report["owned_settlement"] = settle_owned_sessions(server, session["id"], workspace, folder,
                    interrupt=not report["manual_compaction"]["completed"], cancel=monitor.cancel if monitor else None)
                cli_completed &= (report["manual_compaction"]["completed"] and
                                  not report["manual_compaction"].get("obvious_task_contradiction") and
                                  report["owned_settlement"]["idle"])
            elif args.compact_after:
                report["manual_compaction"] = {"admitted": False, "completed": False, "status": "prompt_incomplete"}
            report["stage_finished_unix_ms"] = time.time() * 1000
            events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines() if line.strip()]
            event_session_ids = {event["sessionID"] for event in events if event.get("sessionID")}
            audit = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
            required_ids = audit_session_ids(audit) | event_session_ids | {session["id"]}
            report["event_session_ids"] = sorted(event_session_ids)
            report["audited_generation_session_ids"] = sorted(audit_session_ids(audit))
            report["event_errors"] = [event.get("error") for event in events if event.get("type") == "error"]
            tool_parts = [event.get("part", {}) for event in events if event.get("type") == "tool_use"]
            report["tool_calls"] = len(tool_parts)
            report["tool_errors"] = [{"tool": part.get("tool"), "error": part.get("state", {}).get("error")}
                                     for part in tool_parts if part.get("state", {}).get("status") == "error"]
            exports, report["session_ownership"] = export_owned_sessions(
                server, required_ids, session["id"], workspace, folder)
            report["session_ids"] = sorted(e["data"]["info"]["id"] for e in exports)
            report["native_session_tokens"] = {e["data"]["info"]["id"]: e["data"]["info"].get("tokens") for e in exports}
            report["generation_completion"] = generation_completion(
                exports, report["prompt_started_unix_ms"], session["id"], required_ids)
            report["model_completed"] = bool(cli_completed and not report["event_errors"]
                                             and report["generation_completion"]["verified"])
            report["completed"] = report["model_completed"] and report["session_ownership"]["verified"]
            plugin_after = server.request("GET", "/api/plugin")
            (folder / "plugin-inventory-after.json").write_text(json.dumps(plugin_after, indent=2) + "\n")
            report["audit_plugin_active_after"] = plugin_active(plugin_after, "localai.inference-audit", audit_plugin)
            report["product_plugin_active_after"] = plugin_active(plugin_after, "kryn.product", product_plugin)
            if args.no_tools or attachment or args.thinking_budget is not None:
                audit = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
                checks = acceptance_checks(audit, session["id"], args.no_tools, image_info,
                                           args.thinking_budget, tool_parts, exports)
                if attachment:
                    checks["attachment_unchanged"] = hashlib.sha256(attachment.read_bytes()).hexdigest() == image_info["sha256"]
                report["acceptance_checks"] = checks
                report["completed"] &= all(checks.values())
            # The external grader and transcript review decide task success, never this exit code.
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["completed"] = False
        raise
    finally:
        if monitor is None:
            sampling_stop.set()
            sampler.join(timeout=20)
        else:
            try:
                monitor.close()
            except Exception as error:
                report["resource_cleanup_error"] = type(error).__name__ + ": " + str(error)
                report["completed"] = False
            report["resource_guard"]["reason"] = monitor.guard.reason
            report["resource_guard"]["preflight_passed"] = monitor.preflight_passed
            report["owned_native_server_exited"] = bool(server is not None and server.process is not None
                                                         and server.process.poll() is not None)
        try:
            if "prompt_finished_unix_ms" in report:
                audit = [json.loads(line) for line in (folder / "inference.jsonl").read_text().splitlines() if line.strip()]
                report["route_coverage"] = route_coverage(audit, exports, report["prompt_started_unix_ms"],
                                                         report.get("stage_finished_unix_ms", report["prompt_finished_unix_ms"]))
                report["route_coverage"]["plugin_snapshot_unchanged"] = all(
                    hashlib.sha256((audit_plugin / name).read_bytes()).hexdigest() == digest
                    for name, digest in audit_hashes.items())
                report["route_coverage"]["verified"] &= report["route_coverage"]["plugin_snapshot_unchanged"]
                report["route_coverage"]["plugin_active_before_and_after"] = bool(
                    report.get("audit_plugin_active_before") and report.get("audit_plugin_active_after"))
                report["route_coverage"]["verified"] &= report["route_coverage"]["plugin_active_before_and_after"]
                exported_ids = {e["data"]["info"]["id"] for e in exports}
                report["route_coverage"]["unexported_audit_sessions"] = sorted(audit_session_ids(audit) - exported_ids)
                report["route_coverage"]["sessions_owned"] = report.get("session_ownership", {}).get("verified", False)
                report["route_coverage"]["verified"] &= bool(
                    report["route_coverage"]["sessions_owned"] and not report["route_coverage"]["unexported_audit_sessions"])
                if report["route_coverage"]["unexported_audit_sessions"]:
                    report["model_completed"] = report["completed"] = False
                if report["route_coverage"]["rejected_audit_events"]:
                    report["completed"] = False
            else:
                report["route_coverage"] = {"verified": False, "reason": "No completed native prompt to audit"}
        except (OSError, ValueError, KeyError, TypeError) as error:
            report["route_coverage"] = {"verified": False, "reason": type(error).__name__}
        report["routing_verified"] = report["route_coverage"]["verified"]
        report.setdefault("acceptance_checks", {})["trial_inputs_verified"] = bool(
            report.get("product_plugin_active_before") and report.get("product_plugin_active_after")
            and hashes_match(product_plugin, input_hashes["product"])
            and hashes_match(config_root, input_hashes["config"]))
        report["completed"] &= report["acceptance_checks"]["trial_inputs_verified"]
        if ready_tools or args.no_tools or attachment or args.thinking_budget is not None or monitor is not None:
            report.setdefault("acceptance_checks", {})["routing_verified"] = report["routing_verified"]
            report["completed"] &= report["routing_verified"]
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        report["memory_after"] = memory_snapshot()
        report["power_after"] = power_source()
        report["resources"] = summarize_resources(samples)
        if monitor is not None:
            summary = report["resources"]
            clean = (summary["telemetry_complete"] and not summary["warning_or_critical_observed"]
                     and summary["swap_peak_growth_bytes"] <= 512 * 1024**2
                     and not monitor.guard.reason and not report.get("resource_cleanup_error"))
            report.setdefault("acceptance_checks", {}).update(resource_guard_clean=clean,
                owned_sessions_idle=report.get("owned_settlement", {}).get("idle", False),
                owned_cli_exited=report.get("owned_cli_exited", False),
                owned_native_server_exited=report["owned_native_server_exited"])
            report["completed"] &= all(report["acceptance_checks"].values())
        (folder / "driver.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"evidence": str(folder), "driver_completed": report["completed"], "wall_seconds": report["wall_seconds"]}), flush=True)
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
