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

## Container generation handoff checkpoint

The prospective Linux path now preserves direct OpenCode exit status, native
root/child ownership and completion, exact stopped-worker source export, full
primary request controls, and separate official candidate grading. Frozen canned
controls at source-map SHA-256
`d0419b87442c33cc03433aa0f2e6ade0c956a559f8de885d79cdf325d4427537`
(canonical compact JSON)
cover 92 source files. They do not perform model inference or qualify coding.

Both arms completed a parent/general-subagent run with two verified native
sessions, identical exported patches and matching sampler/tool-schema controls.
Their 14 and 15 resource samples were normal with zero swap growth. A third
control timed out deliberately: its direct exit remains absent, native generation
remains incomplete, and the exact partial patch was preserved before resource
cleanup. Its 16 resource samples were normal with zero swap growth.

The exact timeout patch entered the official candidate grader under manifest
`b25f4bb050621570345e7d9a57330fe3570bd6639d78ce217382605f4171f2c8`.
Grading was valid and unresolved, with zero infrastructure/errors, eight normal
resource samples, zero swap growth and settled ownership. The result retains
`generation_completed=false`, `generation_intervention=timeout` and
`model_generation=false`; official grading does not emit agent acceptance.

The first child controls remain failed: their checker incorrectly required one
tool schema for both root and native general child. The corrected source pins
the exact two observed catalogs and rejects unknown catalogs or sampler drift.
It also closes supplied/missing token-cap and multiple-choice budget gaps,
detects observed root-policy changes between tool calls, and continues other
owned cleanup when retained-worker inspection fails.

Real development work requires a frozen sequential controller and independent
adjudicator. The subsequent checkpoint below implements these mechanics;
their runtime admission precedes model generation. The completed v3 supervisor
and evidence remain untouched. A positive accepted model-generated repair is
still required before fresh validation or promotion.

Independent no-model review passed nine composite checks across 166 cited raw
and source hashes. It re-read the native root/child exports and policy events,
verified exact applied patches, re-parsed coverage of every official expected
test, and checked actual owned-resource absence. Its receipt is
`c83d186da523825f7785a0fa2fe41ae230ee60c61cc93198541cf0ba38fecbdd`.
The first auditor receipt remains failed because it incorrectly expected a
standalone prompt in the grader directory; the corrected audit checks the
pinned generation prompt instead. No arm or grader was replayed.

Full local checks passed 216 setup, 148 research (two skips) and 87 Node tests;
the pinned evaluator additionally passed 28 focused checks. Clean-source package
smoke passed at `fe354db`. The 39-commit PR-range Gitleaks scan found no findings;
the ten working-tree findings remain classified JSON SHA-256 mappings. These
checks do not change the failed quality ladder or authorize publication.

## Durable container controller checkpoint

Source `b8ed5c4` adds sequential generation/grading, exclusive stage markers,
append-only recovery exports, terminal no-change outcomes and independent strict
adjudication. The frozen candidate covers 98 source files with canonical map
SHA-256 `dc840994117144a4e17eb177020d3be225698a3418015f6c4c1da692eb2e13fe`.
It uses the existing resource guards and native session engine. Controller exits
cannot replay a started arm or grader. A recovered interruption remains unscored.

The first controller canary failed before grading: Python 3.11 rejected the TAR
importer's newer `stream` option, and recovery rejected a legitimate owned
route-control container. Both causes were fixed prospectively. The failed source
snapshot and receipts remain immutable; its retained work was separately exported
and cleaned up as unscored. Explicit TAR iteration bounds retained member metadata
on Python 3.11, which CI now tests as well as the package runtime.

The revised normal canned pair completes both root/general-child runs, safe
exports and valid unresolved official grades. An actual battery transition
paused before the next arm; launchd ownership preserved the terminal native
receipt and resumed the unstarted arm after safe power returned. No arm replayed.

The forced-crash control recorded one controller SIGKILL. Launchd restarted it,
recorded the interrupted native arm as unscored, recovered its stopped-worker
export, and continued to the next arm. The original test observer failed because
it queried the old PID while launchd still reported it during restart. This
observer failure remains retained. A separate read-only observation bound the
actual replacement identity and final recovery evidence. Independent current-source
admission passed with receipt SHA-256
`bc03b8ca59c6868aaa2a49d0fea900f1a5c65989ce5818375a896849e9dc1da1`.
It explicitly retains `original_probe_passed=false`, verifies one SIGKILL and
the replacement PID, three completed official grades, the interrupted arm's
unscored export, and absence of seven owner labels and 19 recorded resource IDs.
The original observer remains failed. Temporary control jobs were removed without
changing their evidence.

