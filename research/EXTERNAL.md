# External benchmark calibration (frozen before model generation)

This is a one-instance **calibration**, not the predeclared representative
SWE-bench subset or a benchmark score. It tests whether KRYN's real OpenCode
loop can emit a patch accepted by the official evaluator on this Apple-Silicon
host. The same task will be run KRYN then minimal OpenCode, with the same local
model, timeout, candidate tools, permissions and sandbox. One pair cannot
establish an uplift or generalization.

| Input | Frozen value |
| --- | --- |
| Official evaluator | `SWE-bench/SWE-bench@02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` (`swebench` 5.0.2) |
| Dataset | `SWE-bench/SWE-bench_Lite@b0dde1093fe417d83b7184254edf8199c1f0dff5` |
| Local test parquet SHA-256 | `438e281d80587aa7be470896ce410557002fde02d2ceee3e099331d308f62dd3` |
| Instance | `sympy__sympy-20590` |
| Repository base commit | `cffd4e0f86fefd4802349a9f9b19ed70934ea354` |
| Official Docker image | `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590@sha256:3a282752833ce34730ee0621e22033501c993f45742775ca57f04c9ff27178a0` |
| Agent prompt SHA-256 | `767b87738cc2de709220547740b66623bec8630f8bd5f5dfe8978bede8462f8b` |
| Agent budget | 900 s, one local generation at a time, unchanged 22-GiB process guard and two-warning host guard |

The prompt is a fixed generic work instruction followed by the dataset's
`problem_statement`; it excludes `hints_text`, reference patch and test patch.
The candidate checkout was copied from the official image and reset to the exact
base commit. The evaluator log and gold patch remain outside the whole-process
macOS sandbox; only a one-model inference relay and the candidate's own OpenCode
server port are reachable. The research adapter emits a Git patch, and the
official evaluator alone grades that patch. An agent claim or a local test does
not decide acceptance.

The first official gold-patch preflight errored because the registry has no ARM
manifest for this image. An explicit `linux/amd64` pull under Docker Desktop
emulation fixed the environment; the second gold preflight resolved 1/1 with no
grader errors. Its run ID is `kryn-gold-lite-amd64-20261002`; this is an oracle
check, **not** model performance. The image occupies about 4.0 GB and was
retained for the candidate trials. No unrelated Docker data was deleted.

The first KRYN candidate generation failed the unchanged host-memory guard
after 255.887 s and 33 local inference requests, before any tracked edit. Its
sampled host pressure reached warning twice; sampled swap growth was zero.
Power switched between AC and battery during the run, so it cannot form a
matched performance pair with a later single-power control. The trace also
showed the isolated candidate had no usable ripgrep for OpenCode's `glob` and
`grep` tools, and the host's Python 3.14 could not import this old SymPy tree
(`distutils` was removed). These are calibration-environment faults, not an
accepted patch or a reason to weaken the resource guard. Earlier startup
preflights made no inference call and are retained separately.

A fresh disposable research tool venv now supplies Python 3.9.18, mpmath 1.3.0
and ripgrep 15.1.0 to **both** arms through the whole-process sandbox's
explicit dependency list. The isolated canary successfully imported SymPy
1.7.1 and ran ripgrep on the candidate tree. Its Python executable, ripgrep
binary and mpmath initializer SHA-256 values are respectively
`7787e81ff11ff35703620e6af5e0cd395bea30e9ed099e318940153004c2580f`,
`b8836cfabdf1e40f68431cab9b58d7add60c237b858c62a34cd3b2046fbadf8e`,
and `b241584d2c1fc0304b0a1015ea923749d7b0800411dd406dcab7c82bf25d9fe8`.
This environment correction is development calibration; any task observed here
is ineligible for protected holdout selection.

Neither this calibration nor the earlier public TaskboardLite pilot is sealed
holdout evidence. Full Lite/Verified subsets and Terminal-Bench via Harbor remain
unrun. The frontier-adjacency gate remains open.
