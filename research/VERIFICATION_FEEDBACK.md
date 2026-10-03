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

## Frozen trial input and preflight

The prompt frozen for all four planned disposable runs is exactly:

> In this disposable TaskboardLite workspace, add a Cancel Edit button that appears only while editing an existing entry. Clicking it must leave stored data untouched, clear edit mode, and reset the form, so Save can create a new entry again. Inspect the existing source and tests yourself; no clarifying question is needed. Preserve existing behavior, run relevant tests, and report only observed checks.

Its SHA-256 is `91d2a2c70ae2d9a02da743068501b2c20e7da43dbf801fac1513bad08d85e996`.
The two declared requirements are that exact request and preservation of the
seed's Task06 API, tests and browser flows. Both map to one command check:
`python3 -B evals/development_acceptance.py <WORKSPACE> <EVIDENCE>`, with a
300-second check limit. The normalized managed-spec SHA-256 is
`24cfdaf89996a83b0c6a301074d6211928a88c02c3ea478f745a52c0d7eee105`;
the actual spec hashes differ only in disposable workspace/evidence paths.
The frozen suite manifest is `186fd74343eff01992b48ac7d29b9a01ed7543968da6048745e6c42e1ec63ab6`;
the checker source hash is `539894f1e3b71471d044111a8298f9aa90b8314b2bd11bdcbf7bf86eafd4d30b`.
The common trial driver is `af90430` (source hash
`deb4745bb2dc4a9072deb05955e5d908b95ddd713814226a17e4414dd08b00f4`);
the control controller source hash is
`b8e2de5b99db7c106a020541fd8dff35a7aebe576971e412d7da338d26e96679`,
and the candidate controller source hash is
`0f1be378b8a51c1bc1536386d154b402c6df0724f9fea8cdbab219fd45aa143f`.

A preflight on an untouched prepared control workspace ran the public checker
successfully as a checker process and returned the expected **failure**: both
`task06_browser` and `cancel_edit_browser` failed against the seed. This
establishes a nontrivial baseline and does not count as an agent trial.

## Completed first pair and decision

Only the first, control-then-candidate pair generated. The common driver,
model profile, OpenCode binary, prompt, normalized check spec, product plugin,
41-tool wire schema, effective permissions, sampling settings and daily-use
guard matched by hash. The control began with the model cold; the candidate
began warm. Both crossed AC/battery states at different times, and occupied-host
pressure evolved differently. This is **not a fully matched causal quality or
latency comparison**. Exact compact receipts are in
`history/verification_feedback.jsonl`; run
`python3 -B research/summarize_verification_feedback.py` for the recorded totals.

| Arm | Native/controller outcome | Independent checks | Wall time | Swap growth |
| --- | --- | --- | ---: | ---: |
| Control | Native completed; controller blocked after two repairs | Task06 browser still failed | 1,035.305 s | 0 MiB |
| Candidate | Final repair stopped by unchanged guard; controller blocked | Task06 browser and Cancel Edit still failed after first repair | 1,170.589 s | 706.31 MiB |

The candidate changed the repair message as intended. The control's two repair
messages were 1,300 and 1,233 characters, each containing a 900-character
prefix of the combined check output. Its first prefix cut off the Task06 browser
diagnostic after verbose diff-hygiene output. The candidate's messages were 818
and 649 characters, and both named every failing subcheck, including the later
Cancel Edit browser failure. This confirms delivery of more relevant check
evidence per feedback character. It did **not** produce accepted work: its first
repair took 709.4 seconds, fixed only diff hygiene, and left both browser flows
failing. The independent checker repeated after the guard abort still failed
both flows; that diagnostic is not counted as native acceptance. Both arms had
model completion claims contradicted by independent checks; the controller did
not promote either claim to acceptance.

During the candidate's final repair, whole-host swap grew by 740,619,714 bytes,
exceeding the unchanged 512-MiB daily-use budget. The guard stopped it and
verified that the owned runtime settled. No guard threshold was changed. This
single unbalanced pair cannot prove that the feedback change caused the swap
growth or any quality difference. Accepted work per generation-hour was zero
for both arms. The candidate nonetheless fails the preregistered
no-extra-guard-stop gate under this occupied-host trial. The reverse-order
pair was **not run**: it could not rescue that gate, the model cache and host
swap state had changed, and the Mac was on battery during sustained generation.
The unused prepared workspaces contain no model attempts.

**Decision: reject V1 and change approach.** The candidate controller edit and
its fixture test were reverted; the net product-code diff is empty. Only the
common research-driver ability to use the existing daily-use guard remains.
Released v1.0.0 and the installed owner profile were never changed. Full raw
traces, exported sessions, browser check reports and source snapshots are in
the local ignored `evals/runs/verification-feedback-v1-20261002/` archive;
its SHA-256 manifest is
`d7be3575e1c1f28b117a637a286ba3aa0e77d6814bfd38abfd43618ca94d228b`.
This is a public development failure, not a protected validation result. The
remaining H1, protected holdout, Harbor, long-horizon and frontier-comparator
gates remain unqualified.
