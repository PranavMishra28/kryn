# Local-only campaign outcome, 2026-10-04

**NO DEMONSTRATED UPLIFT.** The corrected frozen SWE-bench campaign finished
22 terminal arms across 11 tasks. Independent raw-evidence adjudication admitted
only **three matched pairs: KRYN 0/3, native OpenCode 2/3**. Eight pairs were
excluded. The paired difference is −66.7 percentage points, with a 10,000-resample
95% percentile interval of [−100, 0] percentage points. This small, attrition-heavy
subset neither qualifies frontier adjacency nor establishes a general model or
hardware ceiling. Released v1.0.0 remains the unchanged supervised product.

## Controls and authoritative evidence

Both arms used OpenCode 2.0.10, local Qwen3.5-9B-6bit through oMLX 0.6.4,
96K configured context, matching tool schemas and effective Agent permissions,
a 900-second task limit, and the official SWE-bench grader. KRYN added its product
plugin and guidance. The frozen source is `18c0f7da1bcaa5d338154fe67e779a9c35f5d688`;
manifest SHA-256 is
`9da8682ec20c87e787d58241ddeb27724dd700a595917fc5eb04dc59731da4b9`.
These bytes were not changed by the later supervision or reporting corrections.

The predeclared independent auditor verified raw receipts, patch/grader hashes,
gold results, local generation, matching controls, resource telemetry and owned
process settlement. Its completed `independent-audit.json` SHA-256 is
`755f4ea44a9e1d5688aeffdf4e53cb8c5d391dfdfc424b1e33c0972ae6d79a2c`.
It is authoritative for the counts above. All raw traces and interrupted archives
remain in the owner's private `kryn-research-private` evidence store, under
`swebench-controller-corrected-20261004-remaining-v3` and its durable-supervisor
state. They are not a public full-suite reproduction bundle.

The original controller report provisionally admitted five pairs (KRYN 0/native 2).
Its aggregate omitted the existing-test-edit exclusion, admitting two extra
failed pairs and diluting the difference. The independent auditor correctly
excluded them. A prospective reporting fix now requires explicitly empty
`edited_test_paths` in both receipts; a clean timeout remains a scoreable failure.
The original report is retained unchanged at SHA-256
`7011d6620d701916cfda38ececfc71f5dbfd37633c81b931ae9bba51fcdf4aeb`.
The preliminary aggregate still cannot replace independent raw-evidence auditing.

## Failures and exclusions

| Terminal arm classification | Count | Interpretation |
| --- | ---: | --- |
| Officially graded | 13 | Eight timed out: six KRYN, two native. Three edited existing tests, overlapping some timeout failures. |
| Resource-gated without a clean grade | 4 | Real occupied-host memory stops, including one before generation. |
| Interrupted before a terminal receipt | 3 | Two power interruptions and one host-memory interruption; retained and unscored. |
| Retired after interrupted gold grading | 2 | One pair's oracle was interrupted at a 94 W reading; neither arm was replayed. |

All three independently scoreable KRYN arms timed out. Four KRYN patches across
the campaign resolved in official grading, but every one of those agents timed
out, so none was strictly accepted. Native had three individual strict successes;
one had an interrupted KRYN counterpart and cannot enter the matched score.
Editing existing tests excluded three arms across three different pairs, even
when a grader ran successfully. A graded failure is distinct from unscored
attrition; neither is silently converted to a pass.

The completion failures justify a focused environment/termination investigation.
The worker environment lacked historical repository dependencies. Compact traces
show repeated test-import/install failures, unavailable SSL inside the sandbox,
and repeated reasoning after a repair was written. In one Django arm the model
created substitute dependency files. Official patch resolution does not certify
artifact hygiene. These observations are failure diagnoses, not a proven causal
explanation of every timeout. Missing dependency setup is a scope caveat shared
by both arms, not permission to discard unfavorable results.

The SSL failure was reproduced without inference and corrected prospectively in
the research runner. Its tool manifest now binds Python's OpenSSL library hashes
as well as the existing tools. The sandbox allows only those exact library files
and metadata for verified Homebrew install-name aliases. Before prompting, the
runner checks SSL and pytest inside the actual child boundary. A paired no-model
canary passed in both OpenCode configurations while synthetic hidden-file access,
library-directory listing and non-loopback networking remained denied. Its private
receipt SHA-256 is
`d7456ba80354c51d1b8e721aee64e076c541d6218011032316089421e6df189d`.
This does not permit package downloads or supply historical repo dependencies.

