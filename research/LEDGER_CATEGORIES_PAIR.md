# Retired multi-file development pair

Frozen before any model request for this task. This is a **development**
diagnostic of the released v1 harness against native OpenCode, not protected H1
evidence. The private `ledger-categories` draft is explicitly retired in
owner-only provisional roster V5 (SHA-256
`6820b7298b0815dab9a30830cbb8fd5631d784e2ec3cf70e05b1ecd32ec1e172`);
it cannot later enter the sealed holdout. The draft manifest is
`554ee191ebe626d314bf7b3c87052479854a6231c89c8c97f6913e4b5642b5b9`,
the candidate-facing prompt is
`47282f2b9e51d7fef373a9da119d9b541d2a218bf8fc6207678d6273b4b41b08`,
the hidden oracle is
`8b06b397351e077ee3268c2fd39972433680acf22630dc4902cf1495e11f5ed7`,
and the clean seed commit is `4426ec3221f45c153ecd25e3620b83316488cc50`.
No private task text or answer is in this repository.

**Question:** on a multi-file coding task with independently checked CSV/JSON and
exact-decimal behavior, does KRYN's v1 policy/state layer improve strict
acceptance over minimal native OpenCode? The only treatment is that layer;
Qwen3.5-9B-6bit, oMLX, 96K profile, OpenCode Agent, Default variant, tool
environment, task prompt, 900-second cap, permissions, hidden oracle and
unchanged daily-use resource guard are shared. The order seed is
`ledger-categories-dev-20261003`; its SHA-256 begins `3c`, so native runs
before KRYN. Both arms get a one-token, setup-only guarded warmup to ensure the
model is loaded before the task. Run each arm **once** with no operator repair.
If the first arm hits the resource guard, stop rather than rerun the same
condition. The paired driver is `run_ledger_development_pair.py` (SHA-256
`6b98a1df9eb48ee4aebc87b74ca0d27a5c26915482a3356d08e85522df561998`).

First require a fresh no-model real-path preflight under the pinned Python
3.14.6/ripgrep/Git environment: seed and partial must fail, reference must
pass, both OpenCode shell boundaries must deny hidden files, and the APFS
candidate volume must detach. The live barrier must detach the candidate,
capture its patch on a read-only remount under the guard, then apply and grade
it in a fresh volume with the hidden oracle. No grader path is mounted into
the Agent process. The arm's strict acceptance requires native completion,
local model requests, no intervention, normal detachment of all three volumes,
complete guard telemetry and oracle exit zero. A workspace that happens to
pass the oracle after a timeout or guard abort still fails strict acceptance.

A pair is **matched** only if the driver verifies exact prompt/seed, model
revision and profile, OpenCode binary, pinned tools, timeout, first-wire
sampler and tool schema, normalized effective Agent permissions, loaded model,
AC power and clean guards. Missing telemetry or a mismatch makes the pair a
diagnostic. Report per-arm result, wall time, requests, tools/tokens when
available, memory and swap, plus the independent oracle. One pair cannot
support population uplift or a product promotion, even if KRYN wins. Retain
all raw failed and successful receipts outside the public package.

The v1.0.0 installation, production model/profile, guard thresholds, release
gates, grader and protected H1 thresholds do not change.

## Instrumentation correction before reverse-order repeat

The first no-model preflight used the copied tool venv as its **trusted grader**
interpreter. Its candidate sandbox could not load that venv's Homebrew Python
framework, so reference control failed before any model request. That failed
receipt remains at `/private/tmp/kryn-ledger-development-pair-20261003-01`.
The second preflight used the draft's frozen canonical Python 3.14.6
interpreter and passed before generation. No task, oracle or model setting was
changed.

The first live pair at source `ac968d9` produced a valid strict acceptance in
**both** arms: native completed in 152.714 Agent seconds with 27 model requests;
KRYN completed in 120.142 seconds with 14. The hidden oracle exited zero for
both. Both had normal sampled pressure, zero sampled swap growth, normal
candidate/capture/grader detachments and no intervention. Its frozen comparator
nevertheless returned `matched=false`, solely on effective permissions. Raw
permission records differ in the randomly generated `kryn-isolated-*` server
private directory beneath each arm's APFS mount; no other permission field
differs. The original pair receipt SHA-256 is
`74cb0e61d22ba65b66608d9282043cfd2cc0d2601c382cff28e0b824817391a0`.
**Do not retroactively count this pair as preregistered matched evidence.**

