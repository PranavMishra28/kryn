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