Complete occupied-host cost and false-completion rates are not established by
these counts. Interrupted arms lack complete terminal timing; missing telemetry
stays unknown. A native-completed but oracle-failed turn is not, by itself, proof
of a false completion claim without checking its final statement.

## Current development decision, 2026-10-06 UTC

The follow-up campaign has **not qualified the PR candidate for daily use or
release**. Engineering is handed off in PR #242 for owner review and testing.
The measured ceiling is supervised local work
with intermittent public-test success and unresolved protocol, UI and resource
failures. This is neither autonomous acceptance nor a general hardware/model
ceiling. Released v1 qualification applies to its original artifact, not this PR.

Two fresh 9B coding workflows stopped on host memory pressure before any completed
model response, tool, test or write. A separate, private 4B model was subsequently
downloaded and screened at 32K context with an 8-GiB ceiling and cache disabled.
The installed 9B profile, owner settings and emergency stops stayed unchanged.

The subsequent runtime-only reserve worker timed out after three hours without
attempting a runtime start. Its 701 samples span 10,795.408 seconds. Raw free
pages ranged from 66,371,584 to 10,991,927,296 bytes; only one sample met the
10,574,847,176-byte reserve, so no 21-sample/five-minute window qualified.
Pressure remained normal and original host checks reported no issue. Swap fell
from 2,060,252,610 to 865,274,429 bytes. These separate counters are not an
available-memory estimate. Normal idle pressure does not prove model-load safety;
the conservative reserve may reject usable cached memory.

Separate retained-evidence review checked raw free-page and swap math, timing,
window resets, the footprint-derived reserve, eight negative projections,
frozen inputs and exact inactive job ownership. Settlement preserved 16 evidence
pins and removed that job; the runtime remains stopped. The review is an author
check, not independent review. No model/task/grader was replayed. Private receipts:

- `native-reserved-runtime-epoch-20261005-v3-settlement.json`:
  `a688ba7df7832b159bd3d742275f1f9fe7150106aa8c313288b7f6af8b878142`.
- `native-reserved-runtime-epoch-20261005-v3-settlement-review.json`:
  `18978f781e5b21e8cce1afcc9dc7e569d53f6dacb638029f688ecde967ba12bd`.

Do not repeat the failed tasks or relaunch the unchanged reserve wait. A future
live attempt needs a materially different, prospectively reviewed safe admission
or profile. Keep the original emergency stops and distinguish supervised policy
from strict research policy; neither can retrospectively upgrade a failure.
No unrelated application may be closed to manufacture daily-use fitness.

## Follow-up evidence and retained failures

| Observation | Bounded outcome |
| --- | --- |
| Linux dependency-ready SWE path | Canned isolation/export/official-grader controls passed. Real exposed Django pair tied without uplift; later pressure-interrupted work remained unscored. Never pool Linux and macOS results. |
| Bounded pytest pair | KRYN timed out at 900 seconds and failed official grading; native edited tests and remained unscored. |
| CLI/API continuity | Two CLI policy attempts failed. A later 16-turn diagnostic passed with one CLI and 15 API turns; this is not active endurance or final-artifact continuity qualification. |
| Native UI | Controls and one bounded UI diagnostic passed; counter, form, duration and length workflows retained strict failures. Canned handoff/repair/routing controls are mechanism evidence only. |
| Rollup and slugs | Strict failures retained despite later public-test output; extra shell actions, truncated evidence or stale reads prevented acceptance. |
| Line codec | 300-second timeout; nine attempts, eight completed responses. Exact owned runtime stopped; partial evidence retained. |
| Interval union | Eight public checks and five reconciled local requests passed. No independent functional grade or endurance claim. |
| Git observation | Strict failure for truncated output/missing header; eight complete raw records distinguished four Apple Git shim failures from four direct CLT successes. |
| Git feedback | Fixed broken/repaired syntax control passed using three tools and four canned replies. Zero model inference; no repository-inspection warning. |
| Quantities and batches | One interrupted relay attempt each, zero completed responses; host-pressure stops. Detached candidate images and empty mounts retained; no grading or capture claimed. |
| Stopped-host observer | 21 samples over 312.330 seconds passed observation-only predicates. No readiness or load-safety claim. |
| Conservative reserve | Three-hour admission timeout, no runtime start; verified settlement above. |
| Isolated 4B load/unload | Passed 65.43 seconds of loaded idle with zero inference and no swap growth; maximum sampled footprint 3.65 GB. Short fit only. |
| 4B labels coding | Strict failure: unavailable bare Node command before the required absolute command. Recovered to eight public test passes; six requests. No autonomous acceptance. |
| 4B parcel UI | Strict failure: two guessed selectors failed before two successful clicks. Browser observed Ready → Dispatched → Delivered; unchanged page, empty patch, eleven requests. |
| 4B handoff continuity | Strict failure: report omitted the required UNVERIFIED label. Three requests; no compaction, restart or operator edit reached. |
| 4B dispatch mechanics | Strict failure: four invented `/workspace` reads were denied before valid reads; test command also differed from the declared command. Seven requests; no compaction or restart reached. |

