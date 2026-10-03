# Explicit preserved-test constraint candidate

Frozen 2026-10-03 before editing the plugin or generating on this candidate.
This is a **public development** mechanism screen, not H1, a protected holdout,
or a production change. The released v1.0.0 owner profile and resource guard
remain unchanged. Base source is
`4e5e4759f9421a6e8f12b63f35ff42b6d91d13d9`; its plugin SHA-256 is
`24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`.

## Observation and hypothesis

In the fully matched public Task03 pilot, KRYN's second Agent turn edited
tracked `test_existing.py` despite the exact instruction to keep all existing
tests unchanged. Its final answer reported the work as complete; the frozen
grader correctly rejected the changed file. Native OpenCode preserved that
file in both paired turns. These are development observations on a seen task,
not an estimate of generalization.

**P1:** when the current user request explicitly says existing tests must stay
unchanged, a small native-tool guard can prevent an Agent from editing a test
file that was already tracked at the start of that request, while still
allowing new focused test files. This changes only the existing OpenCode
plugin's `edit`/`write` before-hook. It does not add prompt text, modify the
model or sampler, change permissions, intercept shell writes, alter the
resource guard, or create a new agent loop. In a Git-less project or if the
tracked-file inventory cannot be established, the candidate must not assert
enforcement. A new user request can change the constraint; compaction and
restart continuity need separate validation before any promotion.

## Frozen screen

1. Add a bounded, conservative detector for explicit *unchanged existing
   tests* wording and a prompt-start inventory of tracked test files. In an
   offline hook fixture, verify that native edits/writes to those files are
   denied, a newly created test file and non-test source remain writable, and
   a prompt without that explicit constraint retains ordinary behavior. Verify
   `make check` and clean package smoke before model generation.
2. Prepare one fresh disposable TaskboardLite 03 workspace. Run exactly one
   candidate trial `preserve-tests-candidate-03-20261003` with the already
   frozen Task03 prompt, user-facing `agent`, Qwen3.5-9B-6bit/oMLX, installed
   96K profile, Default variant, same ready full-tool catalog, 900-second
   cap and unchanged daily-use resource guard. Snapshot candidate product
   source only into that trial; do not install it for the owner. Use no
   operator repair and no same-task retry after a model request.
3. Grade with the frozen Task03 oracle, the independent report/CLI/HTTP probe,
   preserved-file assertions, native completion, actual local inference,
   clean guard, resource settlement and explicit guard-trigger evidence.

The **development screen** is positive only if the candidate is strictly
accepted, the preservation guard actually denies at least one attempted
native edit/write to a baseline test file, the agent recovers by creating a
new test file or otherwise satisfies the task, and no resource stop or false
completion occurs. An accepted run with no guard trigger is not credited to
P1. A positive screen would require separately frozen *fresh* validation,
shell-bypass and compaction/restart checks, accepted-work/hour comparison and
external transfer before product promotion. Otherwise reject the candidate
code and retain a compact failed receipt. The prior Task03 baseline attempts
have different order/cache histories and cannot form a matched causal pair
with this one candidate run.

## Completed development screen

The candidate commit `4831c71ec23e4c76566adfe6e05209ab4198637d`
passed its focused hook fixtures, `make check`, and clean package smoke before
generation. One fresh Task03 Agent trial then ran from that source snapshot with
the frozen prompt, full ready tool catalog, local Qwen3.5-9B-6bit, Default
variant, 96K profile, 900-second cap, and unchanged daily-use guard. oMLX was
idle with no model loaded at preflight, so the driver wall time includes a cold
load; no concurrent heavy generation or operator repair occurred.

The frozen grader **passed** its three checks, confirmed `test_existing.py` and
`data/entries.csv` unchanged, and the additional report/CLI/HTTP probe passed.
But the native turn **timed out** after 908.084 driver seconds, so strict
acceptance is **false**. The trace has 48 tool calls and four tool errors, none
from the new preserved-file guard. The model read the existing test and wrote
new tests; it never attempted a native edit/write to the protected test. It
spent the end of the run repairing its new HTTP tests and port conflicts.
Sampled memory pressure stayed normal, swap did not grow, and the resource
guard did not stop the turn. The trial consumed 269,493 new input and 19,308
output tokens. This one trajectory cannot identify a causal effect of the
candidate on quality or latency, and a functional pass after a timed-out turn
cannot be promoted as accepted autonomous work.

**Decision: reject P1.** The preregistered guard-trigger and native-completion
conditions both failed. Commit `935cd6a` reverts the candidate hook and its
focused tests; the product plugin again hashes to the base
`24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`.
No owner installation or released v1.0.0 profile changed. The compact trial
receipt is in `history/development.jsonl`; raw trace, source snapshot, grader,
supplemental probe, resource samples and a per-file SHA-256 manifest remain in
ignored `evals/runs/preserve-tests-candidate-03-20261003/` on this Mac. The
private manifest at `/private/tmp/kryn-preserved-tests-20261003/raw-manifest.json`
hashes to `34eb67be48c3af42831eafed9e4555a54d0de103a21fe48a1731e819c73ecb71`.
The repeated self-authored-test repair and late port-conflict loop are useful
development observations, not validation of a new mechanism.