Full local checks at `b8ed5c4` passed 216 setup, 183 research (two skips) and 87 Node
tests. The evaluator Python 3.11 passed all 182 research tests present before the
route-control regression was added; that regression also passed independently.
Clean-source package smoke and GitHub CI (including Python 3.11 research tests)
passed. The 41-commit PR-range secret scan found zero findings.

The separate real development pair was preregistered after this admission and
independent protocol review, under manifest SHA-256
`7622212c50dbefb91d6de47abc8b51b429cceb10d68d302dcc871cd6eb4fedbf`.
Its dedicated launchd controller is installed to wait for safe admission,
run each arm once, grade exact candidates, and apply the frozen adjudicator.
It uses an explicitly exposed
public canary outside the earlier six-task subset, never a protected task or v3
replay. Native and KRYN each receive one 900-second local 9B arm. Clean timeouts
remain strict failures even if patches resolve; safety, ownership, wire and test
integrity failures remain unscored. No new release or autonomous quality claim
is admitted by these infrastructure checks.

## First real container development result

The separately preregistered pair above completed. Both native OpenCode and
KRYN achieved strict acceptance: native completion, an exact exported patch,
valid official resolution, full recorded test coverage, unchanged wire/policy
controls and settled ownership. Native took 310.144 seconds and 28 requests;
KRYN took 540.470 seconds and 38 requests. All recorded samples had normal
host pressure and AC power, with zero swap growth. This is one exposed
development task and an acceptance tie, **not demonstrated KRYN uplift**.
The observed time difference does not establish a causal plugin cost.

The frozen adjudication SHA-256 is
`a58d5fe8d7295e7f5cdb5d5f6dcb4ed9a745c19e7a82f87e6e617134506338a1`.
Independent completion review rehashed the 98 source inputs, evaluator, sealed
protocol, both arm receipts and raw official results, and independently parsed
coverage of all expected tests. Its receipt is
`b54485c3d2a66e109219da6e6dfc71665351afd4ac7d2bf2454debfa1a985a70`.
The inactive launchd job was removed after confirming resource absence;
329 campaign JSON receipts and all frozen source hashes remained unchanged.
Neither the final auditor nor benchmark tests were rerun.

The next bounded development comparisons are a reverse-order repetition of this
completed task, followed by two already exposed public tasks from different
cached repositories. Selection is for order coverage and dependency diversity,
not historical outcomes or presumed prompt difficulty. Each needs its own
sealed provenance and admitted worker/grader environment before inference.
They are development work, not fresh validation or protected holdout.

The runner now accepts either exact two-arm order and verifies actual chronology
against the frozen order. An order mismatch remains unscored. This changes no
model, product policy, safety limit or acceptance predicate. A reverse-order
canned control must pass before a reverse-order real pair starts. The earlier
macOS v3 result stays separate and unchanged; broader validation, sustained
coding/UI and truthful final product scope remain open.

At source `18f3988`, full checks pass 216 setup, 186 research (two skips) and
87 Node tests. Evaluator Python 3.11 passes the same 186 research tests with one
skip; clean-source package smoke passes. Independent order-change review found
no blocker, and a 43-commit PR-range Gitleaks scan found no findings.

The first reversed-order canned control did **not** pass admission. AC power
dropped during KRYN startup before any synthetic inference request. The unchanged
guard stopped generation, retained its stopped worker for safe export, and the
existing controller waits to finish recovery. The failed independent receipt is
`553704d18f3e6d64aceeb7e897443ceb106441557d7aa3d792d156ce2e9cc56a`.
It remains failed even after cleanup; no coding capability or code defect is
inferred from this power interruption. The unexecuted real-pair preparer that
required this admission is retired.

A separate prospective no-model control is sealed with the same source and
controls, plus explicit hashes of the interrupted attempt. Its handoff must
verify the prior terminal receipts and actual owned-resource absence before
starting. No further repetition is automatic. A passing independent admission
and new real-pair preregistration still precede any additional model generation.

Safe power returned during recovery, but the stopped worker's ownership/size
check then rejected an inspection. The frozen check did not retain that response,
so the historical cause is unknown. Subsequent read-only observations show the
expected owner, stopped state and 4-KiB writable layer; they do not explain or
erase the failed check. The queued control correctly refused to advance when
its predecessor entered `needs_action`. That queue failed closed, and its
unstarted replacement control is retired. No additional model arm ran.

The prospective worker change closes this diagnostic gap: a failed usage check
now retains bounded ID/owner/size metadata and distinguishes ownership mismatch,
invalid or missing size telemetry, and exceeding the existing 4-GiB cap. Unknown
sizes still fail; negative sizes also fail as unknown. There is no automatic
retry or cap increase. Credential/environment fields are excluded. Separately
guarded recovery preserves stopped work as unscored; it cannot turn the failed
admission into a pass. A new source-frozen no-model admission is required before
the next real comparison.

