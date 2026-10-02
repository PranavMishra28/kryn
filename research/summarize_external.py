#!/usr/bin/env python3
"""Summarize the frozen external subset without treating diagnostics as acceptance."""
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "research/subsets/swebench-20261002.json"
HISTORY = ROOT / "research/history/external.jsonl"


def summarize(tasks, rows, seed=20261002, resamples=10000):
    """Pair only officially graded generation receipts; exclude startup preflights."""
    graded = [row for row in rows if row.get("official_run_id")]
    by_task = {}
    for task in tasks:
        task_id = task["instance_id"]
        pair = {}
        for arm in ("kryn", "native"):
            matches = [row for row in graded if row["task_id"] == task_id and row["arm"] == arm]
            if len(matches) != 1:
                raise ValueError(f"Expected one graded {arm} receipt for {task_id}")
            pair[arm] = matches[0]
        by_task[task_id] = pair
    if len(graded) != 2 * len(tasks):
        raise ValueError("Unexpected graded receipt outside the frozen roster")
    deltas = [int(by_task[t["instance_id"]]["kryn"]["accepted"]) -
              int(by_task[t["instance_id"]]["native"]["accepted"]) for t in tasks]
    rng = random.Random(seed)
    estimates = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas)
                       for _ in range(resamples))
    arms = {}
    for arm in ("kryn", "native"):
        selected = [by_task[t["instance_id"]][arm] for t in tasks]
        accepted = sum(bool(row["accepted"]) for row in selected)
        seconds = sum(row["wall_seconds"] for row in selected)
        arms[arm] = {"accepted": accepted, "attempts": len(selected),
                     "generation_wall_seconds": round(seconds, 3),
                     "accepted_per_generation_hour": round(3600 * accepted / seconds, 3)}
    return {"subset_only": True, "tasks": len(tasks), "arms": arms,
            "paired_deltas": deltas, "difference": sum(deltas) / len(deltas),
            "bootstrap_95_percentile": [estimates[int(.025 * (resamples - 1))],
                                        estimates[int(.975 * (resamples - 1))]],
            "bootstrap_seed": seed, "bootstrap_resamples": resamples}


if __name__ == "__main__":
    tasks = json.loads(ROSTER.read_text())["tasks"]
    rows = [json.loads(line) for line in HISTORY.read_text().splitlines()]
    print(json.dumps(summarize(tasks, rows), sort_keys=True))
