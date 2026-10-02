# Research workspace

[PROTOCOL.md](PROTOCOL.md) freezes the hypothesis, controls, acceptance rule and
research ladder. This directory is **development instrumentation**, not a new
agent runtime and not a product setting. Released v1.0.0 remains installed.

To reproduce one public-fixture pair from a checkout with the installed local
model and oMLX already available:

```sh
python3 -B evals/bench.py verify
python3 -B evals/bench.py prepare 02 unique-native
python3 -B evals/bench.py prepare 02 unique-kryn
python3 -B tools/run_native_trial.py evals/runs/unique-native --arm native --stage attempt1 --agent build --daily-use-guard --ready-tools
python3 -B tools/run_native_trial.py evals/runs/unique-kryn --arm kryn --stage attempt1 --agent build --daily-use-guard --candidate-product-source --expected-tools evals/runs/unique-native/evidence/attempt1/tool-catalog.json
python3 -B evals/bench.py grade unique-native
python3 -B evals/bench.py grade unique-kryn
python3 -B research/record_trial.py evals/runs/unique-native
python3 -B research/record_trial.py evals/runs/unique-kryn
python3 -B research/compare_pair.py evals/runs/unique-native evals/runs/unique-kryn
```

Use fresh run names for every trial and reverse the arm order on the next pair.
`record_trial.py` additionally runs the pre-existing Task02 boundary probe and
the Task03 report/CLI/API boundary probe.
`compare_pair.py` rejects mismatched configuration, effective permissions,
tool catalog, first wire tool schema, sampling settings, guard or power state.
It also fails closed when invocation-time runner, binary, model-profile or timeout
provenance was not captured; the initial pilot predates those fields and is
diagnostic evidence only.
Raw traces, browser artifacts and source snapshots stay in ignored `evals/runs/`;
`research/history/development.jsonl` is an append-only compact index of the
public development runs. Preserve raw failed and interrupted runs. For protected
research, create an independently isolated grader and a new sealed task roster;
these public fixtures cannot be relabeled as holdout evidence.

On macOS, `python3 -B research/check_holdout_boundary.py` checks that the existing
Seatbelt boundary can read a candidate workspace but cannot read a separate grader,
even through a workspace symlink. This is only a boundary preflight; protected
holdout qualification also requires a full sandboxed candidate run with the grader
outside its readable and reachable surfaces.
An actual sandboxed OpenCode call on a public development fixture passed this
runner preflight; its evidence and limitations are in [DEVELOPMENT.md](DEVELOPMENT.md).

The external benchmark and protected-holdout layers are pending. An installed
Docker CLI without a running daemon is insufficient for official SWE-bench or
Harbor grading. Never report a local fixture result as an official benchmark
score or a proof of frontier-level capability.
