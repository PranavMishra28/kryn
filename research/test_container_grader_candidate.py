"""Candidate-grade receipt and verdict checks without Docker or inference."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from research.container_grader import (frozen, generation_settled, grade,
                                       model_generation_proven, official_grade_valid)
from research.local_only import MODEL


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateGraderTests(unittest.TestCase):
    def fixture(self, root, *, completed=True, intervention=None):
        root = Path(root)
        campaign, generation = root / "grade", root / "kryn"
        campaign.mkdir()
        generation.mkdir()
        (root / "prompt.txt").write_text("Public synthetic prompt\n")
        generation_manifest = {"kind": "swe_container_development", "task": {"instance_id": "public-test"},
                               "prompt_sha256": digest(root / "prompt.txt")}
        (root / "manifest.json").write_text(json.dumps(generation_manifest))
        (campaign / "model.patch").write_bytes(b"candidate patch\n")
        (generation / "model.patch").write_bytes(b"candidate patch\n")
        driver = {"kind": "swe_container_generation", "arm": "kryn", "synthetic_inference": False,
                  "manifest_sha256": digest(root / "manifest.json"),
                  "prompt_sha256": digest(root / "prompt.txt"), "task_id": "public-test",
                  "completed": completed,
                  "intervention": intervention, "cli_exit_code": 0 if completed else None,
                  "cleanup_settled": True, "inference_relay_settled": True,
                  "worker_exported": True, "patch_sha256": digest(generation / "model.patch"),
                  "resources": {}, "local_only": {}, "requests": [], "generation": {}}
        (generation / "driver.json").write_text(json.dumps(driver))
        ownership = {"owner": "kryn-worker-0123456789abcdef", "containers": ["container"],
                     "networks": ["network"], "retained_containers": [], "retained_networks": [],
                     "cleanup_errors": []}
        (generation / "ownership.json").write_text(json.dumps(ownership))
        manifest = {"generation_root": str(generation), "arm": "kryn", "synthetic_inference": False,
                    "generation_manifest_sha256": digest(root / "manifest.json"),
                    "task": {"instance_id": "public-test"},
                    "generation_sha256": {name: digest(generation / name)
                                          for name in ("driver.json", "ownership.json", "model.patch")},
                    "patch_sha256": digest(campaign / "model.patch")}
        return campaign, generation, manifest

    def test_settled_complete_and_timeout_exports_can_be_graded(self):
        for completed, intervention in ((True, None), (False, "timeout")):
            with self.subTest(completed=completed), tempfile.TemporaryDirectory() as root:
                campaign, _, manifest = self.fixture(root, completed=completed, intervention=intervention)
                with patch("research.container_grader.subprocess.check_output", return_value="") as docker:
                    driver = generation_settled(campaign, manifest)
                self.assertIs(driver["completed"], completed)
                self.assertEqual(docker.call_count, 2)

    def test_candidate_policy_must_match_generation_and_driver(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign, generation, manifest = self.fixture(folder)
            manifest['power_policy'] = 'battery-capable'
            with self.assertRaisesRegex(RuntimeError, 'generation power policy drift'):
                generation_settled(campaign, manifest)
            path = Path(folder) / 'manifest.json'
            gm = json.loads(path.read_text())
            gm['power_policy'] = 'battery-capable'
            path.write_text(json.dumps(gm))
            manifest['generation_manifest_sha256'] = digest(path)
            with self.assertRaisesRegex(RuntimeError, 'driver power policy drift'):
                generation_settled(campaign, manifest)
            path = generation / 'driver.json'
            driver = json.loads(path.read_text())
            driver.update(power_policy='battery-capable', manifest_sha256=manifest['generation_manifest_sha256'])
            path.write_text(json.dumps(driver))
            manifest['generation_sha256']['driver.json'] = digest(path)
            with patch('research.container_grader.subprocess.check_output', return_value=''):
                self.assertEqual(generation_settled(campaign, manifest)['power_policy'], 'battery-capable')

    def test_changed_or_live_generation_evidence_cannot_enter_grader(self):
        with tempfile.TemporaryDirectory() as root:
            campaign, generation, manifest = self.fixture(root)
            with patch("research.container_grader.subprocess.check_output", return_value="live"):
                with self.assertRaisesRegex(RuntimeError, "remains"):
                    generation_settled(campaign, manifest)
            with patch("research.container_grader.subprocess.check_output", return_value=""):
                with self.assertRaisesRegex(RuntimeError, "settled, pinned"):
                    generation_settled(campaign, {**manifest, "arm": "native"})
                with self.assertRaisesRegex(RuntimeError, "task or prompt drift"):
                    generation_settled(campaign, {**manifest, "synthetic_inference": True})
                with self.assertRaisesRegex(RuntimeError, "manifest drift"):
                    generation_settled(campaign, {**manifest, "generation_manifest_sha256": "0" * 64})
                with self.assertRaisesRegex(RuntimeError, "task or prompt drift"):
                    generation_settled(campaign, {**manifest, "task": {"instance_id": "other"}})
                (generation / "model.patch").write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "drift"):
                    generation_settled(campaign, manifest)
                (generation / "model.patch").write_bytes(b"candidate patch\n")
                (campaign / "model.patch").write_bytes(b"different patch\n")
                with self.assertRaisesRegex(RuntimeError, "differs"):
                    generation_settled(campaign, manifest)
                (campaign / "model.patch").write_bytes(b"candidate patch\n")
                (generation / "ownership.json").write_text(json.dumps({"owner": "other", "cleanup_errors": []}))
                manifest["generation_sha256"]["ownership.json"] = digest(generation / "ownership.json")
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    generation_settled(campaign, manifest)

    def test_pinned_canned_generation_is_admitted_but_retention_is_not(self):
        with tempfile.TemporaryDirectory() as root:
            campaign, generation, manifest = self.fixture(root)
            source = Path(root) / "manifest.json"
            details = json.loads(source.read_text())
            details["kind"] = "swe_container_generation_canary"
            source.write_text(json.dumps(details))
            driver = json.loads((generation / "driver.json").read_text())
            driver.update(synthetic_inference=True, manifest_sha256=digest(source))
            (generation / "driver.json").write_text(json.dumps(driver))
            manifest.update(synthetic_inference=True, generation_manifest_sha256=digest(source))
            manifest["generation_sha256"]["driver.json"] = digest(generation / "driver.json")
            with patch("research.container_grader.subprocess.check_output", return_value=""):
                self.assertTrue(generation_settled(campaign, manifest)["synthetic_inference"])
                owner_path = generation / "ownership.json"
                ownership = json.loads(owner_path.read_text())
                ownership["retained_containers"] = ["container"]
                owner_path.write_text(json.dumps(ownership))
                manifest["generation_sha256"]["ownership.json"] = digest(owner_path)
                with self.assertRaisesRegex(RuntimeError, "ownership receipt is incomplete"):
                    generation_settled(campaign, manifest)

    def test_candidate_kind_requires_open_outcome_before_source_lock(self):
        with tempfile.TemporaryDirectory() as root:
            campaign = Path(root)
            manifest = {"kind": "swe_container_development_grade", "patch_role": "candidate",
                        "expected_resolved": True, "source_sha256": {}}
            raw = json.dumps(manifest).encode()
            (campaign / "manifest.json").write_bytes(raw)
            (campaign / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest())
            with patch("research.container_grader.source_inputs", return_value={}), patch(
                    "research.container_grader.source_lock") as lock:
                with self.assertRaisesRegex(RuntimeError, "open outcome"):
                    frozen(campaign, manifest)
                lock.assert_not_called()

    def test_candidate_kind_uses_existing_sealed_evaluator_lock(self):
        with tempfile.TemporaryDirectory() as root:
            campaign = Path(root)
            dataset = campaign / "dataset/data/test-00000-of-00001.parquet"
            dataset.parent.mkdir(parents=True)
            dataset.write_bytes(b"pinned dataset")
            candidate = campaign / "model.patch"
            candidate.write_bytes(b"candidate patch\n")
            manifest = {"kind": "swe_container_development_grade", "patch_role": "candidate",
                        "synthetic_inference": False, "expected_resolved": None, "source_sha256": {},
                        "evaluator_package_sha256": {"grader.py": "pinned"},
                        "task": {"dataset": "dataset", "instance_id": "public-test"},
                        "datasets": {"dataset": {"test_sha256": digest(dataset)}},
                        "official_image_digest": "image-tag", "official_image_id": "image-id",
                        "patch_sha256": digest(candidate)}
            raw = json.dumps(manifest).encode()
            (campaign / "manifest.json").write_bytes(raw)
            (campaign / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest())
            (campaign / "execution-lock.json").write_text('{}')
            with patch("research.container_grader.source_inputs", return_value={}), patch(
                    "research.container_grader.source_lock", return_value={
                        "evaluator_package_sha256": {"grader.py": "pinned"}}) as lock, patch(
                    "research.container_grader.swebench_local.DATASET_ROOT", campaign), patch(
                    "research.container_grader.swebench_local.image_identity", return_value={"Id": "image-id"}), patch(
                    "research.container_grader.wheel_paths"), patch(
                    "research.container_grader.generation_settled", return_value={"completed": False}) as generation:
                self.assertEqual(frozen(campaign, manifest), {"completed": False})
            lock.assert_called_once_with(manifest, campaign)
            generation.assert_called_once_with(campaign, manifest)

    def test_grade_validity_is_separate_from_candidate_resolution(self):
        official = {"graded": True, "resolved": False,
                    "infra_failure_instances": 0, "error_instances": 0}
        candidate = {"kind": "swe_container_development_grade", "expected_resolved": None}
        self.assertTrue(official_grade_valid(candidate, official, False))
        no_model = {"kind": "swe_container_grader_no_model_admission", "expected_resolved": True}
        self.assertFalse(official_grade_valid(no_model, official, False))
        self.assertTrue(official_grade_valid({**no_model, "expected_resolved": False}, official, False))
        for changed, oom in (({**official, "infra_failure_instances": 1}, False),
                             ({**official, "error_instances": 1}, False),
                             ({**official, "graded": False}, False),
                             (official, True)):
            self.assertFalse(official_grade_valid(candidate, changed, oom))

    def test_candidate_grade_receipt_never_claims_strict_acceptance(self):
        official = {"graded": True, "resolved": False,
                    "infra_failure_instances": 0, "error_instances": 0}
        for synthetic in (False, True):
            with self.subTest(synthetic=synthetic), tempfile.TemporaryDirectory() as root:
                campaign = Path(root)
                manifest = {"kind": "swe_container_development_grade", "synthetic_inference": synthetic,
                            "official_image_id": "image", "wheel_sha256": {}, "task": {"instance_id": "public-test"}}
                (campaign / "manifest.json").write_text(json.dumps(manifest))
                (campaign / "model.patch").write_bytes(b"candidate patch\n")
                guard = MagicMock()
                guard.__enter__.return_value = guard
                guard.samples = []
                docker = MagicMock()
                docker.owner = "kryn-worker-0123456789abcdef"
                docker.create.return_value = "container"
                docker.inspect.return_value = {"State": {"OOMKilled": False}}
                with patch("research.container_grader.frozen", return_value={
                        "completed": False, "intervention": "timeout"}), patch(
                        "research.container_grader.HostGuard", return_value=guard), patch(
                        "research.container_grader.DockerWorker", return_value=docker), patch(
                        "research.container_grader.wheel_paths", return_value=[]), patch(
                        "research.container_grader.require_owned"), patch(
                        "research.container_grader.bounded_output"), patch(
                        "research.container_grader.swebench_local.official_result", return_value=official), patch(
                        "research.container_grader.summarize_resources", return_value={
                            "telemetry_complete": True, "warning_or_critical_observed": False,
                            "swap_peak_growth_bytes": 0}):
                    report = grade(campaign)
                self.assertTrue(report["passed"] and report["grade_valid"])
                self.assertIs(report["resolved"], False)
                self.assertIs(report["generation_completed"], False)
                self.assertIs(report["model_generation"], False)
                self.assertIs(report["synthetic_inference"], synthetic)
                self.assertNotIn("strict_accepted", report)

    def test_model_generation_requires_completed_local_pinned_requests(self):
        clean = {"synthetic_inference": False, "completed": True, "intervention": None,
                 "local_only": {"generation_proven": True}, "requests": [{"model": MODEL}]}
        self.assertTrue(model_generation_proven(clean))
        for changed in ({**clean, "synthetic_inference": True},
                        {**clean, "completed": False, "intervention": "timeout"},
                        {**clean, "requests": []},
                        {**clean, "requests": [{"model": "other"}]},
                        {**clean, "local_only": {"generation_proven": False}}):
            self.assertFalse(model_generation_proven(changed))


if __name__ == "__main__":
    unittest.main()
