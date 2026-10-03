# Candidate V1: failure-only verification feedback

Preregistered 2026-10-02 before changing the Acceptance Controller. This is
public development work; released KRYN v1.0.0 and its installed owner profile
remain unchanged. The previous managed Task06/Cancel Edit attempts and the
TaskboardLite tasks are already seen development data, not validation or holdout.

## Observation and hypothesis

In the three archived managed Task06/Cancel Edit attempts, the independent
checker returned a JSON object containing several named checks. The controller
forwarded only the first 900 characters of that object after each failure. In
the archived first rounds, the prefix included passing checks and the first
failing browser flow but omitted the later failing Cancel Edit flow. The
controller correctly withheld acceptance (0/3), but its repair turn did not
receive all observed failures.

**V1 hypothesis:** extracting only failed check names and their bounded
diagnostics from a structured checker result will get the worker more useful
repair evidence per token. The only candidate behavior change is the text of
the synthetic repair feedback. Requirements, original prompt, checks, model,
tool catalog, permissions, maximum of two repairs, acceptance verdict, source
revision logic, and resource guard are unchanged. The candidate must not reveal
checker commands, reference solutions, or passing-check prose.

The evaluation driver will first be amended to allow `--managed-acceptance`
with the **existing** daily-use resource guard. That common driver change is
applied to both arms before generation. Guard thresholds and monitor behavior
do not change. It is instrumentation, not part of the V1 treatment.

## Frozen public development experiment

1. A deterministic fixture using the archived checker shape must demonstrate
   that both failed browser checks survive candidate feedback, while the v1
   900-character prefix loses the later one. Candidate feedback must be under
   2,000 characters and preserve the exact failure status in the controller's
   evidence ledger. Malformed or non-JSON check output must still be reported
   safely and boundedly.
2. Prepare four fresh TaskboardLite Task06 workspaces from the frozen suite.
   Add the exact previously recorded Cancel Edit request as the turn prompt,
   and use the already existing `evals/development_acceptance.py` as a public
   outside-workspace check. The managed acceptance spec is frozen before the
   first generation and uses the same two requirements and check command in
   both arms. The control uses v1.0.0 Acceptance Controller feedback; V1 uses
   only the candidate feedback serializer. Run two AB/BA pairs, with control
   first in pair A and candidate first in pair B, fresh session/workspace each.
3. Both arms use Qwen3.5-9B-6bit/oMLX/96K, user-facing `agent`, Fast variant,
   a 900-second limit per native turn, `--daily-use-guard`, the full ready tool
   catalog and the same installed product plugin. Record exact source, binary,
   profile, tool and permission hashes, first-turn and repair-turn messages,
   checker source/output hashes, complete failures, wall time, tokens, host
   pressure and swap. The controller may do at most two repairs. Strict
   acceptance requires native completion, controller acceptance, independent
   source/API/browser checks, and a clean unchanged guard verdict. No model
   claim substitutes for the checker.

The mechanistic gate is all-failures-visible feedback on each repair request.
The **development promotion screen** requires at least one additional strictly
accepted candidate trial out of the two paired runs, no loss on another pair,
no extra false completion or guard stop, and accepted work per hour no lower
than control. Because these are two repetitions of one previously seen task
family, a positive result would trigger fresh validation; it would
not promote the change into KRYN. A tie or regression rejects this candidate.
After two failed attempts at this mechanism, change approach instead of adding
more instructions.

The protected holdout, official Terminal-Bench, six long-horizon sequences and
frontier comparator remain separate gates. This experiment cannot by itself
support a frontier-adjacent or autonomous-production claim.
