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
