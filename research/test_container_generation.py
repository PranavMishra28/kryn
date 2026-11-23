import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from research.container_generation import frozen, wire_evidence
from research.container_worker import DockerWorker, LABEL


class GenerationTests(unittest.TestCase):
    def test_unknown_power_policy_rejected_before_source_or_agent_admission(self):
        with tempfile.TemporaryDirectory() as folder, patch('research.container_generation.unchanged') as source:
            root = Path(folder)
            for policy in ('off', None, [], True):
                raw = json.dumps({'kind': 'swe_container_generation_canary', 'baseline': folder,
                                  'power_policy': policy}).encode()
                (root / 'manifest.json').write_bytes(raw)
                (root / 'manifest.sha256').write_text(hashlib.sha256(raw).hexdigest())
                with self.assertRaisesRegex(RuntimeError, 'power policy'):
                    frozen(root)
            source.assert_not_called()

    def test_frozen_accepts_both_exact_arm_orders_and_rejects_invalid_arrays(self):
        with tempfile.TemporaryDirectory() as folder, patch("research.container_generation.unchanged"):
            root = Path(folder)
            (root / "prompt.txt").write_text("unused")
            manifest = {"kind": "swe_container_generation_canary", "baseline": folder,
                "prompt_sha256": hashlib.sha256(b"unused").hexdigest(),
                "wall_seconds": 90, "request_seconds": 360}
            for order in (["native", "kryn"], ["kryn", "native"], [], ["native"],
                          ["native", "native"], ["kryn", "kryn"], ["other", "kryn"],
                          ["native", "kryn", "native"], None, "native,kryn"):
                with self.subTest(order=order):
                    raw = json.dumps({**manifest, "arm_order": order}).encode()
                    (root / "manifest.json").write_bytes(raw)
                    (root / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest())
                    if order in (["native", "kryn"], ["kryn", "native"]):
                        self.assertEqual(frozen(root)["arm_order"], order)
                    else:
                        with self.assertRaisesRegex(RuntimeError, "Unreviewed development arm order"):
                            frozen(root)

    def test_full_wire_must_match_and_canonical_fake_hash_is_used(self):
        wire = {"body_controls_sha256": "a", "tool_schema_sha256": "b"}
        rows = [{"tools": ["read"], "body_controls_sha256": "a",
                 "tool_schema_sha256": "legacy", "tool_schema_canonical_sha256": "b"}]
        self.assertTrue(wire_evidence(rows, wire)["matches_frozen"])
        self.assertFalse(wire_evidence([], wire)["matches_frozen"])
        self.assertFalse(wire_evidence(rows, {**wire, "body_controls_sha256": "drift"})["matches_frozen"])
        rows.append({"tool_count": 1, **wire, "body_controls_sha256": "drift"})
        self.assertFalse(wire_evidence(rows)["stable"])

    def test_native_child_catalog_is_explicitly_pinned(self):
        expected = {"body_controls_sha256": "body", "tool_schema_sha256s": ["root", "child"]}
        rows = [{"tool_count": 2, "body_controls_sha256": "body", "tool_schema_sha256": key}
                for key in ("root", "child", "root")]
        self.assertTrue(wire_evidence(rows, expected)["matches_frozen"])
        rows[-1]["tool_schema_sha256"] = "unknown"
        self.assertFalse(wire_evidence(rows, expected)["matches_frozen"])
        rows[-1]["tool_schema_sha256"] = "root"
        rows[-1]["body_controls_sha256"] = "new sampler"
        self.assertFalse(wire_evidence(rows, expected)["matches_frozen"])

    def test_missing_admissions_cannot_open_the_real_model_route(self):
        with tempfile.TemporaryDirectory() as folder, patch("research.container_generation.unchanged"):
            root = Path(folder)
            (root / "prompt.txt").write_text("unused")
            manifest = {"kind": "swe_container_development", "baseline": folder,
                "prompt_sha256": hashlib.sha256(b"unused").hexdigest(), "arm_order": ["native", "kryn"],
                "wall_seconds": 900, "request_seconds": 360, "admission_sha256": {},
                "adjudicator_sha256": "unset", "wire_controls": {}, "image_preparation_sha256": "unset"}
            raw = json.dumps(manifest).encode()
            (root / "manifest.json").write_bytes(raw)
            (root / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(RuntimeError, "Required named admissions"):
                frozen(root)

    def test_unsafe_export_retains_only_stopped_owned_worker_and_network(self):
        with tempfile.TemporaryDirectory() as folder:
            docker = DockerWorker(folder, Mock())
            docker.containers = ["worker", "relay"]
            docker.networks = ["network"]
            docker.inspect = Mock(return_value={"Config": {"Labels": {LABEL: docker.owner}},
                                                 "State": {"Running": False, "Pid": 0}})
            docker.command = Mock()
            docker.close(retain=["worker"])
            docker.command.assert_called_once_with("container", "rm", "-f", "relay", cleanup=True)
            ownership = json.loads((Path(folder) / "ownership.json").read_text())
            self.assertEqual(ownership["retained_containers"], ["worker"])
            self.assertEqual(ownership["retained_networks"], ["network"])
            docker.inspect.return_value["State"]["Running"] = True
            with self.assertRaisesRegex(RuntimeError, "Container did not settle"):
                docker.close(retain=["worker"])

    def test_retained_inspection_error_still_cleans_other_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            docker = DockerWorker(folder, Mock())
            docker.containers = ["worker", "relay"]
            docker.networks = ["network"]
            docker.inspect = Mock(side_effect=[RuntimeError("temporary inspection failure"),
                {"Config": {"Labels": {LABEL: docker.owner}}, "State": {"Running": False, "Pid": 0}}])
            docker.command = Mock()
            with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
                docker.close(retain=["worker"])
            docker.command.assert_called_once_with("container", "rm", "-f", "relay", cleanup=True)
            receipt = json.loads((Path(folder) / "ownership.json").read_text())
            self.assertEqual(receipt["retained_containers"], ["worker"])
            self.assertIn("temporary inspection failure", receipt["cleanup_errors"])


if __name__ == "__main__":
    unittest.main()
