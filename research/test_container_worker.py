import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import Mock, patch

from research.container_worker import DockerWorker, HostGuard, pinned_image, validate_worker, container_usage, LABEL
from research.container_admission import environment, tool_acceptance, source_inputs, install_policy_probe, PROBE
from research.container_config import worker_environment
from research.local_only import check_environment
from research.local_campaign import PINNED_FILES
from research.ui_gateway.synthetic_dispatch import FakeInference, MODEL
from research.container_grader import frozen, require_owned, worker_settled, require_test_evidence, wheel_paths


class ContainerControlsTests(unittest.TestCase):
    def test_policy_probe_copy_is_readable_but_not_writable_from_sealed_source(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "research/container_policy.py"
            source.parent.mkdir()
            source.write_bytes(b"# synthetic policy probe\n")
            source.chmod(0o400)
            copied = []

            def copy(command, path, destination):
                staged = Path(path)
                self.assertEqual((command, destination), ("cp", "worker:" + PROBE))
                self.assertEqual(staged.read_bytes(), source.read_bytes())
                self.assertEqual(staged.stat().st_mode & 0o777, 0o444)
                copied.append(staged)

            docker = Mock()
            docker.command.side_effect = copy
            with patch("research.container_admission.ROOT", Path(root)):
                install_policy_probe(docker, "worker")
            docker.command.assert_called_once()
            self.assertFalse(copied[0].exists())
            self.assertEqual(source.stat().st_mode & 0o777, 0o400)

    def test_host_guard_records_explicit_battery_admission_and_final_sample(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                HostGuard(root, power_policy=[])
            memory = Mock(cancel=threading.Event(), guard=Mock(reason=None))
            battery = {"ac": False, "battery_percent": 90, "adapter_watts": None}
            with patch("research.container_worker.NativeResourceGuard", return_value=memory), patch(
                    "research.container_worker.power", return_value=battery), patch(
                    "research.container_worker.memory_pressure", return_value=1), patch(
                    "research.container_worker.shutil.disk_usage", return_value=Mock(free=30 * 1024**3)), patch(
                    "research.container_worker.subprocess.Popen", return_value=Mock()):
                guard = HostGuard(root, power_policy="battery-capable")
                with patch.object(guard, "_watch"):
                    with guard:
                        guard.check()
                    guard.check()
            rows = [json.loads(line) for line in (Path(root) / "power.jsonl").read_text().splitlines()]
            self.assertEqual([row["starting"] for row in rows], [True, False])
            self.assertEqual([row["final"] for row in rows], [False, True])
            self.assertTrue(all(row["power_policy"] == "battery-capable" and row["ac"] is False
                                and row["battery_percent"] == 90 and row["adapter_watts"] is None
                                and row["reason"] is None and type(row["unix"]) in (int, float)
                                for row in rows))
            self.assertLess((Path(root) / "power.jsonl").stat().st_size, 512 * 1024)

    def test_host_guard_latches_final_battery_floor_without_raw_error_output(self):
        with tempfile.TemporaryDirectory() as root:
            memory = Mock(cancel=threading.Event(), guard=Mock(reason=None))
            battery = {"ac": False, "battery_percent": 90, "adapter_watts": None}
            with patch("research.container_worker.NativeResourceGuard", return_value=memory), patch(
                    "research.container_worker.power", side_effect=[battery, {**battery, "battery_percent": 25}]), patch(
                    "research.container_worker.memory_pressure", return_value=1), patch(
                    "research.container_worker.shutil.disk_usage", return_value=Mock(free=30 * 1024**3)), patch(
                    "research.container_worker.subprocess.Popen", return_value=Mock()):
                guard = HostGuard(root, power_policy="battery-capable")
                with patch.object(guard, "_watch"):
                    with guard:
                        pass
                    with self.assertRaisesRegex(RuntimeError, "battery_stop_floor"):
                        guard.check()
            rows = [json.loads(line) for line in (Path(root) / "power.jsonl").read_text().splitlines()]
            self.assertEqual(rows[-1]["reason"], "battery_stop_floor")
            self.assertFalse(rows[-1]["starting"])
            self.assertTrue(rows[-1]["final"])

    def test_host_guard_final_power_sample_survives_memory_close_failure(self):
        with tempfile.TemporaryDirectory() as root:
            memory = Mock(cancel=threading.Event(), guard=Mock(reason=None))
            memory.close.side_effect = RuntimeError("memory_close_failure")
            battery = {"ac": False, "battery_percent": 90, "adapter_watts": None}
            with patch("research.container_worker.NativeResourceGuard", return_value=memory), patch(
                    "research.container_worker.power", return_value=battery), patch(
                    "research.container_worker.memory_pressure", return_value=1), patch(
                    "research.container_worker.shutil.disk_usage", return_value=Mock(free=30 * 1024**3)), patch(
                    "research.container_worker.subprocess.Popen", return_value=Mock()) as awake:
                guard = HostGuard(root, power_policy="battery-capable")
                with patch.object(guard, "_watch"):
                    with self.assertRaisesRegex(RuntimeError, "memory_close_failure"):
                        with guard:
                            pass
            rows = [json.loads(line) for line in (Path(root) / "power.jsonl").read_text().splitlines()]
            self.assertEqual([row["final"] for row in rows], [False, True])
            awake.return_value.terminate.assert_called_once()
            awake.return_value.wait.assert_called_once_with(timeout=5)

    def test_host_guard_default_still_denies_battery_and_redacts_probe_errors(self):
        with tempfile.TemporaryDirectory() as root:
            memory = Mock(cancel=threading.Event(), guard=Mock(reason=None))
            battery = {"ac": False, "battery_percent": 90, "adapter_watts": None}
            with patch("research.container_worker.NativeResourceGuard", return_value=memory), patch(
                    "research.container_worker.power", return_value=battery):
                with self.assertRaisesRegex(RuntimeError, "battery_power"):
                    with HostGuard(root):
                        self.fail("AC-only admission reached guarded work")
            memory.start.assert_not_called()
            rows = [json.loads(line) for line in (Path(root) / "power.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["reason"], "battery_power")
            self.assertTrue(rows[-1]["final"])
        with tempfile.TemporaryDirectory() as root:
            memory = Mock(cancel=threading.Event(), guard=Mock(reason=None))
            with patch("research.container_worker.NativeResourceGuard", return_value=memory), patch(
                    "research.container_worker.power", side_effect=RuntimeError("SECRET probe output")):
                with self.assertRaisesRegex(RuntimeError, "SECRET probe output"):
                    with HostGuard(root, power_policy="battery-capable"):
                        self.fail("Missing telemetry reached guarded work")
            raw = (Path(root) / "power.jsonl").read_bytes()
            self.assertNotIn(b"SECRET", raw)
            self.assertEqual(json.loads(raw.splitlines()[0])["reason"], "power_telemetry_unavailable")
            self.assertTrue(json.loads(raw.splitlines()[-1])["final"])

    def test_grading_cannot_self_seal_an_unverified_evaluator(self):
        with tempfile.TemporaryDirectory() as root:
            campaign = Path(root)
            manifest = {"kind": "swe_container_grader_no_model_admission", "source_sha256": {},
                        "evaluator_package_sha256": {"grader.py": "expected"}}
            data = json.dumps(manifest).encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(hashlib.sha256(data).hexdigest())
            with patch("research.container_grader.source_inputs", return_value={}), patch(
                    "research.container_grader.source_lock", return_value={
                        "evaluator_package_sha256": {"grader.py": "modified"}}) as lock:
                with self.assertRaisesRegex(RuntimeError, "sealed before grading"):
                    frozen(campaign, manifest)
                lock.assert_not_called()
                (campaign / "execution-lock.json").write_text('{}')
                with self.assertRaisesRegex(RuntimeError, "independently pinned"):
                    frozen(campaign, manifest)

    def test_offline_wheels_are_exact_bounded_regular_inputs(self):
        with tempfile.TemporaryDirectory() as root:
            wheel = Path(root) / "example.whl"
            wheel.write_bytes(b"pinned")
            manifest = {"wheelhouse": root, "wheel_sha256": {wheel.name: hashlib.sha256(b"pinned").hexdigest()}}
            self.assertEqual(wheel_paths(manifest), [wheel])
            wheel.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "identity drift"):
                wheel_paths(manifest)
            wheel.unlink()
            wheel.symlink_to('/etc/hosts')
            with self.assertRaises(RuntimeError):
                wheel_paths(manifest)

    def test_unresolved_without_real_test_evidence_is_not_grader_admission(self):
        expected = {"FAIL_TO_PASS": ["regression"], "PASS_TO_PASS": ["existing"]}
        report = {"patch_successfully_applied": True, "tests_status": {
            "FAIL_TO_PASS": {"success": [], "failure": ["regression"]},
            "PASS_TO_PASS": {"success": ["existing"], "failure": []}}}
        parsed = {"regression": "FAILED", "existing": "PASSED"}
        require_test_evidence(report, expected, parsed)
        with self.assertRaisesRegex(RuntimeError, "observe every expected"):
            require_test_evidence(report, expected, {"existing": "PASSED"})
        for changed in ({**report, "patch_successfully_applied": False},
                        {**report, "tests_status": {}},
                        {**report, "tests_status": {"FAIL_TO_PASS": {"success": [], "failure": []}}}):
            with self.assertRaises(RuntimeError):
                require_test_evidence(changed, expected, parsed)

    def test_grader_requires_network_none_without_weakening_worker_identity(self):
        info = self.fixture()
        info["Id"] = "container"
        info["Config"].update(User="root", Labels={LABEL: "owner"})
        info["Config"]["Env"] = ["PIP_NO_INDEX=1", "PIP_FIND_LINKS=/opt/kryn-wheels"]
        info["HostConfig"]["NetworkMode"] = "none"
        info["NetworkSettings"]["Networks"] = {"none": {}}
        control = {"container": "container", "owner": "owner", "image_id": info["Image"]}
        require_owned(info, control)
        with self.assertRaises(RuntimeError):
            validate_worker(info, info["Image"], "none")
        for field, value in (("NetworkMode", "bridge"), ("CapAdd", ["SYS_ADMIN"]),
                             ("Binds", ["/host:/host"])):
            changed = copy.deepcopy(info)
            changed["HostConfig"][field] = value
            with self.assertRaises(RuntimeError):
                require_owned(changed, control)
        for field, value in (("owner", "foreign"), ("container", "foreign")):
            with self.assertRaises(RuntimeError):
                require_owned(info, {**control, field: value})
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.command = Mock()
            for options in ({"worker": True}, {"network": "bridge"}):
                with self.assertRaises(ValueError):
                    worker.create("grader", info["Image"], [], grader=True, **options)
            worker.command.assert_not_called()

    def test_unsettled_worker_or_relay_blocks_grading(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "result.json").write_text('{"passed":true}')
            for name in ("native", "kryn"):
                (base / name).mkdir()
                (base / name / "ownership.json").write_text(json.dumps({"owner": name, "cleanup_errors": []}))
                (base / name / "result.json").write_text('{"passed":true}')
            (base / "manifest.json").write_text('{}')
            (base / "kryn/model.patch").write_text('canary')
            manifest = {"admission_root": root, "admission_sha256": {
                p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in base.rglob('*') if p.is_file()}}
            with self.assertRaisesRegex(RuntimeError, "completely pinned"):
                worker_settled({**manifest, "admission_sha256": {}})
            with patch("research.container_grader.subprocess.check_output", return_value=""):
                worker_settled(manifest)
            with patch("research.container_grader.subprocess.check_output", return_value="still-live"):
                with self.assertRaisesRegex(RuntimeError, "remains"):
                    worker_settled(manifest)
            with patch("research.container_grader.subprocess.check_output", side_effect=OSError("Docker absent")):
                with self.assertRaises(OSError):
                    worker_settled(manifest)

    def test_failed_extra_tool_or_nonzero_shell_never_passes(self):
        parts = [{"type": "tool", "tool": "read", "state": {"status": "completed"}},
                 {"type": "tool", "tool": "shell", "state": {"status": "completed", "metadata": {"metadata": {"exit": 0}}}}]
        def verdict(parts):
            return tool_acceptance("\n".join(json.dumps({"part": part}) for part in parts))["passed"]
        self.assertTrue(verdict(parts))
        self.assertFalse(verdict(parts + [{"type": "tool", "tool": "read", "state": {"status": "error"}}]))
        for code in (1, None, False):
            broken = copy.deepcopy(parts)
            broken[-1]["state"]["metadata"]["metadata"]["exit"] = code
            self.assertFalse(verdict(broken))

    def fixture(self):
        return {"Image": "sha256:" + "1" * 64, "Mounts": [],
                "Config": {"User": "10001:10001"},
                "HostConfig": {"CapDrop": ["ALL"], "IpcMode": "private",
                               "Dns": ["127.0.0.1"], "SecurityOpt": ["no-new-privileges"],
                               "Memory": 2 * 1024**3, "MemorySwap": 2 * 1024**3,
                               "NanoCpus": 2 * 10**9, "PidsLimit": 256, "NetworkMode": "net"},
                "NetworkSettings": {"Networks": {"net": {"NetworkID": "id"}}}}

    def test_worker_rejects_binds_routes_privileges_and_larger_limits(self):
        original = self.fixture()
        validate_worker(original, original["Image"], "net")
        for field, value in (("Binds", ["/private:/host"]), ("Privileged", True),
                             ("CapAdd", ["NET_ADMIN"]), ("PidMode", "host"),
                             ("UTSMode", "host"), ("NetworkMode", "host"),
                             ("PortBindings", {"8000/tcp": []}), ("Dns", ["8.8.8.8"]),
                             ("MemorySwap", -1), ("Memory", 4 * 1024**3),
                             ("Devices", [{}]), ("SecurityOpt", ["seccomp=unconfined"])):
            with self.subTest(field=field):
                info = copy.deepcopy(original)
                info["HostConfig"][field] = value
                with self.assertRaises(RuntimeError):
                    validate_worker(info, info["Image"], "net")
        for field, value in (("Mounts", [{}]), ("Image", "another")):
            info = copy.deepcopy(original)
            info[field] = value
            with self.assertRaises(RuntimeError):
                validate_worker(info, original["Image"], "net")

    def test_unpinned_image_and_bad_port_fail_before_docker(self):
        for image in ("latest", "name:1", "sha256:bad", "repo@sha256:" + "a" * 64 + "\n"):
            with self.assertRaises(ValueError):
                pinned_image(image)
        self.assertEqual(pinned_image("sha256:" + "a" * 64), "sha256:" + "a" * 64)
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.command = Mock()
            for port in (True, 0, 80000, "8000"):
                with self.assertRaises(ValueError):
                    worker.route(port)
            worker.command.assert_not_called()

    def test_live_or_foreign_container_cannot_export(self):
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.containers = ["owned"]
            info = {"Config": {"Labels": {LABEL: worker.owner}}, "State": {"Running": True, "Pid": 42}}
            worker.inspect = Mock(return_value=info)
            with patch("research.container_worker.bounded_output") as capture:
                with self.assertRaises(RuntimeError):
                    worker.export("owned", Path(root) / "out.tar")
                info["State"] = {"Running": False, "Pid": 0}
                info["Config"]["Labels"][LABEL] = "foreign"
                with self.assertRaises(RuntimeError):
                    worker.export("owned", Path(root) / "out.tar")
                capture.assert_not_called()

    def test_usage_failures_record_bounded_selected_evidence_without_retry(self):
        missing = object()
        cases = [(missing, "size_telemetry_missing_or_invalid"),
                 (None, "size_telemetry_missing_or_invalid"),
                 (True, "size_telemetry_missing_or_invalid"),
                 (4096.0, "size_telemetry_missing_or_invalid"),
                 ("4096", "size_telemetry_missing_or_invalid"),
                 (-1, "size_telemetry_missing_or_invalid"),
                 (4 * 1024**3 + 1, "work_cap_exceeded"),
                 (2**128, "work_cap_exceeded"),
                 (4096, "owner_mismatch"),
                 (4096, "container_identity_mismatch")]
        for size_rw, reason in cases:
            with self.subTest(size=size_rw, reason=reason), tempfile.TemporaryDirectory() as root:
                worker = DockerWorker(root, Mock())
                worker.containers = ["a" * 64]
                owner = "foreign" * 10000 if reason == "owner_mismatch" else worker.owner
                info = {"Id": "b" * 64 if reason == "container_identity_mismatch" else worker.containers[0],
                        "Labels": {LABEL: owner}, "Env": ["SECRET=must-not-be-recorded"]}
                if size_rw is not missing:
                    info["SizeRw"] = size_rw
                with patch("research.container_worker.container_usage", return_value=info) as inspect:
                    with self.assertRaisesRegex(RuntimeError, reason):
                        worker.check_usage()
                inspect.assert_called_once_with("a" * 64, worker.owner)
                receipts = list(Path(root).glob("usage-failure-*.json"))
                self.assertEqual(len(receipts), 1)
                raw = receipts[0].read_bytes()
                self.assertLess(len(raw), 8192)
                self.assertNotIn(b"must-not-be-recorded", raw)
                self.assertNotIn(b"unrelated-secret", raw)
                evidence = json.loads(raw)
                self.assertEqual(evidence["reason"], reason)
                self.assertEqual(evidence["query"], "container_list_size")
                self.assertEqual(evidence["expected_container_id"], "a" * 64)
                self.assertEqual(evidence["observed_container_id"], info["Id"])
                self.assertEqual(evidence["expected_owner"], worker.owner)
                self.assertEqual(evidence["size_rw_present"], size_rw is not missing)
                self.assertEqual(evidence["limit_bytes"], 4 * 1024**3)

    def test_valid_usage_including_exact_cap_produces_no_failure_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.containers = ["a" * 64]
            for size_rw in (0, 4096, 4 * 1024**3):
                info = {"Id": "a" * 64, "Labels": {LABEL: worker.owner}, "SizeRw": size_rw}
                with patch("research.container_worker.container_usage", return_value=info) as inspect:
                    worker.check_usage()
                    inspect.assert_called_once()
            self.assertFalse(list(Path(root).glob("usage-failure-*.json")))

    def test_usage_query_uses_exact_bytes_and_cli_endpoint_without_retry(self):
        import sys
        sdk = Mock()
        client = sdk.APIClient.return_value
        row = {"Id": "a" * 64, "Labels": {LABEL: "owned"}, "SizeRw": 33705984}
        client.containers.return_value = [row]
        for env, endpoint in (({}, "unix:///context.sock"),
                              ({"DOCKER_HOST": "unix:///override.sock"}, "unix:///override.sock"),
                              ({"DOCKER_HOST": "unix:///override.sock", "DOCKER_CONTEXT": "chosen"},
                               "unix:///context.sock")):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), patch.dict(
                    sys.modules, {"docker": sdk}), patch("research.container_worker.subprocess.run",
                    return_value=Mock(stdout='"unix:///context.sock"')) as context:
                before = dict(os.environ)
                self.assertEqual(container_usage("a" * 64, "owned"), row)
                self.assertEqual(dict(os.environ), before)
                context.assert_called_once_with(["docker", "context", "inspect", "--format",
                    "{{json .Endpoints.docker.Host}}"], capture_output=True, text=True, timeout=5, check=True)
                self.assertEqual(sdk.APIClient.call_args.kwargs["base_url"], endpoint)
                self.assertEqual(sdk.APIClient.call_args.kwargs["version"], "1.45")
                self.assertGreater(sdk.APIClient.call_args.kwargs["timeout"], 0)
                self.assertLessEqual(sdk.APIClient.call_args.kwargs["timeout"], 5)
                client.containers.assert_called_once_with(all=True, size=True,
                    filters={"id": "a" * 64, "label": LABEL + "=owned"})
                client.close.assert_called_once()
                client.reset_mock()

    def test_usage_query_rejects_ambiguous_absent_remote_and_failed_telemetry(self):
        import sys
        sdk = Mock()
        client = sdk.APIClient.return_value
        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, {"docker": sdk}), patch(
                "research.container_worker.subprocess.run", return_value=Mock(stdout='"unix:///context.sock"')) as context:
            for rows in ([], [{}, {}], None, [None]):
                client.containers.return_value = rows
                with self.assertRaisesRegex(RuntimeError, "exactly one"):
                    container_usage("a" * 64, "owned")
                client.containers.assert_called_once()
                client.close.assert_called_once()
                client.reset_mock()
            client.containers.side_effect = TimeoutError("timeout")
            with self.assertRaises(TimeoutError):
                container_usage("a" * 64, "owned")
            client.containers.assert_called_once()
            client.close.assert_called_once()
            client.reset_mock()
            context.return_value.stdout = '"tcp://remote:2375"'
            with self.assertRaisesRegex(RuntimeError, "local Docker socket"):
                container_usage("a" * 64, "owned")
            client.containers.assert_not_called()

    def test_cleanup_refuses_changed_owner(self):
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.containers = ["foreign"]
            worker.inspect = Mock(return_value={"Config": {"Labels": {LABEL: "elsewhere"}}})
            worker.command = Mock()
            with self.assertRaisesRegex(RuntimeError, "ownership"):
                worker.close()
            worker.command.assert_not_called()

    def test_cancelled_create_is_reconciled_by_reserved_name(self):
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            identity = "a" * 64
            name = worker.owner + "-candidate"
            worker.expected["container"][name] = None
            worker.command = Mock(side_effect=[identity + "\n", ""])
            worker.inspect = Mock(return_value={"Name": "/" + name,
                                                 "Config": {"Labels": {LABEL: worker.owner}}})
            worker.close()
            self.assertEqual(worker.containers, [identity])
            self.assertEqual(worker.expected["container"][name], identity)
            self.assertEqual(worker.command.call_args.args, ("container", "rm", "-f", identity))

    def test_unknown_cancelled_create_does_not_claim_settlement(self):
        with tempfile.TemporaryDirectory() as root:
            worker = DockerWorker(root, Mock())
            worker.expected["network"][worker.owner] = None
            worker.command = Mock(return_value="")
            with self.assertRaisesRegex(RuntimeError, "ownership audit"):
                worker.close()

    def test_docker_warning_cannot_corrupt_stdout_identity(self):
        with tempfile.TemporaryDirectory() as root:
            script = Path(root) / "docker"
            script.write_text("#!/bin/sh\nprintf 'architecture warning\\n' >&2\nprintf 'owned-id\\n'\n")
            script.chmod(0o755)
            worker = DockerWorker(root, Mock())
            with patch.dict(os.environ, {"PATH": root + ":" + os.environ["PATH"]}):
                self.assertEqual(worker.command("create"), "owned-id\n")
            self.assertIn("architecture warning", (Path(root) / "docker-001.stderr").read_text())

    def test_fast_exit_cannot_bypass_stdout_or_stderr_budget(self):
        for destination in ("", ">&2"):
            with self.subTest(stream=destination), tempfile.TemporaryDirectory() as root:
                script = Path(root) / "docker"
                script.write_text("#!/bin/sh\n/bin/dd if=/dev/zero bs=1048576 count=9 " + destination + " 2>/dev/null\n")
                script.chmod(0o755)
                worker = DockerWorker(root, Mock())
                with patch.dict(os.environ, {"PATH": root + ":" + os.environ["PATH"]}):
                    with self.assertRaisesRegex(RuntimeError, "output exceeded"):
                        worker.command("create")
                total = sum((Path(root) / name).stat().st_size for name in ("docker-001.log", "docker-001.stderr"))
                self.assertLessEqual(total, 8 * 1024**2)

    def test_shared_harbor_environment_stays_unchanged_and_swe_is_local(self):
        self.assertIn("research/container_config.py", PINNED_FILES)
        self.assertTrue({"research/local_only.py", "tools/native_client.py",
                         "research/local_campaign.py", "tools/context_probe.py",
                         "tools/protocol_probe.py"}.issubset(source_inputs()))
        original = worker_environment()
        self.assertEqual(original["PATH"], "/usr/local/bin:/usr/bin:/bin")
        for native in (True, False):
            env = environment(native)
            config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            self.assertTrue(env["PATH"].startswith("/opt/miniconda3/envs/testbed/bin:"))
            self.assertEqual(config["mcp"]["servers"], {})
            self.assertTrue(check_environment(env, "/tmp/kryn", "http://127.0.0.1:18765/v1"))

    def test_auxiliary_request_does_not_consume_canned_tool_action(self):
        with FakeInference([("read", {"path": "/testbed/README.rst"})], "done") as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            def request(tools):
                body = json.dumps({"model": MODEL, "tools": tools, "stream": True}).encode()
                req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions",
                                             data=body, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.read()
            try:
                self.assertIn(b'"content": "done"', request([]))
                self.assertIn(b'"name": "read"', request([{"function": {"name": "read"}}]))
                self.assertIn(b'"content": "done"', request([{"function": {"name": "read"}}]))
            finally:
                server.shutdown()


if __name__ == "__main__":
    unittest.main()
