# Bounded no-op write-loop candidate

Frozen 2026-10-03 before editing the plugin or generating on this candidate.
This is a **public development** mechanism screen, not a protected holdout,
same-model harness-uplift result, or product promotion. Released v1.0.0 and the
owner's installed profile remain unchanged.

## Observation and hypothesis

The archived Fast Harbor `polyglot-c-py` trial in [EFFORT_POLYGLOT.md](EFFORT_POLYGLOT.md)
ended with 16 identical consecutive successful writes to one file, then hit
the research-only 128-request relay ceiling. Its official reward was 0.0. The
baseline trace and its raw 20-file manifest are frozen there. KRYN already
bounds repeated **shell** calls with unchanged output but has no corresponding
no-op write feedback. This candidate is motivated by that generic tool pattern,
not by the polyglot answer or verifier details.

**W1:** detecting consecutive writes that would leave a file byte-identical
can prevent an unproductive edit loop and improve independently accepted work
within the same bounded turn. The only candidate behavior change is a small
in-memory check in KRYN's existing OpenCode `write` hook. It compares the
current file hash with the requested content hash; after two consecutive
identical no-op writes, it denies the next such write with a concrete message
to inspect the latest failure and change approach. Two denied repetitions end
that Agent turn. A different tool, changed content, changed file or new user
turn resets the counter. No grader, model setting, prompt prefix, tool schema,
permission, relay budget, resource guard, or agent framework changes.

Base source is `ad01464707f541e6b2fd5cf0e516d9b044550ac9` and baseline
plugin SHA-256 is
`24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`.
The task image, Harbor evaluator, OpenCode, model, candidate environment and
profile are pinned in [EFFORT_POLYGLOT.md](EFFORT_POLYGLOT.md). The official
Oracle already returned reward 1.0 on that exact task/image. The baseline
Fast turn made 128 local requests, 71 writes and 57 shell calls, then exited
with provider HTTP 403 caused by the research relay cap; the verifier found an
extra compiled binary and stopped before testing source behavior.

## Frozen procedure and decision

1. Implement only the no-op write-loop hook and focused offline behavior tests.
   Verify that legitimate writes, nonconsecutive writes, changed bytes, and a
   new user turn remain allowed. Run `make check` and package smoke. If either
   fails, do not run local generation.
2. Run one install-only Harbor setup preflight with the candidate source. If
   Docker or installation fails, record an environment failure and stop.
3. Run **one** guarded candidate Fast trial on the same public task, named
   `write-loop-candidate-polyglot-20261003`, with the existing 900-second
   agent timeout and 128-request relay ceiling. No same-task retry after
   generation. Use the exact shipped Fast model variant, actual OpenCode Agent,
   same ten wire tools and unchanged daily-use guard.
4. Grade by official Harbor reward plus normal native completion, actual local
   inference, clean guard and settled runtime. Record tool types, identical
   consecutive writes, requests, token/cache counts, complete wall time, memory
   pressure, swap, power, and any false completion. An agent claim never grades.

The **development screen** is positive only if the candidate is strictly
accepted (reward 1.0 and all operational conditions), has at most three
consecutive identical no-op writes, completes within 128 requests, and does
not trip the unchanged guard. Merely stopping earlier or reducing tokens while
still failing is insufficient. A positive screen triggers a separately frozen
fresh-task, baseline-versus-candidate validation with unaffected tasks and
accepted-work/hour cost; it still cannot change production. Otherwise reject
the candidate code and retain only a compact failed receipt. Power/cache
differences versus the archived baseline are disclosed, never treated as
matched speed evidence.
