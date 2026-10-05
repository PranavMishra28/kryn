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

## Operational recovery

The initial 65 W run was safely stopped at the recorded 15% emergency cutoff.
A later wrapper stopped on power drift at eight terminal arms. Its replacement
supervisor now waits durably under launchd, requires three safe observations at
≥120 W AC and ≥40% battery, and stops active work on AC loss or ≤25% battery.
Existing memory, disk and retained-data limits remain unchanged. It can restart
only the identified owned runtime, verifies model/ceiling/idle state, samples
memory independently, and retains a durable cooldown before resumption.
Caffeinate is held only during active work. Documents-folder permission was
explicitly granted; no permission bypass was used.

A forced-crash launchd probe passed. A real battery interruption archived the
active arm and automatically resumed remaining work about 53 seconds later on
140 W AC. A later non-normal-memory sample also stopped and resumed safely.
The power-cycle receipt verifies the interrupted archive and all 18 prior final
receipts; final inspection verified both later archives, the unchanged prior
receipts, clean frozen source, no owned workers or containers, and an idle
runtime. Recovery qualifies this observed lifecycle path, not task quality.

## Decision and next gates

The earlier Harbor baseline admitted six pairs, KRYN 2/native 3, without uplift.
The exposed staged long-workflow pair failed in both arms. The old protected
roster remains retired/unsealed. No fresh protected validation, autonomous
long-horizon qualification, frontier comparison or new release is admitted by
this result.

Keep the single research PR in draft. Python tool and historical-environment
readiness now pass the bounded development screens below. A separate
no-inference diagnostic checked public imports and the existing test-runner entry
point in a pinned official image, with no network, model turn or gold/test patch.
It cannot revise the frozen campaign or establish an agent-quality score.
The exposed Django image passed that import/test-entry screen with network
disabled, a read-only root, a 2-GiB container limit, normal sampled host pressure
and no swap growth. The first diagnostic lost its terminal receipt to a private
cleanup-argument error and is retained as failed; the corrected no-model
diagnostic has receipt SHA-256
`8ae0d3a46be5622e7b54a17320fe4405548a37f1953d3cc9d0bca1f3cfb2e80c`.
That import screen alone did not establish a usable container Agent or an
acceptance result. The subsequent
[container worker screen](CONTAINER_SWE_DEVELOPMENT.md) passed a frozen, canned
OpenCode turn in both arms, including dependency use, observed route isolation,
bounded stopped-worker export, active protected plugin bytes and matching tool
schemas. Independent worker admission passed 40 raw-evidence checks. A separate
official-grader handoff now passes negative and reference controls with exact
patch and parsed-test evidence; an earlier offline-build dependency failure is
retained. Subsequent no-model controls preserve exact output below the official
SDK cap and reject oversized output, and capture six native session-policy
changes/restorations in both arms. The first policy probe's missing persistent
log assumption failed and is retained; the corrected live observer establishes
only its documented public-event scope. These are instrumentation results.
A new development preregistration and frozen generation/adjudication path still
precede model generation.
This changes execution OS and tools and retains separate development provenance.
Preregister any subsequent environment or termination experiment separately on
development tasks. Preserve the completed campaign;
do not replay its interrupted arms or reinterpret it as a new candidate result.
Fresh validation follows only a positive development screen. The remaining
research ladder is not exhausted, so this checkpoint is not the overall Goal's
completion or a demonstrated hard ceiling.