The comparator now normalizes only that exact generated server-private root,
alongside the already normalized candidate workspace and OpenCode temporary
basename. A regression proves two randomized roots match, while a real `allow`
→ `deny` change remains unequal and a missing expected root fails closed. The
corrected driver SHA-256 is
`cc7ca58d4c0c64f370fce806d99a13775737a66c625cfa7e561e7b127befbc48`;
its focused regression SHA-256 is
`a260a383d3503712d95562f61c2c832643f226ad1e36dd7ccce04a6a881211f8`.
Recomputing on the preserved first-pair inventories gives the same permission
digest `747d4ef55102ad727d4e26f6d547d1f8d3fac1c7cf9d264015185fb943ba086a`
in both arms, but that is post-hoc diagnosis only.

Run one **reverse-order** pair (KRYN → native) with the unchanged task, frozen
oracle, model, guard, arm acceptance and no-repair rules. A fresh no-model
preflight is required at the corrected clean source commit. Each arm again
receives guarded setup-only warmup, and the first guard stop ends the pair.
The corrected, now-frozen matcher decides validity prospectively. This repeat
is still development data and cannot repair the missing protected H1 roster or
support a production change by itself.

## Completed reverse-order result

At clean source `74a966c9c04652bf1802a51e4c2b2b49d44191ba`, the fresh
no-model preflight passed its real OpenCode boundaries, seed/partial failures,
reference pass and image detachment. Both setup-only warmups loaded the same
local model. The reverse-order pair was **fully matched** under all ten frozen
controls: source, task, model/revision/profile/binary, tool environment,
timeout, wire sampler and tool schema, normalized permissions, warm model,
AC power and clean guard. Both arms used the 10-tool wire schema
`1b56b6b37c804f7fd30cd60d131476c6a619cda5269ac2ccf9d2fc8a5d34a81e`.

| Arm | Strict result | Agent time | Model requests | Tools / errors | New input / output / cache-read tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| KRYN first | **Accepted**; oracle exit 0 | 174.486 s | 21 | 26 / 3 | 33,852 / 6,897 / 143,360 |
| Native second | **Failed**; oracle exit 1 | 125.294 s | 22 | 21 / 5 | 29,137 / 4,593 / 110,592 |

The native turn completed and claimed “all changes are complete and tested,”
but its patch omitted the top-level export of `category_totals`. Its own
checks imported internal modules and missed the public API shape; the hidden
grader's package-level import failed. KRYN read all five relevant source files,
including `__init__.py`, before editing and exported the function. This is a
trace observation, not a one-variable causal attribution. In the earlier
**unmatched** pair, native did read `__init__.py` and both arms passed. The
stochastic difference on one task prevents a general quality claim.

Both reverse-order arms completed without operator intervention or a guard
stop. Sampled pressure stayed normal, sampled swap growth was zero, and the
candidate, read-only capture and fresh grader volumes all detached. Sampled
peak oMLX physical footprint was 12.25 GB for KRYN and 11.64 GB for native;
these process-wide samples may miss transients and do not isolate KV usage.
KRYN took longer and used more new tokens in the matched pair. The result is
one KRYN-only accepted task, not a rate or confidence-interval estimate.

The private `pair.json` for the matched repeat hashes to
`34a8c7ceae5473fba83cfdee4d077deced037e2c4fa0c80dbc77e75aae06ee45`; its 184-file raw archive and independently checked
index hash to `f2be362095773bbdc84c1c629ed18c1b3b3bbe7429131801b419f75537210c2e`
and `e12d52cd773f1f6309491d36404a803f3ea969e887b0b8a6f0edbbc6e825b5d7`.
The owner-only analysis SHA-256 is
`ddd3a8bc9f32760e2a24c45b92bcf84dc948d2fa367fe223f5e7b5e556e41985`.
Provisional roster V6 records four development model turns and permanently
withholds this task from protected use (SHA-256
`472d878e4476001d82ae7238df7a045245e2726cf483906d2e897e0d774fe46f`).
The original invalid preflight and unmatched pair remain in the same archive.

**Decision:** retain released v1.0.0 unchanged. The development observation
justifies testing source-coverage and public-API verification on fresh tasks,
but H1's protected roster, statistical uplift, UI and long-session gates remain
open. It does not offset the earlier matched public Task03 losses or qualify
frontier adjacency.
