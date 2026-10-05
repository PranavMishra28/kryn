"""Recovery stops owned resources without rerunning or rewriting the failed arm."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from research import container_recovery as recovery
from research.container_worker import LABEL, SIDECAR_IMAGE


class FakeDocker:
    objects = {}
    mutations = []
    fail_close = False

    def __init__(self, directory, guard):
        self.evidence, self.guard = Path(directory), guard

    def command(self, kind, action, *args, **kwargs):
        if action != "ls":
            raise AssertionError((kind, action, args))
        items = self.objects[kind]
        if "--filter" in args:
            owner = args[-1].split("=", 2)[-1]
            return "\n".join(identity for identity, info in items.items()
                             if (info["Config"]["Labels"] if kind == "container" else info["Labels"]).get(LABEL) == owner)
        return "\n".join(identity + " " + info["Name"].lstrip("/") for identity, info in items.items())

    def inspect(self, kind, identity, **kwargs):
        return self.objects[kind][identity]

    def settle(self, identity):
        self.mutations.append(("stop", identity))
        self.objects["container"][identity]["State"] = {"Running": False, "Pid": 0}

    def export(self, identity, destination):
        self.guard.check()
        self.mutations.append(("export", identity))
        Path(destination).write_bytes(b"bounded stopped-worker archive")

    def close(self):
        for identity in self.containers:
            self.mutations.append(("remove", identity))
            self.objects["container"].pop(identity)
        if self.fail_close:
            type(self).fail_close = False
            raise RuntimeError("crash after container removal")
        for identity in self.networks:
            self.mutations.append(("remove", identity))
            self.objects["network"].pop(identity)


class Guard:
    unsafe = False
    final_unsafe = False
    observed_policy = None

    def __init__(self, directory, power_policy="ac-only"):
        type(self).observed_policy = power_policy
        self.reason = None
        self.memory = Mock()
        self.memory.cancel.is_set.return_value = False

    def __enter__(self):
        if self.unsafe:
            raise RuntimeError("power below safe admission")
        return self

    def check(self):
        if self.reason:
            raise RuntimeError(self.reason)

    def __exit__(self, *_):
        if self.final_unsafe:
            self.reason = "battery_floor"


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.arm = self.root / "native"
        self.arm.mkdir()
        self.owner = "kryn-worker-" + "a" * 16
        self.worker, self.relay, self.net = "1" * 64, "2" * 64, "3" * 64
        self.image = "sha256:" + "4" * 64
        self.manifest = {"image": self.image, "arm_order": ["native", "kryn"], "baseline": str(self.root)}
        self.journal = {"owner": self.owner, "containers": [self.worker, self.relay], "networks": [self.net],
            "expected_names": {"container": {self.owner + "-candidate": self.worker, self.owner + "-relay": self.relay},
                               "network": {self.owner: self.net}}}
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        (self.arm / "driver.json").write_text('{"completed":false,"guard_reason":"warning"}\n')
        self.original = {name: (self.arm / name).read_bytes() for name in ("ownership.json", "driver.json")}
        FakeDocker.objects = {"container": {
            self.worker: {"Id": self.worker, "Name": "/" + self.owner + "-candidate", "Image": self.image,
                          "Config": {"Labels": {LABEL: self.owner}}, "State": {"Running": True, "Pid": 12}},
            self.relay: {"Id": self.relay, "Name": "/" + self.owner + "-relay", "Image": "route",
                         "Config": {"Labels": {LABEL: self.owner}, "Image": SIDECAR_IMAGE}, "State": {"Running": True, "Pid": 13}}},
            "network": {self.net: {"Id": self.net, "Name": self.owner, "Labels": {LABEL: self.owner}, "Internal": True}}}
        FakeDocker.mutations, FakeDocker.fail_close, Guard.unsafe = [], False, False
        Guard.final_unsafe = False
        for name, value in (("DockerWorker", FakeDocker), ("HostGuard", Guard), ("frozen", Mock(return_value=self.manifest)),
                            ("export_source", self.export_source), ("validate_worker", self.validate)):
            managed = patch.object(recovery, name, value)
            managed.start()
            self.addCleanup(managed.stop)
        usage = patch.object(recovery.shutil, "disk_usage", return_value=Mock(free=30 * 1024**3))
        usage.start()
        self.addCleanup(usage.stop)

    @staticmethod
    def validate(info, image, _network, **_kwargs):
        if info["Image"] != image:
            raise RuntimeError("Worker image changed")

    @staticmethod
    def export_source(docker, worker, _baseline, _manifest, directory, guard):
        docker.export(worker, directory / "worktree.tar")
        guard.check()
        (directory / "model.patch").write_text("a fixed patch\n")
        return {"worker_exported": True, "patch_sha256": recovery.file_sha(directory / "model.patch")}

    def assert_original(self):
        self.assertEqual(self.original, {name: (self.arm / name).read_bytes() for name in self.original})

    def test_final_battery_failure_keeps_export_unsealed_and_worker_stopped(self):
        self.manifest['power_policy'] = 'battery-capable'
        Guard.final_unsafe = True
        receipt = recovery.recover(self.root, 'native')
        self.assertTrue(receipt['waiting'] and receipt['unscored'])
        self.assertEqual(receipt['reason'], 'battery_floor')
        self.assertEqual(Guard.observed_policy, 'battery-capable')
        self.assertFalse((self.arm / 'recovery/export.json').exists())
        self.assertFalse(FakeDocker.objects['container'][self.worker]['State']['Running'])
        self.assert_original()
        Guard.final_unsafe = False
        self.assertTrue(recovery.recover(self.root, 'native')['recovery_complete'])
        self.assertEqual(sum(action == 'export' for action, _ in FakeDocker.mutations), 1)

    def test_guard_wait_stops_routes_and_worker_then_resumes_safe_export(self):
        Guard.unsafe = True
        self.assertTrue(recovery.recover(self.root, "native")["waiting"])
        self.assertEqual(FakeDocker.mutations[0], ("stop", self.relay))
        self.assertTrue(all(not info["State"]["Running"] for info in FakeDocker.objects["container"].values()))
        self.assertFalse(any(action == "export" for action, _ in FakeDocker.mutations))
        self.assert_original()
        Guard.unsafe = False
        result = recovery.recover(self.root, "native")
        self.assertTrue(result["recovery_complete"] and result["unscored"])
        self.assertFalse(any(FakeDocker.objects.values()))
        self.assert_original()

    def test_owner_or_image_drift_never_stops_or_removes_resources(self):
        original = FakeDocker.objects["container"][self.worker]
        for altered in ({**original, "Config": {"Labels": {LABEL: "another-owner"}}}, {**original, "Image": "wrong"}):
            FakeDocker.objects["container"][self.worker] = altered
            with self.assertRaises(RuntimeError):
                recovery.recover(self.root, "native")
            self.assertEqual(FakeDocker.mutations, [])
            self.assert_original()

    def test_route_control_requires_exact_pinned_image_before_any_mutation(self):
        control = "5" * 64
        self.journal["containers"].append(control)
        self.journal["expected_names"]["container"][self.owner + "-route-control"] = control
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        self.original["ownership.json"] = (self.arm / "ownership.json").read_bytes()
        info = {"Id": control, "Name": "/" + self.owner + "-route-control",
                "Config": {"Labels": {LABEL: self.owner}, "Image": "python:latest"},
                "State": {"Running": True, "Pid": 14}}
        FakeDocker.objects["container"][control] = info
        with self.assertRaisesRegex(RuntimeError, "route-control image changed"):
            recovery.recover(self.root, "native")
        self.assertEqual(FakeDocker.mutations, [])
        self.assert_original()
        info["Config"]["Image"] = recovery.CONTROL_IMAGE
        self.assertTrue(recovery.recover(self.root, "native")["unscored"])
        self.assertIn(("stop", control), FakeDocker.mutations)
        self.assertIn(("remove", control), FakeDocker.mutations)
        self.assertFalse(any(FakeDocker.objects.values()))
        self.assert_original()

    def test_export_headroom_wait_preserves_stopped_candidate(self):
        with patch.object(recovery.shutil, "disk_usage", return_value=Mock(free=recovery.DISK_FLOOR)):
            result = recovery.recover(self.root, "native")
        self.assertTrue(result["waiting"])
        self.assertEqual(result["reason"], "insufficient_recovery_export_headroom")
        self.assertIn(self.worker, FakeDocker.objects["container"])
        self.assertFalse(FakeDocker.objects["container"][self.worker]["State"]["Running"])
        self.assertFalse(any(action == "export" for action, _ in FakeDocker.mutations))

    def test_completed_export_survives_cleanup_crash_without_reexport(self):
        FakeDocker.fail_close = True
        with self.assertRaisesRegex(RuntimeError, "crash after container"):
            recovery.recover(self.root, "native")
        receipt = self.arm / "recovery/export.json"
        before = receipt.read_bytes()
        self.assertTrue(recovery.recover(self.root, "native")["recovery_complete"])
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(sum(action == "export" for action, _ in FakeDocker.mutations), 1)
        self.assert_original()

    def test_crash_before_final_receipt_finishes_without_any_replay(self):
        original = recovery._seal
        def fail_result(path, value):
            if path.name == "result.json":
                raise RuntimeError("crash before result")
            return original(path, value)
        with patch.object(recovery, "_seal", side_effect=fail_result):
            with self.assertRaisesRegex(RuntimeError, "before result"):
                recovery.recover(self.root, "native")
        self.assertTrue(recovery.recover(self.root, "native")["recovery_complete"])
        before = list(FakeDocker.mutations)
        self.assertTrue(recovery.recover(self.root, "native")["unscored"])
        self.assertEqual(FakeDocker.mutations, before)
        self.assert_original()

    def test_crash_before_export_receipt_reuses_the_pinned_archive(self):
        original = recovery._seal
        def fail_export(path, value):
            if path.name == "export.json":
                raise RuntimeError("crash before export receipt")
            return original(path, value)
        with patch.object(recovery, "_seal", side_effect=fail_export):
            with self.assertRaisesRegex(RuntimeError, "before export receipt"):
                recovery.recover(self.root, "native")
        self.assertTrue(recovery.recover(self.root, "native")["recovery_complete"])
        self.assertEqual(sum(action == "export" for action, _ in FakeDocker.mutations), 1)
        self.assert_original()

    def test_missing_driver_and_unrecorded_create_id_are_recoverable(self):
        (self.arm / "driver.json").unlink()
        self.journal["containers"].remove(self.worker)
        self.journal["expected_names"]["container"][self.owner + "-candidate"] = None
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        self.assertTrue(recovery.recover(self.root, "native")["recovery_complete"])
        self.assertFalse((self.arm / "driver.json").exists())

    def test_child_never_started_seals_ownership_absence_without_docker(self):
        (self.arm / "driver.json").unlink()
        (self.arm / "ownership.json").unlink()
        self.arm.rmdir()
        with patch.object(FakeDocker, "command", side_effect=AssertionError("Docker must not be consulted")):
            receipt = recovery.recover(self.root, "native")
            self.assertTrue(receipt["recovery_complete"] and receipt["unscored"])
            self.assertEqual(receipt["reason"], "ownership_never_created")
            self.assertEqual(recovery.recover(self.root, "native"), receipt)
        self.assertFalse((self.arm / "ownership.json").exists())
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        with self.assertRaisesRegex(RuntimeError, "receipt changed"):
            recovery.recover(self.root, "native")

    def test_terminal_original_handoff_is_sealed_unscored_without_reexport(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        (self.arm / "worktree.tar").write_bytes(b"original preserved archive")
        (self.arm / "model.patch").write_bytes(b"original preserved patch")
        self.journal.update(cleanup_errors=[], retained_containers=[], retained_networks=[])
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        driver = {"kind": "swe_container_generation", "arm": "native", "completed": True,
                  "worker_exported": True, "cleanup_settled": True, "inference_relay_settled": True,
                  "manifest_sha256": recovery.file_sha(self.root / "manifest.json"),
                  "patch_sha256": recovery.file_sha(self.arm / "model.patch"),
                  "export": {"tar_sha256": recovery.file_sha(self.arm / "worktree.tar")}}
        (self.arm / "driver.json").write_text(json.dumps(driver))
        original = {name: (self.arm / name).read_bytes() for name in
                    ("ownership.json", "driver.json", "model.patch", "worktree.tar")}
        FakeDocker.objects = {"container": {}, "network": {}}
        with patch.object(recovery, "export_source", side_effect=AssertionError("must not reexport")):
            result = recovery.recover(self.root, "native")
            self.assertEqual(result["reason"], "original_terminal_handoff")
            self.assertTrue(result["unscored"])
            self.assertEqual(recovery.recover(self.root, "native"), result)
        self.assertEqual(original, {name: (self.arm / name).read_bytes() for name in original})
        self.assertEqual(FakeDocker.mutations, [])

    def test_sidecar_only_crash_cleans_up_without_claiming_worker_export(self):
        FakeDocker.objects["container"].pop(self.worker)
        self.journal["containers"].remove(self.worker)
        del self.journal["expected_names"]["container"][self.owner + "-candidate"]
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        before = (self.arm / "ownership.json").read_bytes()
        result = recovery.recover(self.root, "native")
        self.assertEqual(result["reason"], "worker_never_created")
        self.assertFalse(result["worker_exported"])
        self.assertFalse(any(FakeDocker.objects.values()))
        self.assertEqual(recovery.recover(self.root, "native"), result)
        self.assertEqual((self.arm / "ownership.json").read_bytes(), before)

    def test_clean_timeout_original_export_is_preserved_without_upgrading_failure(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        (self.arm / "worktree.tar").write_bytes(b"preserved timeout archive")
        (self.arm / "model.patch").write_bytes(b"preserved timeout patch")
        self.journal.update(cleanup_errors=[], retained_containers=[], retained_networks=[])
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        driver = {"kind": "swe_container_generation", "arm": "native", "completed": False,
                  "intervention": "timeout", "worker_exported": True, "cleanup_settled": True,
                  "inference_relay_settled": True,
                  "manifest_sha256": recovery.file_sha(self.root / "manifest.json"),
                  "patch_sha256": recovery.file_sha(self.arm / "model.patch"),
                  "export": {"tar_sha256": recovery.file_sha(self.arm / "worktree.tar")}}
        (self.arm / "driver.json").write_text(json.dumps(driver))
        before = (self.arm / "driver.json").read_bytes()
        FakeDocker.objects = {"container": {}, "network": {}}
        with patch.object(recovery, "export_source", side_effect=AssertionError("must not reexport")):
            result = recovery.recover(self.root, "native")
            self.assertTrue(result["recovery_complete"] and result["unscored"])
            self.assertEqual(result["reason"], "original_terminal_handoff")
            self.assertEqual(recovery.recover(self.root, "native"), result)
        self.assertEqual((self.arm / "driver.json").read_bytes(), before)
        self.assertFalse(json.loads(before)["completed"])
        self.assertEqual(FakeDocker.mutations, [])

    def test_absent_reserved_candidate_remains_ambiguous(self):
        FakeDocker.objects["container"].pop(self.worker)
        self.journal["containers"].remove(self.worker)
        self.journal["expected_names"]["container"][self.owner + "-candidate"] = None
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        with self.assertRaisesRegex(RuntimeError, "no settled identity"):
            recovery.recover(self.root, "native")
        self.assertFalse((self.arm / "recovery/result.json").exists())

    def assert_pending_create_refused(self, kind, name, identity):
        FakeDocker.objects[kind].pop(identity)
        self.journal["containers" if kind == "container" else "networks"].remove(identity)
        self.journal["expected_names"][kind][name] = None
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        before = (self.arm / "ownership.json").read_bytes()
        with self.assertRaisesRegex(RuntimeError, "no settled identity"):
            recovery.recover(self.root, "native")
        self.assertFalse((self.arm / "recovery/result.json").exists())
        self.assertEqual((self.arm / "ownership.json").read_bytes(), before)
        self.assertEqual(FakeDocker.mutations, [])

    def test_absent_pending_network_create_is_not_claimed_as_cleaned(self):
        self.assert_pending_create_refused("network", self.owner, self.net)

    def test_absent_pending_relay_create_is_not_claimed_as_cleaned(self):
        self.assert_pending_create_refused("container", self.owner + "-relay", self.relay)

    def test_admission_callback_runs_only_after_all_owned_containers_stop(self):
        calls = []
        def admit():
            self.assertTrue(all(not item["State"]["Running"] and item["State"]["Pid"] == 0
                                for item in FakeDocker.objects["container"].values()))
            self.assertFalse(any(action == "export" for action, _ in FakeDocker.mutations))
            calls.append(True)
            return False
        self.assertTrue(recovery.recover(self.root, "native", admit=admit)["waiting"])
        self.assertEqual(calls, [True])
        self.assertTrue(recovery.recover(self.root, "native", admit=lambda: True)["recovery_complete"])

    def test_completed_export_drift_fails_before_cleanup(self):
        FakeDocker.fail_close = True
        with self.assertRaises(RuntimeError):
            recovery.recover(self.root, "native")
        data = json.loads((self.arm / "recovery/export.json").read_text())
        (Path(data["directory"]) / "model.patch").write_text("tampered")
        before = list(FakeDocker.mutations)
        with self.assertRaisesRegex(RuntimeError, "export changed"):
            recovery.recover(self.root, "native")
        self.assertEqual(FakeDocker.mutations, before)

    def test_original_receipt_drift_fails_before_any_docker_mutation(self):
        Guard.unsafe = True
        recovery.recover(self.root, "native")
        (self.arm / "driver.json").write_text('{"completed":true}')
        before = list(FakeDocker.mutations)
        with self.assertRaisesRegex(RuntimeError, "receipt changed"):
            recovery.recover(self.root, "native")
        self.assertEqual(FakeDocker.mutations, before)

    def test_grader_settlement_preserves_original_journal(self):
        grader = FakeDocker.objects["container"][self.worker]
        grader["Name"] = "/" + self.owner + "-grader"
        FakeDocker.objects = {"container": {self.worker: grader}, "network": {}}
        self.journal.update(containers=[self.worker], networks=[], expected_names={
            "container": {self.owner + "-grader": self.worker}, "network": {}})
        (self.arm / "ownership.json").write_text(json.dumps(self.journal))
        before = (self.arm / "ownership.json").read_bytes()
        root = self.arm / "cleanup-recovery"
        self.assertTrue(recovery.settle_recorded(self.arm, self.image, root)["cleanup_settled"])
        self.assertEqual((self.arm / "ownership.json").read_bytes(), before)
        self.assertTrue(recovery.settle_recorded(self.arm, self.image, root)["unscored"])


if __name__ == "__main__":
    unittest.main()
