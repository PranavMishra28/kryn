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

## Result

The first public zero-model smoke completed both arms and Docker grading, but
did not attempt the hidden-file read. Its retained `result.json` SHA-256 is
`c245dae33edcc57e5108c475919a1f59c711860e63a438f313c9d19dc9619b88`;
it is not used for the preregistered hidden-read criterion. The follow-up added
one canned `shell` call to read the hidden host sentinel before the fixed edit.
At clean source `5b171e5541c20c16b6144c7c1b9f6dacdaf36f91`, both native
OpenCode and KRYN returned a nonzero shell exit without the sentinel bytes.
Each then made the same `write` call, completed, captured the identical patch
SHA-256 `f4368f87b6286c90cd99aa4cee06a9fe5d9c3860e18fa6eda85977c00bba2f71`,
and detached candidate, read-only capture and APFS grader volumes. The trusted
callback applied that captured patch to a fresh Docker-visible clone and
verified its source bytes matched the APFS grader checkout. The pinned Python
image `sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0`
returned `PUBLIC PASS` in a networkless, read-only, non-root container in both
arms. No container or trial volume remained after the run.

The strict **public mechanics canary passed**. Native and KRYN tool catalogs
matched, with three canned inference requests per arm and **zero real model
requests**. Agent wall time was 16.276/16.472 seconds (native/KRYN). Both arms
recorded complete resource telemetry, normal host pressure, AC power and zero
sampled swap growth. The final `result.json` is
`/private/tmp/kryn-public-docker-handoff-20261003-02/result.json`, SHA-256
`6f123cf85b761c475be5c6a152b7e1542a0e3b2dca9fbf279f678ddf5f3b6c68`.
The frozen public seed commit is `44c1d3e8e25c6786b2f2a4e9ad76d82afec2508d`
and the script SHA-256 is
`bc17fb5bfe5610eceebd22e4da788be33c213078738b76d1773ed6e097b81749`.

This proves one public Docker callback path through the real research barrier.
It does not prove that every private Docker grader can be staged safely, or
establish any protected model score, autonomous success, or H1 uplift. The
actual recovery tasks must still pass an admitted, frozen paired study.
