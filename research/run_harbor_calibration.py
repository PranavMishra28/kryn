#!/usr/bin/env python3
"""Run one official Harbor trial under KRYN's unchanged daily-use host guard."""

import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys

from harbor.models.environment_type import EnvironmentType
from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig
from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_native_trial import NativeResourceGuard, runtime_is_idle  # noqa: E402
from context_probe import summarize_resources  # noqa: E402
from learning import InferenceRelay  # noqa: E402
from native_client import MODEL_ID  # noqa: E402

MIN_DATA_FREE_BYTES = 12 * 1024**3


def data_free_bytes():
    return shutil.disk_usage("/private/tmp").free


async def run_trial(task: Path, trials_dir: Path, name: str, arm: str, variant: str,
                    install_only: bool,
                    relay: InferenceRelay):
    evidence = trials_dir / name / "host-guard"
    evidence.mkdir(parents=True, exist_ok=False)
    disk_start = data_free_bytes()
    (evidence / "disk-preflight.json").write_text(json.dumps({
        "free_bytes": disk_start, "min_free_bytes": MIN_DATA_FREE_BYTES,
        "passed": disk_start >= MIN_DATA_FREE_BYTES,
    }, indent=2) + "\n")
    if disk_start < MIN_DATA_FREE_BYTES:
        raise RuntimeError("Data volume has less than 12 GiB free before trial")
    if not runtime_is_idle(evidence, "preflight-idle", model_id=MODEL_ID, guard_gib=22):
        raise RuntimeError("The guarded local model runtime is not idle")
    config = TrialConfig(
        task=TaskConfig(path=task), trial_name=name, trials_dir=trials_dir,
        install_only=install_only,
        agent=AgentConfig(import_path="research.harbor_kryn_agent:" +
                          ("NativeOpenCode" if arm == "native" else "KrynOpenCode"),
                          model_name="local/qwen", override_timeout_sec=900,
                          env={"KRYN_HARBOR_RELAY_PORT": str(relay.port),
                               "KRYN_HARBOR_VARIANT": variant}),
        environment=EnvironmentConfig(type=EnvironmentType.DOCKER, delete=True),
    )
    trial = await Trial.create(config)
    if data_free_bytes() < MIN_DATA_FREE_BYTES:
        raise RuntimeError("Data volume fell below 12 GiB during trial setup")
    monitor = None
    samples = []

    async def begin(_event):
        nonlocal monitor
        monitor = NativeResourceGuard(evidence, samples, warning_samples=None)
        monitor.start()

    async def end(_event):
        if monitor is not None and not monitor.log.closed:
            monitor.close()

    trial.add_hook(TrialEvent.AGENT_START, begin)
    trial.add_hook(TrialEvent.AGENT_END, end)
    active = asyncio.create_task(trial.run())
    cancelled = False
    disk_stopped = False
    try:
        while not active.done():
            if data_free_bytes() < MIN_DATA_FREE_BYTES:
                disk_stopped = True
                cancelled = True
                relay.cancel()
                active.cancel()
                break
            if monitor is not None and monitor.cancel.is_set():
                cancelled = True
                relay.cancel()
                active.cancel()
                break
            await asyncio.sleep(.5)
        try:
            result = await active
        except asyncio.CancelledError:
            result = trial.result
    finally:
        if monitor is not None and not monitor.log.closed:
            monitor.close()

    disk_end = data_free_bytes()
    disk_stopped = disk_stopped or disk_end < MIN_DATA_FREE_BYTES
    reward = (result.verifier_result.rewards or {}).get("reward") if result.verifier_result else None
    reason = monitor.guard.reason if monitor is not None else None
    (evidence / "inference.json").write_text(json.dumps(relay.records, indent=2) + "\n")
    report = {
        "harbor_trial": name, "arm": arm, "variant": variant,
        "harbor_result": str(trial.paths.result_path),
        "install_only": install_only, "reward": reward,
        "exception": result.exception_info.exception_type if result.exception_info else None,
        "guard_preflight_passed": monitor.preflight_passed if monitor else False,
        "guard_reason": reason, "guard_cancelled": cancelled,
        "disk_free_start_bytes": disk_start,
        "disk_free_end_bytes": disk_end,
        "disk_min_free_bytes": MIN_DATA_FREE_BYTES,
        "disk_stopped": disk_stopped,
        "inference_requests": len(relay.records),
        "resources": summarize_resources(samples) if samples else None,
        "runtime_idle": runtime_is_idle(evidence, "final-idle") if monitor else None,
    }
    report["strict_accepted"] = bool(not install_only and reward == 1 and relay.records and
                                     report["exception"] is None and reason is None and
                                     report["runtime_idle"] and report["guard_preflight_passed"] and
                                     report["resources"] and report["resources"]["telemetry_complete"] and
                                     not disk_stopped)
    (evidence / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if install_only and report["exception"] is None or report["strict_accepted"] else 1


async def run(task: Path, trials_dir: Path, name: str, arm: str, variant: str,
              install_only: bool):
    with InferenceRelay(MODEL_ID, 8192, 360) as relay:
        return await run_trial(task, trials_dir, name, arm, variant, install_only, relay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path)
    parser.add_argument("trials_dir", type=Path)
    parser.add_argument("name")
    parser.add_argument("--arm", choices=("kryn", "native"), default="kryn")
    parser.add_argument("--variant", choices=("default", "fast"), default="default")
    parser.add_argument("--install-only", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.task.resolve(), args.trials_dir.resolve(),
                                     args.name, args.arm, args.variant, args.install_only)))
