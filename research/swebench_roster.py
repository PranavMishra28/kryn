#!/usr/bin/env python3
"""Freeze an unseen, repository-balanced SWE-bench subset from pinned local data."""

import argparse
import hashlib
import json
from pathlib import Path

from datasets import load_dataset

SEED = "kryn-swebench-campaign-20261003-v1"
REPOS = ("django/django", "sphinx-doc/sphinx", "matplotlib/matplotlib",
         "scikit-learn/scikit-learn", "pytest-dev/pytest", "astropy/astropy")
EXPOSED = {"django__django-15996", "sphinx-doc__sphinx-7440",
           "matplotlib__matplotlib-25498", "scikit-learn__scikit-learn-25747",
           "pytest-dev__pytest-5495", "astropy__astropy-13398",
           "sympy__sympy-20590"}
PREFIX = ("Fix the issue described below in the current repository. Edit the source, "
          "run focused checks, and report what you verified. Do not edit existing tests.\n\n")
PARQUET = {"lite": ("438e281d80587aa7be470896ce410557002fde02d2ceee3e099331d308f62dd3",
                     "b0dde1093fe417d83b7184254edf8199c1f0dff5"),
           "verified": ("030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25",
                        "78f471bf655a3137b2e8a75af1501690ec009ec3")}
EVALUATOR = "02e7a74ffd0b707aab73d203fe87bdc7c76afc8e"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def freeze(datasets_root, output):
    if output.exists():
        raise FileExistsError(output)
    datasets = {}
    for kind, (expected, _) in PARQUET.items():
        file = datasets_root / kind / "data/test-00000-of-00001.parquet"
        if sha(file.read_bytes()) != expected:
            raise RuntimeError("Pinned official " + kind + " test data changed")
        datasets[kind] = load_dataset("parquet", data_files=str(file), split="train")
    tasks = []
    chosen = set(EXPOSED)
    for repo in REPOS:
        for kind in ("lite", "verified"):
            eligible = [row for row in datasets[kind]
                        if row["repo"] == repo and row["instance_id"] not in chosen]
            if not eligible:
                raise RuntimeError("Frozen source lacks eligible task in " + repo)
            row = min(eligible, key=lambda item: sha(
                (SEED + "\0" + kind + "\0" + item["instance_id"]).encode()))
            chosen.add(row["instance_id"])
            prompt = (PREFIX + row["problem_statement"] + "\n").encode()
            tasks.append({"dataset": kind, "repo": repo,
                          "instance_id": row["instance_id"],
                          "base_commit": row["base_commit"],
                          "image_tag": row["image"],
                          "prompt_sha256": sha(prompt),
                          "arm_order": ["kryn", "native"] if len(tasks) % 2 == 0
                          else ["native", "kryn"]})
    manifest = {"schema": 1, "kind": "swebench_local_baseline",
                "selection_seed": SEED, "selection": "one new Lite and one new Verified task per preregistered repository; lowest SHA256(seed + NUL + split + NUL + id); alternating arm order",
                "previously_exposed_ids_excluded": sorted(EXPOSED),
                "datasets": {kind: {"test_sha256": item[0], "revision": item[1]}
                             for kind, item in PARQUET.items()},
                "evaluator_commit": EVALUATOR, "model": "Qwen3.5-9B-6bit",
                "prompt_prefix": PREFIX, "timeout_seconds": 900,
                "max_heavy_generations": 1, "tasks": tasks}
    output.mkdir(mode=0o700, parents=True)
    data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    (output / "manifest.json").write_bytes(data)
    (output / "manifest.sha256").write_text(sha(data) + "\n")
    return sha(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps({"manifest_sha256": freeze(args.datasets_root, args.output)}))