All earlier failed preparations, interrupted attempts, missing usage receipts and
failed review writers remain retained. Settlement verifies preservation and
ownership; it never changes an experiment's outcome.

All four 4B task attempts ended with verified owned runtime shutdown and preserved
detached images. Their resource samples stayed at normal pressure with no swap
growth; sampled inference footprints were approximately 6.2–6.4 GB. These are
short-run observations, not daily-use or endurance qualification. Labels and
parcel retained usage matched post-generation runtime counters; dispatch also
preserved the complete first-stage export before checking. Handoff did not
retain a complete export for usage reconciliation. None reached the worker's
final successful reconciliation/unload sequence.

Independent bounded mechanism reviews found no demonstrated product defect in
the later tool/path failures. Model recovery does not upgrade the frozen strict
outcomes. No further unchanged trials are scheduled. The owner can perform fresh
[supervised tests](../docs/testing.md), preserving interventions and failed
attempts separately. The research heartbeat is paused for this handoff.

The final dispatch terminal review is bound by SHA-256
`2a37c852c9a6ff964b9ccca28871cc5e60864bd99b645f20b34d276fc9b0b579`;
its separate settlement preserved 81 evidence pins and removed the inactive job
(`35093697d72542678a783e135873670d1f5b0340c6bddfc1a987ce86b9275b35`).
Private source, model and owner-setting pins were rechecked. Full traces remain
private; this summary is not a public reproduction bundle.

The initial 65 W campaign reached a recorded 15% battery emergency stop. Later
owned supervisor recovery was observed after power and memory interruptions.
That is lifecycle evidence, not proof of coding quality or permission to lower
power thresholds. Full per-phase receipts and policies remain in the archive.

## Candidate validation and remaining gates

Product revision `e9bec021bcf85a43c12dbb27eea126e75e1e64ab` passed 220 setup
checks, 216 research checks (two skips), 88 Node checks, native/frozen offline
checks, a clean-source isolated package smoke and documentation/secret checks.
CI run 37398929900 for `8d4581d` passed its complete 13-step job. An independent
source review found no P1/P2 issue in the reviewed product/boundary paths; its
sole trailing-newline finding was fixed. That review did not cover every research
line or establish live acceptance. These checks were not replayed for settlement.
Cancelled CI 37366560264 remains failed with zero executed steps and unknown cause.

Fresh representative coding/UI acceptance, compaction/restart continuity,
45–60 minutes of **active** supervised use and
final-artifact install/rollback remain unmet for this candidate. The resource
wait does not count as endurance. Keep version 1.0.0 and the owner installation
unchanged. No merge, release, tag, benchmark uplift or frontier-quality claim.
The [supervised contract](../docs/v1-qualification.md) remains the release gate.

## Full immutable checkpoint history

Repeated checkpoint narratives were consolidated here for reviewability. The
[complete pre-settlement history](https://github.com/PranavMishra28/kryn/blob/f712718f00c8f0a162fb1911140509a345d7ad2c/research/LOCAL_CAMPAIGN_2026-10-04.md)
preserves every earlier result, protocol revision and failure reference in Git.
Raw private traces, images, mounts and hash-bound receipts remain in the owner's
private evidence store. Historical “active” and “next” statements in that archive
are superseded by the current decision above.
