# Public staged-continuity lifecycle screen

Frozen before the no-model canary on 2026-10-03. This is research
instrumentation, not a protected holdout, model-quality result, or change to
released v1.0.0. The installed model, profile and resource guard stay fixed.

**S1 hypothesis:** an isolated OpenCode server can serve three turns in one
owned session, complete two manual native compactions, and restart its actual
server process twice without losing that session or its raw history. The one
changed variable from the existing one-turn research runner is retaining its
already isolated private state across the two server process restarts. The
native and KRYN arms use the same local canned inference, OpenCode binary,
workspace fixture, tool policy and manual compaction schedule; only the
preregistered KRYN product plugin and guidance differ.

Run one fresh paired public canary with a new APFS candidate volume per arm.
The canned provider emits text only and never forwards a request to oMLX.
Each arm must finish three distinct user turns in the same root session; after
turns one and two, request native compaction through the pinned OpenCode API,
observe exactly one new completed compaction, prove the session and model
runtime idle, terminate the server cleanly, prove its listener closed, then
restart the same binary in its same isolated private state. After both
restarts, query the session by exact ID and verify its workspace/model identity.
The final export must retain all three user prompts and both compaction records;
the prompts' exact nonces must appear in stored history. The resource guard
must remain clean, there must be no real model request, and the candidate
volume must detach. Keep raw receipts and a compact hash-indexed result.
The manual endpoint and durable-history semantics follow
[OpenCode's V2 compaction documentation](https://opencode.ai/v2/docs/compaction).

From a clean KRYN checkout on this Mac, run:

```sh
python3 -B research/staged_lifecycle_canned.py /private/tmp/a-new-receipt-directory
```

Reject this mechanics screen if any compaction never completes, a restart
loses or changes the session, stale/extra compaction records appear, guard
intervenes, listener/process shutdown is uncertain, or volume detachment
cannot be proved. A pass only allows development of a staged protected runner;
it does not admit private tasks 07–12, prove context fidelity in a real model,
or establish same-model harness uplift. Two failed implementation attempts
should trigger a different state-retention approach rather than more prompt
rules.

## Observed public mechanics result

At clean code commit `1a5e0050d6e0a4dcc946b2fb2dc86e7ee400c1b8`, the
paired canary passed with a first-wire full tool-schema match. Each arm stored
three distinct user turns and two completed compactions in one native session,
restarted the actual OpenCode server process twice with new PIDs, and proved
the old listener closed before reuse. Both candidate volumes detached. The
unchanged guard reported complete telemetry, normal pressure, AC power, zero
sampled swap growth and no stop. Native took 14.433 seconds and made five
canned inference calls (three turns, two compactions); KRYN took 14.347
seconds and made three (its two compactions used deterministic checkpoints).
The exact private result SHA-256 is
`07a5e868f666bc8882dfb37c95810b1ea7ec57ef67f49c4a2162259e3f87cbc5`.

The first two no-model probes failed native compaction because the canned
provider returned an ordinary sentence instead of OpenCode's required
structured summary; KRYN's deterministic checkpoint path passed. A focused
diagnostic exposed the exact `compaction.failed` record. After the canned
provider emitted a valid template, both arms completed. A later probe caught
and corrected the canary's own mistaken assumption that a tool-bearing wire
request always represented a user turn: native compaction also carries the
tool catalog. All failed and superseded receipts are retained under
`/private/tmp/kryn-staged-continuity-*`; the compact index records their hashes.

This proves process/session mechanics only. The canned summary does not carry
the public nonce forward, so this result does not establish model-visible
context fidelity, real-model staged coding, hidden-grader isolation, or
accepted work. Private tasks 07–12 remain unadmitted. The next test is a
research-only staged Agent-to-grader runner with trusted stage checks and
then guarded live local-model turns, if the occupied-host preflight permits.

A follow-up clean-source canary at `c4ef326ef804120c0e67cc66d311dabe8b7ada80`
also waited for the native policy and selected KRYN plugin to become active
after each restart and required every wire tool schema to remain identical.
Both arms passed again with normal pressure and zero swap growth. Its result
SHA-256 is `bd7708907fc36d8a2449c2c7db01076b70666030235782a4a423372dab4cbaca`;
the earlier passing receipt remains indexed rather than replaced.

## Public staged Docker handoff screen

A separate no-model public-fixture canary combined the actual three-turn
session lifecycle with fresh Docker grading **after each stage**, while the
candidate APFS volume stayed mounted for the next turn. In each native/KRYN
arm, the first OpenCode tool call failed to read a host-only oracle; the second
wrote stage-one source through the native tool. A trusted test controller made
the stage-two and stage-three source changes after their canned text turns.
Each stage was copied into a new host Git clone before Docker's first bind,
byte-compared with the candidate source, and graded in a pinned, networkless,
read-only, non-root container. The broken seed failed stage one; all three
expected stage grades passed in both arms.

Each arm retained one session through two completed compactions and two real
server restarts, with all three exact prompts in raw history. Runtime-resolved
Agent permissions, full wire tool schema and tool catalogs matched across
arms. Native made seven synthetic requests and KRYN five because its native
compaction used deterministic checkpoints; neither made a real model request.
The unchanged guard recorded normal pressure, zero sampled swap growth and
complete telemetry. Both candidate images detached and no trial container
remained. The private result SHA-256 is
`4eae6d8adfa8e7a19412a927a7da9e76519846d4445b08d3a4b3a3301be40ad8`;
its verified 164-file owner-only archive index SHA-256 is
`e95429242d88466016d8d2c4c149aab193a8037c43a1a39a309ed4c162141538`.

**Scope:** this proves a public three-stage grader transport path under canned
inference. The later edits came from the trusted controller, so it does not
establish autonomous long-workflow quality, model-visible context fidelity,
protected task admission or same-model H1 uplift. The private staged tasks
remain unsealed.

## Guarded live-model Docker transfer screen

The next screen repeated the already exposed public Python task with **real**
Qwen3.5-9B-6bit turns. Its owner-only plan was frozen before the grader change
(SHA-256 `d84438f2c197337518745ab067be669eae821386d3d6f4a8bb2b0078b6fba3bc`).
This is a development transport test, not fresh validation or a protected
holdout. The frozen fixture and installed profile were pinned by hash. The
research adapter at `6234dda` cloned only the current two regular source files
from each candidate APFS workspace into a fresh host checkout after each turn;
the Docker grader saw that checkout, not the candidate volume or expected
answers. It used the pinned Python image, networkless read-only non-root
containers, bounded output, and host-side oracle comparison. Docker controls
confirmed seed failure, reference passes at all three stages, and rejection of
a stale separator before model generation.

| Arm | Stage grades | Read before edit | Requests | Tool errors | Wall time |
| --- | --- | --- | ---: | ---: | ---: |
| KRYN | pass, pass, **fail** | 3/3 | 25 | 2 | 174.777 s |
| Native OpenCode | pass, pass, **fail** | 3/3 | 38 | 3 | 201.173 s |

Both arms kept one session through two completed compactions and two real
server restarts. All three prompts remained in raw history; both candidate
images detached; every stage clone matched its APFS source bytes; no trial
container remained. Each guard had complete telemetry, normal sampled host
pressure, AC power, zero sampled swap growth and no intervention. The full
tool schema stayed stable within each arm and matched at first wire.

The **original executable matched-permissions check failed**. Its configured
rules matched, but it hashed four generated OpenCode private-state paths
literally. Posthoc inspection of the saved `/api/agent` inventories found the
same 28 rules in the same order; narrowly replacing each arm's exact owned
`kryn-isolated-*` path makes the lists equal. A later research-only normalizer
uses that exact path and has a negative control for a changed rule. The
original result remains `matched_effective_permissions=false`; it is **not**
retroactively counted as a protocol-matched H1 pair or rerun to improve score.

The functional failures are also clear. KRYN tracked suffixes per base slug,
so distinct bases could yield the same final slug. Native began collision
suffixes at 1 despite the task's explicit starting value of 2 and also reused
a slug. Each final answer claimed completion. A separate **posthoc, unscored**
collision case failed in both final sources while the frozen reference passed.
The corrected transport does not turn either failed model output into accepted
work. No v1 product, installed profile or resource guard changed.

The immutable raw `result.json` SHA-256 is
`503700fb60a6d248a4182947e174eec3b83eb3f7c3de7fa501f21bba50cfe85c`.
The owner-only 170-file raw index SHA-256 is
`4d263d0364185c3edd991eacd8aff2ec7da1c0ecb7998b09b232b1479d77c321`;
the posthoc result SHA-256 is
`7aced4ea1671cead2463b55a6a1c275461be1462f371e648fd8096404e8036ba`.
The private receipt, retained disk images and final source snapshots are at
`~/Documents/Codex/kryn-research-private/experiments/public-staged-docker-live-20261003/`.
This screen advances live staged **grader-transport feasibility** only. The
unsealed private tasks, genuine long-workflow acceptance, same-model uplift,
and frontier-relative gates remain open.
