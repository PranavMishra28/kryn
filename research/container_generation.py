"""One frozen container development arm; native OpenCode owns all agent work.

No retries, oracle access, scoring or alternate model route. The same lifecycle
can be exercised using canned local responses before any model admission.
"""

import argparse
import contextlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time

from research import local_only
from research.container_admission import (ROOT, PYTHON, SERVER, environment, start_server,
    plugin_inventory, source_inputs, unchanged, routes)
from research.container_export import extract_worktree
from research.container_policy import parse_log, policy_during_tools
from research.container_worker import DockerWorker, HostGuard, validate_worker
from research.local_campaign import atomic, file_sha
from research.run_external_patch import collect_patch
from research.record_external import edited_tests
from research.ui_gateway.synthetic_dispatch import FakeInference
from tools.context_probe import summarize_resources
from tools.learning import InferenceRelay
from tools.run_native_trial import (settle_owned_sessions, export_owned_sessions,
                                    generation_completion)

PROBE = "/opt/kryn-policy-probe.py"


class ContainerServer:
    """JSON transport adapter for existing native ownership/export functions."""
    def __init__(self, docker, worker, password):
        self.docker, self.worker, self.password = docker, worker, password

    def probe(self, mode, *args, timeout=30, cleanup=False):
        return self.docker.command("exec", "-e", "OPENCODE_PASSWORD=" + self.password,
            self.worker, PYTHON, "-I", PROBE, mode, *args, timeout=timeout, cleanup=cleanup)

    def request(self, method, path, body=None, timeout=5):
        return json.loads(self.probe("request", method, path, json.dumps(body),
                                     timeout=timeout, cleanup=True))


def frozen(campaign):
    manifest = json.loads((campaign / "manifest.json").read_text())
    if (file_sha(campaign / "manifest.json") != (campaign / "manifest.sha256").read_text().strip()
            or manifest.get("kind") not in {"swe_container_development", "swe_container_generation_canary"}):
        raise RuntimeError("Unsealed container experiment")
    baseline = Path(manifest["baseline"])
    if manifest.get("power_policy", "ac-only") not in ("ac-only", "battery-capable"):
        raise RuntimeError("Unknown generation power policy")
    unchanged(manifest, baseline)
    if file_sha(campaign / "prompt.txt") != manifest["prompt_sha256"]:
        raise RuntimeError("Frozen prompt changed")
    if manifest.get("arm_order") not in (["native", "kryn"], ["kryn", "native"]):
        raise RuntimeError("Unreviewed development arm order")
    if not 5 <= manifest["wall_seconds"] <= 900 or manifest["request_seconds"] != 360:
        raise RuntimeError("Unreviewed generation budget")
    if manifest["kind"] == "swe_container_development":
        if manifest["wall_seconds"] != 900 or "sequence" in manifest:
            raise RuntimeError("Development cannot substitute a synthetic arm")
        required = {"adjudicator_sha256", "admission_sha256", "wire_controls", "image_preparation_sha256"}
        if not required.issubset(manifest):
            raise RuntimeError("Generation admission pins are incomplete")
        admission = manifest["admission_sha256"]
        if set(admission) != {"generation", "grader", "output", "policy", "image"}:
            raise RuntimeError("Required named admissions are missing")
        for name, pin in admission.items():
            path, digest = Path(pin["path"]), pin["sha256"]
            if path.is_symlink() or not path.is_file() or file_sha(path) != digest:
                raise RuntimeError("Admission evidence drift")
            receipt = json.loads(path.read_text())
            if receipt.get("passed") is not True:
                raise RuntimeError("A required admission did not pass")
            if name == "image" and receipt.get("image") != manifest["image"]:
                raise RuntimeError("Image admission covers another worker")
            if name == "generation" and receipt.get("source_sha256") != manifest["source_sha256"]:
                raise RuntimeError("Generation admission covers different source")
            if name == "generation" and receipt.get("power_policy", "ac-only") != manifest.get("power_policy", "ac-only"):
                raise RuntimeError("Generation admission covers different power policy")
        if manifest["image_preparation_sha256"] != admission["image"]["sha256"]:
            raise RuntimeError("Worker image preparation identity drift")
        wire = manifest["wire_controls"]
        if (set(wire) != {"body_controls_sha256", "tool_schema_sha256s"}
                or not isinstance(wire["body_controls_sha256"], str) or len(wire["body_controls_sha256"]) != 64
                or not isinstance(wire["tool_schema_sha256s"], list) or not 1 <= len(wire["tool_schema_sha256s"]) <= 2
                or any(not isinstance(value, str) or len(value) != 64 for value in wire["tool_schema_sha256s"])):
            raise RuntimeError("Full wire controls are not pinned")
        if file_sha(campaign / "adjudicate.py") != manifest["adjudicator_sha256"]:
            raise RuntimeError("Frozen adjudicator drift")
    return manifest


