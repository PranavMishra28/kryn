import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import Mock, patch

from research.container_worker import DockerWorker, pinned_image, validate_worker, LABEL
from research.container_admission import environment, tool_acceptance, source_inputs
from research.container_config import worker_environment
from research.local_only import check_environment
from research.local_campaign import PINNED_FILES
from research.ui_gateway.synthetic_dispatch import FakeInference, MODEL


class ContainerControlsTests(unittest.TestCase):
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
