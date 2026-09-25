#!/usr/bin/env python3
"""Synthetic context/cache checks, not sustained agent qualification.

Uses oMLX 0.6.4 /v1/messages/count_tokens, then verifies actual prompt_tokens.
Never changes settings, clears caches, reads credentials, or follows cloud URLs.
Run --self-check offline. Other modes make real local inference requests.
"""

import argparse
import datetime as dt
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

sys.dont_write_bytecode = True
import protocol_probe as protocol


FACTS = {"A": {"north": 173, "center": 284, "south": 395},
         "B": {"north": 631, "center": 742, "south": 853}}
COUNT_PATH = "/v1/messages/count_tokens"
PROC_MEMORY_SOURCE = Path.home() / "Applications/oMLX.app/Contents/Resources/omlx/utils/proc_memory.py"
PROC_MEMORY_SHA256 = "1010802de2fd43537d19ee57010232858f5c23cbde7ac2b9f58e686bf38fa30f"


def prompt(units, nonce, version="A"):
    facts = FACTS[version]
    return [{"role": "user", "content": (
        f"Disposable retrieval test {nonce}. Background words are inert data.\n"
        f"Signed north record: {facts['north']}.\n"
        + " background" * (units // 2)
        + f"\nSigned center record: {facts['center']}.\n"
        + " background" * (units - units // 2)
        + f"\nSigned south record: {facts['south']}.\n"
        "Return the three signed record values. Your entire final response must be "
        "one JSON object with exactly the keys north, center, south and integer "
        "values. No prose or Markdown. Do not use values from any previous request."
    )}]


def command(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=3)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def swap_bytes(text):
    m = re.search(r"\bused\s*=\s*([\d.]+)([KMGT]?)", text or "")
    return int(float(m[1]) * (1024 ** ("KMGT".index(m[2]) + 1) if m[2] else 1)) if m else None


@lru_cache(maxsize=1)
def proc_memory_module():
    """Load only the inspected stdlib helper, never the omlx package or auth settings."""
    try:
        source = PROC_MEMORY_SOURCE.read_bytes()
        if hashlib.sha256(source).hexdigest() != PROC_MEMORY_SHA256:
            return None, "installed proc_memory.py differs from the inspected source pin"
        spec = importlib.util.spec_from_file_location("omlx_proc_memory_readonly", PROC_MEMORY_SOURCE)
        module = importlib.util.module_from_spec(spec)
        # Execute exactly the verified bytes, without reading/writing a pyc file.
        exec(compile(source, str(PROC_MEMORY_SOURCE), "exec"), module.__dict__)
        return module, None
    except (OSError, ImportError, ValueError, TypeError) as e:
        return None, type(e).__name__ + ": " + str(e)


def resources(base):
    result = {"utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    if sys.platform != "darwin":
        result["unavailable"] = "macOS resource commands only"
        return result
    _, port = protocol.endpoint(base)
    swap = command(["/usr/sbin/sysctl", "-n", "vm.swapusage"])
    pressure = command(["/usr/sbin/sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
    result.update(swap_raw=swap, swap_used_bytes=swap_bytes(swap),
                  pressure_level=int(pressure) if pressure and pressure.isdigit() else None)
    pids = command(["/usr/sbin/lsof", "-nP", "-a", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
    ids = sorted({int(x) for x in (pids or "").split() if x.isdigit()})
    processes = {pid: {"pid": pid, "rss_bytes": None, "phys_footprint_bytes": None,
                      "lifetime_max_phys_footprint_bytes": None} for pid in ids}
    if ids:
        text = command(["/bin/ps", "-o", "pid=,rss=,comm=", "-p", ",".join(map(str, ids))])
        for line in (text or "").splitlines():
            fields = line.split(None, 2)
            if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
                processes[int(fields[0])].update(rss_bytes=int(fields[1]) * 1024,
                                                command=fields[2])
        module, error = proc_memory_module()
        result["phys_footprint_source_sha256"] = PROC_MEMORY_SHA256
        if error:
            result["phys_footprint_unavailable"] = error
        for pid, process in processes.items():
            if module is not None:
                process["phys_footprint_bytes"] = module.get_phys_footprint(pid) or None
                process["lifetime_max_phys_footprint_bytes"] = module.get_lifetime_max_phys_footprint(pid) or None
                if process["phys_footprint_bytes"] is None:
                    process["phys_footprint_unavailable"] = "libproc returned no measurement; process may have exited or access was denied"
    result["listener_processes"] = list(processes.values())
    return result


def telemetry_ready(sample):
    processes = sample.get("listener_processes", [])
    return (type(sample.get("swap_used_bytes")) is int and sample["swap_used_bytes"] >= 0
            and type(sample.get("pressure_level")) is int
            and sample["pressure_level"] in {1, 2, 4, 6}
            and len(processes) == 1 and type(processes[0].get("pid")) is int
            and any(type(processes[0].get(k)) is int and processes[0][k] > 0
                    for k in ("phys_footprint_bytes", "rss_bytes")))


class ResourceGuard:
    """Declared request-local cancellation gates; a brief warning still fails grading."""
    def __init__(self, max_swap_growth, warning_samples, baseline_swap=None):
        self.max_swap_growth, self.warning_samples = max_swap_growth, warning_samples
        self.baseline_swap, self.pid, self.warnings = baseline_swap, None, 0
        self.reason = None

    def check(self, sample):
        if self.reason:
            return self.reason
        if not telemetry_ready(sample):
            self.reason = "resource telemetry missing or listener identity ambiguous"
        else:
            pid = sample["listener_processes"][0]["pid"]
            if self.pid is not None and self.pid != pid:
                self.reason = "listener process changed during the request"
            self.pid = pid
            swap = sample["swap_used_bytes"]
            if self.baseline_swap is None:
                self.baseline_swap = swap
            level = sample["pressure_level"]
            self.warnings = self.warnings + 1 if level & 2 else 0
            if level & 4:
                self.reason = "critical host memory pressure"
            elif swap - self.baseline_swap > self.max_swap_growth:
                self.reason = "whole-probe swap growth exceeded the declared budget"
            elif self.warnings >= self.warning_samples:
                self.reason = "sustained host memory warning"
        return self.reason


def summarize_resources(samples):
    swaps = [s["swap_used_bytes"] for s in samples if s.get("swap_used_bytes") is not None]
    processes = [p for s in samples for p in s.get("listener_processes", [])]
    rss = [p["rss_bytes"] for p in processes if p.get("rss_bytes") is not None]
    footprints = [p["phys_footprint_bytes"] for p in processes if p.get("phys_footprint_bytes") is not None]
    lifetime = [p["lifetime_max_phys_footprint_bytes"] for p in processes if p.get("lifetime_max_phys_footprint_bytes") is not None]
    levels = [s["pressure_level"] for s in samples if s.get("pressure_level") is not None]
    return {"sample_count": len(samples), "max_listener_rss_bytes": max(rss) if rss else None,
            "max_sampled_listener_phys_footprint_bytes": max(footprints) if footprints else None,
            "max_observed_listener_lifetime_phys_footprint_bytes": max(lifetime) if lifetime else None,
            "swap_start_bytes": swaps[0] if swaps else None,
            "swap_end_bytes": swaps[-1] if swaps else None,
            "swap_peak_bytes": max(swaps) if swaps else None,
            "swap_peak_growth_bytes": max(swaps) - swaps[0] if swaps else None,
            "pressure_levels_observed": sorted(set(levels)),
            "warning_or_critical_observed": any(x & 6 for x in levels),
            "telemetry_complete": bool(samples) and all(telemetry_ready(s) for s in samples),
            "rss_available": bool(rss), "phys_footprint_available": bool(footprints),
            "caveat": "Physical footprint is process-wide and includes Metal-backed allocations; it is not per-model or KV usage. Sampled peaks can miss transients. Lifetime peak covers the whole process lifetime, not this case. RSS may underreport Metal memory. Short samples do not establish bounded long-run swap."}


def observe_request(args, folder, label, payload, baseline_swap=None, dispatch_state=None):
    samples, stop, cancel = [], threading.Event(), threading.Event()
    guard = ResourceGuard(args.max_swap_growth_mib * 1024**2, args.warning_samples, baseline_swap)
    with (folder / (label + ".resources.jsonl")).open("x") as log:
        def sample():
            try:
                item = resources(args.base_url)
            except Exception as error:
                item = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "unavailable": type(error).__name__}
            reason = guard.check(item)
            if reason:
                item["guard_reason"] = reason
                cancel.set()
            samples.append(item)
            try:
                log.write(json.dumps(item) + "\n")
                log.flush()
            except Exception:
                guard.reason = "resource evidence write failed"
                cancel.set()
                raise

        def poll():
            while not stop.wait(args.sample_interval):
                try:
                    sample()
                except Exception:
                    return  # sample() has already signalled owned cancellation.

        # Refuse to begin on a non-green sample, even if warning persistence
        # has not yet reached the mid-request cancellation threshold.
        for index in range(3):
            sample()
            if cancel.is_set() or samples[-1].get("pressure_level") != 1:
                raise RuntimeError(guard.reason or "resource preflight was not green; no generation sent")
            if index < 2:
                time.sleep(args.sample_interval)
        watcher = threading.Thread(target=poll, daemon=True)
        watcher.start()
        try:
            if dispatch_state is not None:
                dispatch_state["attempted"] = True
            response = protocol.request(args.base_url, folder, label,
                "/v1/chat/completions", payload, timeout=args.timeout,
                cancel_event=cancel, cancel_reason="context resource guard")
        finally:
            error_in_flight = sys.exc_info()[0] is not None
            stop.set()
            watcher.join()  # Every command in the sampler has a bounded timeout.
            try:
                sample()
            except BaseException as cleanup_error:
                if dispatch_state is not None:
                    dispatch_state["resource_cleanup_error"] = type(cleanup_error).__name__
                if not error_in_flight:
                    raise
    summary = summarize_resources(samples)
    summary.update(guard_reason=guard.reason, warning_samples_to_abort=args.warning_samples)
    return response, summary


def calibrate(target, count, build):
    """Find an exact server-counted length; never substitute a chars/token estimate."""
    seen = {}

    def measure(n):
        if n not in seen:
            seen[n] = count(build(n))
        return seen[n]

    base = measure(0)
    if target < base:
        raise ValueError(f"target {target} is below the fixed prompt size {base}")
    if target == base:
        return build(0), 0, base, seen
    upper = 128
    upper_count = measure(upper)
    if upper_count <= base:
        raise ValueError("token counter did not grow with padding")
    # Initial interpolation is based on actual API measurements; the result is
    # always counted again, and binary search handles nonlinear tokenization.
    upper = max(upper, int((target - base) * 128 / (upper_count - base)) + 1)
    upper_count = measure(upper)
    while upper_count < target:
        upper *= 2
        if upper > 524288:
            raise ValueError("padding calibration exceeded its bound")
        upper_count = measure(upper)
    lower = 0
    while lower <= upper and len(seen) <= 24:
        middle = (lower + upper) // 2
        value = measure(middle)
        if value == target:
            return build(middle), middle, value, seen
        if value < target:
            lower = middle + 1
        else:
            upper = middle - 1
    raise ValueError("exact requested token count is unattainable with fixed padding; no inference sent")


def answer_matches(response, expected):
    try:
        def unique(items):
            if len(items) != len({k for k, _ in items}):
                raise ValueError("duplicate JSON key")
            return dict(items)
        value = json.loads(response.get("assistant", {}).get("content", ""), object_pairs_hook=unique)
        return (value == expected and isinstance(value, dict)
                and all(type(v) is int for v in value.values()))
    except (ValueError, TypeError):
        return False


def context_rejected(response):
    errors = response.get("metrics", {}).get("errors", [])
    detail = json.dumps(response.get("json", {})) + " " + json.dumps(errors)
    explicit = bool(re.search(r"context|too many tokens|token.{0,30}limit", detail, re.I))
    status = response.get("http_status")
    return (explicit and not response.get("transport_error")
            and (status in (400, 413, 422) or (status == 200 and bool(errors)))
            and not response.get("assistant", {}).get("content"))


def perform(args, folder, report):
    counter_calls = 0
    status_calls = 0
    baseline_swap = None

    def idle(label, wait=False):
        nonlocal status_calls
        start, quiet = time.monotonic(), 0
        evidence = {"stage": label, "idle": False, "samples": []}
        while time.monotonic() - start < 30:
            status_calls += 1
            r = protocol.request(args.base_url, folder, f"status-{status_calls:03}", "/api/status",
                                 timeout=min(3, max(.01, 30 - (time.monotonic() - start))))
            state = r.get("json") or {}
            sample = {k: state.get(k) for k in ("default_model", "active_requests", "waiting_requests")}
            good = (r.get("http_status") == 200 and not r.get("transport_error")
                    and sample["default_model"] == args.model
                    and all(type(sample[k]) is int and sample[k] == 0 for k in ("active_requests", "waiting_requests")))
            evidence["samples"].append(sample)
            quiet = quiet + 1 if good else 0
            if quiet >= (2 if wait else 1):
                evidence["idle"] = True
                break
            if not wait or r.get("transport_error") or sample["default_model"] != args.model:
                break
            time.sleep(min(.5, max(0, 30 - (time.monotonic() - start))))
        evidence["wall_seconds"] = round(time.monotonic() - start, 3)
        report.setdefault("idle_checks", []).append(evidence)
        return evidence["idle"]

    def count(messages):
        nonlocal counter_calls
        counter_calls += 1
        r = protocol.request(args.base_url, folder, f"count-{counter_calls:03}", COUNT_PATH,
                             {"model": args.model, "messages": messages}, timeout=args.timeout)
        n = (r.get("json") or {}).get("input_tokens")
        if r.get("http_status") != 200 or r.get("transport_error") or type(n) is not int or n <= 0:
            raise RuntimeError("No trustworthy token-count API response; exact-size testing unavailable")
        return n + args.template_token_offset

    def send(label, messages, target, expected, oversize=False):
        nonlocal baseline_swap
        if not oversize and (target > advertised or (args.planning_budget is not None
                and target + args.max_tokens > args.planning_budget)):
            raise RuntimeError("Measured input exceeds text admission or the declared conservative planning budget")
        if not idle(label + "-before"):
            raise RuntimeError("Runtime is not idle on the expected model; no generation sent")
        payload = protocol.body(args.model, args.variant, messages, 1 if oversize else args.max_tokens)
        payload["thinking_budget"] = 0 if oversize else args.thinking_budget
        dispatch = {"stage": label, "attempted": False}
        report.setdefault("dispatches", []).append(dispatch)
        settled = False
        try:
            response, telemetry = observe_request(args, folder, label, payload, baseline_swap, dispatch)
        finally:
            # Preserve the original interruption/write error while still
            # verifying that our possibly dispatched request has settled.
            error_in_flight = sys.exc_info()[0] is not None
            if dispatch["attempted"]:
                try:
                    settled = idle(label + "-after", wait=True)
                    dispatch["runtime_idle_after"] = settled
                except BaseException as cleanup_error:
                    dispatch["idle_cleanup_error"] = type(cleanup_error).__name__
                    if not error_in_flight:
                        raise
        if baseline_swap is None:
            baseline_swap = telemetry["swap_start_bytes"]
        usage = response.get("usage") or {}
        actual = usage.get("prompt_tokens")
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        metrics = protocol.compact(response)
        metrics.update(requested_input_tokens=target, actual_input_tokens=actual,
                       token_count_verified=actual == target, expected_answer=expected,
                       answer_correct=answer_matches(response, expected), resources=telemetry,
                       runtime_idle_after=settled,
                       cached_tokens=cached,
                       cache_fraction=cached / actual if type(cached) is int and actual else None,
                       pass_scope="synthetic retrieval and protocol only")
        if oversize:
            metrics["explicit_context_rejection"] = context_rejected(response)
            metrics["pass"] = metrics["explicit_context_rejection"]
            metrics["token_count_evidence"] = "count endpoint; rejected request has no generation usage"
        else:
            metrics["pass"] = bool(protocol.healthy_stream(response) and actual == target
                and metrics["answer_correct"] and response["metrics"]["finish_reason"] == "stop"
                and not telemetry["warning_or_critical_observed"])
        metrics["swap_budget_exceeded"] = (telemetry["swap_peak_growth_bytes"] is not None
            and telemetry["swap_peak_growth_bytes"] > args.max_swap_growth_mib * 1024 ** 2)
        metrics["pass"] &= bool(settled and telemetry["telemetry_complete"] and not telemetry["guard_reason"]
                                and not telemetry["warning_or_critical_observed"] and not metrics["swap_budget_exceeded"])
        if label.endswith("-initial"):
            metrics["observed_cold"] = cached == 0
        report["cases"][label] = metrics
        protocol.save_json(folder / (label + ".assessment.json"), metrics)
        return metrics

    health = protocol.request(args.base_url, folder, "health", "/health", timeout=args.timeout)
    if health.get("http_status") != 200 or health.get("transport_error"):
        raise RuntimeError("local runtime health failed")
    models = protocol.request(args.base_url, folder, "models", "/v1/models", timeout=args.timeout)
    listed = [m.get("id") for m in (models.get("json") or {}).get("data", []) if isinstance(m, dict)]
    if models.get("http_status") != 200 or args.model not in listed:
        raise RuntimeError("requested model is not listed by this local server")
    advertised = next(m.get("max_model_len") for m in models["json"]["data"] if m.get("id") == args.model)
    if type(advertised) is not int or advertised <= 0:
        raise RuntimeError("Runtime did not advertise a trustworthy text-prompt admission limit")
    report["advertised_text_admission_limit"] = advertised
    if args.server_context_limit is not None and args.server_context_limit != advertised:
        raise RuntimeError("Asserted text-prompt admission limit differs from advertised max_model_len")
    if args.mode != "oversize" and any(n > advertised for n in args.input_tokens):
        raise RuntimeError("Positive input target exceeds runtime text-prompt admission; use oversize mode")
    if not idle("before-token-calibration"):
        raise RuntimeError("Runtime is not idle; token calibration and generation were not started")
    targets = [args.server_context_limit + 64] if args.mode == "oversize" else args.input_tokens
    for target in targets:
        nonce = report["run_nonce"] + "-" + str(target)
        messages, units, preflight_tokens, seen = calibrate(target, count, lambda n: prompt(n, nonce))
        report["calibrations"].append({"target_tokens": target, "units": units,
            "predicted_generation_tokens": preflight_tokens,
            "counted_tokens": preflight_tokens - args.template_token_offset,
            "template_token_offset": args.template_token_offset, "adjusted_samples": seen,
            "count_endpoint": COUNT_PATH, "template": "single user message; Qwen " + args.variant})
        if args.mode == "oversize":
            send("oversize", messages, target, FACTS["A"], oversize=True)
            break
        cold = send(f"{target}-initial", messages, target, FACTS["A"])
        # A nonce reduces accidental reuse. Do not call a request cold unless its
        # reported cache count is actually zero; this helper never flushes caches.
        if not cold["pass"]:
            break
        if args.mode == "cache":
            warm = send(f"{target}-repeat", messages, target, FACTS["A"])
            if not warm["pass"]:
                break
            changed = prompt(units, nonce, "B")
            changed_count = count(changed)
            unrelated = send(f"{target}-changed-facts", changed, changed_count, FACTS["B"])
            if not unrelated["pass"]:
                break
            restored = send(f"{target}-restore-original", messages, target, FACTS["A"])
            report["cache_reuse_pass"] = all(
                type(case["cached_tokens"]) is int and case["cache_fraction"] is not None
                and case["cache_fraction"] >= args.min_cache_fraction
                for case in (warm, restored))
            report["cache_correctness_pass"] = all(c["answer_correct"] for c in (cold, warm, unrelated, restored))
            break
    report["counter_requests"] = counter_calls


def self_check():
    import copy
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch
    messages, n, count, samples = calibrate(1000, lambda m: 20 + len(m), lambda n: "x" * n)
    assert len(messages) == 980 and n == 980 and count == 1000 and len(samples) <= 24
    try:
        calibrate(21, lambda m: 20 + 2 * len(m), lambda n: "x" * n)
    except ValueError:
        pass
    else:
        raise AssertionError("inexact token count accepted")
    assert swap_bytes("total = 2.00G used = 1.50G free = 0.50G") == int(1.5 * 1024 ** 3)
    assert swap_bytes(None) is None
    assert swap_bytes("used = 4096") == 4096
    a = {"assistant": {"content": json.dumps(FACTS["A"])}}
    assert answer_matches(a, FACTS["A"]) and not answer_matches(a, FACTS["B"])
    assert not answer_matches({"assistant": {"content": "It passed."}}, FACTS["A"])
    assert not answer_matches({"assistant": {"content": '{"north":1,"north":173,"center":284,"south":395}'}}, FACTS["A"])
    assert context_rejected({"http_status": 400, "json": {"error": "Context limit exceeded"}})
    assert not context_rejected({"http_status": 400, "json": {"error": "Unknown model"}})
    assert not context_rejected({"http_status": 200, "json": {"message": "Context works"}})
    assert "173" in prompt(20, "offline", "A")[0]["content"]
    assert "631" in prompt(20, "offline", "B")[0]["content"]
    telemetry = summarize_resources([
        {"swap_used_bytes": 50, "pressure_level": 1, "listener_processes": [
            {"pid": 1, "rss_bytes": None, "phys_footprint_bytes": 100,
             "lifetime_max_phys_footprint_bytes": 200}]},
        {"swap_used_bytes": 45, "pressure_level": 1, "listener_processes": [
            {"pid": 1, "rss_bytes": 90, "phys_footprint_bytes": 120,
             "lifetime_max_phys_footprint_bytes": 200}]}])
    assert telemetry["max_sampled_listener_phys_footprint_bytes"] == 120
    assert telemetry["max_observed_listener_lifetime_phys_footprint_bytes"] == 200
    assert telemetry["max_listener_rss_bytes"] == 90 and telemetry["telemetry_complete"]
    assert not summarize_resources([])["telemetry_complete"]
    green = {"swap_used_bytes": 100, "pressure_level": 1, "listener_processes": [
        {"pid": 1, "rss_bytes": 100, "phys_footprint_bytes": 120}]}
    warning = {**green, "pressure_level": 2}
    assert not telemetry_ready({**green, "pressure_level": True})
    guard = ResourceGuard(50, 2)
    assert guard.check(green) is None and guard.check(warning) is None
    assert guard.check(green) is None and guard.check(warning) is None
    assert guard.check(warning) == "sustained host memory warning"
    assert ResourceGuard(50, 2).check({**green, "pressure_level": 4}) == "critical host memory pressure"
    assert ResourceGuard(50, 2, 0).check(green) == "whole-probe swap growth exceeded the declared budget"
    assert ResourceGuard(50, 2).check({})
    assert not summarize_resources([green, {}])["telemetry_complete"]
    guard = ResourceGuard(50, 2)
    guard.check(green)
    assert guard.check({**green, "listener_processes": [{"pid": 2, "rss_bytes": 100}]})
    args = SimpleNamespace(base_url="http://127.0.0.1", model="test", mode="cache", variant="think", thinking_budget=3072, template_token_offset=0, timeout=1,
        max_tokens=128, input_tokens=[512], server_context_limit=4096, planning_budget=4096,
        sample_interval=.01, warning_samples=2, max_swap_growth_mib=512, min_cache_fraction=.5)
    sent, busy, bad_repeat, bad_telemetry, fault = [], False, False, False, None
    def fake_request(_base, _folder, _label, path, payload=None, **_kwargs):
        if path == "/api/status":
            if fault == "cleanup-fail" and sent:
                raise OSError("offline cleanup failure")
            value = {"default_model": "test", "active_requests": int(busy), "waiting_requests": 0}
        elif path == "/v1/models":
            value = {"data": [{"id": "test", "max_model_len": 4096}]}
        elif path == COUNT_PATH:
            value = {"input_tokens": 100 + payload["messages"][0]["content"].count(" background")}
        else:
            assert path == "/health"
            value = {}
        return {"http_status": 200, "json": value}
    def fake_observe(_args, _folder, label, payload, _baseline, dispatch):
        if fault == "preflight":
            raise RuntimeError("offline preflight refusal")
        dispatch["attempted"] = True
        sent.append(label)
        if fault in {"interrupt", "cleanup-fail"}:
            raise KeyboardInterrupt("original offline interruption")
        text = payload["messages"][0]["content"]
        answer = FACTS["B" if "Signed north record: 631." in text else "A"]
        if bad_repeat and label.endswith("-repeat"):
            answer = {}
        n = 100 + text.count(" background")
        result = {"http_status": 200, "assistant": {"content": json.dumps(answer)},
            "usage": {"prompt_tokens": n, "completion_tokens": 1, "total_tokens": n + 1,
                      "prompt_tokens_details": {"cached_tokens": n - 1}},
            "metrics": {"protocol_complete": True, "finish_reason": "stop"}}
        summary = summarize_resources([green, {}] if bad_telemetry else [green])
        return result, {**summary, "guard_reason": None}
    def fresh(): return {"run_nonce": "offline", "cases": {}, "calibrations": []}
    with tempfile.TemporaryDirectory() as tmp, patch.object(protocol, "request", fake_request), \
            patch(__name__ + ".observe_request", fake_observe), patch.object(time, "sleep", lambda _: None):
        root = Path(tmp)
        for label in ("good", "warm-fail", "missing", "busy", "cap"):
            folder = root / label; folder.mkdir(); sent.clear()
            busy, bad_repeat, bad_telemetry = label == "busy", label == "warm-fail", label == "missing"
            trial_args = copy.copy(args)
            if label == "cap": trial_args.server_context_limit = 2048
            report = fresh()
            try:
                perform(trial_args, folder, report)
            except RuntimeError:
                assert label in {"busy", "cap"} and not sent
            else:
                assert label not in {"busy", "cap"}
                assert len(sent) == {"good": 4, "warm-fail": 2, "missing": 1}[label]
                assert all(c["pass"] for c in report["cases"].values()) == (label == "good")
        busy = bad_repeat = bad_telemetry = False
        for fault in ("interrupt", "cleanup-fail", "preflight"):
            folder = root / fault; folder.mkdir(); sent.clear(); report = fresh()
            try:
                perform(args, folder, report)
            except KeyboardInterrupt as error:
                assert fault != "preflight" and str(error) == "original offline interruption"
                dispatch = report["dispatches"][0]
                assert dispatch["attempted"] and (dispatch.get("runtime_idle_after") is True
                    if fault == "interrupt" else dispatch.get("idle_cleanup_error") == "OSError")
            except RuntimeError:
                assert fault == "preflight" and not report["dispatches"][0]["attempted"]
                assert not any(s["stage"].endswith("-after") for s in report["idle_checks"])
            else:
                raise AssertionError("original failure was swallowed")
    print("Offline self-check passed: exact counts, strict answers, guards/telemetry, idle/cap refusal and cache fail-fast; no network or inference.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--model")
    p.add_argument("--nonce", help="optional fixed fixture ID for exact request replay across configurations")
    p.add_argument("--runs-dir", type=Path)
    p.add_argument("--mode", choices=("cache", "context", "oversize"), default="cache")
    p.add_argument("--variant", choices=("fast", "think"), default="think", help="match the agent's fast or thinking request while measuring context")
    p.add_argument("--thinking-budget", type=int, help="reasoning budget; defaults to up to 3072 in think while leaving 256 output tokens, or 0 in fast")
    p.add_argument("--template-token-offset", type=int, default=0,
                   help="measured generation-minus-count endpoint offset for this model and variant; actual usage must still match")
    p.add_argument("--input-tokens", default="8192", help="exact input counts, comma separated; not combined windows")
    p.add_argument("--server-context-limit", type=int, help="text-prompt admission limit, checked against max_model_len; not a combined window")
    p.add_argument("--planning-budget", type=int, help="optional probe-only conservative input+requested-output budget; never changes the runtime")
    p.add_argument("--max-tokens", type=int, default=768)
    p.add_argument("--timeout", type=float, default=900)
    p.add_argument("--sample-interval", type=float, default=5)
    p.add_argument("--warning-samples", type=int, default=2, help="consecutive warning samples before cancelling; any warning still fails acceptance")
    p.add_argument("--min-cache-fraction", type=float, default=0.5)
    p.add_argument("--max-swap-growth-mib", type=int, default=512)
    args = p.parse_args()
    if args.thinking_budget is None:
        args.thinking_budget = min(3072, max(0, args.max_tokens - 256)) if args.variant == "think" else 0
    if args.self_check:
        self_check()
        return 0
    try:
        protocol.endpoint(args.base_url)
        args.input_tokens = [int(x) for x in args.input_tokens.split(",")]
        if not args.model or not args.runs_dir:
            raise ValueError("--model and --runs-dir are required")
        if args.nonce and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.nonce):
            raise ValueError("nonce must be 1..64 ASCII letters, digits, underscores or hyphens")
        if not args.input_tokens or any(not 512 <= x <= 131072 for x in args.input_tokens):
            raise ValueError("input counts must be within 512..131072")
        if args.mode == "cache" and len(args.input_tokens) != 1:
            raise ValueError("cache mode accepts exactly one input size")
        if args.server_context_limit is not None and not 1024 <= args.server_context_limit <= 131072:
            raise ValueError("server context limit must be within 1024..131072")
        if not -64 <= args.template_token_offset <= 64:
            raise ValueError("template token offset must be within -64..64")
        if args.mode == "oversize" and args.server_context_limit is None:
            raise ValueError("oversize mode requires the observed --server-context-limit")
        if args.mode != "oversize" and args.server_context_limit is not None and any(
                x > args.server_context_limit for x in args.input_tokens):
            raise ValueError("input exceeds the supplied text-prompt admission limit")
        if args.planning_budget is not None and (not 1024 <= args.planning_budget <= 262144
                or args.mode == "oversize" or any(x + args.max_tokens > args.planning_budget for x in args.input_tokens)):
            raise ValueError("planning budget must be 1024..262144 and cover input+requested output; omit for oversize")
        if not 1 <= args.max_tokens <= 4096 or not 0 < args.timeout <= 3600:
            raise ValueError("max-tokens must be 1..4096; timeout must be >0 and <=3600")
        if args.thinking_budget < 0 or args.thinking_budget >= args.max_tokens and args.mode != "oversize":
            raise ValueError("thinking budget must be nonnegative and leave output room")
        if not 1 <= args.sample_interval <= 60 or not 0 < args.min_cache_fraction <= 1 or args.max_swap_growth_mib < 0:
            raise ValueError("invalid telemetry interval, cache threshold or swap budget")
        if not 1 <= args.warning_samples <= 10:
            raise ValueError("warning-samples must be 1..10")
    except ValueError as e:
        p.error(str(e))
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    nonce = args.nonce or run_id
    folder = args.runs_dir / ("context-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + run_id[:8])
    folder.mkdir()
    report = {"schema_version": 2, "probe_revision": 3, "run_nonce": nonce,
        "model": args.model, "base_url": args.base_url, "mode": args.mode, "variant": args.variant,
        "thinking_budget": args.thinking_budget,
        "server_context_limit_asserted_by_operator": args.server_context_limit,
        "requested_output_max_tokens": 1 if args.mode == "oversize" else args.max_tokens,
        "planning_budget_tokens": args.planning_budget, "min_cache_fraction": args.min_cache_fraction,
        "max_swap_growth_mib": args.max_swap_growth_mib,
        "resource_guard": {"green_samples_before_generation": 3, "sample_interval_seconds": args.sample_interval,
                           "warning_samples_to_abort": args.warning_samples, "critical_aborts_immediately": True,
                           "missing_telemetry_aborts": True, "any_warning_fails_acceptance": True},
        "calibrations": [], "cases": {}, "synthetic_probe_pass": False,
        "sustained_context_qualified": False, "memory_before": protocol.memory_snapshot(),
        "limitations": [
            "Token-count API omits per-request template kwargs; actual generation usage must match.",
            "Exact-size claims refer to active input, not total input plus output.",
            "Server max_model_len is text-only prompt admission, not a hard combined limit; this probe sends no images.",
            "Planning budget is an optional conservative probe check, not a runtime setting or guarantee.",
            "Idle checks are not an atomic reservation; other inference must remain paused. Socket cancellation may take time to reach the GPU.",
            "One synthetic retrieval run cannot qualify a sustained coding-agent window.",
            "No cache flush: coldness is observed, not assumed. Reuse thresholds are test criteria, not upstream guarantees.",
            "Short host/process samples cannot prove bounded long-run memory or swap."]}
    try:
        perform(args, folder, report)
        report["synthetic_probe_pass"] = bool(report["cases"]) and all(c["pass"] for c in report["cases"].values())
        if args.mode == "cache":
            report["synthetic_probe_pass"] &= report.get("cache_reuse_pass", False) and report.get("cache_correctness_pass", False)
        resource_rows = [c["resources"] for c in report["cases"].values()]
        starts = [r["swap_start_bytes"] for r in resource_rows if r["swap_start_bytes"] is not None]
        peaks = [r["swap_peak_bytes"] for r in resource_rows if r["swap_peak_bytes"] is not None]
        growth = max(peaks) - starts[0] if starts and peaks else None
        report["whole_probe_swap_peak_growth_bytes"] = growth
        report["resource_telemetry_complete"] = bool(resource_rows) and all(r["telemetry_complete"] for r in resource_rows)
        report["synthetic_probe_pass"] &= report["resource_telemetry_complete"]
        if growth is not None and growth > args.max_swap_growth_mib * 1024 ** 2:
            report["synthetic_probe_pass"] = False
    except BaseException as e:
        report["fatal_error"] = type(e).__name__ + ": " + str(e)
        if not isinstance(e, Exception):
            raise
    finally:
        report["memory_after"] = protocol.memory_snapshot()
        protocol.save_json(folder / "metrics.json", report)
    print(json.dumps({"synthetic_probe_pass": report["synthetic_probe_pass"],
                      "sustained_context_qualified": False,
                      "metrics": str((folder / "metrics.json").resolve())}))
    return 0 if report["synthetic_probe_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
