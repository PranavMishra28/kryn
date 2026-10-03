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
