"""Official SWE-bench source and grader steps for the local campaign controller.

The model receives only the issue prompt and a clean image-derived checkout.
Gold patches and official test data remain outside its whole-process sandbox.
"""

import json
from pathlib import Path
import shutil
import subprocess

from research.local_campaign import MIN_FREE, atomic, file_sha, sha

DATASET_ROOT = Path("/private/tmp/kryn-swebench-datasets")
EVALUATOR_PYTHON = Path("/private/tmp/kryn-swebench-venv/bin/python")


def row_for(manifest, task, dataset_root=DATASET_ROOT):
    from datasets import load_dataset
    kind = task["dataset"]
    parquet = dataset_root / kind / "data/test-00000-of-00001.parquet"
    if file_sha(parquet) != manifest["datasets"][kind]["test_sha256"]:
        raise RuntimeError("Pinned official SWE-bench data changed")
    rows = load_dataset("parquet", data_files=str(parquet), split="train")
    matches = [row for row in rows if row["instance_id"] == task["instance_id"]]
    if len(matches) != 1:
        raise RuntimeError("Frozen SWE-bench instance is absent or ambiguous")
    row = matches[0]
    prompt = (manifest["prompt_prefix"] + row["problem_statement"] + "\n").encode()
    if (row["repo"] != task["repo"] or row["base_commit"] != task["base_commit"]
            or row["image"] != task["image_tag"] or
            sha(prompt) != task["prompt_sha256"]):
        raise RuntimeError("Frozen issue metadata or prompt changed")
    return row, prompt


def docker(command, *, timeout=60):
    return subprocess.check_output(["docker", *command], text=True, timeout=timeout).strip()


def image_identity(task):
    return json.loads(docker(["image", "inspect", task["image_tag"]], timeout=30))[0]


def pin_image(task):
    prior = set(docker(["image", "ls", "-a", "-q", "--no-trunc"]).splitlines())
    if subprocess.run(["docker", "image", "inspect", task["image_tag"]],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      timeout=20).returncode:
        subprocess.run(["docker", "pull", "--platform", "linux/amd64",
                        task["image_tag"]], check=True, stdout=subprocess.DEVNULL,
                       timeout=900)
    image = image_identity(task)
    if image.get("Architecture") != "amd64" or image.get("Os") != "linux":
        raise RuntimeError("Pinned official SWE-bench image is not linux/amd64")
    repository = task["image_tag"].rsplit(":", 1)[0]
    digest = next((item for item in image.get("RepoDigests", [])
                   if item.startswith(repository + "@sha256:")), None)
    if digest is None:
        raise RuntimeError("Official image has no immutable registry digest")
    return {"image_tag": task["image_tag"], "image_id": image["Id"],
            "image_digest": digest, "image_owned": image["Id"] not in prior}


def prepare(manifest, task, campaign, work, *, dataset_root=DATASET_ROOT):
    """Copy one official image's /testbed to a clean, private base checkout."""
    ident = task["instance_id"]
    directory = campaign / "prepared" / ident
    receipt = directory / "receipt.json"
    base = work / ident / "base"
    prompt_file = directory / "prompt.txt"
    if receipt.exists():
        info = json.loads(receipt.read_text())
        if (file_sha(prompt_file) != task["prompt_sha256"] or
                subprocess.check_output(["git", "-C", str(base), "rev-parse", "HEAD"],
                                        text=True, timeout=20).strip() != task["base_commit"] or
                subprocess.check_output(["git", "-C", str(base), "status", "--porcelain"],
                                        text=True, timeout=30).strip() or
                file_sha(base / ".git/config") != info["base_git_config_sha256"] or
                image_identity(task)["Id"] != info["image_id"]):
            raise RuntimeError("Prepared SWE-bench task drifted")
        return base, prompt_file, info
    if directory.exists() or base.exists():
        raise RuntimeError("Partial SWE-bench preparation needs an audit")
    _, prompt = row_for(manifest, task, dataset_root)
    image = pin_image(task)
    if shutil.disk_usage(campaign).free < MIN_FREE:
        release_image(image)
        raise RuntimeError("Official image pull left less than 12 GiB free")
    directory.mkdir(mode=0o700, parents=True)
    prompt_file.write_bytes(prompt)
    prompt_file.chmod(0o600)
    base.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    base.mkdir(mode=0o700)
    container = "kryn-sweprep-" + sha(ident.encode())[:16]
    if subprocess.run(["docker", "container", "inspect", container],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      timeout=15).returncode == 0:
        raise RuntimeError("A previous SWE-bench preparation container remains")
    try:
        subprocess.run(["docker", "create", "--platform", "linux/amd64",
                        "--name", container, "--label", "kryn.swebench.prep=" + ident,
                        image["image_digest"], "/bin/true"], check=True,
                       stdout=subprocess.DEVNULL, timeout=60)
        subprocess.run(["docker", "cp", container + ":/testbed/.", str(base)],
                       check=True, stdout=subprocess.DEVNULL, timeout=240)
    finally:
        found = subprocess.run(
            ["docker", "container", "inspect", "--format",
             '{{index .Config.Labels "kryn.swebench.prep"}}', container],
            capture_output=True, text=True, timeout=15)
        if found.returncode == 0 and found.stdout.strip() != ident:
            raise RuntimeError("SWE-bench preparation container ownership changed")
        if found.returncode == 0 and found.stdout.strip() == ident:
            subprocess.run(["docker", "rm", "-f", container], check=True,
                           stdout=subprocess.DEVNULL, timeout=60)
    subprocess.run(["git", "-C", str(base), "reset", "--hard", task["base_commit"]],
                   check=True, stdout=subprocess.DEVNULL, timeout=60)
    subprocess.run(["git", "-C", str(base), "clean", "-fdx"],
                   check=True, stdout=subprocess.DEVNULL, timeout=60)
    status = subprocess.check_output(["git", "-C", str(base), "status", "--porcelain"],
                                     text=True, timeout=30).strip()
    if status:
        raise RuntimeError("Official image base checkout is not clean")
    info = dict(image, base_commit=task["base_commit"],
                prompt_sha256=task["prompt_sha256"],
                base_git_config_sha256=file_sha(base / ".git/config"))
    atomic(receipt, info)
    return base, prompt_file, info


