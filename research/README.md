# Research workspace

[PROTOCOL.md](PROTOCOL.md) freezes the hypothesis, controls, acceptance rule and
research ladder. This directory is **development instrumentation**, not a new
agent runtime and not a product setting. Released v1.0.0 remains installed.
[CACHE_ABLATION.md](CACHE_ABLATION.md) preregisters the first one-variable
prompt-stability candidate before its implementation.
[VERIFICATION_FEEDBACK.md](VERIFICATION_FEEDBACK.md) records the rejected
failure-only repair-feedback candidate and its resource-guard stop.
[HARBOR_CALIBRATION.md](HARBOR_CALIBRATION.md) freezes a public Terminal-Bench
sample task, the exact KRYN OpenCode adapter and Harbor's official verifier.
[REVIEWER_SCREEN.md](REVIEWER_SCREEN.md) preregisters a read-only Reviewer
mechanism screen on two archived, public Harbor worker failures.
[EFFORT_POLYGLOT.md](EFFORT_POLYGLOT.md) records an inconclusive Default/Fast
mode screen: Docker interrupted Default, and Fast exhausted the research relay
after repeated writes before a successful grade.
`python3 -B research/summarize_verification_feedback.py` checks its compact
public-development receipts. Neither rejected candidate changed the product.

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

The protected holdout and a representative Harbor subset remain pending. One
public Harbor sample calibration ran through the official verifier and failed;
see [HARBOR_CALIBRATION.md](HARBOR_CALIBRATION.md). Docker availability is checked
at each external trial; it was interrupted once during the mode screen. The first
pinned official SWE-bench calibration and the
frozen six-task Lite/Verified subset are documented in
[EXTERNAL.md](EXTERNAL.md). Record every subset attempt with
`research/record_external.py`; it checks task/prompt/base identity and, when an
official result is supplied, verifies that the submitted patch is exactly the
one archived by the runner and grader. New schema-2 receipts also require the
grader's per-task patch and report beneath the declared run directory, and
publish only the exception class when a driver fails. Earlier schema-1 rows
remain immutable; their raw evidence and SHA-256 manifests are retained for
audit. The compact append-only
`research/history/external.jsonl` index is public; full prompts and traces stay
in ignored evidence directories. Never report a subset as a full benchmark
score or a proof of frontier-level capability.
`python3 -B research/summarize_external.py` reproduces the frozen six-task
strict-acceptance totals and paired bootstrap from the graded compact receipts.

The calibration's single resolved KRYN patch and interrupted native control
are development observations, not the representative external subset.
