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