def fresh_candidate(base, work, task):
    """Use the same absolute path for both arms so tool schemas can be paired."""
    candidate = work / task["instance_id"] / "candidate"
    if candidate.exists():
        raise RuntimeError("Candidate checkout from a prior arm still exists")
    shutil.copytree(base, candidate, symlinks=True)
    if subprocess.check_output(["git", "-C", str(candidate), "rev-parse", "HEAD"],
                               text=True, timeout=30).strip() != task["base_commit"]:
        raise RuntimeError("Fresh candidate is not at the frozen base commit")
    if (subprocess.check_output(["git", "-C", str(candidate), "status", "--porcelain"],
                                text=True, timeout=30).strip() or
            file_sha(candidate / ".git/config") != file_sha(base / ".git/config")):
        raise RuntimeError("Fresh candidate differs from the clean prepared base")
    return candidate


def prediction(evidence, task, arm, destination):
    patch = evidence / "model.patch"
    if not patch.is_file() or patch.stat().st_size > 16 * 1024**2:
        raise RuntimeError("Candidate patch is missing or over the frozen byte budget")
    payload = [{"instance_id": task["instance_id"],
                "model_name_or_path": "kryn-local-9b-" + arm,
                "model_patch": patch.read_text()}]
    atomic(destination, payload)
    return sha(patch.read_bytes())


def official_command(task, run_id, prediction_path, *, dataset_root=DATASET_ROOT):
    parquet = dataset_root / task["dataset"] / "data/test-00000-of-00001.parquet"
    return [str(EVALUATOR_PYTHON), "-B", "-m", "swebench.harness.run_evaluation",
            "--dataset_name", str(parquet), "--split", "test",
            "--instance_ids", task["instance_id"],
            "--predictions_path", str(prediction_path), "--max_workers", "1",
            "--timeout", "1800", "--run_id", run_id]


def official_result(grade_root, task, run_id, *, model_patch=None):
    run = grade_root / "logs" / "evaluation" / run_id
    result = run / "results.json"
    if not result.is_file():
        return {"graded": False, "resolved": None, "result_sha256": None}
    data = json.loads(result.read_text())
    if data.get("submitted_ids") != [task["instance_id"]]:
        raise RuntimeError("Official grader reported a different instance")
    resolved = task["instance_id"] in data.get("resolved_ids", [])
    if model_patch is not None and model_patch.stat().st_size:
        matches = list(run.rglob("patch.diff"))
        if len(matches) != 1 or file_sha(matches[0]) != file_sha(model_patch):
            raise RuntimeError("Official grader applied different patch bytes")
    return {"graded": True, "resolved": resolved,
            "result_sha256": file_sha(result),
            "infra_failure_instances": data.get("infra_failure_instances"),
            "error_instances": data.get("error_instances")}


def release_image(info):
    if not info["image_owned"]:
        return {"preexisting_preserved": True, "removed": False}
    current = image_identity({"image_tag": info["image_tag"]})
    if current["Id"] != info["image_id"]:
        raise RuntimeError("Owned SWE-bench image tag changed before cleanup")
    for reference in (info["image_tag"], info["image_digest"]):
        subprocess.run(["docker", "image", "rm", reference],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    remaining = subprocess.run(["docker", "image", "inspect", info["image_id"]],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=20).returncode == 0
    if remaining:
        raise RuntimeError("Owned SWE-bench image remained after cleanup")
    return {"preexisting_preserved": False, "removed": True}
