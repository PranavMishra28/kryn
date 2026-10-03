# Public official-source rate-limit task (preregistered 2026-10-03)

This is a fresh **public development** task, not a sealed holdout or an H1
estimate. The hypothesis is that the research-only exact-file source channel
works on a materially different GitHub Docs page and a different engineering
problem than pagination. The released v1.0.0 model, OpenCode loop, resource
guard, provider and permissions stay unchanged. Start from clean `main`
`39ae96b0116d000167f0880d173cdb6955af9c3a`.

The official [REST rate-limit guide](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
is pinned from `github/docs` commit
`2bd66de8cea336061c9ea060c9b37385136e6ab3`, path
`content/rest/using-the-rest-api/rate-limits-for-the-rest-api.md`, 9,870 bytes,
SHA-256 `3815984e337dad4da3ceb1a60da044da5c05db5df969719c40e10dd9a0d490ac`.
Its owner-only provenance sibling has SHA-256
`a119247a97d8212e2923f00159cd365a042553b309de833d5a76274ebd7dcbde`.
Only the pinned page is available to the Agent; the grader and provenance
sibling remain outside its readable boundary.

**Task:** implement `request_with_backoff(fetch, sleep, now, max_retries=2)` in
one Python module. `fetch()` returns a response dict with `status`, `headers`
and `body.message`; `sleep(seconds)` and `now()` are injected, so no real wait
or network is needed. Return an ordinary response unchanged. For documented
primary 403/429 exhaustion, wait until after the reset epoch. For secondary
403/429 limits, use `retry-after` when present, otherwise reset when remaining
is zero, otherwise at least 60 seconds; repeated secondary failures increase
the delay exponentially. Header casing can vary. Never retry an unrelated
403/429. `max_retries` bounds additional `fetch` calls; raise `RuntimeError`
when a recognized limit persists after that budget. The prompt will provide
deterministic rounding and malformed-header fallback rules so the oracle is
unambiguous, and require the Agent to read the pinned source.

Before generation, freeze seed, prompt, source, reference and partial hashes;
run seed-fail/reference-pass/partial-fail controls on fresh networkless,
read-only, non-root Docker clones. Independently grade normal response,
unrelated 403, primary reset, secondary `retry-after`, fallback 60 seconds,
mixed header casing, repeated secondary backoff and retry exhaustion. All
cases must pass. The grader never enters the candidate process boundary.

Then run one native-first matched real-model pair, 900 seconds per arm, with
Qwen3.5-9B-6bit, 8192 output cap, exact same tools/permissions, unchanged
occupied-host resource guard and no operator repair. Stop on a guard abort.
Measure independent acceptance, source read, false completion, latency,
requests/tokens/tool errors, pressure, swap and cleanup. A single public pair
cannot establish transfer, confidence intervals, protected H1 or frontier
adjacency even if it passes. Preserve failed attempts and do not tune the
grader after model exposure.

## Frozen controls and first live pair

From clean `728f043e4f5bc9ab42e72696f5aa2bebbba5870f`, `make check` passed
before generation. Fresh networkless Docker clones produced the preregistered
controls: seed 2/8, deliberate partial 2/8, reference 8/8. The source,
provenance, seed, prompt and patch hashes are in
`/private/tmp/kryn-public-rate-limit-20261003-01/fixture.json` (SHA-256
`3ee47a1e1facc0b64da13aae66f1e4e22dc38279f80758461385d5b1f62ebc3d`).

The native-first guarded pair completed with equal effective permissions and
identical model, output, sampling/thinking and ten-tool wire contracts. **Both
arms failed strict acceptance at 7/8 independent Docker cases.** The raw pair
receipt is `/private/tmp/kryn-public-rate-limit-20261003-01/pair.json`, SHA-256
`825e4f494e19e1420c636cb366d5c32e3c62d1b26d08cd244e4ccb3e5cb12b6c`.

| Arm | Independent result | Work and resources |
| --- | --- | --- |
| Native OpenCode | 7/8; retry exhaustion failed. | 195.164 s; 12 model requests and tool calls, no tool errors; 24,219 input / 8,187 output / 124,928 cached-read session tokens; sampled listener physical peak 12.05 GB. |
| KRYN | 7/8; the same retry-exhaustion case failed. | 682.028 s; 34 model requests and tool calls, two read-before-edit denials; 199,423 input / 20,905 output / 622,592 cached-read session tokens; sampled listener physical peak 13.56 GB. |

Both agents made an untruncated native read of the pinned source. The guard
reported complete telemetry, AC power, normal sampled pressure and zero
sampled swap growth. Source and provenance hashes stayed unchanged; candidate,
capture and grader images detached, and no Docker container remained.

The frozen retry-exhaustion criterion required `RuntimeError` after two total
fetches and only the first 60-second wait. A separate read-only diagnostic
executed each captured patch in the same pinned networkless Docker worker and
observed `RuntimeError`, two fetches **and waits of 60 then 120 seconds** in
both arms. Their own test files asserted the exception but did not assert the
sleep sequence; both final messages claimed completion. That is a measured
false completion in each arm. KRYN's extra requests and local repair attempts
did not improve accepted work on this fresh task.
The separate diagnostic receipt is
`/private/tmp/kryn-public-rate-limit-20261003-01/diagnostic.json`, SHA-256
`c26659c3938366b5b0782fc060543043403365131166d3f4dab3cfe2b790bf08`;
it retains the pinned worker/image and both captured patch hashes.

**Decision:** retain this public failure without changing its task or grader.
The source channel transferred, but successful autonomous implementation did
not. This one public task cannot estimate H1 or admit the external-information
category. The observed deficiency is exact criterion-to-check coverage at a
retry boundary; any general remedy needs a separate preregistered candidate
and fresh validation, not a task-specific prompt rule or replay of this oracle.
