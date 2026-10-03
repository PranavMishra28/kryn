#!/usr/bin/env python3
"""Start the frozen SWE-bench baseline after the local Harbor baseline finishes.

This lightweight handoff does no model inference and is safe to leave running
without a Codex session. The two phase controllers own all task attempts.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.local_campaign import atomic, file_sha, runtime_idle


def run(harbor, swebench, work, expected_sha, harbor_pid):
    status = swebench / "chain-status.json"
    while True:
        final = harbor / "final-report.json"
        if final.is_file():
            report = json.loads(final.read_text())
            if not report.get("finished"):
                raise RuntimeError("Harbor final report is incomplete")
            break
        command = subprocess.run(["ps", "-p", str(harbor_pid), "-o", "command="],
                                 capture_output=True, text=True, timeout=10)
        if command.returncode or "research/local_campaign.py run" not in command.stdout:
            atomic(status, {"state": "harbor_controller_stopped_without_final",
                            "updated_unix": time.time()})
            raise RuntimeError("Harbor controller stopped before final report")
        atomic(status, {"state": "waiting_for_harbor", "updated_unix": time.time()})
        time.sleep(120)
    if file_sha(swebench / "manifest.json") != expected_sha:
        raise RuntimeError("SWE-bench manifest changed before phase handoff")
    if (swebench / "manifest.sha256").read_text().strip() != expected_sha:
        raise RuntimeError("SWE-bench manifest receipt changed before handoff")
    while not runtime_idle():
        atomic(status, {"state": "waiting_for_idle_runtime", "updated_unix": time.time()})
        time.sleep(60)
    atomic(status, {"state": "swebench_running", "updated_unix": time.time()})
    command = ["/private/tmp/kryn-swebench-venv/bin/python", "-B",
               str(ROOT / "research/swebench_controller.py"), str(swebench),
               str(work), "--expected-sha256", expected_sha]
    log = swebench / "controller.log"
    with log.open("ab") as output:
        child = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                               stdout=output, stderr=subprocess.STDOUT)
    atomic(status, {"state": "finished" if child.returncode == 0 else "failed",
                    "returncode": child.returncode, "updated_unix": time.time()})
    if child.returncode:
        raise RuntimeError("SWE-bench controller failed; inspect its local log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harbor", type=Path)
    parser.add_argument("swebench", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--harbor-pid", type=int, required=True)
    args = parser.parse_args()
    run(args.harbor.resolve(), args.swebench.resolve(), args.work.resolve(),
        args.expected_sha256, args.harbor_pid)


if __name__ == "__main__":
    main()
