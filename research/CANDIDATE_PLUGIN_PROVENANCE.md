# Candidate plugin provenance correction (research-only)

Frozen before editing the research runner. Production v1.0.0, its installed
plugin and resource guard remain unchanged.

One isolated direct-Git candidate passed a no-model Seatbelt check. A subsequent
guarded Agent turn on a retired Python development task passed its independent
functional grader but emitted the baseline Git-coverage warning. The loaded
OpenCode plugin inventory pointed to the installed plugin, whose `server.js`
SHA-256 was `24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`,
while the candidate source was
`e1580149d3e2665b0fb12779306c6df42bf6fcaf1f73630b94bb6c78df2ca877`.
Therefore that live turn cannot validate the candidate. Its raw receipt is
retained and not rerun as if it were a clean first attempt.

**I1:** the research Agent-to-grader runner must explicitly install exact
candidate source bytes into a disposable, read-only-to-Agent plugin package
when requested. The default remains the installed product plugin for released
v1 comparisons. The native arm must reject a candidate-plugin request. This
changes research instrumentation only; no model policy or product setting.

The fixed no-model acceptance screen is: from a clean source checkout, build a
fresh candidate package with only the five known plugin files; record hashes;
start real OpenCode with that package under the current whole-process sandbox;
read its plugin inventory and require `kryn.product` active at the exact
candidate package path and exact `server.js` hash. The installed package must
remain byte-identical. Candidate code must not be able to write its package or
read any hidden grader. Native control must still load no KRYN product plugin.
Package smoke and all offline tests must pass. Failure leaves the research
candidate unqualified and does not change the released product.

Only after this no-model gate may a new public development Agent task screen
the direct-Git candidate. Even then, protected transfer and uplift remain
unproven until the sealed roster and matched trials pass.

## Result

At clean research commit `c46df54a25fb892928de51044230c21e5a404f25`,
the real OpenCode no-model canary loaded the direct-Git candidate's
`server.js` SHA-256 `e1580149d3e2665b0fb12779306c6df42bf6fcaf1f73630b94bb6c78df2ca877`
from a disposable package. The KRYN inventory named that exact package's
`server.js`; the native arm had no `kryn.product`. Both arms read their visible
workspace file and were denied the host-side marker. Candidate shell writes
to the plugin package were denied, its five file hashes and the installed
plugin hash stayed unchanged, and the APFS candidate volume detached. The
passing report SHA-256 is
`abeca5be0632cec2da964891b1c8253630631cb1896eb951e262cb934d1b5ea3`.
The first canary run had the correct loaded plugin but compared the inventory
file path with its parent directory and therefore failed its own final
assertion; that failed report SHA-256 is
`b637f1e17f59d951d9b1a8120e77640a285653e7ec4c48ce6144bc4881c43e52`.

The loader branch passed `make check` (215 setup tests, 27 research tests,
87 Node tests and frozen offline suites) and clean `make package-smoke` (wheel
SHA-256 `97ef8f7148e8201cf812204d56ba83001644cbab7be2071371b414fa4b3ea36d`).
No model request was made by this loader screen. It proves candidate-byte
selection and the tested isolation properties, not engineering quality or
protected-task admission. The earlier invalid live turn is retained in an
owner-only 30-file archive, SHA-256
`3105f8ac87cb376281c57bb01b628ff3b4d1c3a0a6b2adb410a5c8973c642d87`;
its per-file index hashes to
`e6568a31e80fc05ea258f7d9651cda975381a38bb9643df3c3c9f5644be773e1`.
The owner-only loader-canary archive contains 27 files outside the repository;
`evidence.tar.gz` hashes to
`ff5d0020979575a81107446643488f75a60ad06526e44b68fcbac89f58abaafb`
and its manifest to
`f2e29244102cf9f4f7bcaa7885737b65f60a6edd78b21539e0a2261a495b03a6`.
