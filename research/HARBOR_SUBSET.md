# Three-task Harbor development subset

This is a small, public Terminal-Bench 2.0 development screen, **not** a
protected holdout, a full benchmark score, or evidence of frontier equivalence.
The released KRYN v1.0.0 runtime and its 22-GiB oMLX guard were unchanged.
No paid model was used.

The selection and arm order were frozen before reading these task prompts or
solutions. From 87 eligible tasks, SHA-256 of
`kryn-harbor-subset-20261003-v1` + NUL + task name selected the first three
lexicographically after excluding two previously inspected sample tasks.
The private preregistration SHA-256 is
`80fe73994882ca736f632ee4e748c943a4e6774b865609605390aa31281584d3`.
The official Harbor checkout was
`fd1521a1da6250d9ed8fc7505caa0b7a72f36c4b` (0.23.0), and the task
source was Terminal-Bench 2.0 commit
`69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`. Each pinned task/image
passed an official gold-solution preflight with reward 1.0; its NOP control
received 0.0. Each arm had one planned attempt, a 900-second agent bound,
the same local Qwen3.5-9B-6bit model, and no operator repair. The independent
review compared main-agent wire model, sampler, thinking settings and tool
schemas within the completed pairs. A tool-free title request used a different
output cap in the second pair, so the whole wire trace was not identical.

| Task | Order | KRYN | Native OpenCode | Interpretation |
| --- | --- | --- | --- | --- |
| `raman-fitting` | KRYN, native | Ungraded after host sleep and manual settlement | Ungraded after 900-second agent stop | Invalid pair; retained in attrition, never rerun |
| `nginx-request-logging` | Native, KRYN | Reward 1; strict pass | Reward 1; strict pass | Valid 1–1 tie; clean resource evidence |
| `sqlite-with-gcov` | KRYN, native | Reward 0; strict fail | Reward 0; strict fail | Valid 0–0 tie; both saw warning memory pressure |

All six planned arms were attempted. Four reached the official verifier. Each
arm had one strict success among its three scheduled attempts. The two
scoreable pairs have a success difference of zero. The invalid first pair
cannot be counted as an efficacy tie. This subset shows **no observed
same-model harness uplift**; it is too small to establish equivalence, infer
general performance, or estimate a stable latency difference. Task order,
cache warmth and pressure also differ across arms.

In the final pair, the native arm made 126 search calls, with 112 exact
input/output repeats and 108 consecutive repeats over roughly 633 seconds.
It reached the research relay's 128-request cap and exited after that relay's
403 response. This was the local research relay limit, not a refusal by an
OpenCode free model provider. KRYN made 23 inference requests; native made
128. Both had official reward 0.0, complete telemetry, warning-pressure
samples, no swap growth, no guard stop, and an idle runtime afterward. The
loop makes the elapsed times unsuitable as a causal speed comparison.
KRYN's final-pair worker compiled SQLite, but the independent grader could
not find `sqlite3` on `PATH` in its fresh process. The worker had seen
`which sqlite3` fail in a fresh shell, then checked it only after sourcing
`/etc/environment` and wrote an interactive-shell startup file before
claiming completion. This is an observed environment-propagation and
verification failure, not evidence that a task-specific prompt fix transfers.

Raw logs, model traces, task copies, resource samples, launch receipts and
independent pair reviews remain in the private local research directory.
The six compact, machine-readable arm receipts are public in
`research/history/harbor_subset.jsonl` (SHA-256
`5c2c3b598d38a01c63ad799da3d3c22231c8291d38278a8a54211a7af4bcdae6`).
Their token fields come from Harbor's agent trajectory and exclude auxiliary
title requests; they are not full relay-counter totals.
The frozen environment lock v7 SHA-256 is
`0502bbcc8df9de226a6a6cf4dff29749e98eda85e8a0b2cddbff26ae5bcf7440`.
The three independent pair-review receipt hashes are recorded beside those
traces. The hash-bound private aggregate `subset-final.json` has SHA-256
`40d3768aa7ce9a1237b89e4b5d2d5ce6a3650e49140f1dc61719dd7c66df29bc`.
The public runner is `research/run_harbor_calibration.py`; install
Harbor at the pinned commit in a disposable Python environment and provide
one pinned task, a private trials directory and a fresh trial name as in
`research/HARBOR_CALIBRATION.md`. A replay is another stochastic sample, not
a replacement for these one-shot observations.

The runner's 900-second threshold cancels an active agent and rejects a late
result. Cancellation can take additional time while Harbor cleans up its
container, so this is **not** a hard whole-process wall limit. The first KRYN
arm had only Harbor's configured timeout, which did not survive host sleep as
an effective wall bound. The five continuation arms used a 2700-second outer
supervisor and checked owned Docker cleanup before the next arm. Reproducers
requiring a hard total wall bound need an external supervisor and must retain
its stop/cleanup receipt. Install-only preflight is a separate setup check:
it must finish with zero model requests and an idle runtime; it is never
scored as agent success.
