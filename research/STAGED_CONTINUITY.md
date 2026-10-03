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
