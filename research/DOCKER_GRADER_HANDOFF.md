# Public Docker-grader handoff canary

Preregistered at clean `main` `0845d757e479755b9409319650f20a3fa3cb134f`.
This is a no-model, public-fixture mechanics test, not a holdout score or
product change. Keep the released v1.0.0 runtime and resource guard unchanged.

**Question:** Can a canned Agent turn pass a frozen patch through KRYN's actual
candidate-detach, read-only-capture and fresh-grader-volume sequence, then be
graded by a pinned, networkless Docker verifier without exposing a hidden host
file to the candidate? The recovery-draft preflight showed Docker Desktop did
not see a newly mounted nested APFS checkout, and did not see a Git patch made
after a prior bind of the same grading path.

**Hypothesis D1:** keeping the Agent and capture phases unchanged, then applying
the already captured patch once more to a fresh host-side Docker-visible clone
inside the trusted grader callback, permits exact independent Docker grading.
The one changed variable is where the Docker verifier reads the final checkout.
The baseline is the failed direct/reused-path grader controls preserved in
`HOLDOUT_BOUNDARY.md`. The candidate stages a fresh clone, applies the exact
captured patch before its first Docker bind, and compares relevant file bytes
with the fresh APFS grader checkout. It does not send reference bytes to Agent.

Use a new public one-file Python fixture with a deliberately wrong seed and a
fixed canned `write` tool call, not a real model. Run both minimal OpenCode and
KRYN arms through `run_candidate_to_grader` with the same pinned binary, tools,
profile, permissions, and Docker image digest. Predeclare success only if both
arms complete the native Agent turn, expose matched tool catalogs, detach their
candidate/capture/grader volumes, capture the same patch, validate exact staged
source equivalence, pass the Docker verifier, leave no probe containers or
mounted images, and report zero real model requests. Record wall time and
resource samples; missing telemetry is a failure, not zero. A failed arm or
uncertain cleanup rejects this mechanics candidate. No prompt/policy change,
model inference or protected task is allowed to rescue it.

Even a pass would establish only a public Docker grading handoff. The three
corrected recovery drafts remain unsealed; independent oracle review, the
30-task roster and paired real-model H1 trial are separate gates.
