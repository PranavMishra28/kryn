# Direct Git evidence candidate (research only)

Preregistered before editing the plugin. Released v1.0.0 stays unchanged.

The exposed rate-limit repair emitted a JavaScript syntax-coverage warning in a
Python-only repository. The hook did not find JavaScript; its Git snapshot was
unavailable. In the unchanged research Seatbelt profile, `/usr/bin/git` exits 1
because Apple's shim cannot read `/var/select/developer_dir`. The installed
Command Line Tools Git exits 0 with the same workspace, environment and profile.
Both observations were reproduced without a model request on 2026-10-03.

**G1:** choosing the root-owned Command Line Tools Git directly when present,
and retaining `/usr/bin/git` as a fallback, restores complete Git evidence in
the research sandbox without changing the model, prompts, tools, permissions,
grader or guard. The only implementation variable is the Git executable used
by the plugin's two read-only evidence commands.

The development screen is fixed now: a Python-only committed repository with
one changed tracked file must produce a non-null Git snapshot and no JavaScript
syntax-coverage warning after a completed shell call in the actual Seatbelt
profile. A deliberately malformed changed JavaScript file must still produce
syntax feedback. The same two checks must pass in ordinary unsandboxed plugin
tests. Capture the exact source/tool hashes and both pre/post results. Revert
this candidate if the sandbox result fails, if it widens the file/network
boundary, or if product tests fail. These no-model checks alone do not justify
product promotion or show accepted-work uplift; fresh model validation,
protected transfer and release checks remain prerequisites.

## No-model development result

The first smoke invocation selected a Homebrew Node build whose `libuv` dylib
was not in the sandbox's dependency list, so neither arm started. The second
started both arms but incorrectly looked for Git evidence in a first-turn
context hook, which intentionally does not emit a checkpoint. The corrected
smoke uses a compaction hook and a pinned standalone Node binary. These two
scaffolding failures are retained as the `-20261003.json` and
`-20261003-02.json` receipts under `/private/tmp/kryn-direct-git-evidence*`;
they do not count as candidate behavior.

The corrected screen (`-03.json`) reproduced the baseline failure: no current
Git snapshot, the irrelevant Python-task warning, and no changed-JavaScript
syntax feedback. The candidate reported a current Git snapshot, omitted the
Python-task warning, and reported the malformed JavaScript. Both arms exited
normally. The candidate also passed `make check` with 215 setup, 26 research,
87 Node and the frozen offline suite checks. This is a deterministic sandbox
compatibility result, not an accepted coding task or evidence of H1 uplift.

## Frozen live compatibility screen

Before any model request, use the already-retired `linecfg-duplicate-key`
development task (private manifest SHA-256
`804278f90dac2d253d28b008b4150c449e361f0b4513ff41929968b1d025c314`)
in one fresh candidate-volume KRYN Agent turn. This task cannot enter a sealed
holdout. Run the current-source no-model preflight first. The one-attempt live
screen passes only if the unchanged guarded turn completes, the independent
grader passes, the candidate/capture/grader volumes detach, telemetry is
complete with no guard stop, and the raw Agent trace has no irrelevant
JavaScript-coverage notice. The source, prompt, grader, model, tool environment
and resource policy are frozen; no operator repair or retry after generation.
This tests real OpenCode compatibility, not same-model harness uplift.

## Live screen disposition

The first no-model preflight ran from a source clone under world-writable
`/private/tmp`; the trusted oracle correctly refused that source. The owner-
only source clone passed boundary mechanics and seed/reference/partial
controls, while its final eligibility remained false because the task is
retired. One guarded Agent turn then completed and passed its independent
functional grader with clean resource telemetry and volume detachment.
However, its OpenCode inventory loaded the **installed v1.0.0 plugin**
(`24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`),
not this candidate (`e1580149d3e2665b0fb12779306c6df42bf6fcaf1f73630b94bb6c78df2ca877`).
The irrelevant JavaScript warning appeared once. The live candidate screen
therefore **failed provenance** and cannot be counted as candidate validation,
even though the underlying coding task passed. It is not retried under this
frozen one-attempt screen.

The invalid live barrier report SHA-256 is
`3c484cbaf13f99889f2b0b0488beaa3951d7fab95ee1608993fc9ab3853b96bd`.
Its owner-only 30-file evidence archive hashes to
`3105f8ac87cb376281c57bb01b628ff3b4d1c3a0a6b2adb410a5c8973c642d87`
and its index to
`e6568a31e80fc05ea258f7d9651cda975381a38bb9643df3c3c9f5644be773e1`.
The separate research-runner loader correction is required before a new,
fresh-task candidate trial. No production integration is justified yet.