def wire_evidence(records, expected=None):
    rows = [row for row in records if row.get("tool_count", len(row.get("tools", []))) > 0]
    wires = [{"body_controls_sha256": row.get("body_controls_sha256"),
              "tool_schema_sha256": row.get("tool_schema_canonical_sha256", row.get("tool_schema_sha256"))} for row in rows]
    controls = {wire["body_controls_sha256"] for wire in wires}
    schemas = {wire["tool_schema_sha256"] for wire in wires}
    valid = bool(wires) and None not in controls and None not in schemas and len(controls) == 1
    observed = {"body_controls_sha256": wires[0]["body_controls_sha256"],
                "tool_schema_sha256s": sorted(schemas)} if valid else None
    if expected and "tool_schema_sha256" in expected:
        expected = {"body_controls_sha256": expected["body_controls_sha256"],
                    "tool_schema_sha256s": [expected["tool_schema_sha256"]]}
    matches = valid and (expected is None or (
        observed["body_controls_sha256"] == expected["body_controls_sha256"]
        and schemas.issubset(expected["tool_schema_sha256s"])))
    return {"stable": valid, "wire": observed, "matches_frozen": matches}



@contextlib.contextmanager
def inference(manifest):
    if manifest["kind"] == "swe_container_generation_canary":
        fake = FakeInference(manifest["sequence"], "Synthetic generation completed.")
        thread = threading.Thread(target=fake.serve_forever, daemon=True)
        thread.start()
        try:
            yield fake, fake.server_address[1]
        finally:
            fake.shutdown(); fake.server_close(); thread.join(timeout=5)
    else:
        with InferenceRelay(local_only.MODEL, 8192, manifest["request_seconds"], expected_wire=manifest["wire_controls"]) as relay:
            yield relay, relay.port


def export_source(docker, worker, baseline, manifest, directory, guard):
    archive = directory / "worktree.tar"
    docker.export(worker, archive)
    capture = directory / "capture"
    evidence = extract_worktree(archive, capture, archive_root=".",
        expected_git_config_sha256=manifest["git_config_sha256"],
        baseline_symlinks=manifest["baseline_symlinks"])
    shutil.copytree(baseline / ".git", capture / ".git")
    private = directory / "git-private"; private.mkdir()
    git = Path(subprocess.check_output(["/usr/bin/xcrun", "--find", "git"], text=True).strip()).resolve()
    patch, names, size, sha = collect_patch(capture, manifest["base_commit"], directory,
        private=private, dependencies=[], git_binary=git, tool_path=None,
        cancelled=lambda: bool(guard.reason or guard.memory.cancel.is_set()))
    return {"worker_exported": True, "export": evidence, "patch_sha256": sha,
            "patch_bytes": size, "new_paths": names, "edited_test_paths": edited_tests(patch.read_text())}


