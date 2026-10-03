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
[WRITE_LOOP.md](WRITE_LOOP.md) records the preregistered, rejected no-op write
hook screen. Its official Harbor reward was 0.0, the hook never fired, and the
candidate code was reverted. The raw and compact failed evidence is retained.
[H1_PROVENANCE_PILOT.md](H1_PROVENANCE_PILOT.md) records two fully matched
public Task03 pairs using the user-facing Agent role. Native OpenCode accepted
2/2 and KRYN 0/2; this validates the corrected runner, not H1 transfer.
[PLUGIN_GUIDANCE_ABLATION.md](PLUGIN_GUIDANCE_ABLATION.md) records a matched
public Task03 diagnostic that retains KRYN guidance while removing only its
product plugin. Strict acceptance tied at 1/2 per arm; it cannot establish
protected uplift.
[PUBLIC_UI_RESOURCE_PROBE.md](PUBLIC_UI_RESOURCE_PROBE.md) records a one-turn
public Task06 browser/resource diagnostic: initial browser dispatch worked,
but strict guard and UI acceptance failed.
[PRESERVED_TESTS.md](PRESERVED_TESTS.md) records the rejected explicit
preserved-test guard screen: the functional grader passed, but the Agent timed
out and the candidate guard never fired. Its code was reverted.
[HOLDOUT_BOUNDARY.md](HOLDOUT_BOUNDARY.md) freezes the correction to the
protected-holdout isolation gate after a same-volume hardlink exposed a hidden
oracle. No protected task is qualified yet.
[PYTHON_CALIBRATION.md](PYTHON_CALIBRATION.md) records the development-only
candidate-volume model screen and the isolated Python/Git tool correction.
[AGENT_GRADE_PILOT.md](AGENT_GRADE_PILOT.md) records a passing real
Agent-to-grader volume handoff on an already-retired Python task; it cannot
count as holdout evidence.
[DOCKER_GRADER_HANDOFF.md](DOCKER_GRADER_HANDOFF.md) preregisters and records a
passing public zero-model Agent-to-Docker-grader handoff in both OpenCode arms.
It does not admit private recovery tasks or measure model quality.
[SOURCE_GATEWAY.md](SOURCE_GATEWAY.md) preregisters and records a passing
zero-model, exact-file read-only official-source channel canary in both arms.
It does not admit external-information tasks or measure model quality.
[SOURCE_AGENT_TRIAL.md](SOURCE_AGENT_TRIAL.md) records the native Agent shell
output-cap failure and the passing six-chunk, zero-model Agent-to-Docker handoff.
That handoff does not test live-model coding or protected task admission.
[PUBLIC_SOURCE_PAGINATION.md](PUBLIC_SOURCE_PAGINATION.md) records the failed
first public official-source pair and the later accepted six-case pair after
the research-only exact-file permission fix. The task was reused for diagnosis;
neither pair is a protected H1 score.
[PUBLIC_SOURCE_RATE_LIMIT.md](PUBLIC_SOURCE_RATE_LIMIT.md) records a fresh
official-source task with frozen Docker controls. Both arms reached the source
but failed the same retry-exhaustion criterion; the longer KRYN run did not
improve accepted work.
[CRITERION_REPAIR.md](CRITERION_REPAIR.md) records one public, guarded repair of
that exposed failure: the independent functional grader passed, while the
worker deleted its tracked test afterward. No product change was promoted.
[CANDIDATE_PLUGIN_PROVENANCE.md](CANDIDATE_PLUGIN_PROVENANCE.md) records the
research-runner correction that loads exact isolated candidate plugin bytes.
Its no-model OpenCode boundary check passed; no product plugin was changed.
[ui_gateway/README.md](ui_gateway/README.md) records the research-only fixed-page
browser gateway, its no-model OpenCode dispatch check, the rejected
deferred-worker resource experiment and remaining UI gates.
[STAGED_CONTINUITY.md](STAGED_CONTINUITY.md) preregisters a public, zero-model
three-turn canary for two native compactions and two actual server restarts.
[PUBLIC_STAGED_MODEL.md](PUBLIC_STAGED_MODEL.md) freezes and reports the first
matched three-stage live-model coding calibration. KRYN failed its final
independent case; the released product was unchanged.
`python3 -B research/summarize_verification_feedback.py` checks its compact
public-development receipts. Rejected candidates did not change the product.

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
Public-fixture raw traces, browser artifacts and source snapshots generally stay
in ignored `evals/runs/`;
`research/history/development.jsonl` is an append-only compact index of the
public development runs. Preserve raw failed and interrupted runs. For protected
research, create an independently isolated grader and a new sealed task roster;
these public fixtures cannot be relabeled as holdout evidence.
The recent public official-source traces and source snapshots also have an
owner-only durable archive at
`~/Documents/Codex/kryn-research-private/experiments/public-source-20261003-archive/`:
`evidence.tar.gz` SHA-256
`85d7f31d5ca72f68c6d4db6edd970cb547ea43dfa133ae6e924958136bbaa474`,
and its 670-file SHA-256 `manifest.json` SHA-256
`032766d27701eae1d3b9b06da8ca209fcdad81a8469cb5b73a31937399244380`.
The archive is local and private, not a public reproducibility download.

On macOS, run both boundary modes:

- `python3 -B research/check_holdout_boundary.py same-volume` (expected exit 1
  **and** `negative_control_exposed: true`; exit 2 means an invalid control)
- `python3 -B research/check_holdout_boundary.py encrypted-volume` (expected exit 0)

The second canary checks a separate encrypted grader volume, real OpenCode
startup and shell-tool denials. It is a
boundary preflight, not a protected score: the same-volume control exposes a
workspace hardlink to the hidden oracle, while the separate encrypted volume
prevents that alias. The public OpenCode model turns and their mixed results
are distinct from these checker verdicts; their receipts and
remaining gates are in [HOLDOUT_BOUNDARY.md](HOLDOUT_BOUNDARY.md).

`python3 -B research/check_holdout_boundary.py candidate-volume` tests the
alternative layout with candidate workspace and temporary files on a separate
APFS volume and the hidden oracle on the host. Its no-model OpenCode shell
canary passes, but the draft task graders and browser/source gateways still
require independent admission review before any protected result can be scored.
`research/preflight_protected_python.py` adds a no-model real-task boundary and
grader-control check for the private Python draft. A passing receipt requires a
clean research commit; it is not a protected model result.
`research/preflight_recovery_draft.py` likewise checks the three corrected
owner-only recovery drafts through both real OpenCode shell configurations and
fresh Docker grader controls. All three no-model mechanics receipts pass; the
actual Docker Agent-to-grader handoff and protected roster remain unqualified.
The research-only fixed-page UI gateway now has a paired zero-model
Agent→Browse→fresh-grader canary in
[`ui_gateway/barrier_canned.py`](ui_gateway/barrier_canned.py). It verifies
native routing and lifecycle, not protected task admission or local-model
quality.

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
