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