A second recovery attempt encountered the same rejection and remains failed.
The unlaunched durable recovery wrapper was retired instead of repeating it.
Read-only diagnosis then reproduced missing `SizeRw` in both the CLI and direct
Engine API 1.56 response for the exact stopped worker. ID, owner and image still
matched. On the same Docker endpoint, API 1.45 returned an integer 4,096 bytes;
the exact-ID list endpoint independently returned that value. This establishes
an observed API compatibility difference, not the daemon's internal cause or
the contents of earlier unrecorded responses.

The prospective correction pins **only** the sized-inspect subprocess to the
verified API 1.45 schema. It preserves the selected
Docker context, all other process environment, the strict integer requirement
and the unchanged 4-GiB limit. There is no retry or alternate-size fallback.
The scoped CLI confirmation receipt is
`a1048aec47335ddd64f66b43efd2620c10b03c112d275833e4414e6376473537`.
Recovery with this correction needs a separately pinned, unscored adapter;
the frozen failed source and original receipts remain unchanged. Neither that
cleanup nor read-only telemetry qualifies the next model comparison.

That separately pinned recovery has now passed independent verification: both
98-file source maps, all 13 original/prior receipts, 6,881 exported entries and
10,092 TAR members match. All recorded container/network IDs, reserved names
and owner labels are absent. Native never started; the original failures remain
unchanged and unscored. The independent settlement receipt is
`4a3a52d6dd9412bfb3b6e5a9ec88dbf303ea931ee47b2a06919fbc1d4e6b7e41`.
The inactive recovery job was removed after verification.

A new reverse-order no-model controller admission is sealed at source `ff2ff5a`.
Its manifest is `4ecdb6c40f6590c77326046617bc61d7b20b25f656c2fc5ba2a986e296d0c478`;
independent prelaunch review verifies inherited canned root/child actions,
prompt, image, wire controls, budgets and grader template, plus explicit failed
attempt and unscored-settlement provenance. It is a new prospective control,
not a replay or a successful admission yet. Source `ff2ff5a` passes full checks
(216 setup, 189 research with two skips, 87 Node), evaluator Python 3.11 research
checks, clean package smoke and GitHub CI. A 46-commit branch scan has no Gitleaks
findings. No additional model quality claim follows from these checks.

The new reverse-order control also failed admission. Both canned agents
completed their root/child actions, but the parent guard stopped their source
exports after missing telemetry. The KRYN interruption recorded no listener;
the native interruption recorded neither power nor a listener in both samplers.
Adjacent samples had normal pressure, unchanged swap and the same runtime PID.
A bounded power-log inspection found no corresponding sleep/wake transition;
this does not establish uninterrupted execution or the missing commands' cause.
The original query exit status and timing were not retained. Native diagnosis
receipt: `5667f9fe81f782230eee5afe245b4f106494c93aa61378c5c16bc5837040704a`.
These arms remain unscored and are not replayed. Recovery preserves their source
and settles only their owned resources. No grader or real model ran.

Prospective resource samples now record bounded command status, return code,
elapsed time and output byte counts for the four existing telemetry queries.
They capture no new raw output, command arguments or exception text. Each query
still runs once with the same three-second timeout; missing telemetry still
stops immediately and stays latched. This closes an observability gap, not a
proven runtime fix. The next diagnostic isolates export and resource sampling
without running another agent or grader; another unchanged full control is
not justified. Further real development remains gated.

The completed controller's frozen independent audit is failed:
`904d21f9c882079c0e0db74fa76076915428c3be4e2843f2e12e479bfc7e4eb5`.
Separate cleanup verification checks both recovered archives and 6,882 inventory
entries per arm, all original source/receipt pins, no grader launch, and absence
of each arm's three containers and one network. The inactive controller job was
removed without changing evidence. Cleanup-only receipt:
`d2b8bf68d77a3bf68a4c4277898359a8e73bc4278c724b0c4f3fa750c2c2a8a5`.

Diagnostics source `9927229` passes GitHub CI, clean-source package smoke,
independent review and a 48-commit Gitleaks scan with no findings. Local suites
passed 220 setup, 189 research (two skips) and 87 Node tests; evaluator Python
3.11 passed 189 research tests (one skip). The shell logging wrapper failed
after those suites completed because it assigned zsh's read-only `status`
variable. That wrapper failure and the successful test logs remain retained;
the later exact-source CI passed without that wrapper.

