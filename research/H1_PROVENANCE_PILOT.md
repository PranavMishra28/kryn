# Same-model runner provenance pilot

Frozen 2026-10-03 before these model turns. This is a **public development**
instrumentation check on TaskboardLite 03, which has already guided prior
development. It cannot establish H1, transfer, or frontier adjacency. Released
v1.0.0, the installed profile and the resource guard remain unchanged.
The research base is `234abaaa0eb99b26aad12ca256c7a646267677bf`;
the frozen fixture manifest, installed model profile, product plugin, runner
and pair comparator have SHA-256 hashes `186fd74343eff01992b48ac7d29b9a01ed7543968da6048745e6c42e1ec63ab6`,
`05c4645f3b691ae09b239534c026a9da5fa929677e39cff3c0d867fe9e91fe52`,
`24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`,
`deb4745bb2dc4a9072deb05955e5d908b95ddd713814226a17e4414dd08b00f4`,
and `ab00d65ec08e2221602585a1bf7b0f9c75ac0a90cbc54e98d4aa2e2a984ea1c5`.
The task prompt with its final newline hashes to
`6deb57fad2c0df31af114ca88ebd836a520f4aa9d09950190bd25227efb61f2a`.

The earlier Task02/03 pilot recorded equal wire tools and effective permissions
but omitted invocation-time runner, OpenCode binary, model-profile and timeout
provenance. The corrected recorder and comparator now fail closed on those fields.
Run two fresh Task03 pairs with the user-facing `agent` role, alternating
**native → KRYN** then **KRYN → native**. Use Qwen3.5-9B-6bit through the same
oMLX listener, OpenCode 2.0.10, the installed 96K profile, Default variant,
the same full MCP tools and effective permissions, a 900-second turn cap, and
the unchanged daily-use memory guard. Both arms start with the model loaded
and idle; a setup-only, non-task warmup is allowed and must be recorded.
No two agent turns overlap. Keep the exact frozen task prompt and fixture, and
use a new disposable workspace/session per arm. No operator repair or replay
after a model request.

| Pair | First run | Second run |
| --- | --- | --- |
| 1 | `h1p-03-r1-native-20261003` | `h1p-03-r1-kryn-20261003` |
| 2 | `h1p-03-r2-kryn-20261003` | `h1p-03-r2-native-20261003` |

Each arm passes only if its native turn completes, the frozen Task03 grader
and the additional report/CLI/HTTP edge-case probe pass, intervention count is
zero and the resource guard is clean. The pair is **matched** only if
`research/compare_pair.py` verifies invocation source/binary/profile/timeout,
model and first-wire sampler, full tool schema, effective permissions, guard,
power and cold/warm status. A mismatch is retained as an invalid pair rather
than counted as a capability difference. Record raw traces and append compact
receipts with `research/record_trial.py`. A pass here qualifies the runner for
future protected tasks; Task03 outcomes themselves remain development data.

## Completed result

Both frozen pairs passed the fail-closed comparator. Each arm used the same
loaded local model, Default sampler, AC power, 900-second cap, daily-use guard,
41 wire tools, identical full tool catalogs and effective permissions. The first-wire tool-schema SHA-256
was `3fcb5b056c05da695548bfe35da9002b628b51df87a2e2aca80e78906da9e085`
and the effective-permission SHA-256 was
`d66eff9de90022486e7e8bdc3555b484174fc7af9dd6c7bcfa976b8b8db9f6e6`
in all four turns. Invocation-time runner, OpenCode binary, model-profile and
timeout provenance were present and matched; model revision provenance was
verified. No turn tripped the guard or grew sampled swap. One KRYN turn saw
warning pressure, permitted by the unchanged daily-use guard.

| Pair and order | Native OpenCode | KRYN |
| --- | --- | --- |
| 1, native first | **accepted**, 329.432 s, 37 requests | **failed**, 908.193 s, 57 requests; native turn timed out |
| 2, KRYN first | **accepted**, 584.754 s, 55 requests | **failed**, 330.473 s, 36 requests; changed an existing test file |

In pair 1, the KRYN workspace passed both functional probes after the turn,
but its Agent never completed within 900 seconds. It spent many calls repairing
its own malformed test file, then continued API checks. The trace contains a
read-before-edit denial, a browser wait with no open page, and a correctly
denied direct process signal. Those hard guards remained in force; the model's
repair trajectory and extra checking consumed the bound. In pair 2, KRYN
completed and passed the functional probes but appended 61 lines of new tests
to `test_existing.py`. The frozen task explicitly required all existing tests
unchanged and allowed *new* focused tests. The grader detected the changed
file. KRYN's final answer presented the work as complete, so this is one
observed false-completion claim. Native preserved the file in both runs.

Strict acceptance was **native 2/2, KRYN 0/2** on this seen task. Native spent
914.186 driver wall seconds and produced 7.88 accepted trials per driver hour;
KRYN spent 1,238.666 seconds and produced zero. KRYN used 427,344 new input
tokens versus native's 163,128, despite nearly equal model-request counts
(93 versus 92). Native's primary system prompt stayed byte-identical across
both turns; KRYN's changed 16 times. This supports a cache/prompt-churn
diagnosis but does not attribute the acceptance failures to that churn. The
earlier C1 prompt-stability candidate reduced churn while worsening accepted
work, so this result does not justify reviving C1 or adding prompt rules.

The four compact receipts are appended to
[history/development.jsonl](history/development.jsonl). Raw traces, workspace
state, independent grades and a private per-file manifest remain in ignored
`evals/runs/h1p-03-*` on this Mac. The private manifest at
`/private/tmp/kryn-h1-provenance-20261003/raw-manifest.json` hashes to
`bd92178d24e9295a305cf0d34c5eff5f8ad20de809920d33ddecb0f45e79df72`.
This two-pair public pilot validates the corrected matched-runner controls and
shows **no demonstrated harness uplift** on Task03. It is not a protected
holdout, a representative task distribution, a confidence interval, or a
frontier comparison. No product/profile/release change is promoted.
