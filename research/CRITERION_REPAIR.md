# Public criterion-witness repair screen

Preregistered on 2026-10-03 before any repair-model turn. This is a **public
development** screen on an already exposed failed task, never protected H1 or
validation evidence. Released v1.0.0, its installed profile and resource guard
remain unchanged. The original rate-limit pair and immutable Docker grader are
documented in [PUBLIC_SOURCE_RATE_LIMIT.md](PUBLIC_SOURCE_RATE_LIMIT.md).

Both original agents explicitly listed the requirement to raise without an
extra sleep when the retry budget is exhausted. Both then wrote local tests
that checked the exception but not the sleep trace. The Docker grader rejected
both at 7/8. The KRYN arm used 34 requests versus native's 12, largely editing
tests and debugging other branches, without improving accepted work. This is
a coverage failure, not a source-delivery failure. One trace cannot establish
that KRYN caused the extra work.

**Hypothesis R2:** if the existing KRYN worker receives an exact independent
failure observation with the expected and observed side-effect trace, it can
repair its already generated patch and pass the unchanged eight-case grader in
one guarded turn. The baseline is its frozen 7/8 patch. The only new input is
the observed failure; model, tools, permissions, source, runtime, source guard,
and grader remain unchanged. This measures repair ability with evidence,
not autonomous discovery of missing checks. It is a different mechanism from
the rejected Reviewer-only and failure-feedback-compression screens.

The runner copies the KRYN patch with SHA-256
`04c74f195db46923a469620cb6730c3ea604ee57b8c0539ad402b8ee3768827c`
from the original pair SHA-256
`825e4f494e19e1420c636cb366d5c32e3c62d1b26d08cd244e4ccb3e5cb12b6c`,
commits it to a fresh seed, and independently confirms 7/8 before generation.
Its prompt preserves the original full task and appends the single observed
failure: expected `RuntimeError`, fetches `[429,429]`, sleeps `[60]`; observed
the same exception and fetches but sleeps `[60,120]`. It asks the worker to
repair and check that boundary. No hidden grader, reference or patch enters
the Agent workspace. After one turn, the unchanged networkless Docker worker
grades a fresh clone of the captured patch.

R2 screens positive only if the original 7/8 baseline reproduces; the repair
turn completes under the unchanged guard, reads the pinned official source,
all eight original Docker cases pass, APFS source and Docker-visible source
match, and every owned volume/container settles. Record wall time, requests,
tokens, pressure, swap and false completion. A guard stop or partial grade
rejects this screen. Do not retry the same failed repair turn. Even a pass
only justifies a **new** preregistered task-derived-verifier candidate and
fresh validation; it cannot promote a product change or show H1 uplift.

## Result and boundary of the result

The one attempt from frozen research commit
`4e83e249a7aaa684407522e43e9d471257797ec9` reproduced the 7/8 baseline,
then the real KRYN Agent made a native untruncated read of the same pinned
source, completed, and passed **8/8** in the unchanged networkless Docker
grader. The captured repair patch SHA-256 is
`7f76a8d5b3780073ab07d0e8e94c76e6023a106cb61374c015344a9f99cfe41d`.
The repair added a retry-budget check before sleeping in both primary and
secondary branches. The fresh Docker-visible clone matched the APFS grader
source. Candidate, capture and grader volumes detached, the container was
absent, and the owned model runtime settled.

The repair took **586.674 seconds**, 19 model requests and tool calls, 167,731
new input / 18,479 output / 282,624 cached-read tokens. Sampled listener
physical footprint peaked at 13.48 GB. The unchanged guard saw AC power,
normal host pressure and zero swap growth. This is substantial work for a
single known failure and is **not** an accepted-work-per-hour improvement over
the 195-second native first pass. Different initial states and prompt content
also make that contrast diagnostic, not a causal matched comparison.

The post-turn patch **deleted the tracked 338-line `test_backoff.py`** after
the worker's local eight-test command had passed. The independent grader
checks `backoff.py` behavior and therefore still passed; it did not require
test preservation. This is a posthoc repository-quality regression, not a
reason to rewrite the frozen 8/8 verdict. The final model message described
the behavior fix, but a passing local command before deleting its test file
does not establish a durable test suite. The trace also contains a JavaScript
syntax-coverage notice during this Python-only task; that notice was not a
failing check and needs separate diagnosis before any product change.

**Decision:** R2's narrow repair-ability screen is positive, but no candidate
is promoted. The model needed a supplied exact failure, spent nearly ten
minutes, and removed its test. The next general experiment must generate or
select executable witnesses for task criteria *before* claiming completion,
and preserve those witnesses through the final diff. It needs fresh tasks and
an independently frozen grader; this exposed rate-limit task cannot validate
that mechanism or estimate H1.

The raw result `/private/tmp/kryn-rate-limit-repair-20261003-01/result.json`
has SHA-256 `6f04482be5518abffcf835e0cca468d62d95b45c0a7dad8ae3f31ea27394e5e6`.
The owner-only archive at
`~/Documents/Codex/kryn-research-private/experiments/rate-limit-repair-20261003/evidence.tar.gz`
contains the prompt, baseline seed files, raw native events/session, patch,
resource trace and grader result. Its SHA-256 is
`eb1a92a1cc9bcf45a631746eaed88c0feed529e30145ae7a86a8afdccf7a6c74`;
the independently checked 32-file manifest SHA-256 is
`195b40967b1405ddc58397334b322ee9276ecff822bf2bc05df65aa25d6bf624`.
Sparse images are excluded; the runner recreates them from the pinned inputs.