The isolated TAR-only diagnostic completed in 10.514 seconds using the frozen
`9927229` source and the exact recovered native archive. Parent/child guards
recorded ten normal samples; all 40 telemetry queries succeeded, with the
slowest taking 0.066 seconds. The extracted member/byte counts match the
retained archive, the child settled, its disposable capture was removed, and
all eleven original/failure pins remain unchanged. Result receipt:
`804b07908b6da74c698f2b8e9a273ba409ed262c46066036f6ed4747a606115b`.
This did not reproduce the combined stage's missing telemetry and does not
identify its historical cause. The first diagnostic draft was rejected before
launch for a shutdown race; its sealed script and review remain retained. The
corrected draft passed seven mocked shutdown/finalization checks and independent
review before its single execution. No original arm, grader or auditor reran.

The next diagnostic uses the existing full no-model controller with the new
query observations and explicit failed-control/phase-isolation provenance.
It must be separately frozen and independently reviewed before launch. It
changes observability, not safety or task policy; a failed stage remains
unscored, and successful telemetry alone cannot qualify its admission.

The separately frozen full-pipeline diagnostic completed KRYN then native,
including parent/general-child actions and expected negative official grades
with all 1 fail-to-pass and 9 pass-to-pass test identifiers covered. Its
predeclared independent audit passed:
`4471189c55e57edc4cbc9390e2666da50e50f22c12c7d8def6460cc7009ccfb3`.
All eight parent/child generation/grader logs were present: 107 normal samples
and 428 successful queries, with no latched guard failure. The slowest query
took 0.111 seconds. Exact source, prior failures, wire/policy, session completion
and recorded resource absence passed the independent checks.

This is technical diagnostic evidence. The sealed receipt explicitly keeps
`admission_qualified: false`. Neither the cause of the historical telemetry
failure nor a causal fix is established. A separate prospective readiness assessment must
compare the actual evidence with the next real experiment's requirements; it
cannot rewrite the diagnostic or promote it as broad reliability or coding
quality. Original failed controls remain failed.

A separate prospective assessment compared that evidence with one real
reverse-order development pair's requirements. It verified 198 source/evidence
hashes, all inherited worker/grader/image/output/policy admissions and actual
resource absence. Readiness receipt:
`cececc0b2885ef20db6623579736131fa7c818de93b4da842f24f5fdf185d159`.
Its scope is preparation of one guarded comparison, requiring a separately
frozen protocol and review before launch. The diagnostic's original
`admission_qualified: false` remains unchanged. The inactive diagnostic job was
removed without changing evidence; cleanup receipt:
`9d3f94cbada0d83dc09f79ce488b95d07ea8469f00b0422063f2a3450a55bd1a`.

A separate metadata-only screen for the next cached repository stopped on
battery at admission, before any Docker command or ownership allocation. Its
private result writer then failed on a binary-mode JSON write; the empty result
and raw guard sample remain retained, with a separate failure receipt:
`c7fd6434ce79e478c2a22a9da59ab37b2537252196aa59abae38feb9ca4afb34`.
No dependency-readiness conclusion follows, and the second repository probe
remains unrun. Corrected preparation must retain this failed attempt and wait
for safe AC admission; no resource limit changes are justified.

The next real experiment is separately preregistered as one exposed public
reverse-order development repetition. It keeps the completed pair's task,
prompt, image, 9B model, 96K context, full sampler/tool catalogs, official grader,
900-second arm budget, 360-second request limit and 128-call cap; KRYN runs
before native OpenCode. Current frozen source is `9927229`, with the same
98-input map as the successful diagnostic. Manifest:
`7eb0503a2c63e58d04e841c5f717ec64beafe6bf1cb78dc83452729ef3fb75df`.

Independent prelaunch review rehashed 212 source/evidence inputs and approved
only this guarded development pair:
`17ff9c28582db4eeec3821913bff711beaf32b1a33e81042cc6def6299e6d0a2`.
Review caught an ambiguous admission pointer in an unexecuted draft. Its sealed
replacement points generation admission to the separate readiness assessment
and retains the explicitly unqualified diagnostic as provenance; the prior
draft remains retired. A root precheck also initially assumed a generic review
field, failed before executing the preparer, and is retained separately. The
corrected operator check reads the actual approval field without changing the
sealed review or protocol.

Preparation completed once and the existing durable controller is installed
under its own launchd job. Runtime and safety admission remain unchanged; it
waits automatically for adequate AC power. It will not replay interrupted arms.
The predeclared one-shot independent validity audit additionally checks every
parent/child generation/grader resource sample, including a final latched guard
failure. It admits accepted outcomes or clean strict failures only when all
validity requirements pass; unscored evidence cannot enter a matched result.
No result, uplift or production qualification is claimed before completion.
