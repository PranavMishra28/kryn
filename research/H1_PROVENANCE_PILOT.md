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