def run(campaign, arm):
    manifest = frozen(campaign)
    if arm not in manifest["arm_order"]:
        raise ValueError("Unknown arm")
    directory = campaign / arm
    directory.mkdir(mode=0o700)  # Existing, partial and interrupted arms cannot replay.
    synthetic = manifest["kind"] == "swe_container_generation_canary"
    report = {"kind": "swe_container_generation", "arm": arm, "synthetic_inference": synthetic,
              "power_policy": manifest.get("power_policy", "ac-only"),
              "manifest_sha256": file_sha(campaign / "manifest.json"), "task_id": manifest["task"]["instance_id"],
              "prompt_sha256": manifest["prompt_sha256"], "local_only": None, "generation": {},
              "completed": False, "cli_exit_code": None, "intervention": None,
              "cleanup_settled": False, "inference_relay_settled": False, "worker_exported": False}
    start = time.monotonic()
    worker = server = session = guard = docker = relay = None
    try:
        with inference(manifest) as (relay, port), HostGuard(directory, power_policy=manifest.get("power_policy", "ac-only")) as guard:
            docker = DockerWorker(directory, guard)
            retain = []
            try:
                net, side, ip = docker.route(port)
                worker = docker.create("candidate", manifest["image"], ["sleep", "1200"], network=net, worker=True)
                info = docker.inspect("container", worker)
                validate_worker(info, manifest["image"], docker.owner)
                atomic(directory / "worker-inspect.json", info)
                report["routes"] = routes(docker, worker, side, ip)
                env = start_server(docker, worker, arm == "native", directory, ip, report)
                config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
                if config["providers"]["local"]["models"]["qwen"]["body"] != manifest["model_body"]:
                    raise RuntimeError("Frozen model sampler differs from actual config")
                if not synthetic:
                    report["local_only"] = local_only.attest(env, "/tmp/kryn", "http://127.0.0.1:18765/v1")
                docker.command("cp", str(ROOT / "research/container_policy.py"), worker + ":" + PROBE)
                server = ContainerServer(docker, worker, env["OPENCODE_PASSWORD"])
                session = server.request("POST", "/api/session", {"title": "Frozen container development",
                    "agent": "agent", "permissions": [], "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                    "location": {"directory": "/testbed"}})["data"]["id"]
                report["session_id"] = session
                before = json.loads(server.probe("snapshot", session))
                atomic(directory / "policy-before.json", before)
                docker.command("exec", "-d", "-e", "OPENCODE_PASSWORD=" + env["OPENCODE_PASSWORD"],
                               worker, PYTHON, "-I", PROBE, "watch", session)
                atomic(directory / "policy-ready.json", json.loads(server.probe("ready")))
                docker.last_command = None
                frozen(campaign)
                cli_started = time.time() * 1000
                try:
                    docker.command("exec", "-w", "/testbed", worker, "/usr/bin/env", "-i",
                        *[k + "=" + v for k, v in sorted(env.items())], "/usr/local/bin/opencode", "run",
                        "--server", SERVER, "--session", session, "--model", "local/qwen", "--agent", "agent",
                        "--format", "json", "--auto", "--", (campaign / "prompt.txt").read_text(),
                        timeout=manifest["wall_seconds"])
                    report["cli_exit_code"] = docker.last_command["returncode"]
                except TimeoutError:
                    report["intervention"] = "timeout"
                except Exception as error:
                    report["intervention"] = "resource_guard" if guard.reason or guard.memory.cancel.is_set() else "cli_error"
                    report["cli_error"] = str(error)
                    if report["intervention"] == "cli_error" and docker.last_command:
                        report["cli_exit_code"] = docker.last_command["returncode"]
                cli = docker.last_command
                if cli:
                    atomic(directory / "cli-process.json", cli)
                    shutil.copyfile(cli["stdout"], directory / "events.jsonl")
                    shutil.copyfile(cli["stderr"], directory / "stderr.log")
                if report["intervention"] and not synthetic:
                    relay.cancel()
                owned = settle_owned_sessions(server, session, Path("/testbed"), directory,
                    interrupt=report["intervention"] is not None, cancel=guard.memory.cancel,
                    model_id=local_only.MODEL, guard_gib=22,
                    idle_probe=(lambda: True) if synthetic else None)
                report["settlement"] = owned
                if not owned["idle"]:
                    raise RuntimeError("Native owned sessions did not settle")
                exports, ownership = export_owned_sessions(server, owned["verified_sessions"], session,
                                                          Path("/testbed"), directory)
                report["ownership"] = ownership
                report["generation"] = generation_completion(exports, cli_started, session, set(owned["verified_sessions"]))
                report["plugin_after"] = plugin_inventory(docker, worker, arm == "native", env["OPENCODE_PASSWORD"])
                after = json.loads(server.probe("snapshot", session))
                atomic(directory / "policy-after.json", after)
                report["policy_restored"] = all(before["session"]["data"].get(key) == after["session"]["data"].get(key)
                                                for key in ("agent", "model", "permissions"))
                text = server.probe("finish", session)
                (directory / "policy-log.sse").write_text(text)
                report["policy_mutations"] = policy_during_tools(parse_log(text, session), through_end=True)
                if report["policy_mutations"] or not report["policy_restored"]:
                    raise RuntimeError("Observed native policy mutation or snapshot drift")
                report["completed"] = bool(report["intervention"] is None and report["cli_exit_code"] == 0
                                           and ownership["verified"] and report["generation"]["verified"])
            finally:
                if relay and not synthetic:
                    relay.cancel()
                # Stop all inference routes and worker processes before import or grading.
                try:
                    for identity in docker.containers:
                        try:
                            docker.settle(identity)
                            if identity == worker:
                                retain = [worker]
                        except Exception as error:
                            report.setdefault("settlement_errors", []).append(str(error))
                    if retain and not guard.reason and not guard.memory.cancel.is_set():
                        try:
                            report.update(export_source(docker, worker, Path(manifest["baseline"]), manifest, directory, guard))
                            retain = []
                        except Exception as error:
                            report["export_error"] = str(error)
                finally:
                    docker.close(retain=retain)
                    report["retained_for_safe_export"] = retain
                    report["cleanup_settled"] = not retain
        guard.check()
        frozen(campaign)
    except Exception as error:
        report.update(completed=False, error=str(error))
    finally:
        if relay:
            report["requests"] = relay.calls if synthetic else relay.records
            report["wire"] = wire_evidence(report["requests"], manifest.get("wire_controls"))
            report["relay_rejections"] = {key: getattr(relay, key, None) for key in ("request_rejection", "wire_rejection")}
            report["inference_relay_settled"] = synthetic or (
                not relay.thread.is_alive() and not relay.connections and not relay.gate.locked())
        if guard:
            report["resources"] = summarize_resources(guard.samples)
            report["guard_reason"] = guard.reason or guard.memory.guard.reason
        if not synthetic and report.get("local_only"):
            receipt = report["local_only"]
            try:
                receipt["runtime_same_after"] = local_only.same_runtime(receipt)
            except Exception as error:
                receipt["runtime_same_after"] = False
                receipt["error"] = str(error)
            receipt["observed_local_model_only"] = bool(relay.records and all(r["model"] == local_only.MODEL for r in relay.records))
            receipt["generation_proven"] = receipt["runtime_same_after"] and receipt["observed_local_model_only"]
        r = report.get("resources", {})
        report["completed"] = bool(report["completed"] and report["cleanup_settled"] and report["worker_exported"]
            and not report.get("settlement_errors") and report.get("wire", {}).get("matches_frozen")
            and (synthetic or (report.get("local_only") or {}).get("generation_proven") is True)
            and not any(report.get("relay_rejections", {}).values())
            and report["inference_relay_settled"] and r.get("telemetry_complete") and not r.get("warning_or_critical_observed")
            and r.get("swap_peak_growth_bytes") == 0 and not report.get("guard_reason") and not report.get("edited_test_paths"))
        report["wall_seconds"] = round(time.monotonic() - start, 3)
        atomic(directory / "driver.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("arm", choices=["native", "kryn"])
    args = parser.parse_args()
    result = run(args.campaign.resolve(strict=True), args.arm)
    print(json.dumps({key: result.get(key) for key in ("completed", "cli_exit_code", "intervention", "error", "worker_exported", "cleanup_settled")}))
    raise SystemExit(0 if result["completed"] else 1)
