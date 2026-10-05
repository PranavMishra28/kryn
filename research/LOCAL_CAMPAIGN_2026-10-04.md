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

Preparation completed once and the existing durable controller was installed
under its own launchd job. It waited for adequate AC power without starting an
arm, then was retired before the prospective power-policy change below.
The predeclared one-shot independent validity audit additionally checks every
parent/child generation/grader resource sample, including a final latched guard
failure. It admits accepted outcomes or clean strict failures only when all
validity requirements pass; unscored evidence cannot enter a matched result.
No result, uplift or production qualification is claimed before completion.

Independent preparation continued while that comparison waited safely for AC.
The next image metadata probe now writes exclusive UTF-8 JSON receipts; a pure
check covered successful and failed results and rejected existing files. Its
new manifests bind the preserved failed/unrun attempts and unchanged source,
image, command and 60-second limits. Prelaunch review receipt:
`e811d58e79ebb5a202ab668f48c746345308911d307cc0f78174659bdce612a4`.
Both probes remain unrun. They may execute only after the real comparison has
settled, safe admission passes and each fresh evidence directory still contains
only its sealed manifest. This preparation establishes no dependency or coding
acceptance result.

### Prospective battery-capable campaign policy

The unstarted AC-only reverse-order campaign was retired with its manifest,
source and all immutable inputs unchanged. The first retirement check failed
because graceful shutdown appended a `supervisor_exit` event and updated the
status file. That failed receipt remains retained. A separate read-only addendum
verified exactly those two state changes, the unchanged event prefix, no stage
starts or generation/grading directories, and absence of the controller/job:
`96c87ca32c2bf855a2ebdccca7a2fa78c29761c9f72fd313a210058924940908`.
No task arm was spent; the retired protocol and unused auditor must not run.

The new explicit `battery-capable` policy retains 40% admission, a 25% stop,
known power telemetry, and every existing memory, disk, data and local-runtime
limit. The omitted/default policy remains AC-only. Generation, parent stages,
recovery and grading share the frozen policy and record it in their receipts.
Final guard failures cannot seal successful stages or exports. Independent
adjudication requires bounded power observations spanning resource sampling,
including a final observation, and rejects mismatched policy or invalid charge
data. The pipeline must pass a separately frozen no-model control before a new
real preregistration. An AC-only observation cannot establish battery-at-load
operation, and neither is evidence of model quality or uplift.


The new battery-profile canned pair completed both root/general-child sessions
and both expected unresolved official grades without model inference. Its
original one-shot independent audit failed during ownership observation because
Docker exposes network `Name`, whereas containers expose `Names`. That audit
remains failed and unqualified:
`c93dc17da34f2a00d4cf0ad623679cc1a52c0ccda70d309574819091fc5fc033`.
No controller, arm, grader or original auditor was replayed.

A separately reviewed read-only observer verified absence of eight owned
container IDs/names, two network IDs/names and four owner labels, with all
361 campaign JSON/JSONL files unchanged:
`ddc00c14dc11dd584a7540eb062245799c10bc7613fae3ad2c9fdb9e92a2cf55`.
It qualifies ownership absence only. The inactive launchd job was then removed,
again preserving all 361 files:
`5e7e68f297d0a71cab76530b8dcf63f103b8d428f261ea69b85ac3a2c9d34dc3`.
The separate prospective readiness assessment passed:
`334b696347b761f30ae8e9b17e1ba4d38abec0f6d7085e167a843894c655dd59`.
It rechecked native root/child completion, the exact candidate patch and official
negative grades with one fail-to-pass and nine pass-to-pass tests per arm, all
four process stages, and eight guard logs. All 105 resource samples and 89 power
observations were valid; charge stayed at 90% on AC. Each parent guard was bound
to its process start, launch event and exit. The original failed audit remains
failed. This new assessment permits preparation of one separately preregistered
exposed development pair, with no task-quality or battery-at-load claim.


Final prelaunch review then found a separate test-integrity defect: both patch
classifiers inspected only a diff's destination. A synthetic Git rename of an
existing test to a non-test path escaped both exclusions. The failed review is
retained as `7be69ec862a33f8452aa4ebf37374d3c4d003c068052b02ed15af5064dacdf69`.
The new real-pair preregistration was retired before its campaign directory was
created; no model or grader ran. Its retirement receipt is
`f523a8ab383bcd504e05dba13a8d0f3e8cc1dd7f0bd1351d3f15bd02520853c5`.

Prospective classifiers now validate both old and new paths, deduplicate matching
test paths and continue to allow genuinely new test files. Synthetic Git
regressions cover renames into and out of tests, deletion, modification, new
tests and an invalid old path. Frozen earlier source and receipts stay unchanged.
A new source-specific admission must prove that only these classifiers and their
tests changed, exercise both classifiers and reclassify the retained canned
patches before another real pair is frozen. The completed pipeline's execution,
resource and ownership evidence can be cited for unchanged mechanisms; its old
readiness receipt cannot stand alone as admission for the new source map.


The separate source-delta assessment passed against the corrected source:
`12161a53fd3d16c537abab8405dfb621063de98c98c11f7401571fd4546dc262`.
It verified the exact four-file difference and unchanged AST outside the two
classifiers, plus 67 non-Python runtime assets. Real synthetic Git controls
reproduced the old rename miss and confirmed the correction in both classifiers;
the two archived canned patches remained unchanged and free of test edits.
This is a new, narrowly scoped source admission using the unchanged execution
controls. It does not relabel or rerun any previous audit or campaign.

A separate historical path-only impact screen found neither exact archived patch
from the first completed real pair affected:
`9ffacc252802ae08a70a09bc775dbd91b6d4429c69073ddefd09171440a4bcc2`.
No official tests or original auditors ran, and no previous score changed.


The corrected-source real development protocol passed independent static review:
`29c21e6c0aaaa2f67bb5433ec278c0e2fef829116ba64de905561602a7fa19df`.
It was prepared once, validated against the pinned evaluator and image, and
installed under the existing native launchd controller. Its frozen 98-input source
map is `c042c4c079f28d3bcfb3cc2063e5e0b2ed0b7e84b05c089a90c4dfbd5bfd78fe`;
manifest `7d496c4f56f6a13ba2a26dcc2e005b72c4bf816c5814b59f338918a156c36070`.
Initial activation verified a live controller stabilizing safety admission before
any arm started, receipt
`952ab4c046e3ff662212e3824c6f2ae0af13b76a800b79b61d1a875ea7d467a2`.

This is one exposed public development repetition, KRYN then native, with the
unchanged task, image, model sampler and 900-second arm/360-second request budgets.
It uses the separately frozen battery-capable policy and corrected test exclusion;
interrupted or invalid arms remain unscored. A clean timeout remains a strict
failure even if its patch resolves. The preregistered independent outcome audit
will run once after terminal product adjudication. Activation is not a task-quality
or battery-at-load result; broader validation and release qualification remain open.

An additional root static identity check failed because the new auditor uses a
more specific failure-receipt label. The failed check is retained separately;
exact AST comparison found only that metadata literal changed in the compared
writer, with the guard and request predicates unchanged. The protocol review and
separate diagnosis preserve that distinction. Code `dfe6912` passed the full local
checks, Python 3.11 research compatibility, clean package smoke and GitHub CI run
`37272670062` before this launch.


The pair is now terminal. Product adjudication accepted KRYN's arm after official
resolution and native completion (491.260 seconds, 46 model requests). The native
comparison hit the unchanged host-memory guard after 429.240 seconds and 40
requests; its stopped worker was exported through recovery and remains unscored.
Both parent and worker resource logs recorded warning pressure; sampled swap growth
was zero. These observations establish the guard trigger, not its underlying cause.

The preregistered independent auditor ran once and failed on the latched pressure
failure, receipt
`78b792df9dc5f2947e834a8239523bc71f70cdd87a0ac39e27b0042bab09c46c`.
It admits **no matched score**. Product adjudication
`5d3ee4c81a1c3f24c2e2f90d21d1ef9c65d35ac4af9c1d899fba88502a882211`
and the compact observation
`d7849d6c38bac1161816d113a0f2b13cc98cf8e0e6825b699410ef2f4d6b47af`
remain separate from that failed independent qualification. This result does not
show comparative uplift, a model ceiling, or broader release readiness. The next
work is dependency readiness for the preselected exposed repository slate; this
pair and its failed audit will not be replayed.


Separate recovery and ownership settlement passed after verifying the preserved
export, exact baseline symlinks, archive, terminal receipt links, and actual absence
of every owned container, network, name and label. The exact inactive launchd job
was removed with campaign receipts unchanged, settlement
`f61aff883f27578834689da5b28da58ba6b79b5d1d1f53a97223682f0871b6a9`.
The first root cleanup precheck had rejected legitimate baseline symlinks; its
failure is retained. The corrected checker passed independent review before its
single execution. This qualifies resource cleanup only and leaves the independent
campaign audit failed.


Both preselected repository images now passed one no-model metadata screen each.
The old corrected AC-only probe remains sealed and retired without execution;
the separately sealed v3 probe uses the current source and explicit
`battery-capable` policy. Sphinx and pytest each reported Python 3.9.20, working
SSL and a successful main-package import. Their package versions were respectively
3.0.1 and 4.6.1.dev144+g1aefb24b3.d20260815. No task source or solution was inspected
by Codex, and no model or grader ran in these screens.

Sphinx result: `39ecbbcbfb369cf3117d744871d5c40f4fbd68095fd41b74e777854f36aa11e0`.
Pytest result: `56abbe7f911ebb728c1e38af5606e5c33360d7d0f26d85e2dc8742498729cb44`.
Each screen recorded five normal-pressure resource samples on AC, zero sampled
swap growth and settled cleanup. A separate read-only observation rechecked the
source, commands, guard logs, worker boundary, unchanged evidence and actual
absence of owned IDs and labels:
`5ee1935b045b7f65124973cdd92b3598ecf6c36873b73102cfbd890f7067e8d2`.

The receipt field `dependency_ready` is limited to these interpreter, SSL and
main-package imports. It does not establish complete task dependencies, a
sanitized worker or baseline, official negative/reference grader controls, or
battery operation under load. Those gates remain prerequisites to separate real
preregistrations for the already exposed Sphinx and pytest development cases.
The first metadata guard/writer failure, the retired v2 inputs and the v3 mock
fixture precheck failure remain retained; no started screen was repeated.

Sphinx subsequently passed trusted worker preparation. The sanitized repository
has one commit and the exact original task-base tree, with a complete baseline
file-hash inventory. The first preparation failed because ordinary staging omitted
two ignored tracked files; the separate v2 preparation used forced staging and
proved tree equality. Its result is
`63372f25582d9fe7545a6a8e617e81bfc79ab59c4fa57a6d26f0a6fbb390e135`.
The worker image is
`sha256:1b5d9f87215ab9971ef379f0777197fa32412ba0f3e002952c47b2d2e0d0cc88`.

The Sphinx native-then-KRYN canned controls completed once: each direct CLI exited
zero after six canned requests, including a general child session. Both separate
offline official grades returned the expected negative result with all one
fail-to-pass and twelve pass-to-pass checks covered. The separate deterministic
evidence auditor passed, receipt
`3c51a014fd78072ba7e25ab8a943b9b3370a0683e440356b5e79858b5f97883c`.
Eight resource logs contained 96 valid normal-pressure samples and 83 power
observations, all on AC at 90% battery. The inactive controller job was removed
after actual owned-resource absence and 260 unchanged JSON/JSONL receipts were
verified, cleanup
`422d2cdbf8e2362b0f8dbb23dfce7990392ded01104f790fb8522e0443c75a10`.

A separate Sphinx reference positive control then passed the unchanged official
grader, with complete required test coverage, seven normal-pressure resource
samples, zero sampled swap growth and owned-resource settlement. The reference
patch was handled programmatically and never displayed to Codex or given to a
candidate worker. Its one-shot evidence audit is
`47c95b4a44ceca7b3ac806b0ca9e1c8893b170b654c696ae4a3fdced1328743d`;
inactive-job cleanup preserved all 25 audited JSON/JSONL receipts,
`c133575b9791010e4ae1b7538cdf12f202e895312ae6041e80cb127ebbb23c48`.
The root's static preparation review is distinct from an independent author
review; the deterministic evidence auditor checks the recorded execution.
These controls establish repository-specific readiness, not a model-quality or
battery-at-load result.

Pytest preparation remains unsuccessful. Its v2 attempt removed generated runtime
version metadata during source cleanup and the package import failed. The separate
v3 attempt invoked offline editable packaging before removing history, but failed
on an assumed `src/_pytest/_version.py` path during its metadata hash check.
Neither attempt created a worker image or trusted baseline, ran a model, or ran
a grader. Their failed results remain unchanged, with actual resource absence
verified separately. The v3 result and settlement are respectively
`bc87ad8c7c71752a56cedf6416c49342438f1d079856ab827108ed92642d77d4` and
`b3928bae2a2f46473704c6ca1949d04b63e8b4e5952f39caa4fd60c6ff669545`.
After those two failures, another build requires a different approach based on
measured package-layout metadata; neither failed build will be replayed.

One real Sphinx native-then-KRYN development pair is now prepared and separately
preregistered, manifest
`788a7a40ae104f11a9e685a102ba4647789bd37fa7d82173254e674382764b65`,
predeclaration
`3d2c6860e9a1c264124d1e42d090df0698b40de85e78fd1fa82be2ccc2c5ef2a`.
It retains the current frozen source, full model and wire controls, 900-second
arm and 360-second request budgets, and explicit battery-capable policy.
The terminal evidence auditor is sealed before launch and must run only once
after product adjudication. Preparation is not an execution or accepted outcome.
This previously exposed public task remains development-only; no protected or
fresh-validation claim, pooling with macOS, or release qualification follows.

The native Sphinx attempt subsequently stopped on host memory pressure after
20.844 seconds and one local request. It remains unscored. The controller then
failed during recovery because Docker omitted writable-size telemetry, leaving
the stopped owned worker retained and KRYN unstarted. There is no terminal
adjudication or matched result. The earlier inference that waiting status meant
no arm had started was incorrect; the correction and actual start/exit evidence
are preserved in checkpoint
`4a22a7ec6e63a44626b5a203b948589c6413f869fe96b110e16be5c41e8fbf7e`.

A read-only direct API 1.45 request reproduced the missing size fields,
`6e2dd7a6b97b64c8dda38ec7848e1ec966e6e7f6845b01ce4a694cd3b33e71a7`.
A different, filtered container-list query returned an explicit 33,705,984
writable bytes for that exact stopped ID and owner,
`1d5196dc9e64d0c6773ada24160f7c0e76f7fdef1a002b44a1607dfce2613a65`.
The prospective shared usage check now uses that endpoint, preserves the exact
4-GiB cap, and rejects missing, malformed, ambiguous or foreign results. It passed
a read-only check against the retained worker,
`6bb67c0baf4e8768f79ef245ea1405b68f215503702361bcb654eeaeb004355c`.
This establishes a query compatibility correction, not the cause of host pressure.

A separate guarded recovery is limited to preserving the interrupted worker and
settling its owned resources, with no agent, grader or adjudicator execution.
Its first wrapper stopped before export because the reused canned-control
admission copy lacked the real campaign's pinned adjudicator file. That failure
remains retained; a separate corrected wrapper validated the complete four-file
admission copy before launch. Frozen generation evidence and the failed campaign
status remain unchanged. No unstarted KRYN arm will be launched from this failed
pair. The unused terminal auditor cannot be treated as a completed audit.

Repeated pressure stops in Django and Sphinx require a prospective host-memory
readiness diagnosis before any new real campaign. Their underlying cause remains
unknown. Resource emergency stops, the normally occupied host, local-only task
inference and the remaining research and release gates are unchanged.


The separate Sphinx salvage v2 completed without model or grader execution,
result `7a64659becd4259fd67da2b488790ce4bf8ce7c11704675566913284bbfe2188`.
Settlement `c99fdfc9a703c53334ca11c8f70cb71471d622ec0aa6b8bf40bf6e1142931a2f`
verified all 220 original files unchanged, 3,099 exported inventory files, the
24,472,064-byte archive and exact members, all parent/child/final resource and
power evidence, and actual owned ID/name/label absence. The successful recovery
had five normal resource and four power samples. Only then were the original
failed controller and both inactive salvage jobs removed. The original campaign
still says `needs_action`; it is not adjudicated or accepted. The unstarted KRYN
arm and original unused terminal auditor are retired without execution.

The original pytest layout diagnostic was retired unrun because its gate required
an adjudicated Sphinx pair. Its separately reviewed successor instead binds the
actual unscored settlement and removed jobs. Layout v2 passed,
`57f3b9f4fd44847b848ed2cafc92036436a5baa9d009c099c1d086c6e6e3e42c`:
`src/_pytest/_version.py` is a regular, ignored, untracked 590-byte file with SHA-256
`8098cb642e5cc65d2a29f240915ee3dcba4ed432d932992582ef0e402d9131d9`.
The cached package imports from `/testbed/src`; `setuptools-scm` is absent.
Five normal resource samples and four power observations passed the full guard
checks. Settlement `88256c545a00951ae6354cc1de7122bdb344bd781fd3bde603ed052dc1b13c2d`
verified 44 unchanged evidence/admission files, the frozen source, actual resource
absence and removal of the inactive diagnostic job. This is a metadata diagnostic,
not worker or model-quality admission.

The new guarded pytest preparation v4 preserves only that measured file across
cleanup, verifies its exact bytes, stages only the original tracked roster and
requires the original Git tree plus matching package import. It removes the
unsuccessful metadata-reinstallation step. Script and manifest are respectively
`2e390d98bb33c579e9bc39d42c5314126a12420f667ed9bf87311ad6b29ddd21` and
`921bb804657e7f1e2176dcdbd2aa50acd20647b9f5fbe3228aa8aea8650dbca9`.
Root review `0564f02a334544807dacb58232d7e27b2ba7bb0797d33807e011965019b7da09`
verified all source/input pins and five synthetic Git cases, including missing,
changed, symlinked and tracked metadata rejection. It is not an independent-author
review. An initial synthetic fixture omitted the tracked package directory; its
failure is retained separately and the sealed builder was unchanged. The one-shot
native job was installed with automatic 60-second cooldown and three green
observations, fixed resource guards and no model, task tests or grader. Launch
alone was not a successful preparation result.

Preparation v4 then passed,
`67423e37d83e064960865586cfa855114ec9b0656588b867f88e6761220a04f4`.
Settlement `812ed0c8fe547f84921bb42164c846da337b176fcfa2d5fabbdc785a26d46c14`
verified the exact original Git tree, all 1,007 baseline files, unchanged runtime
metadata, the immutable nonroot image, 18 normal resource samples, 16 power
observations and actual owned-resource absence. All 66 evidence/admission files
remained unchanged when the inactive build job was removed. This qualifies
artifact preparation only.

The separately frozen pytest canned controls v2 exhausted both arms but failed
before any model request or official grade. Each worker could not read the policy
probe: the host's sealed source had mode `0400`, which Docker preserved when
copying it into a nonroot container. Neither native completion nor negative-grade
coverage was established. The preregistered audit ran once and withheld admission,
`1938b6819780372ab90136eb2fd5baeb13207a890a44d88fbc527236b137ac42`.
The `canary_complete` sequence status does not mean the control passed.

Settlement `b43665b00a2f4e0c658cb23cf45a493b3fd7a61192c409ec14bf740e8bac2d73`
verified 126 unchanged JSON/JSONL receipts, both complete exports and archive
member maps, all four resource/power logs and final observations, and actual
owned container/network ID, name and label absence. Only the exact inactive
controller job was removed. Neither arm, grader nor auditor was replayed.

The prospective fix shares policy-probe installation between admission and
generation: it stages the same bytes with mode `0444` before Docker copies them,
leaving the sealed source unchanged. An owner-only-source regression and the full
220 setup / 212 research / 87 Node checks passed; evaluator Python 3.11 also passed
212 research tests. The prospective source and an isolated no-model permission
diagnostic are frozen separately. The first read-only prelaunch check timed out
querying Docker before any diagnostic attempt; its failure is retained. No new
control or quality admission follows from these code checks.

The isolated permission diagnostic then passed and was settled. It reproduced
foreign-owned mode `0400` as unreadable by UID 10001, and measured the identical
mode `0444` copy as readable, nonwritable and importable, with a nonwritable
parent. Five normal resource samples and four power observations passed; all
source/input pins, 63 evidence files and actual owned-resource absence were
verified before removing the inactive job. Result and settlement hashes are
`bed9dbf00d634bf60fbd2c503189258a874e5bb8c400d63efb8423fa6c408174` and
`4d1ffb25b3d2bc434e808ebfd93f495a28e61b7536dc7c76163f08835666e342`.
This was a permission diagnostic, not worker or quality admission.

An explicit source/image compatibility check bound the new 98-file source to the
unchanged prepared image and all 1,007 baseline files. The only source changes
were the shared probe installer, its two callers and its regression; guards,
wire, policy bytes, export and grading stayed unchanged. Compatibility receipt
`3c98bbcbebf312063523ebc3dc7727ec03e659bcc9aa2f234d16fce403b6f24f`
allowed a new separately frozen pytest canned protocol, preserving failed v2.

The corrected-source canned controls v3 passed KRYN then native: each completed
the direct CLI and root/general-child sessions with six fixed synthetic calls,
an identical two-path canned patch, and the expected negative official grade.
Both grades covered the required two fail-to-pass and 86 pass-to-pass tests.
The preregistered auditor ran once and passed,
`88d6fa96d7165f4009cdc2d9664c8febbbe951989097a523e849bd10665b4f93`.
Eight parent/child guard logs covered 94 normal resource samples and 77 power
observations, all on AC, with no sampled swap growth. Settlement
`23ee1ddb469d958e011af08d53cd1d6693d0bc1e1d65871d791dda101acc5158`
verified all 256 evidence receipts unchanged and actual IDs, names and labels
absent for all four owners before removing only the inactive v3 controller.
No model ran and this is not a quality score or battery-at-load qualification.

A separate pytest reference positive control is now prepared and preregistered
on the same corrected source and prepared image. The official reference patch
was copied privately without displaying it or supplying it to a candidate.
Manifest and predeclaration hashes are
`dbf10c0c59bcfb827e7e4b3c324b2fcce4f7a6ed7b197fbd43c3d6b76e28388f` and
`002a543de3d50c9a51ea3a112b9212a1471253ebb78c8fe1cb44245d76a5ae4e`.
Root static review
`2aa4fe8f45f1bb2abf03fa8e3eb37a2ad300495e4b5b3dea1c5552e3a87d7062`
checked exact source/input pins, unchanged auditor predicates and the existing
admission loop; it is not an independent-author review. The one-shot native job
waited for 60 seconds and three green observations before invoking the unchanged
guarded official grader. The reference grade passed in 14.244 seconds, with full
two fail-to-pass and 86 pass-to-pass coverage. The once-only audit
`007fe3cf040f0cf2966d33829402ce68a7ee2feaf3b1fc46b5cd20bc718b9b2e`
verified eight normal resource samples, six valid AC power observations and all
final guards. Settlement
`e5ccc90c5c71c8bb53dbe7477af8d6311c520da18934faa5ece55d940082149f`
verified 57 pinned files unchanged and actual owned-resource absence before
removing the inactive job. This establishes repository control validity only.
The unchanged official grader runs as root inside its offline container;
candidate workers use UID 10001. No grade, auditor or control was replayed.

The prospective no-generation loaded-idle diagnostic then passed: one local
model load, 180.214 seconds of idle observations and one unload. All 13 loaded
status records preserved request/token counters and reported 8,597,826,742 bytes
of model memory. All 87 resource observations had normal pressure and zero
sampled swap growth; all 75 power observations were valid and on AC at 90%.
Result `cf9e53fefad5eb88036233bde094bd421130b99b6a1e2c17a2dd9817a95f34cb`
and settlement
`7dcc20887f2dcffde355d68f9e330446e8a1b1ed95bb5d9048b1f409a7bd4be8`
bind the complete interval, unchanged source/runtime inputs and 61 pinned files.
The original runtime was idle and unloaded; only the inactive diagnostic job was
removed. No settings, inference requests or unrelated apps were changed.

Two separately frozen single-request diagnostics subsequently passed. The first
used only local oMLX; the second kept an isolated, idle OpenCode/KRYN worker
present. Actual usage was 14,381 prompt / 340 completion tokens in 25.863279
seconds, and 14,383 / 573 in 30.215682 seconds, respectively. Both reconciled
request/token counters exactly and unloaded the model. Their 16 and 19 resource
observations had normal pressure and zero sampled swap growth; their 13 and 16
power observations were valid and on AC. These were fixed synthetic text
requests, with no agent session, tool task, benchmark or grade. Process-wide
physical footprints do not establish model or KV-memory bounds.

The direct-request result
`93c700bed811db7dd0b5f2fb03dd098275645b52a8c52c88fb7ec14ce7b85737`
and settlement
`2b321393c4f2c02b371ff7070fa87427142e9ac30d7c0f7faba9137dd2e08340`
bind 43 unchanged files. The container-presence result
`f53d77e8ebac1024ab7036f69c77538db6befdf5b3adcd0a3599e389fe428e78`
and settlement
`774ee0f3ffc10c26ae4514e9b24e49a7be09f02a91093277b343394d0239e018`
bind 100 unchanged files, complete response/usage reconciliation and actual
owned-container absence. Both inactive jobs were removed. The first
container-presence settlement precheck used the previous job label and failed
before removal; that failure was retained, and a separately reviewed correction
removed only the correct inactive job. No inference was replayed.

The next real local synthetic agent diagnostic **failed**. Its root shell
created a temporary fixture and delegated to one general child. The child read
of that fixture outside the project remained unfinished until the unchanged
900-second CLI timeout. Both owned sessions were interrupted and exported;
there was no repository patch or test edit. Three local requests reconciled
exactly with 14,376 prompt tokens (including cache reads) and 601 completion
tokens. All 421 parent and 419 child resource observations had normal pressure
and zero sampled swap growth; all 370 and 368 power observations were valid and
on AC. This is a timeout failure, not evidence of another pressure stop.

After generation, the runtime reported unloaded idle. The wrapper required a
loaded model at that point, raised an assertion, and stopped its reverified owned
runtime. Result
`1345019fa72bae3fc1615bda5c1dfd084a12b72cc514c5b0b95f761e927a4d42`
remains failed. Separate settlement
`135a57419c6fbb1f1c85ef9dd5685ce96668fb980aa43139ea7ba325daa1fc5f`
verified the complete export archive/member set, all guard finals, 1,299
unchanged files, actual owned-resource absence and the stopped runtime, then
removed only the inactive job. Settlement does not upgrade readiness.

The frozen general-agent policy asks permission for external directories. The
retained CLI source handles permission replies for the root session; the failed
run did not capture the child's pending permission inventory, so the exact
cause remains unproven. A separate no-model diagnostic captured an actual
pending external-directory approval on its owned general child and linked it
to the unfinished read tool. The 60-second timeout and three canned calls were
expected for this diagnostic; no permission reply or policy change occurred.
The separately declared cold start restored a fresh owned runtime with the same
profile. It remained unloaded idle with zero request and token counters. All
79 parent/child resource observations were normal, all 69 power observations
were valid and on AC, and sampled swap growth was zero. Result
`3d0fc451132e86ce2286049083e740ea79712787d956193e3fa81f855f6c6f60`
passed this narrow diagnosis. Settlement
`41071b17d4a76101180a64b21a13b4517a39ad990129b216dbb0f0cbedf7888a`
preserved 1,297 files, verified the complete archive and actual resource absence,
then removed the inactive job. A copied-label settlement precheck failed before
removal and remains retained. The correction derives the exact job from its
pinned launch plist and verifies its program arguments.

The next in-project canned control **failed**. Its root created the fixture and
the child read completed, but the child's shell hash/delete action remained
unfinished at the 90-second timeout. Four canned calls left exactly the known
257-byte synthetic fixture patch, with no test edits. This attempt captured no
pending permission request. Global shell approval and the CLI's root-only reply
handling support an approval hypothesis; the exact cause is unproven. The
runtime remained unloaded idle with zero request/token counters, and all parent
and child resource/power finals passed with normal pressure and zero sampled
swap growth. Result
`73f72f89eb7f114100556081d9a7e2cba880e838007a16ebd03b1dc852e134b7`
remains failed. Separate settlement
`6aa29037a27af861b31434f0ed963371520092b0b2be9d4358fd37611b6f92ee`
verified 1,286 unchanged files, the complete 1,322-member export archive, the
sole known fixture patch and actual owned-resource absence before removing the
inactive job. No task or diagnostic was replayed.

A new local-model protocol narrows the task to a root shell creating and
hash-verifying one in-project fixture, followed by a general child that only
reads it. The earlier successful canned controls covered root writes plus a
read-only child, not child shell execution. This protocol deliberately retains
the fixture and requires its exact 258-byte patch as the sole change, exact tool
sequence, two completed owned sessions, direct CLI success and unchanged wire,
policy, routes and resource limits. Predeclaration
`6d8025f62f8d66ca3f9f737c4b9cb2daad65e5d2e0f9f244cd25498a178767fb`
pins the new prompt and mechanical acceptance. The root author's static/mock
review passed 44 checks; it is not independent-author review. The wrapper
reconciles all owned request and cache-inclusive token deltas before accepting
either loaded idle or already-unloaded idle. It unloads at most once when
loaded, refuses unload and stop on concurrent activity or counter drift, and
retains exact-ownership emergency stops. The single durable job was launched;
an immediate process-verification assertion failed after successful bootstrap,
and a separate observation verified the exact running command without another
bootstrap. Both receipts are retained.

The read-only-child run then completed both owned native sessions and direct
CLI execution in 51.744 seconds, with five local requests and the exact sole
258-byte fixture patch. Its **original literal acceptance failed** because the
root changed Python literal quote style in the shell command. Result
`489ed2dd8636f566c3cdb8100a5c4a6421fc6c2c5175cf402926c4b4dc589315`
remains failed. All 23,809 prompt tokens including native cache accounting and
626 completion tokens reconciled before one model unload. Both parent and child
guard finals passed: 53 normal resource observations, 45 valid AC power
observations and zero sampled swap growth. Separate settlement and quotation
diagnosis
`a9f38b68dc22078552d7282afc502c592eca318007071bd043385badd565450c`
verified canonical shell arguments and identical Python AST, the complete export,
1,301 unchanged files, current runtime idle and actual owned-resource absence,
then removed the inactive job. That diagnosis does not upgrade the exact-text
protocol or general readiness. No task was replayed.

A new larger-input synthetic text diagnostic then passed with an idle isolated
OpenCode/KRYN container present. Its actual usage was 57,406 prompt tokens with
zero cached tokens, 3,080 completion tokens and 60,486 total tokens, taking
148.345 seconds. It made one loopback request and exercised no agent session or
tool. Result
`2100a61a1bc61b44f4795c92ed92cc2b62ea24d03eabcdf712fc55fc1d8f529e`
keeps real-campaign admission false. The exact request and token deltas
reconciled; one unload returned the original runtime to unloaded idle. All 74
resource observations had normal pressure and zero sampled swap growth; all 64
power observations were valid and on AC. The sampled runtime physical-footprint
peak was 15,756,926,152 bytes, a process-wide observation rather than a per-model
or KV-memory measurement.

Separate settlement
`5db5a66ae10bdcaa5796b7a217e4bfcdf13eaa34f2e10ee76a3190d6a2631bcb`
verified full raw-response equality privately, actual usage and receipt hashes,
worker readiness bracketing, isolation and protected plugin, current runtime
identity and idle counters, prior evidence and 107 unchanged pinned files. The
owned container's ID, name and label were absent. Only the inactive job derived
from its pinned plist and exact arguments was removed. The prior wake's compact
observer encountered an empty in-progress output file; it did not alter the
runner or imply a diagnostic failure.

The next preregistered request increases only the fixed synthetic input, requiring
81,920–90,112 actual prompt tokens and zero cached tokens. The upper input bound
plus the unchanged 8,192-token output limit fits the existing 98,304-token
context. Manifest
`80e69f4feffda7d3514f51291d6263e78bf217cd700ecca9b363663929ca661a`
binds the unchanged profile and limits, completed prior settlement, exact input
and initial counters. The author's review passed 47 static/mocked checks,
including unchanged function AST after the declared identity/input-bound
substitutions, counter conflicts, runtime identity changes and cleanup failures;
it is not independent-author review. One durable runner was launched with
unchanged automatic admission and emergency stops. It performs no task inference,
agent tools, benchmark, reference patch, official grade or answer judging.
Child shell approval, task quality, exact full-context consumption, endurance,
general agent readiness and real-comparison admission remain open.

The near-context request completed with **86,078 actual input tokens**, zero
cached tokens, 1,029 completion tokens and 87,107 total tokens in 160.914 seconds.
Result
`18147057f01726a91ceba8fd9eaf5348648edc4b6b998f46b112379ccfd69470`
is passed for this single synthetic memory observation only. All runtime deltas
matched the response; one unload returned the same process to unloaded idle.
All 80 resource observations were normal, all 69 power observations were valid
and on AC, and sampled swap growth was zero. No agent tools, benchmark or answer
judging ran. This does not establish exact full-context consumption, useful
reasoning at that length, endurance or real-campaign admission.

Separate settlement
`e52ab1d3660d0440e03fbe080dc34704ab961a54fd93d3e53e3df142f3d1aa8c`
verified raw-response equality privately, actual usage and operation hashes,
worker readiness/isolation and protected plugin, current runtime identity and
idle counters, prior pins and 114 unchanged files. Actual owned container ID,
name and label were absent before removing the exact inactive job derived from
its pinned plist and arguments. Settlement review passed 11 author checks;
neither review nor settlement is labeled independent-author evidence.

The next no-model diagnostic isolates the unresolved child shell stall. The
retained native CLI source filters automatic permission handling to its root
session. A new fixed root/general-child sequence will create and read one known
in-project fixture, then request a shell hash check. The unchanged bounded
GET-only observer must capture one pending child shell permission whose source
call and message match the exact unfinished tool. The declared 60-second timeout
is expected; the sole exact fixture patch, owned interruption/export/cleanup,
unchanged policy/full wire and unchanged runtime counters are required. It
sends no permission reply, changes no native policy and performs no inference.
Initial counters are seven requests, 167,293 prompt tokens and 4,735 completion
tokens on the existing unloaded idle runtime. Resource limits and automatic
60-second/three-green admission remain unchanged.

The first preparation failed author review on a mistaken prior-module attribute
before any attempt or worker existed. Failure/retirement
`963c8161030ca32451f2fcc811f22a3e33a2a7dc86ecd56012c600d3c18a2569`
preserves that version unrun. The separately prepared V2 uses the explicit
pinned prior-manifest path. Its predeclaration
`f786e5e67d3d2fb767ce16b3ac143f3c8b48a2965705ac86504990dfe8f41e47`
and manifest
`b5b8f810a072f72a87d417c8e18fb5698a19fbec769a9ba15dc526d7a26b691a`
bind this prospective control. Author review
`50da89a1cad83fe7c90b581def2c888872f0968ec0822d2a56309aaaf231e5fd`
passed 25 static/mocked checks, including the actual GET-only observer, foreign
ownership/source rejection and failure retention in the actual wrapper. It ran
no container or inference. Earlier failed controls are not replayed or upgraded;
this diagnostic cannot qualify general agent readiness or task quality.

The child-shell V2 diagnostic completed with result
`0eb6574bf4448dcb4d7d73c5fae86de32d8266b976d814cec8ba8ca02e2e6c19`
and driver
`1eeabae1e457c9a962e1ad5fbc55ab620c71f37094375608c27e5887d2e7109c`.
The GET-only observation captured one owned child shell permission whose source
call and message match the exact unfinished tool. Root creation and child read
completed; the shell and parent delegation were interrupted at the declared
60-second timeout. Four canned calls left only the exact 280-byte fixture patch.
No permission reply, policy edit, model request or grade occurred. Existing
runtime counters stayed at seven requests, 167,293 prompt tokens and 4,735 output
tokens, with the original process unloaded idle. All 80 parent/child resource
observations were normal, all 69 power observations were valid AC at 90%, and
sampled swap growth was zero. This establishes this control's pending permission,
not the exact cause of earlier failures or successful child-shell execution.

Separate once-only settlement
`421b8f9560afee9042212f3508748fe4a89d53e51dd5afe10eb02332996bd500`
verified the permission/export link, full policy/catalog/plugin/wire evidence,
all guard finals, the 5,753,856-byte archive and exact member map, 1,295 unchanged
files, and actual owned IDs/names/labels absent. It removed only the exact
inactive job derived from the pinned plist and arguments. Author review passed
11 checks with the actual settlement prechecks and intercepted job removal;
no old runner, review, task or grader was replayed.

The prospectively declared local-model diagnostic extended the supported read-only
child path to parent resumption. A new synthetic parent creates a unique fixture,
delegates one read to a general child, then verifies the fixture and writes a
completion receipt. Only the exact 538-byte two-file patch is accepted. Shell
acceptance requires exactly `python -c` with one code argument and the same full
Python AST, permitting equivalent quotation/whitespace prospectively. Added
commands, paths, values and shell syntax fail. The old literal-match failure is
unchanged. No repository coding problem, reference patch or grader is involved.

Predeclaration
`4813b9213d72c5f9af7b5004b8e3a2cd198c8b580d32b910be74f0e904db2666`
and manifest
`81a4383b9e913afb4fa736a222fa3443c12ad11849a3a8b84144cef42c8d915c`
bind the new task, current source/runtime, prior settlements and exact fixtures.
Runner
`90b184f7ce0aed0dc61300034dc9ff510e18ae947719b4d9c5d01977b60e547c`
retains the unchanged generation path, native policy, wire, 900-second task and
360-second request limits, 60-second/three-green admission and resource stops.
Actual owned request/token counters must reconcile before at most one unload;
concurrent requests, counter drift or identity changes withhold settlement and
refuse conflicting runtime actions. Author review
`e388cc925f991c97903e4d197f9810c5f301766c727d0da1a7de69901626451e`
passed 53 static/mocked checks, including actual fixed commands in isolated
temporary files, AST-equivalence acceptance and injection rejection, owned
parent/child tool order and wrapper failure cases. No live inference or container
ran during review. This remains a synthetic agent diagnostic, not broad task
quality, child-shell approval, endurance or real-campaign admission.

The parent-resume diagnostic completed successfully with result
`82b3e11471d4f5d20700983d80ed23d37279b160ffdbe42c937950dea9a07529`
and driver
`e198f916623b644f15fc7e4b460b30f034dbf2be63ff37fcc4a1f4e36af245e4`.
The CLI and both sessions completed in 66.199 seconds. Root tools were shell,
subagent, shell; the child performed only its declared read. Both shell commands
met the prospective Python-AST criterion, and the exact 538-byte patch matched.
Six local requests used 31,964 prompt and 928 completion tokens. Exact runtime
counters advanced from 7/167,293/4,735 to 13/199,257/5,663; one unload returned
the same process to idle. All 66 resource and 57 AC power observations passed,
with zero sampled swap growth. The original literal-match failure stays failed.

Once-only settlement
`b5daef0998baa6195dcdbd48a2dda631bdbab74cd1fd8e4b8cf7080b3b505a84`
verified all native tool, policy, wire, usage and guard evidence, the complete
5,754,880-byte archive and member map, 1,301 unchanged files, and actual owned
IDs/names/labels absent before removing only the inactive job. Settlement review
`a7ca55f64dd3914cd136566d0b323416b4501d29b43f7ca184890ca4c3d52608`
passed 12 author checks with actual prechecks and intercepted job removal. This
is evidence for one synthetic parent-resume path, not task quality or endurance.

A new, separate prospective readiness decision
`f612870add66b5e68e65ddaf7ef5fad586fbc8ceb390ca1fee8317b847a6ed8f`
permits exactly one bounded pytest development pair. It rechecks the settled
repository controls, source/image compatibility, memory diagnostics and parent
resumption, including 1,725 evidence files and the original unloaded idle
runtime at exact counters. Review
`86f765408711e1debe176fa64b0caf3a6239a7f9b685d1a2576811fb4f932e76`
passed 12 author checks. Its first review failed in a mock fixture after the
read-only verification, before campaign preparation or inference; failure
`a4d0d312fc07d7277a81dc9783cf5571c69148bebab89d676433f0cf0665af93`
is retained, and the corrected review used an explicit identity mock. No failed
runner, arm, grader or review was replayed.

The new pair uses the already exposed pytest task from the original slate,
KRYN then native. Manifest
`6ca2314801c517168a302b22bb1c3c4d8deba953874664a5df4e8a6eaf8e6aae`
and predeclaration
`55288be3a6857e299c6d6b697db485a92639dc750ab5a8e601dd1793d1aadb8a`
pin the original problem prompt, current source, prepared V4 image/baseline,
unchanged model/wire/policy, official grader and all admission evidence. The
private wrapper
`ee9e8f7044bfae4154f5cff58b668897d7c61330e402430e00c43ebfd01cd0c7`
uses the frozen controller with two narrower gates: no runtime start/restart,
and no subsequent arm after an unscored terminal outcome. All underlying
stage, recovery, guard, grader and scoring functions remain unchanged. The
900-second/360-second/128-request bounds, at least 60-second initial cooldown,
three-green admission and resource emergency stops remain in force.

Protocol review
`8541010555ae4c6e424006648a2fcab0dbe122f930c12a9b38306fdceace35a8`
passed 16 author checks, including actual read-only bundle preparation and
mocked execution of normal, strict-failure and unscored runner paths. The future
deterministic auditor
`888f3b548a896f4213155c6dd4bb13712a01efcd00bfa4cbe98c29727e976a43`
retains the established raw evidence predicates with explicit current-source,
arm-order and admission changes. It was eligible to run once only after a complete
pair; the incomplete integrity-excluded outcome below retired it unrun. A clean timeout
remains a strict failure; safety, integrity, ownership, recovery and missing
evidence remain unscored. These reviews are not independent-author review.
No result, fresh/protected validation, broad headroom, endurance, production
qualification or uplift is claimed by preparation or admission.

The bounded host-memory observation
`9403cd030e6e7c8360ec93b8c2e5924246f19db4159eb6eef1649a4ca5b9bd3d`
compared the retained pressure logs with current host/runtime metadata. Both affected arms recorded warning
pressure and zero sampled swap growth. The recorded runtime physical footprints
do not identify the cause or establish exhaustion of the model-memory ceiling. The later idle observation had no loaded model and
cannot establish safe memory headroom during inference. The cause remains
unknown. Two failed operator metadata probes are retained. No unrelated apps,
runtime settings or emergency stops changed. The separate bounded pytest
admission above follows later loaded-model and agent evidence; it does not
explain historical pressure or qualify arbitrary real workloads.


## Bounded pytest pair: incomplete and settled

The exposed pytest pair stopped after both 900-second CLI timeouts. KRYN made
56 relay requests and took 920.759 seconds including settlement. Its candidate
patch resolved the official tests with complete 2 fail-to-pass and 86
pass-to-pass coverage, but the unchanged completion rule makes this a strict
failure. Native made 48 relay requests and took 920.153 seconds including
settlement. It edited one existing test, so the unchanged integrity rule excludes
it and its official grader never started. The private wrapper stopped with
`needs_action`; no campaign adjudication was synthesized. This pair has no
matched score or comparative uplift. The preregistered pair audit is retired
unrun, and neither arm nor grader may be replayed.

Runner failure receipt:
`c7e6414e88ca74374279b9ac80b45726925c850e5c4ba5bcc685bacdb3cd963e`.
The original source, budgets, policies, test exclusion and resource stops remain
unchanged. Six parent/worker/grader logs contain 1,720 normal resource samples
and 1,496 valid AC power observations, with zero sampled swap growth within
each stage and all final checks present. These observations do not explain
historical pressure or establish endurance.

Settlement
`c3533510d5aa9e1dc2b14ed4a906a37d80bfe5dd3672018af0ff6c6dcc60509c`
verified 4,492 unchanged files, both full TAR/member maps, exact source and
baseline, native policies/catalogs, wire controls, raw grade coverage and actual
owned IDs/names/labels absent. Of 104 relay requests, the exports contain 102
token-accounted assistant messages and two terminal provider-error messages
without token records. The 102 counted requests, 2,328,338 prompt tokens and
16,795 completion tokens exactly reconcile the runtime counter increases.
After this reconciliation, one guarded unload returned the same runtime to
unloaded idle; only the exact inactive controller job was removed.

The first settlement review rejected a copied whole-catalog equality check:
native initializes 84 built-ins after an initially empty inventory. Its final
catalog exactly matches the settled native control and excludes `kryn.product`.
A new settler retains that observation and uses the frozen arm-specific rule.
A second review fixture failed when hashing its deliberately intercepted output;
a new review models the in-memory output consistently. Both failed reviews are
retained. The successful review performed actual read-only checks with unload,
job removal and output intercepted; it is author review, not independent-author
review. Settlement does not upgrade the incomplete comparison.

Future compact adjudication receipts now retain the internal validation reason
in `evidence_error`, for example `existing_tests_changed` or
`terminal_pin_drift`. External exception text is omitted. This is a reporting
change only: acceptance, exclusions, resource guards and existing frozen
campaigns are unchanged. Targeted regressions cover both reason propagation and
private exception suppression. Broader development, fresh/protected validation,
coding/UI, continuity/endurance and final production scope remain open.


## Two-CLI continuity attempt failed before inference; next control uses canned replies

The synthetic V1 bundle was retired unrun after static inspection found an
incorrect copied server URL. V2 imported the authoritative server constant, but
its private command hook assumed the candidate worker was the last owned
container. The actual three-container journal and validated worker inspection
identify the candidate in the middle; a later route probe is last. Reconstructing
the frozen framework call against the hook reproduces the failed assertion.
The earlier mock used only one container and missed this ordering.

V2 stopped before either CLI started: no user message, model request, tool or
patch was produced. Its original result remains failed
(`0445f5648f008fe13465f57f1c9fc39fe42dc9688c14bb3ce85eaf3b9db25907`).
The generation driver separately confirmed export and owned cleanup. A later
settlement verified the complete 5,751,808-byte archive and member map, all
1,261 pinned files unchanged, actual owned-resource absence and unchanged
unloaded runtime counters. Parent/worker resource observations remained normal,
with zero sampled swap growth and all power/final checks passing. Only the exact
inactive job was removed. Settlement passed
(`393a127e26c67198c73bbd2aa28d783b803505f075e9c22b7336927f5735474f`)
and does not upgrade the failed diagnostic.

The first settlement review rejected an overstrict whole-model metadata check
because native metadata also includes its default variant. That review and
unexecuted settler are retained. The corrected settler uses the frozen
provider/model identity predicate; its separate author review passed 12 checks
before execution. No task, runner or request was replayed.

After these two wrapper faults, the next protocol tests the actual CLI boundary
with the existing empty-sequence canned inference handler. One new root session
receives two distinct CLI invocations and exactly two canned stop replies, with
zero tools and an empty patch. Each CLI is bounded to 30 seconds; the combined
CLI and intermediate-check interval is bounded to 60 seconds. First-turn exit
zero, owned settlement and native completion are required before the second.
The hook binds the candidate to the recorded inspection, validates its image and
owner with the frozen worker validator, then checks that exact ID against both
the owned set and the CLI target. It no longer relies on container order.

This no-model control uses frozen source `59ce852`, the same prepared image,
policy, relay, export and resource guards. Runtime access is status-only and
must show unloaded idle with unchanged counters. There is no model load,
unload, restart, benchmark, grading, compaction or server restart. Acceptance
requires both exact native turns, direct exit/completion evidence, full exports,
chronology, ownership and resource finals. Its author review passed 38 static,
synthetic and mocked checks, including the retained three-container ordering
and first-turn failure paths:
`29b9cc09e2bb367fe810e388549522ef4f9dc1048a14a598165b96cc5f4dab9b`.
The prospective manifest is
`59a0f1544af3844e50c54b5ce65212c8fc020ee91cb66cf88f6d03cf6a6b1882`.
These were prospective author checks, not independent-author review or proof
of application acceptance. The actual outcome follows.

## Canned CLI turns completed, but exact prompt delivery failed

Both native CLI invocations exited zero and completed on the same owned root.
The driver recorded two canned replies, no tools, an empty patch and settled
export/cleanup in 28.321 seconds. Runtime counters remained unchanged and the
model remained unloaded. The wrapper nevertheless failed its original exact
user-message hash check; that result remains failed:
`2f3c76a2fcca0815783263678273b5757d54f6fb1e5e48e5792d9ef52f616070`.

Each exported user message contains two quoted copies of its submitted input.
The retained native CLI handler appends arguments following `--` to its parsed
message list, and its formatter quotes message parts containing spaces. These
source observations support the mechanism; they do not establish an isolated
parser execution result. A separate deterministic diagnosis confirms the exact
retained-byte relation and all remaining original pure acceptance predicates.
It does not replace the failed prompt predicate or upgrade this control.

Settlement passed after separate author review with job removal intercepted:
`bd7225dae13466d5679b4f03b9fbc87e7946f6800a7df613929b284eed1d2e6b`.
It verified 1,349 unchanged files, the complete 5,751,808-byte archive and member
map, both CLI receipts/exports, source and prior pins, unchanged unloaded runtime
and actual owned-resource absence. All 31 parent/worker resource observations
were normal, with zero sampled swap growth; all 26 power observations were AC
at 90%, and all final checks passed. Only the exact inactive job was removed.
Neither model inference nor grading occurred, and the started control was not
replayed.

The separately preregistered no-model control sends two new UTF-8 fixtures through native CLI stdin,
with Docker stdin enabled and no positional prompt arguments or `--` separator.
Each includes internal line breaks and quotes; exact exported bytes are required.
The existing 4,096-byte worker stdin bound remains enforced, so this does not
yet establish a general transport for arbitrarily long task prompts. Two canned
stop replies, no tools/patch, both direct CLI exits and new native completions,
owned settlement, unchanged runtime counters and all guard finals remain required.
The per-CLI 30-second and combined 60-second bounds are unchanged.

Its author review passed 43 checks, including exact stdin forwarding, rejection
of oversized inputs and the prior duplicated prompt form, preserved candidate
binding and no continuation after first-turn failure:
`48e163548b52d35b85570753a1a7d08566014fde25d7da8985e8e415364248e6`.
The prospective manifest is
`fca8c43b254eeb88a5d9deb34126863af7efd197ac12a00515bc57639d06cec9`.
Its outcome is recorded below. Frozen product source, policies, resource stops and
runtime settings remain unchanged. Model continuity, broader development,
fresh/protected validation, sustained coding/UI, endurance and final production
scope remain open.


## Exact stdin control passed; new local model continuity protocol

The preregistered stdin control passed without relaxing its exact input hashes.
Two distinct native CLI processes completed on one owned root session, preserving
both UTF-8 inputs (130 and 125 bytes), including internal line breaks, quotes and
Unicode. The driver completed in 28.947 seconds with two canned stop replies,
zero tools, zero patch bytes and no model inference. Result:
`cb1b7f123aaaa4cb73fc8824e4f411b23c38ef3a75f3e60cd7981fdac45d5055`.
This establishes only the measured bounded native stdin path. The earlier
positional-input control remains failed; arbitrary long-input transport and
model continuity are not established by canned replies.

Separate settlement verified 1,351 unchanged evidence files, the complete
5,751,808-byte archive with 1,319 members, exact capture/member equality, both
CLI receipts and per-turn exports, source/baseline/prior pins, actual owned-resource
absence and unchanged unloaded runtime counters. All 31 resource observations
were normal with zero sampled swap growth; all 26 power observations were AC at
90%, and final guards passed. The exact inactive exit-zero job was removed.
Settlement:
`9d18a5e491579bcd7d6e705e787e86f25b921de34f42436fe35fcca064e6a7ce`.
The first settlement review failed before execution because a copied plist
filename still named the preceding control. That failure is retained as
`e88c1a38564e7f795ef743fc71a9f4deb89f9a4698310c46dac1f28c8bff2f37`.
The corrected settler derives the sole plist and verifies its label, pins the
failed review and original script, and passed 12 separate author checks before
execution. No diagnostic, request, original review or settlement was replayed.

The subsequently executed diagnostic used local OpenCode/oMLX with one new synthetic
root session, two distinct native CLI invocations and new fixture identities.
The first invocation creates one fixture and finishes; the follow-up contains
neither command nor fixture bytes and asks for the read/finalization procedure
from the first message. Mechanical acceptance requires exact exported inputs,
completed tools in the declared order, an exact 599-byte two-file patch, both
native CLI exits and new generation completions, full owned usage accounting,
settled ownership and all resource finals. No model answer judging is used.
The 1,806- and 137-byte inputs fit the unchanged 4,096-byte stdin bound. Each CLI
has a 300-second limit; both calls and intermediate checks share 600 seconds.
The second invocation cannot start after first-turn failure or incomplete
ownership/completion evidence. No retry, benchmark, grader, comparison,
compaction, server restart or permission change is included.

Manifest:
`576a1e9a3fdfc3435c51d4152b1a786a9977abc2735fc8fc8bbed3f60618d579`.
Predeclaration:
`cb49c2ffd251e8d9754ac896a70517e7a7cf95fd81d264b87f61cb304580b216`.
Author review passed 52 checks:
`7a14509695e139cf76be30bf1efcf097bd0160e6737c96fa9707dc8982a6aa6c`.
These include the actual retained three-container ordering, exact stdin bytes,
first-turn rejection paths and unchanged admission, usage accounting, unload
and emergency-stop control flow. Frozen source remains `59ce852`; the editable
reporting change is not part of this diagnostic. This is a new protocol, not a
replay or upgrade of the failed earlier continuity attempt. No local-model
continuity outcome was claimed at launch; its failed outcome and settlement are
recorded below. Broader production gates remain open.

## Model stdin continuity failed at the policy gate; agent reuse control

Both native CLI invocations completed with exit zero and new owned generation
completions. The first turn used `shell`; the second used `read` then `shell`.
Both exported inputs and the exact 599-byte two-file fixture patch matched the
prospective protocol. The driver nevertheless remains **failed**: the unchanged
through-end policy gate recorded `session.agent.selected` with both previous
and selected values equal to `agent`, after the first turn's tools had finished.
The event had no active tool. Agent/model/permission snapshots and the other
policy inventories were unchanged. The gate intentionally records selection
events after tools begin; no exception was added after seeing this result.
Native CLI source contains an explicit agent-switch call when an agent is
supplied. This supports testing omission of redundant selection; it does not
upgrade the original failure or establish model continuity.

Result:
`9f9838308a4f7830a2b5e232fec1f3405e77b03b8697584e0defe7573096bdc9`.
Driver:
`a528127378776650a4981f51a7bccb2b81b66ca3598ca053f05317975eb5c8c8`.
The wrapper's original usage admission requires a completed driver, so it
failed before accounting and executed its unchanged exact-owned emergency
stop. The original runtime PID and port are now absent. Separate deterministic
settlement reconciled five native requests, 26,482 prompt tokens and 959 output
tokens against retained runtime counters. It verified the remaining exact
transport/fixture predicates separately while requiring the original policy
failure. No result, driver, task or grader was rewritten or replayed.

Settlement verified 1,363 unchanged files, the complete 5,754,880-byte archive
with 1,323 members, all 562 capture entries, actual owned IDs/names/labels absent,
source/baseline/prior evidence and both per-turn exports. All 61 resource samples
were normal with zero sampled swap growth; all 53 power samples were AC at 90%,
and final guards passed. Existing absolute swap was nonzero. A separate author
review passed 13 checks before the exact inactive exit-one job was removed.
Settlement:
`836fa0b1f73a5c0489bfe48a50315208157d254bc151a2aa1ccc677dfccf85f1`.

The subsequently attempted control used a new synthetic fixture and **no model**.
Its first actual CLI call receives a canned fixture tool followed by a stop;
the second receives one canned stop. Only the second invocation omits the
redundant `--agent agent` pair. All other native CLI arguments, exact stdin,
candidate identity, first-turn completion requirements and the full unchanged
policy gate remain enforced. Acceptance requires three canned calls, one exact
279-byte fixture patch, two exact native input hashes, both CLI/native
completions, unchanged policy snapshots, zero recorded policy mutations and
all resource finals. Each CLI has 30 seconds; calls and intermediate checks
share 60 seconds, with no retries. The prior runtime PID and port must remain
absent throughout admission and at both boundaries; the control performs no
runtime start, stop, load, unload or model inference.

Manifest:
`f14fd748d81168e4fc9497123a9f372fca9e0424648d1c60a1d382a8e879fc4c`.
Predeclaration:
`b2d9b7be1f1d57d0e2e58911ace05addf2b26bceb468e252e3af3955359775b8`.
Author review passed 55 checks:
`1c5d304551f6ad2ead3933ba9e9412f83c91da3b5e4677353cc0808e59439146`.
This is a prospective CLI mechanism control, not an accepted continuity result,
benchmark or production qualification. Frozen source remains `59ce852`; no
policy classifier, resource stop or released product scope changed. Broader
development, fresh/protected validation, coding/UI and endurance remain open.

## Stopped-runtime control failed before generation; revised cold-start control

Agent reuse control V1 attempted entry but failed at the unchanged HostGuard
before `generation-start.json`, a worker directory, ownership journal or either
CLI existed. The two retained resource samples had no runtime listener; the
frozen resource guard correctly rejected incomplete telemetry. Pressure was
normal and sampled swap growth was zero, but listener footprint/RSS were
unavailable, so this is **not** a successful resource check. The earlier protocol
incorrectly combined a stopped-runtime requirement with a guard requiring one
known listener. That failure remains preserved:
`a69f36999e240c27f3ae7de7386ec249aecd3229e28bc9881b59ab799ba7bbe8`.
No task, model request, canned response, container or CLI ran.

Separate settlement rehashed 21 unchanged files plus the full prior evidence
chain, reproduced the exact rejection using the frozen `ResourceGuard`, retained
the incomplete telemetry and power finals, verified absent PID/port and no
owner-labelled Docker objects, and removed only the exact inactive exit-one job.
Its separate author review passed nine checks before execution. Settlement:
`fea5d31a4f2b19fe53a6664a0ae6c1aa8cfd4623242739b7cbe31ee52cf02bc0`.
This settles the attempt; it does not accept the failed control or weaken the
guard. The once-started controller is never replayed.

The revised V2 protocol declares a new fixture and input identity. After the
existing 60-second cooldown and three green admission observations, it verifies
that the old runtime PID and port are absent, then makes one call to the existing
owned runtime start command. It verifies a fresh owned PID and the same model,
context and 22-GiB ceiling. Before any container generation, the full HostGuard
must admit the known listener and status must show unloaded idle with zero
request/token counters. The same fresh PID and unchanged zero counters are
required afterward. This starts no model inference and performs no model load,
unload or retry. Startup uses the existing bounded owned-app procedure and
active-work-only caffeinate; no unrelated application or runtime setting changes.

The native command hook, exact acceptance predicates, 30-second CLI/60-second
combined bounds and through-end policy classifier remain unchanged from V1.
The canned sequence still uses one fixture shell and two stop replies; only the
second CLI omits `--agent agent`. The exact new single-file patch is 279 bytes.
The revised main preserves the previously reviewed no-model stdin controller's
status and resource checks, with the prospective cold start replacing its
assumption of an already running fixed PID.

Manifest:
`30462f66d69fa08e6503742616fa43f10f4420949dafea52df4963939b59a177`.
Predeclaration:
`f1dd8a20a0fa50f07a63d5567270717847ba7b04645251397ad12fc2c9a4fb77`.
Author review passed 68 checks, including actual hook tests, unchanged acceptance
and guard control flow, cold-start success/failure mocks and refusal of wrong
identity, profile or busy state:
`2f791d7953d8230cdf6e173c1d8df328bc7c8b389c6d3bd022216fd22bcaa4d4`.
No outcome was claimed at launch; the failed outcome and separate settlement
are recorded below. Model continuity and broader production gates remain open.

## Agent option omission still failed; native prompt API control

Agent reuse V2 completed both actual CLIs and native generations, preserving
both exact stdin messages, the one 279-byte fixture patch and three canned calls.
It nevertheless **failed** the original policy gate: one `session.agent.selected`
event selected `agent` from `agent` after the first turn's tool completed. The
second CLI had omitted `--agent agent`, so omission alone does not prevent this
native event. Policy snapshots remained unchanged. The retained CLI source passes
a resolved target agent into its noninteractive routine, which contains an agent
switch call; the partial source snapshot does not establish every resolution
step. No classifier exception, policy change or acceptance upgrade was made.

Result:
`2ebf604ad2742305d761bddec46385984d47169770a039acaaf22ede964abc2f`.
Driver:
`96ef24f4d01da273f813673a45094bbeaa9e760bb959dee6f8c45ea5a7aa5573`.
The safely admitted cold start established a fresh owned runtime, which remained
unloaded idle with zero request, prompt-token and completion-token counters.
There was no model inference, load, unload or emergency stop in this control.

Separate settlement verified 1,356 unchanged files, the complete 5,753,856-byte
archive with 1,322 members and 561 capture entries, both exact per-turn exports,
stdin and agent-option receipts, source/baseline/prior evidence, and actual owned
container/network IDs, names and labels absent. All 33 resource samples were
normal with zero sampled swap growth; all 28 power samples were AC at 90%, with
final guards checked. The fresh owned runtime still had unloaded idle zero
counters. A separate 13-check author review preceded removal of the exact
inactive exit-one job. Settlement:
`4067868c60c301a420e67a19541366c721aa8a2b11000f83a4dbf04291049687`.
The original failure remains frozen and is never replayed.

The following control changed the continuation transport. One native CLI creates a
new synthetic fixture and completes. After the original owned-session settlement,
export and generation checks, one bounded POST to OpenCode's native
`/api/session/:sessionID/prompt` endpoint admits the follow-up. This is the same
prompt endpoint used by the CLI. The adapter rechecks the owned session's agent,
model, permissions, directory and project before submission, sends no policy
selection request, and leaves both generations to the existing native engine.
It restores the actual first CLI receipt; it does not claim a second CLI ran.

Acceptance requires exactly three canned calls, zero actual model requests, two
exact native user messages, tool order `[shell]` then `[]`, the new 256-byte
single-file patch, both native generation completions, unchanged snapshots and
zero events rejected by the original continuous through-end policy gate. The
first CLI has 30 seconds, prompt submission five seconds, and calls plus
intermediate checks share 60 seconds, without retries. Existing settlement bounds,
parent/child/final guards, 60-second cooldown, three green observations and all
resource limits remain unchanged. The current owned runtime must remain unloaded
with unchanged zero counters; no start, stop, load or unload is planned.

Manifest:
`a827733fab0b434924c824760897d546e78c41fc4201d0ccc6b51c72437980ba`.
Predeclaration:
`a42d9b67c1f15dd38cf6118c8dd6661c8b70b40594e7ffd40806ac1b73dbfa22`.
The protocol passed 59 author checks, including actual scoped-hook failure cases,
real retained container ordering, exact request transport, prior failure rejection
and unchanged main/admission guard control flow:
`814680e08ff050bdfe4c14b48f8dedeccbc3e7e736fa891c5e0e5f9997298f45`.
This no-model API mechanism control establishes no model continuity,
second-CLI compatibility, endurance, benchmark quality or production qualification.
All broader gates and truthful final scope remain open.

## Native CLI/API control passed; local model continuity remains prospective

The no-model CLI/API control passed its original predicates. One actual CLI
completed the fixture shell and stopped; one subsequent native prompt API call
completed a second generation on the same owned root. Both exact inputs (99 and
92 UTF-8 bytes), the sole 256-byte fixture patch and three canned calls matched.
There were zero model requests and zero recorded policy mutations under the
unchanged continuous through-end classifier. Driver wall time was 28.877 seconds.
Result:
`6e38c46bacc5cf532d7c7861a7b466129144ef1cd49fd27c61742390bbc43e8a`.
Driver:
`f65d6754fc0c8d87de508c682194b7e7b7ade94cb0ce1e19aca79fd8e6e95e6a`.
This establishes this canned transport path only, not second-CLI compatibility
or local-model continuity.

Separate settlement verified all 1,357 pinned files unchanged, the complete
5,753,856-byte archive (1,322 members; 482 regular files, 79 directories, no
symlinks), exact native exports and CLI/API receipts, frozen source and baseline,
prior evidence, and actual owned IDs, names and labels absent. All 31 resource
samples were normal with zero sampled swap growth; all 27 power samples were AC
at 90%, with both final guards checked. The same fresh owned runtime remained
unloaded idle with zero counters. A separate 13-check author review preceded
removal of the exact inactive exit-zero job. Settlement:
`01db87cdf672afbaac4afc41adfbc7469406c2a7aac32b865aef8596ed668b14`.
No task, inference, runner or original review was replayed.

The next local-model diagnostic uses a new root and fixture. The first native
CLI is instructed to create the fixture and retain a future read-only instruction.
The second user input, delivered by the native prompt API, omits the path and
contents. Acceptance requires exact tool order `[shell]` then `[read]`, a sole
248-byte fixture patch, both exact user messages, four fully reconciled local
model requests, two native generation completions, unchanged snapshots and the
original through-end policy gate. There is one actual CLI and one prompt POST;
the native engine owns both generations. No second-turn shell or permission
change is planned. The first CLI has 300 seconds, the combined operations and
intermediate checks 600 seconds, and prompt submission five seconds. The native
owned-session settlement retains its existing 30-second bound. All admission,
resource, accounting, emergency-stop and conditional unload behavior is unchanged.

Manifest:
`bf0ce98bca05aa0cf96d87d0e4c4d819c22d49c2e879de047331aa6236fa1b9e`.
Predeclaration:
`6be2855a5ce47c73db144ff10ecfbec09e8bdf12d67511ed2844b8226dd7e452`.
The first author review failed before launch because its source comparison did
not normalize the new predeclaration filename. That review failure is retained:
`7e4c17fb2ef9f3048a68b2722caf152e78891ed0dd78ade9b7b7e0198cf1dfb9`.
A separate corrected review of the unchanged runner passed 67 checks:
`ccccc5df6898d03ca586c834532850e0190869f2021936ae85d33b7134b020ce`.
A separate nine-check launcher review preceded the single launch. No outcome
is claimed here. Benchmark quality, second-CLI compatibility, sustained coding/UI,
endurance and broader production gates remain open.

CI run `37319186002` at documentation commit `35b2bdf` failed the evaluator-Python
compatibility step: `test_uncertain_detach_prevents_grading` received “Expected
disk image mount is missing or changed” before reaching its injected “detachment
uncertain” error. Other offline checks and package smoke passed. The cause of
the mount-identity failure is unproven, and the failed CI run was not replayed.
One local invocation failed to import the test because `PYTHONPATH` was missing;
that log is retained. The corrected local invocation passed eight barrier tests
with one skip. This does not upgrade failed CI or justify weakening the mount or
grading gates. Observation:
`ad3d8440188595300fbb92d998238b99463456a9bb4a7da9f5ef91245e8c05a2`.
The next changed-commit CI must pass independently.


## CLI/API model continuity passed; bounded multi-turn continuation

The new synthetic model continuity diagnostic passed one actual CLI and one
native API continuation: both native generations completed in 45.705 seconds,
with exact input hashes, `shell` then `read`, the sole 248-byte fixture patch,
no recorded policy mutations and full original gates. Four local requests,
18,833 prompt tokens and 291 completion tokens reconciled exactly before one
guarded unload. Separate settlement retained 1,407 files unchanged, verified
complete export and owned-object absence, and removed only the inactive job.
Its receipt is `5cbcdde91e4b8bef7f86da1ff40c8195b4844faa5d36ded07373e1d9307b68dd`.
This qualifies one bounded synthetic path, not second-CLI compatibility or
coding quality. All resource observations were normal, with zero sampled swap
growth; absolute swap was nonzero and all observations were on AC.

A new prospective 16-turn run has been launched: one CLI and fifteen native API
prompts on a fresh root/fixture, with distinct follow-ups retaining the initial
read instruction. The original time/resource/policy/accounting gates remain.
The first author review's identity-comparison failure is preserved; a corrected
review of the unchanged runner passed 55 checks before separate launch review
and one bootstrap. No new run outcome is claimed at launch. Full protocol,
limits and pins are in the [container record](CONTAINER_SWE_DEVELOPMENT.md).

CI **37320571511** passed the changed commit `0442f5b`; earlier failed
**37319186002** remains retained without replay or a proven cause. PR #242 stays
draft. Broader development, fresh protected validation, coding/UI, full-context
reasoning, long-duration endurance and truthful final production scope are open.

## Sixteen-turn result and transition to the UI boundary

The 16-turn local model diagnostic passed all declared checks in 185.682 seconds:
one CLI, fifteen native API continuations, exact inputs/exports, shell then fifteen
reads, 32 reconciled local requests and a sole 264-byte fixture patch. The original
policy and resource gates passed. Separate settlement verified 3,125 files
unchanged, all owned objects absent and the same unloaded runtime, then removed
only the inactive job. Settlement:
`a1154a9e176c4e8e484e4141dd5716ff61eaf88a7a73e917f23c40ffdee5cad6`.

The next prospective no-model control moves to the native Agent/Browse path,
separate browser container and existing APFS barrier on a new public fixture.
It keeps native engine/guards and uses the frozen candidate plugin, with parent
HostGuard cancellation propagated to both native monitors. It is a boundary
control, not a model UI score. Full evidence and protocol limits are in the
[container record](CONTAINER_SWE_DEVELOPMENT.md).

CI **37322172389** passed at `7aa1d42`. The earlier failed mount-identity CI run
remains failed without a proven cause or replay. Bounded read continuity does
not close coding/UI, fresh/protected validation, full-context reasoning,
long-duration endurance or final production scope. The single PR remains draft.

The first UI-control review's 15-second Docker inventory timeout is retained.
A separate local API health observation found no owned worker containers; the
unchanged runner subsequently passed a separate 13-check author review and a
nine-check launcher review. It was launched once with no outcome claimed.

## Native UI source preflight failure and new control

The first no-model UI control failed at the native driver's Git HEAD lookup:
the frozen source export was not a Git checkout. The candidate APFS volume was
detached; relay, browser, native-session, capture and grading startup had not
been reached. A subsequent absent-driver exception and the wrapper/helper
receipt-path mismatch are also preserved. The original result remains failed
(`24b1710aacfb93f6213d8f9c03ce9fe1378cde0cd5515b76ac2120c944980708`).
Separate settlement
`38bc9fc4ca6307b1432c6a22fc84945186888511dd69e07a794c18291bf90dc9`
verified 26 unchanged files, retained the detached candidate image, checked
actual mount absence and unchanged unloaded runtime counters, then removed only
the inactive job. Four normal resources and three AC/90% power samples passed
final checks. Twelve author checks preceded separate settlement execution.

Source preparation now proves an authentic detached `59ce852` commit, all 414
tracked blobs, the original 98 runtime hashes and five matching plugin assets.
The first whole-export assertion failure is retained: exactly two documentation
files differed. A further preparation caught mixed module imports before any
campaign or fixture was created; that runner is retired unrun. Neither failure
is upgraded or replayed. Full identities are in the container protocol above.

Fresh V3 uses the verified source consistently and one declared receipt for
boundary execution, export reads and returned results. Trial failures are
reported before dereferencing an absent driver. Fourteen author checks covered
the actual source Git lookup and a complete mocked trial, alongside unchanged
guards and acceptance predicates. Review
`8113f19fe02890c8bfa66b2e4a62e605ef224d9ad0dc881e9adfcbdad4553867`
passed before a separate nine-check launcher review and one bootstrap. This
prospective control retains six canned calls, zero model inference, one KRYN
arm, the original 120-second CLI and APFS/browser boundaries. No outcome is
claimed at launch; no broad UI, endurance, benchmark or production claim follows.
CI **37324458958** passed at `fabcf06`; older failed CI remains failed.


## Native UI interpreter mismatch and supported-runtime control

V3 failed before native OpenCode process launch because the research controller
used Python 3.11 while the native engine requires >=3.13 for retained temporary
directories. The driver preserved the actual error; browser cleanup completed,
the candidate image detached, and no model request, session export, capture or
grading occurred. Zero canned calls and unchanged unloaded runtime counters are
retained. Separate settlement verified 38 unchanged files and actual owned
browser/mount absence, then removed only the inactive job. Its receipt is
`3c3f695aa2cb31737cee356e5524f9522cad80fb19301dd268e270edc1b83e44`.
The first settlement review's copied-directory error and a Docker inventory
timeout remain preserved. Normal samples and settlement do not upgrade the
original failed control.

A mechanism preflight now exercises actual native background preparation under
existing Python 3.14.6 through intercepted process creation, including original
temporary-directory retention and cleanup. Historical evaluator checks run
read-only in their original Python 3.11 environment. Two preflight failures
(missing evaluator metadata and malformed synthetic broker identity) remain
retained. No engine, guard, dependency installation or owner setting changed.
The successful mechanism receipt is
`9881c06c643469b3a9acbf549a233f9f4d8d74ffc6f256a8043c7641ce2d3753`.

Fresh V4 passed 19 author checks and nine launcher checks before one bootstrap.
The launcher's immediate process-name comparison failed on macOS framework
Python's distinct process executable; a separate actual argv/proc_pidpath and
hash observation verified the active worker. It was not bootstrapped again.
This new fixture retains original six-call canned sequence, native engine,
APFS/browser boundaries, acceptance and resource stops. No outcome or quality
claim is made at launch. Full pins and retained limitations are in the
[container record](CONTAINER_SWE_DEVELOPMENT.md).

CI **37326329635** passed at `0aab7ce`; earlier failures are not replayed or
upgraded. Broader development, valid fresh/protected validation, coding/UI,
full-context reasoning, long-duration endurance and final scope remain open.
PR #242 stays draft.

## Native UI boundary passed; fresh local-model diagnostic launched

Supported-runtime V4 passed its canned protocol with native CLI exit 0, one
Agent root/Browse child, six calls, exact 75-byte native input and a sole 320-byte
page patch. The readonly capture and fresh synthetic marker grader passed, and
all three volume phases detached. No model inference or official benchmark
score was involved. Separate settlement verified 68 unchanged files, both
preserved images, actual owned mount/browser absence, normal final resource
samples and the same unloaded runtime counters before removing only the inactive
job. Settlement:
`42322ae4a36807199e7b1971be79acc975ffda79d27dc8dddea43c7970c0e365`.
The cleanup script's static correction and two failed reviews are retained;
none mutated the job. The corrected review passed before separate execution.
Browser ID/port and continuous native policy snapshots were not retained, so
those stronger evidence claims remain unavailable.

A new local-model V2 diagnostic is now launched once on a fresh fixture under
the same native/browser/APFS boundaries and unchanged emergency stops. It asks
local OpenCode/oMLX to write a declared public page and delegate navigation and
snapshot to Browse. Exact admitted sampler and both role schemas are enforced
by the existing local relay before forwarding. The original guard and usage
accounting must pass before unloading the owned runtime. One 300-second CLI,
128-request cap and automatic safe admission bound this diagnostic.

The first model draft was retired unrun after static review found it selected
the canned recorder's different JSON hash format. V2 uses the retained canonical
hashes from the shared digest function. Sixteen author checks and a separate
nine-check launcher review passed; actual process identity was verified after
one bootstrap. No outcome or broad model/UI quality claim is made at launch.
Protocol and primary hashes are in the [container record](CONTAINER_SWE_DEVELOPMENT.md).
CI **37328203434** passed at `1963cc4`. Earlier failed CI and research runs remain
failed without replay. Broader development, valid fresh/protected validation,
sustained coding/UI, full-context reasoning, endurance and final scope stay open;
PR #242 remains draft.

## Local-model native UI execution completed; strict protocol failed

Model V2 completed its native CLI in 86.601 seconds with nine local requests,
three successful owned sessions and a sole 322-byte page patch. Readonly capture
and the fresh synthetic marker check passed; all three APFS phases detached.
The declared diagnostic nevertheless **failed**: its pure acceptance function
requires one Browse child, while execution created two. Root tools were write,
subagent, skill (`opencode`), subagent; one child used no tools and the other
navigated and took a snapshot. The write used the exact absolute workspace path,
which also differs from the protocol's later literal relative-path predicate.
Neither completed execution nor settlement upgrades that failed result.

Nine native assistant usages exactly matched runtime increases of 38,721 prompt
and 2,984 completion tokens. One original guarded unload left the same runtime
unloaded and idle at 45 requests, 248,165 prompt and 6,301 completion tokens.
No resource stop occurred. All 49 parent, 42 native and four capture samples
were normal; 43 power observations were AC/90%, with zero sampled swap growth
and nonzero absolute swap. Separate settlement verified all 70 files unchanged,
actual browser/mount absence and both preserved images before removing only the
inactive exit-1 job. Its receipt is
`87a1915c5257011ae56252e7c456431cbe2dcc6194f52160457eae148e197b3a`.
A static correction to the new settlement script's receipt-field lookup was
retained before review or mutation; 15 author checks then passed before separate
execution. No task, grader or runtime operation was replayed, and original
acceptance was not upgraded.

Fresh V3 declares skill loading before write/delegation and permits only
`index.html` or that exact file beneath the recorded candidate workspace. It
still requires one Browse child, the declared tool sequence, exact page bytes,
all original ownership/isolation/accounting checks and unchanged resource stops.
Eighteen author checks included rejection of an outside path and wrong skill;
nine launcher checks preceded one bootstrap. This is a new synthetic fixture,
not a repair of V2's score. Outcome remains unknown at launch.

CI **37329916187** passed at `8289c25`. Full pins and the native evidence
limitations remain in the [container record](CONTAINER_SWE_DEVELOPMENT.md).
Broader development, fresh/protected validation, sustained coding/UI,
full-context reasoning, endurance and final scope remain open. PR #242 is draft.


## Native local-model UI V3 passed and settled

Fresh V3 passed its declared skill/write/delegate and Browse navigation/snapshot
protocol: native CLI exit 0, seven local requests, one successful Agent root and
one successful Browse child, 60.795 seconds and a sole 322-byte page patch.
Readonly capture matched that patch; the fresh synthetic marker check passed
and all three APFS phases detached. This is bounded synthetic tool-use evidence,
not official benchmark quality or sustained UI qualification. Earlier V2 remains
failed under its original protocol.

Exact native usage reconciled seven requests, 31,406 prompt and 1,824 completion
tokens. One original guarded unload left the same runtime unloaded and idle at
52 requests, 279,571 prompt and 8,125 completion tokens. All 37 parent, 30 native
and four capture resource samples were normal; 33 AC/90% power observations
covered the work and finals, with zero sampled swap growth and nonzero absolute
swap. Separate settlement preserved all 67 files and both images, verified actual
owned mount/browser absence and removed only the inactive exit-0 job. Fifteen
author checks passed before separate settlement execution; no task, grader or
runtime operation was replayed.

This successful run still lacked the browser container ID and broker port in
its native receipt. The prospective reporting fix retains the ID from Docker's
boundary inspection and the broker port, checks the inspected name/ID, and
continues to omit the authentication credential. Existing cleanup, isolation,
native engine, accounting and emergency stops are unchanged. Old receipts are
not backfilled. Full evidence pins are in the [container record](CONTAINER_SWE_DEVELOPMENT.md).
CI **37331355910** passed at `5874201`. Broader development, valid fresh/protected
validation, sustained coding/UI, full-context reasoning, endurance and final
scope remain open; PR #242 stays draft.


A fresh canned browser receipt control is now launched once against frozen
`37f2ed0`. It retains the six-call Agent/Browse sequence, original APFS barrier,
120-second CLI, browser image and emergency stops; no real model request is
scheduled. It additionally requires the actual full container ID, safe broker
port and exact ID/name/listener absence on the verified local Docker endpoint.
The original runtime must remain unloaded at 52/279,571/8,125. Twenty-one author
checks and nine launcher checks passed; exact process identity was verified.
Outcome is unknown at launch. Two earlier drafts were retired unrun: copied
scope text, then an API/CLI endpoint binding gap missed by the first review.
Both are preserved. This new control does not replay any prior native task.


## Browser identity control passed; local counter UI launched

The fresh canned browser identity V3 control passed: CLI exit 0, six canned
calls, zero model requests, 9.320 seconds of native execution and a sole
321-byte page patch. Readonly capture and the fresh marker check passed; all
three APFS phases detached. The receipt retained the actual full browser
container ID and port. Separate settlement verified exact ID/name/broker
absence, closed port, three empty owned mounts and both preserved images, then
removed only the inactive exit-0 job. All 61 files remained unchanged; 15 author
checks preceded separate settlement execution.

This run was on **battery at 90%**, with the runtime unloaded throughout.
All 13 parent, six native and four capture resource samples were normal; 11
battery power observations covered the work and finals. Sampled swap growth
was zero and absolute swap was nonzero. Runtime counters stayed exactly at
52 requests, 279,571 prompt and 8,125 completion tokens. This does not establish
loaded-model battery endurance. CI **37332655393** (`37f2ed0`) and
**37336300276** (`9b9ab34`) passed; full job/step observations were retained.

The next fresh local-model diagnostic asks OpenCode/oMLX to implement a small
counter in `index.html`, without supplying its implementation. Native Browse
observations must show counts **0 → 1 → 2 → 0 → 0** after navigation, two
increment clicks, reset and snapshot. The fresh applied-artifact callback
checks a bounded page and public marker; it is not an independent functional
grader. Browser tool outputs supply the interaction evidence. Workspace-only
edits, exact prompt and role identities, complete admitted tool schemas and
sampler controls, owned usage accounting and all existing resource/isolation
predicates remain required.

The worker was bootstrapped once with verified process identity after 20 author
checks and nine launcher checks. It uses frozen `37f2ed0`, one 300-second CLI,
300-second requests, the unchanged 128-request cap and automatic battery-capable
admission. Outcome is unknown at launch. This is a new public synthetic fixture,
not a replay or a benchmark score. Broader development, valid fresh/protected
validation, sustained coding/UI, full-context reasoning, endurance and final
scope remain open; PR #242 remains draft. Full pins are in the
[container record](CONTAINER_SWE_DEVELOPMENT.md).


## Counter interaction failure, settlement and Browse handoff clarification

The counter interaction V1 remains a strict failure. Both native sessions
finished and CLI exited 0 in 102.431 seconds, but Browse first attempted an
unavailable `write` and a permission-denied project `read`. It then completed
the five declared browser operations with visible counts 0, 1, 2, 0, 0.
Those observations do not satisfy the original all-tools-completed and exact
Browse-sequence predicates. The 775-byte model-authored page and sole 1,012-byte
patch passed only the separately scoped applied-artifact callback; no official
quality score or independent functional grade is claimed.

Separate settlement required both exact rejected tool errors and checked the
remaining retained predicates, without invoking the original acceptance or
replaying the task, browser or grader. Twelve local requests used 56,311 prompt
and 3,533 completion units, exactly reconciling counters 52/279,571/8,125 to
64/335,882/11,658. One original unload left the same owned runtime unloaded and
idle. All 55 parent, 48 native and four capture resource samples were normal;
50 battery power observations covered the stages and finals, with a minimum of
84%. Sampled swap growth was zero; absolute swap was nonzero. This bounded
battery observation is not endurance qualification.

The exact browser ID/name and recorded port were absent/closed on the bound
local Docker endpoint, and its broker was absent. Both whole images were
preserved, detached, with three empty owned mount paths on the host device.
Sixteen author checks, including failure-preserving negative cases, preceded
separate settlement execution. All 67 files remained unchanged across removal
of only the inactive exit-1 launch job.

| Counter interaction V1 artifact | SHA-256 |
| --- | --- |
| Failed result | `aaddf8b546de715251db0bcd5cfbf195915c593830f45624b147a1c5dda22e21` |
| Driver | `bced0763ff5f4f20a1d6f248bc77b57e85d3c2460a74e0ea9eaeeb49ad9e2513` |
| Barrier | `3d578c7216d6354f253c0aacdb9e7aec23d762b9cf52a35a4e84ef7638bd9e93` |
| Patch | `96422c53fef975c80ab8336382dcaf01e51cfe71b0f2b5a1844a9e3b32d9f226` |
| Settlement review | `e4eb0b7a43448d60e1cebb8046db3981c454188f45cf188c7215dc98b385d40d` |
| Settlement | `26000b749c9425ecfca28e3f3b85f662bd50cd4098543a622a60b076cbda7666` |
| CI 37337972945 observation | `366136de0771cac3ecb9c055850a922caf5044862849f83e814951060c6d527c` |

Static inspection identified ambiguous role framing in the product: Browse's
handoff appends the complete parent coding request to the inspection prompt.
The plugin now identifies that request as reference context, closes that block
with an explicit inspection-only instruction, and returns implementation and
repair work to Agent. Browse guidance also explains that `read` is restricted
to saved tool output permitted by native policy. The full user criteria remain
present. Tool catalogs, permissions, native engine, resource guards and scoring
are unchanged. This is a prospective clarity fix; causation of the model's two
rejected calls and improvement in future model behavior are not established.
The existing hook regression now checks both sides of the reference context,
restricted guidance, unchanged tool filtering and private metadata exclusion.

CI 37337972945 at `30a5d10` passed, with full job/step JSON retained. Earlier
failed results remain failed. Broader development, valid fresh/protected
validation, sustained coding/UI, full-context reasoning, long-duration endurance
and final truthful production scope remain open. PR #242 remains draft.


### Fresh handoff control after the product clarification

Code `4a35ab0` passed 220 setup, 214 research (two skips), 87 Node and
native/frozen offline checks. Clean-source package smoke, documentation/link/
diff checks and one-commit secret scanning passed; validation is
`52acc038379ae5b6d005622001566f887ef8ce0fcb45bb62f25298b05fadd672`.
The new detached Git source verifies all 414 tracked blobs, keeps the 98-file
research runtime map identical, and limits runtime changes to three plugin
string-bearing lines. Exact reversal of those lines reproduces the old plugin;
only its existing regression and two research documents also differ. Source
proof: `a597c20b156ba8de06b9011a61b6017387174c9bae01a7b1e2d528c439d87917`.

A fresh no-model handoff V1 control was bootstrapped once with verified
framework-app process PID 58363. It retains six canned write/delegate/navigate/
snapshot calls, the same 120-second CLI, browser image and isolation, three
512 MiB APFS phases, linked resource guards and battery-capable admission.
The additional predicate compares the actual native child user prompt with the
complete parent criteria enclosed by the new inspection-only framing. Altered
criteria or framing, extra input and the old ambiguous child prompt are rejected.
Twenty-two author checks and nine launcher checks passed before activation.

The original runtime must remain unloaded and idle at 64/335,882/11,658;
this runner cannot start, load, unload, stop or restart it. No actual model
request or benchmark is scheduled. Outcome is unknown at launch. Even a pass
would establish only delivery of the clarified native handoff, not improved
model compliance or general UI quality. The failed counter run remains failed.

| Prospective handoff V1 artifact | SHA-256 |
| --- | --- |
| Runner | `945c1a18d1a87a958b9e03bff467a8c247798bc3011078397c3d576092454ba3` |
| Predeclaration | `32da558abaca3ce637dad0830e0298ca7fdfd44aaf8ada41a9ab6dd7d4a540ba` |
| Manifest | `1b5e065b3488247200be06bf0b044fa6a836c4ba184e560f9e69b02c2e916205` |
| Author review | `56e1b0ee8f10fa97a5967840f91dbb4e89718fa2977a8245d35bac81e8c7cc65` |
| Launcher review | `5b0202b59b6acdd3a117a04351df7055cbd504a46978580df190393fcd1e7ecc` |
| Launch | `fc691c2c13607684b1b5a112cdfa36d8801986e043947e34a29c2cdbd0f7bd4d` |
| Activation | `6edbcc3a4fa2b61b065b2d30c0f751212ecf46fcdd597b2cceef2a46ebbb5269` |

The heartbeat will inspect the next meaningful terminal checkpoint and continue
eligible engineering. Broader research and production gates remain open; this
launch is not completion, and PR #242 remains draft.

## Handoff delivery passed; fresh model-authored form admitted prospectively

The no-model handoff V1 control passed in 9.844 seconds with six canned calls
and zero real model requests. Its actual native Browse user prompt contained
all 713 declared bytes, including the complete parent criteria and the
inspection-only framing before and after them. Agent write/delegate and Browse
navigate/snapshot all completed. This establishes delivered user context only;
it does not establish full system-prompt provenance or better model compliance.

The three APFS phases detached; the sole 307-byte index patch matched capture.
All 13 parent, six native and four capture resource samples were normal, with
zero sampled swap growth and nonzero absolute swap. Eleven battery observations
covered the stages and finals at a minimum of 81%. The same runtime stayed
unloaded and idle at 64 requests, 335,882 prompt and 11,658 completion units;
there was no loaded-model battery observation in this canned control.

The first settlement review stopped on a 20-second historical Docker CLI
inventory timeout before any cleanup mutation. The separately bounded, locally
bound Docker API health/absence check passed; the timeout's cause remains
unknown. A new settlement script pinned that failure and the original unexecuted
script, retained all original preflight checks, and passed 16 author checks
before separate execution. All 65 evidence files, including two whole detached
images, remained unchanged across removal of only the inactive exit-0 job.
Exact browser ID/name and broker absence, recorded-port closure, and three empty
owned mount directories were verified. No original task, grader or acceptance
function was replayed.

| Handoff V1 terminal artifact | SHA-256 |
| --- | --- |
| Passed result | `6aa3a6d787c94db6393c72a1e0e968f2b70ead8226375d8ae03332dba3a2e21d` |
| Driver | `53192d8dc2af9166e6b09d99981423633ab349c6afbbf906f7b3fec46710a0a4` |
| Barrier | `03ed4696b1a9cb799bf2649e186a28a850d1f22637c2e5e540e2e535e5e58dd1` |
| Exact delivered child prompt | `47ffe861874e95a8ca5de80c27676a15c7d50949f8fb4f781206721f08282d9f` |
| First settlement review failure | `47137737f881903a771998e8bcaee4c18a583a6028bcf2459f83e55989507bc9` |
| Separate Docker health check | `42579671ffa37866031c10cf0ea4de3923ce0511ce8706cdbaaec9c207cdea0f` |
| Revised settlement review | `bdd6c7b0d87bc6abd543c46fb76097339275e9e0bf21de414ee744983e184faf` |
| Settlement | `a674f05a7abc9c54c6b5d521887855daaa6c48a21cb73f2a6781835bdbcce43c` |

The next prospective task is a different public name-entry form, with a blank
seed and requirements only. Local OpenCode/oMLX must author the implementation.
Native Browse observations must demonstrate empty-submit failure, a valid River
submission, then clearing both the accessible input and status. The prospective
state checker permits extra snapshots within 12 browser calls; it rejects
wrong origins, selectors, values, stale/duplicate states, truncated observations,
missing flows, file tools and failed calls. All original tool-completion,
identity, isolation, usage, resource and cleanup gates remain. The failed
counter's exact-sequence protocol and result are unchanged.

The new runner also checks the exact delivered child user context. Its applied
artifact callback checks bounded regular UTF-8 page bytes and public-marker
integrity; it is not an independent functional grade. One 300-second CLI,
300-second requests, the original 128-request cap, exact before-forward sampler
and complete role schemas, the same frozen `4a35ab0` source and plugin bytes,
and unchanged battery-capable admission and emergency stops bound the task.
Historical prior-chain checks retain every predicate while receiving the
explicit current counter expectation after legitimate new generation.

Twenty-three author checks covered actual preflight, intercepted trial bindings,
positive and negative native evidence, counter binding, and success/unload,
failure/owned-stop and concurrency/no-operation branches. Nine launcher checks
preceded one bootstrap, with actual framework-app PID 63837 verified. These
reviews are not independent-author reviews. A missing local alias was corrected
in the unsealed draft before preparation/review/execution, with both hashes
retained. Outcome is unknown at launch; no original task was replayed.

| Fresh form V1 artifact | SHA-256 |
| --- | --- |
| Runner | `e6474db3762cdabbbf097dec2f3dcd88e3dedc02ac6e848150c20eedac19ddfd` |
| Predeclaration | `d6f4a8622063a00bbb69073b5bef2a439a98402ca95d4cdaddc1014f088c9bf3` |
| Manifest | `09c11847faaa0f8f5ee6a4d814514c554aee2b6ee89f605decac61bd9b3bb72f` |
| Author review | `6bdc311234c0b80a2de380e1afc71cfe14e1931eb1aca173614e79429451e1e6` |
| Launcher review | `f64fa0f9d25d43f8d1cd059e72d18e3c2c132149553e48c7d9ee0d248b5f1139` |
| Launch | `5e34251c216a9a4ad24c6e8e5b9c42b7081ecfe844264ed5819252003c8dffda` |
| Activation | `cc1460cfe6ea7b363c9fbe912031f902db4a071519dd87ff0e8ad383b6925c04` |

CI 37339605406 (`4a35ab0`) and 37340011501 (`ab2929d`) passed; full job/step
JSON is retained. Broader quality, valid fresh/protected validation, sustained
coding/UI, full-context reasoning, endurance and final production scope remain
open. PR #242 stays draft; this launch is a continuation checkpoint.

## Form failure settled; canned parent repair workflow launched

The local-model form V1 finished its native CLI in 99.934 seconds with 12 local
requests, but failed its original strict protocol. Agent wrote the page before
loading the required `opencode` skill, attempted unavailable skill `browse`, then
delegated Browse. The root skill call failed. All seven Browse calls completed:
initial navigation, snapshot, empty submission, filling River, valid submission,
clear and final snapshot. The greeting was `Status: Hello, River`, omitting the
period required by the declared checker. The original result remains failed.

Both native sessions reported succeeded. The full 2,881-byte child user prompt
matched the declared inspection framing and complete parent request. Browse used
only browser tools. These observations do not establish that the handoff prompt
change caused better behavior. The 3,338-byte page passed the artifact callback,
and the sole 3,666-byte index patch matched capture; neither upgrades the failed
functional/protocol checks or establishes an independent functional grade.

Exact native usage reconciled 12 requests, 52,505 prompt and 3,263 completion
units. After the original single unload, runtime 85947 was unloaded and idle at
76 requests, 388,387 prompt and 14,921 completion units. All 55 parent, 48 native
and four capture resource samples were normal, with zero sampled swap growth
and nonzero absolute swap. Fifty power observations were on battery, minimum
74%, including all finals. This is a bounded observation, not endurance evidence.

Separate settlement required the exact failed root sequence, failed skill input
and greeting mismatch while verifying the remaining evidence. It did not invoke
the original acceptance function. The first review rejected an incomplete
expected skill-call record; the second hit a five-second exact Docker API query
timeout. Both failures were retained before cleanup mutation. A separate bounded
health check verified the local endpoint and exact browser ID/name absence; the
timeout's cause remains unknown. A new review passed 16 author checks before
separate settlement execution. All 67 files, both whole detached images and
three empty owned mount paths were preserved. Browser ID/name/broker absence
and port closure were verified, and only the inactive exit-1 job was removed.

| Form V1 terminal evidence | SHA-256 |
| --- | --- |
| Failed result | `a25bfab4d082e98232b29fa1fbeccbed3460bc0ac57ea48a46846b5ab01a53fd` |
| Driver | `476a7f91888da9aeca62bfe688bd5b57114d870a64934b50b954b3764cab4dab` |
| Barrier | `a4c9c0f0149dc5ab71737da26cc2c95c8b1b3059b3fd746918787d01211d2bc5` |
| Settlement review | `629a8256d896897c51c5beac79473fd078c76d650cacb6f71e1b09e49504c3fa` |
| Settlement | `764ea30b5204f65f9942b605ac734bcf599c27f5ec2de39e7a6c80aabf503953` |

The next diagnostic changes approach to the native repair workflow. A fresh
fixed canned fixture requires skill loading, writing `Revision: before`, a
Browse inspection and repair request, parent resumption and a second write, then
a distinct Browse child navigating again and observing `Revision: after`.
Acceptance requires both exact child contexts, native tool completion, returned
reports, timestamps placing the second write after the first handoff, fresh
browser observations, complete role catalogs and the captured final fixture.
There are 12 canned HTTP responses and zero real model requests. This tests the
transport and repair mechanism, not whether a model can diagnose or fix a task.

The same frozen `4a35ab0` source, native engine, 120-second canned CLI, browser
isolation, APFS phases and original resource stops remain. Runtime identity and
all three counters must remain unchanged; no runtime start/load/unload/stop is
allowed. Eight groups of author checks covered full preflight, original
controller AST, actual local canned HTTP/SSE responses, 13 negative native
acceptance cases and intercepted trial/failure paths. An initial review client
hit BrokenPipe when sending an oversized body after the server rejected its
length; the failure was retained, and a new review verified the original 413
response by sending only the oversized length header. The runner was unchanged.
Nine launcher checks preceded one bootstrap with verified process 70773.

| Fresh repair control V1 artifact | SHA-256 |
| --- | --- |
| Runner | `9d932cc07ff685916eb09e4eedcf603bc574d564586772a50e5652e955e19039` |
| Predeclaration | `da9ba2310705ca40be2f81560b15718eb2827616bf04d1688a8d44d43aaa4410` |
| Manifest | `68f43e1b307d8ba47a9fd5331134a0e424f9062b9baf884ab79001dfeda9e138` |
| Author review | `08df00b0f348ae56e0d415d4947fc44f210a7f0dad97fe4719e8d4c13ffc4b46` |
| Launcher review | `981017a61da931a3538f90bfa59943f8f25c6a5e3eb95d5c90a091f574856679` |
| Launch | `1b58952a11cfed652f44375bb18fa3bb45b690376496dcbf189f077d9e098de0` |
| Activation | `7984f34ecca31232a2c819f70f20ca322de6706495cf8fa65da9cde846471279` |

Outcome is unknown at launch. No original task, grader or control was replayed.
CI 37341589860 at `cb47595` passed; full job/step JSON is retained. Product code
is unchanged this checkpoint. PR #242 remains draft, with broader development,
valid fresh/protected validation, sustained coding/UI, full-context reasoning,
endurance and truthful final production scope still open.

## Canned repair workflow settled; local-model duration diagnostic launched

The repair control V1 passed with 12 canned responses and zero model requests.
Agent loaded the skill, wrote the before revision, received the first Browse
report, resumed and wrote the after revision, then delegated a distinct Browse
child. Both children observed their respective revisions through completed
navigation and snapshot calls. Exact delivered child contexts, returned reports,
role catalogs and native timestamps matched the declared workflow. The CLI took
10.479 seconds; the three-phase barrier took 20.383 seconds. The sole 317-byte
index patch matched capture, and the final 119-byte canned page matched the
artifact callback. This establishes the canned mechanism, not model repair
ability or an independent functional grade.

Runtime 85947 remained unloaded and idle at 76 requests, 388,387 prompt and
14,921 completion units, with no runtime operation. All 13 parent, six native
and four capture resource samples were normal, with zero sampled swap growth
and nonzero absolute swap. Eleven power observations were on battery, minimum
71%, including finals. This is not loaded-model or endurance evidence.

Separate settlement preserved all 63 files, both whole detached images and
three empty owned mount paths, verified exact browser ID/name/broker absence
and port closure, and removed only the inactive exit-0 job. The original
acceptance function was not replayed. A first read-only review hit a historical
Docker CLI inventory timeout; its failure and separate successful bounded API
health check are retained, with no causal diagnosis. A later negative fixture
selected a terminal message without content and failed in the review itself.
A corrected review selected the assistant message and passed 15 author checks
before separate settlement execution. The runner and original outcome were
unchanged; neither failed review performed cleanup mutation.

| Repair control V1 terminal evidence | SHA-256 |
| --- | --- |
| Result | `e8beb7f63094bcf911184603465fd34fd6777e980fbb96b3f78519f4f47f4105` |
| Driver | `656da610413f561594a7a136f3249f635ebd1b4d35d5cc1b7edbc7705ff74cab` |
| Barrier | `8dca59c879b64bf56dce7cf2f86c88da55ce1fa4490bd68ce52a423ea17d7362` |
| Settlement review | `db544906842417af045eab59e474b20406723b8fc63280e343f1ec8cfee2634e` |
| Settlement | `a7bc76eabb0002ae56038a619c77f4196069be1e603943f07ba83a9668dfc3ff` |

The fresh duration diagnostic supplies a blank page and public requirements,
with implementation left entirely to local OpenCode/oMLX. It requires empty-input
failure, conversion of 90 minutes to `Status: 1h 30m`, then reset of status and
input. Its prospective protocol permits one to three Browse inspections, with
an actual intervening code revision before each repeated inspection. The final
child must inspect after the latest edit and demonstrate every required state.
Earlier functional discrepancies may be repaired within this new protocol;
all native tools must still complete. The old counter and form failures remain
failed under their unchanged original predicates. A chronological revision count
alone does not prove diagnosis, causal repair or model reasoning.

Nineteen groups of author checks covered full source/prior-chain admission,
actual intercepted trial and main paths, exact usage, one/two/three-child
fixtures, state/context/ownership/chronology negatives and rejection of a fourth
child. The original model controller, status, admission, query and trial AST
remain unchanged apart from report metadata; current counters are forwarded to
the original historical check without changing fixed settlement facts. Nine
launcher checks preceded one bootstrap with verified process 79200. The same
frozen `4a35ab0` source, 300-second CLI/request limits, canonical role schemas,
local relay, resource emergency stops, browser isolation and APFS phases remain.

| Fresh duration V1 artifact | SHA-256 |
| --- | --- |
| Runner | `7d4751c750491cd631a055ff8f101c4fcb6aed0b04cdfce1329deba4c5b94ab2` |
| Predeclaration | `d4e69908e070f64bb72502eaf2a686a1990ff3281e42e0a1b4c66b6ac0e9cb06` |
| Manifest | `6e37c07f8cb691354ba1be49e95c826a8c038a2b865baaa3bb999b3ae7889ea5` |
| Author review | `dba904f0997199071bf5d41778a0675fc29509b593970e6e1991e17b75c7261d` |
| Launcher review | `cac7476eb6c5e65a53254da93b08e9e1e47ad9824b8d655bd9b366fd7f86e2e1` |
| Launch | `dc293e01b4abd167dca973d8e1ba2f2e94b4d14485367e03bf059900208a4536` |
| Activation | `3cc45f354c0d4eb17db9aa91ec2e3a819f7593bb6527a38f7caf60ea8b37cc65` |

Outcome is unknown at launch. CI 37343403861 at `6709576` passed, with full
job/step JSON retained. No product code, release, version or install changed.
PR #242 remains draft; broader development, valid fresh/protected validation,
sustained coding/UI, full-context reasoning, endurance and final production
scope remain open. This launch continues the campaign and is not completion.

## Duration strict failure settled; native skill and agent routing clarified

The duration diagnostic completed its native CLI in 97.097 seconds with 11 local
requests. Browse completed all six calls and observed the exact required states:
Ready, empty-input error, unchanged error after filling 90, `Status: 1h 30m`, then
reset and final Ready with empty input. It used one child and made no intervening
revision; this provides no model repair observation. The original strict run
still failed: Agent wrote first, then called unavailable `skill` with `id: browse`
instead of loading `opencode` initially. That skill call failed before a correct
`subagent` call. Both native sessions reported succeeded; session outcome alone
does not override the failed tool and protocol predicates.

The complete 3,123-byte child user context was delivered exactly. The sole
3,117-byte index patch matched capture, and the 2,784-byte page passed the marker
artifact callback. That callback is not an independent functional grade. Exact
usage reconciled 11 requests, 48,561 prompt and 3,181 completion units. After the
original single unload, runtime 85947 was unloaded and idle at 87 requests,
436,948 prompt and 18,102 completion units. All 53 parent, 46 native and four
capture resource samples were normal, with zero sampled swap growth and nonzero
absolute swap. All 46 power observations were AC, minimum battery 73%, with
complete finals; this is not endurance evidence.

Separate settlement required the exact failed root sequence and complete failed
skill input while preserving every remaining original predicate, including all
six functional states. It did not invoke the original acceptance function or
replay a task. Six negative projection checks rejected changed failure facts and
altered functional/context evidence. Sixteen author checks passed before separate
settlement preserved all 67 files, both whole detached images and three empty
owned mount paths, verified exact browser ID/name/broker absence and port closure,
and removed only the inactive exit-1 job. No settlement review or mutation failed.

| Duration V1 terminal evidence | SHA-256 |
| --- | --- |
| Failed result | `de7362bc0e7d4dda6c7592616456615871920adff99a19c21a7b436e7ddd6200` |
| Driver | `978d65c8c864c10b2bde397d5424698d1af535c902e91fd20e80e18ab021bc64` |
| Barrier | `0c136635c9e3c2280d69ab311153b438c33621cfbb94d609c2ee01a4fa3034d2` |
| Settlement review | `f3d2e4b1c5059d38ad5179c4cd40aa462ad90f5e74b21648bb8a09b6274e110c` |
| Settlement | `2a7ea55beac27b91b65d8a2b1c90e4a9450c6fbeb2fe4433a4d5e48daa7fb337` |

The repeated skill/agent confusion motivates a prospective clarification in the
existing Agent/Build guidance. It now directs loading native instructions with
`skill` and `id: opencode` before acting, distinguishes agent names from skill
IDs, and names the actual Browse route: `subagent` with `agent: browse`. The
existing hook regression verifies that both Agent and Build receive this guidance
while their edit, shell, skill and subagent catalog entries remain present.
Only the guidance string and regression change; native tools, permissions,
execution, guards and failed diagnostic criteria remain unchanged. Causal
attribution and improved model compliance remain unproven.

CI 37345477604 at `266d06f` passed; full job/step JSON is retained. The code
clarification needs its own prospective evidence. PR #242 remains draft, with
broader quality, valid fresh/protected validation, sustained coding/UI,
full-context reasoning, endurance and final production scope still open.

## Fresh no-model native skill-routing delivery control launched

The Agent/Build routing clarification at `e576633` passed 220 setup, 214 research
(two skips), 87 Node and native/frozen offline checks, targeted hook checks,
clean-source package smoke, documentation/link/diff checks and one-commit secret
scanning. A fresh authentic Git clone freezes that code; all 98 research runtime
files match the earlier source, while the five packaged plugin assets are pinned
separately. Reversing the single guidance line exactly restores the old plugin.
The old source copies, failed duration/form/counter results and receipts remain
unchanged.

A fresh canned native control now exercises the original six write, delegate,
navigate and snapshot responses. It performs no model forwarding. A read-only
metadata wrapper records the exact new guidance occurrence count and system-text
hash without changing the request payload or original inference controls. The
prospective gate requires one copy in each of three Agent system requests and
none in the three Browse system requests. It also retains the exact child user
context, patch/capture, browser identity, APFS, resource and cleanup predicates.
This tests delivery of routing guidance; it does not test model compliance,
repair ability, benchmark quality or full system-prompt provenance.

Twenty-six author review checks passed, including the actual six-request local
HTTP/SSE control with intercepted trial boundary, unchanged original controls,
role/content/duplicate negatives and full source/prior-chain validation. Nine
launcher checks preceded one bootstrap with verified process 87108. Runtime
85947 must remain unloaded and idle at 87 requests, 436,948 prompt and 18,102
completion units before and after; no runtime operation is permitted. The same
native engine, role catalogs, permissions, browser image, guard thresholds and
three APFS phases remain unchanged.

| Skill-routing control V1 artifact | SHA-256 |
| --- | --- |
| Frozen source proof | `7ac03c64fc66cc5c6b12ed33117c5e31b87eb89a02f90510d1f674f2797cd779` |
| Runner | `11ad58608ba1a6b64bade8ac0e8fd5ec8be27e7c8f8f57e184517b2ba755ce18` |
| Predeclaration | `6a25675e1e197a216a0c2ce1e6c9061094a770f8f17955a6a8e751912f1db93c` |
| Manifest | `03bbccf3b313b1a980137284cfa169e0eac2b19c9e00a51597e509d049975de7` |
| Author review | `25b72dd876c640cdeee225b1412ae3c101ce2ad7758027fdd91d624c3c8e0198` |
| Launcher review | `7a90ce5b46a25dea24b35171b867fcfc898e3637fb392e3da7a3347c96dcfaa7` |
| Launch | `da31ca1944edb479ef7026f70fbee15dbdeecb5919259dd804bf4dfd11d3e644` |
| Activation | `1fb58d57bde692bf0399215507d771b737c6baebca5f664f9fc2b4977db5f936` |

Outcome is unknown at launch. Code and launch-doc CI will be inspected once at
the next meaningful terminal. PR #242 remains draft. Broader development, valid
fresh/protected validation, sustained coding/UI, full-context reasoning,
endurance and final production scope remain open; this launch is not completion.

## Routing delivery verified and settled; fresh local-model length UI launched

The no-model routing control passed. Its six canned native requests completed
in 9.648 seconds. Each of three Agent requests contained the exact new guidance
once in system content; none of the three Browse requests contained it. The
recorded system-text hashes were stable within each role. Complete canonical
role-schema and sampler metadata matched the retained controls, and the exact
706-byte child user context preserved the parent criteria and inspection framing.
The sole 312-byte index patch matched capture. This establishes guidance delivery
in this canned control, not model compliance or full system-prompt provenance.

Separate settlement used independent evidence predicates and did not invoke the
original acceptance function. Eighteen author checks included seven metadata
negatives and native write/delegation/navigation/snapshot chronology. All 61
files and both whole images remained unchanged before and after removing only
the inactive exit-zero job. Exact browser ID/name/broker absence and port closure,
two detached images and three empty owned mount paths were verified. All 13
parent, six native and four capture resource samples were normal; all ten power
samples were AC at 85%, with complete finals and zero sampled swap growth.
Absolute swap was nonzero. Runtime 85947 remained unloaded and idle at 87
requests, 436,948 prompt and 18,102 completion units, with no runtime operation.
No settlement review or cleanup mutation failed.

| Routing control V1 terminal evidence | SHA-256 |
| --- | --- |
| Result | `c8babd42606b4ff01e9c827ce22d6c6c0ae5f6c650c0478b11ecf2bff205bf19` |
| Driver | `0ecac7e88088fa4b06199154c5377a92a69fbeeb63bc1c3d36e1fb054aa86e92` |
| Barrier | `0b771091913888148a3a5a1f17f269b1d5bcb3e4d107d5697b8ef987ae1d8d0f` |
| Settlement review | `46b85b3ee40d4fc09fe1746177f96de585633af0c0e04d8a67553d31fcf9524e` |
| Settlement | `3e3296cf30703099255becc5e4152f0e540d9e8ba8cf912a81772d4d55b1d380` |

CI 37346459228 at `e576633` and 37347162446 at `e6e3a2f` passed; full job/step
JSON is retained. The frozen `e576633` source now supports a fresh public
text-length task: empty-input error, counting Maple as five characters, and
reset. Only a blank page and requirements are supplied; local OpenCode/oMLX
chooses and writes the implementation. The prospective one-to-three inspection
workflow retains required intervening revisions, final verification after the
latest edit, exact child context, all completed tools and strict state checks.
The old duration/form/counter failures remain unchanged.

Nineteen groups of author checks passed for the fresh protocol, including full
source/prior-chain checks, intercepted trial and main paths, artifact negatives,
one/two/three-child fixtures, state/context/chronology negatives and exact usage.
The original duration controller functions are unchanged; the acceptance and
state checker differ only in task literals/selectors. New source validation
preserves every routing-control predicate with explicit forwarding of current
counters to the isolated historical check; fixed settlement counters stay fixed.
Nine launcher checks preceded one bootstrap with verified process 94088. The
same 300-second CLI/request limits, canonical role schemas, before-forward relay
checks, resource emergency stops, browser isolation and APFS phases apply.

| Fresh length UI V1 artifact | SHA-256 |
| --- | --- |
| Runner | `1af1f139c73ad416fd9a2f2298d5fbb37fcdee74ad1ecd5ef9bc56b5fdb10dc7` |
| Predeclaration | `e4456c89e4123e72b03e900da8f1e64ad00423b7f09b7e01fc39cec4a135eb2c` |
| Manifest | `722a4fe6837ecfb884c031591056fcbdbf1b5a8a407bd291b59b1cc0bee89ebe` |
| Author review | `8a738805af4fbbbc2345456ab2f2c47ff42278edbcec76717eb80e3e1fc1bfb7` |
| Launcher review | `0c81e86ec9737c8fdd03f06f7ac3892ba9507d127954b1b6fa40c8492b1579d3` |
| Launch | `045180c2a44d0bc06c2e648a4bacf11e19e653bd5a69abb269529b370f382fd7` |
| Activation | `e0df2cf14004d6e300b08e80949a8b4eb02e8f3d6e5a286e8abc07b67220c238` |

Outcome is unknown at launch. No product code, version or owner install changed
in this checkpoint. PR #242 remains draft. Broader development, valid
fresh/protected validation, sustained coding/UI, full-context reasoning,
endurance and final truthful production scope remain open; this is not completion.

## Length UI failure settled; skill relevance correction

The text-length run completed its native CLI in 106.364 seconds with 16 local
requests, but its original strict protocol **failed**. Agent loaded `opencode`
first, wrote the page, then loaded `report`, called `skill` with subagent arguments
(missing `id`), attempted nonexistent skill `browse`, and finally delegated Browse.
The two skill errors remain failures. Browse completed seven permitted observations
with the exact empty-error, five-character and reset states, then added a screenshot.
That eighth action violates the declared action set and final-snapshot rule. Neither
correct functional observations nor a completed native session upgrades the result.
There was one child and no intervening repair. The artifact callback only checked
the retained 1,262-byte page; it was not an independent functional grade.

Separate settlement explicitly requires the observed root sequence, both exact
errors and the extra screenshot, then checks the seven preceding observations and
all remaining context, chronology, ownership and isolation predicates. Sixteen
author checks, including ten negative projection cases, passed. All 67 files and
both whole images remained unchanged; the exact inactive exit-one job was removed.
Browser ID/name/broker absence, closed port, two detached images and three empty
owned mount paths were verified. All 58 parent, 51 native and four capture resource
samples were normal; 49 power samples were AC at 90%, with complete finals and
zero sampled swap growth. Absolute swap remained nonzero. The 16 requests account
for 83,707 prompt and 3,117 completion units. One original unload left runtime
85947 idle at 103 requests, 520,655 prompt and 21,219 completion units.

The first settlement review failed before mutation because its copied comparison
used spaced JSON serialization for a compact-JSON digest; the exact error also
contains literal newline escapes. The new settlement fixes those representations,
pins the old script/review failure and retains all evidence predicates. The old
settler was never executed. This is a review failure, not a task replay.

| Length UI V1 terminal evidence | SHA-256 |
| --- | --- |
| Strict failed result | `1abd07434e4998e9591fd392e1ec07e9d6fd3a0e11986e6d843816c88f7ed10c` |
| Driver | `4985ef30b4bfb1c815373fe4c936d8af8d7e5ca89d0f954b26c00cfe728bd9ba` |
| Barrier | `cf2faa95ff1223078611997e2c4c9a758f636f23118178fd47768a944cf9dab6` |
| Retained first settlement review failure | `1d0436c77955f8c5cb0f86db073058e19787d4c07866c18643f85b3b44a85cd5` |
| Passed settlement review | `9561541d43cc2736bc683963177ee5c6bba2246d072eb61518de5bc16a8b93d9` |
| Settlement | `750d350f8d7b7b051c64963d9d07e66e112cd99b10c1f8c547cd17bb5035721f` |

The retained native skill outputs expose a concrete product guidance error:
`opencode` is documentation for configuring and integrating OpenCode, and `report`
prepares OpenCode issue reports. The preceding instruction to load `opencode`
before ordinary coding therefore forced irrelevant documentation. One existing
Agent/Build guidance string now says to use skills only when their descriptions
match the task and explains those two built-in scopes. It retains the explicit
`subagent`/`agent: browse` routing guidance. The existing regression checks the
corrected instruction and unchanged tool availability. This does not establish
that the earlier instruction caused the later skill errors or screenshot, or
that the correction improves model compliance.

CI 37348333380 at `b339736` passed; full job/step JSON is retained. The next
prospective control will check delivery of the corrected guidance in actual native
system requests without forwarding to oMLX. All prior task predicates and failures
remain frozen. No engine, catalog, permission, resource guard, browser boundary,
relay, APFS, scoring, version or owner-install change is involved. PR #242 remains
draft; broader research and final production scope remain open.

## Relevant-skill guidance control launched

Code `23815ca` passed 220 setup tests, 214 research tests (two skips), 87 Node
tests, native/frozen offline checks, two targeted hooks, clean-source package
smoke, 17 documentation entry points/link checks and one-commit secret scanning.
The first validation-receipt writer looked for a nonexistent PASS string in the
successful package output and stopped before writing a receipt. Its separate
failure note is retained; the corrected writer checked the actual package JSON
and exit-zero result without rerunning the package check.

A new authentic, detached, read-only source contains 414 tracked files. Its
98-file research runtime map is unchanged, and five packaged plugin assets are
pinned separately. Reversing only the single changed guidance line reproduces
the previous plugin. A fresh six-response canned native control reuses the same
write/delegate/navigate/snapshot workflow, HTTP dispatcher, read-only system-text
metadata hook, exact child context and original safety checks. It expects the
corrected complete guidance once in each Agent request and absent from Browse
requests. No model request is forwarded; this tests delivery, not model behavior.

The control passed 26 author checks: full source/prior-chain/current-runtime
validation, unchanged controller/trial/metadata/acceptance AST checks, actual
canned HTTP/SSE dispatch under the metadata hook, role/context/guard/ownership
negatives and failure preservation. Nine launcher checks preceded one bootstrap,
with process 4387 verified by executable hash, proc_pidpath and exact arguments.
Runtime must remain unloaded and idle at 103/520655/21219; no runtime operation
is allowed. All resource stops, automatic admission, browser isolation and APFS
phases remain unchanged. No task, acceptance function or grader was replayed.

| Relevant-skill control V1 artifact | SHA-256 |
| --- | --- |
| Code validation | `28a72b07a6b140bd56e4c0c4a5a28e97a031a29ed9e86ad4f2066242a36b203e` |
| Native skill-scope diagnosis | `95d862ed9178341a60424988ca5849bac54048a489ff9b46f0f8168455946c50` |
| Source proof | `9e60288974dccc19d3b67dbb64d26325174d09af0d9c32074d989aad0a3a6586` |
| Runner | `34315481c937c9dfb1c866c6259d237b8dde5130919375823a95691ed2db92e4` |
| Predeclaration | `e4c1d5c8fbcca81e95e57e39aa77bcc662f15c3cc6f0672f2c88a6ae7429e22b` |
| Manifest | `aab11fe8669b382ddd8bf9f0f0dd78ed86c924163a2e901786ec82dbb3d3f80a` |
| Author review | `8c05eb73fdd2760f8aaa67ad83bde6f7db39580e87a839bdae43161cc0180e67` |
| Launcher review | `cf5ff12b37fbd86cb18a52ecf9193205e7cb5f939910247b87c47ecd6b64e1ba` |
| Launch | `fe6e3f37bd412b8491b9127ae646b3e6077bfdcbae7ad63ffa3b17ff4668544f` |
| Activation | `59d2eeb8a8e49d8dd6a5abdf562a126c09b5f6b4984a8ee6b048ad31255bd86d` |

Outcome is unknown at launch. Code and launch-doc CI will be inspected once at
the next meaningful terminal. PR #242 remains draft; production scope and broader
research gates remain open. This launch is not overall completion.

## Relevant-skill delivery settled; native test feedback next

The relevant-skill guidance control passed. Six canned requests completed in
9.778 seconds, with the corrected guidance exactly once in every Agent system
request and absent from Browse system requests. The separate terminal review
verified complete canonical tool catalogs, sampler/body metadata, exact child
context, native chronology, initial policy inventories and the sole 318-byte
patch against capture. This proves delivery of the guidance, not improved model
behavior or full system-prompt provenance.

Settlement passed after a separate 18-check author review and removed only the
inactive exit-zero job. All 61 retained files remained unchanged, both images
were retained and detached, all three owned mounts were empty, and the exact
browser ID/name/port and broker were absent. Runtime 85947 remained unloaded and
idle at 103 requests, 520655 prompt units and 21219 completion units, with no
runtime operation. All 13 parent, six native and four capture resource samples
were normal with zero sampled swap growth; 11 power observations were AC at 90%
and 94 W. Absolute swap remained nonzero. This is not endurance evidence.

| Relevant-skill V1 terminal artifact | SHA-256 |
| --- | --- |
| Passed result | `82130499b88af89b329a29a1fe44c2dd2eed72ad3752ff4f3a57bf14b0d55c27` |
| Driver | `0b74368cde88c145ef0de75d366011567c6e51a7e38b8f8f2c4703ebbb84c79e` |
| Barrier | `1e7712c71b2b1116d8d38e7658d87987864e3359dae538e07f491ebd788fa29f` |
| Settlement review | `73f0bb9877aa83eb5e1954b8567da439fbfbf9049b11ffef6df2b92dd7b9110e` |
| Settlement | `9ec673740b44611de6112b692bebfde2b3eb0dc23a844e2db3803e642d8bf290` |

CI 37350022379 for code `23815ca` and CI 37350192990 for launch docs `3f8b283`
both passed; full job/step records were retained once. There is no product-code
change at this checkpoint. PR #242 remains draft.

The next mechanism changes approach to native test feedback: a fixed canned
Agent writes a public before fixture, runs an unchanged trusted Python check
that must exit one with the expected failure, writes the after fixture, runs the
same check that must exit zero with the expected success, then stops. No skill
or subagent is required. It retains the existing native boundary, catalogs,
permissions, browser isolation and three APFS phases; the browser is present but
unexercised. The artifact callback only compares data and trusted-check bytes;
it does not execute candidate code. This control cannot demonstrate model repair
ability or benchmark quality.

The first new preparation mistakenly included `.git` in a file-permission glob,
removing directory traversal. Its first review stopped before admission. That
entire V1 draft is retained and retired unrun; a fresh V2 restricts permission
changes to regular files. V2's first review completed the actual preflight but
its synthetic barrier fixture omitted the existing `workspace` field. That
review failure is also retained. The subsequent review restores the actual
barrier/driver relationship and asserts its schema before exercising acceptance;
the V2 runner remains unchanged. Neither failure started a native task, browser,
APFS trial or model request. All prior UI task failures remain strict failures.

The V2 control passed eight groups of author checks, including the complete
preflight, unchanged dispatcher/boundary/admission/main operations, trusted
check outputs, synthetic native exports and failure cases, actual capped
HTTP/SSE dispatch, artifact negatives and main failure preservation. Nine
launcher checks preceded one bootstrap. Process 19703 was verified by its
framework executable hash, proc_pidpath and exact arguments. The existing
supervisor enforces safe admission and all original emergency stops. Runtime
must remain unloaded and idle at 103/520655/21219 without any runtime operation.

| Native test-feedback control V2 artifact | SHA-256 |
| --- | --- |
| V1 retired-unrun record | `fc3b3220979daeabae21f70af93d0fc605c4726adb860104d6095c3e32ebd2c1` |
| Runner | `1ef48733643dc010d3bfc9ce501b66e8356213cd18baadc67dd90cf8997add43` |
| Predeclaration | `3e9aecfd0c4c3059f5be9dd089e97ef9986188d8594732ceaeb02273f4c30c86` |
| Manifest | `7cf41b12da6e77555307aa1e8666e0b8533c85a29320b0e7be1e0fe94e1bb26a` |
| Passed author review | `41b3a53967e3349c8802d92929286ee67ef713ee8e5a6ca191261c32fbd9951b` |
| Launcher review | `b57e05c4858af3b8fa110b1dc7d73fbe858bb305d954293bb0535a27017819c7` |
| Launch | `61be7c57c46f70946ce68ef41ae0e8e7615626f7410e9ee538239c9e4727f08a` |
| Activation | `24fa01b3547695f2e164c7c47f953ea6be0ac7788198afb69d2bb7922e8f4d1f` |

Outcome is unknown at launch. The next wake will inspect compact current state
and leave an active or safely waiting worker alone. No original task, grader or
acceptance function was replayed. All broader research gates and final scope
remain open; this launch does not complete the overall goal.

## Test-feedback startup failure settled; retain native guard reasons

The test-feedback V2 control failed before a native task session or tool call.
During browser MCP startup, child resource sample eight recorded a listener
query timeout after 3.062534 seconds and an empty listener inventory. The original
guard correctly latched `resource telemetry missing or listener identity
ambiguous`; the following two samples recovered listener 85947 but retained the
stop. Memory pressure stayed normal and sampled swap growth was zero. The
underlying query-timeout cause is unknown; this is not evidence of model memory
pressure or a model-ceiling problem.

No canned response or model request occurred. Runtime stayed unloaded and idle
at 103/520655/21219. No task CLI result, session export, patch, capture phase or
grader phase exists. The candidate volume detached. Separate settlement checked
all 40 retained files, the whole candidate image, the sole empty owned mount,
exact browser ID/name/port and broker absence, and the closed canned-relay port.
It removed only the inactive exit-one job. The 20 parent resource samples and 13
AC power observations passed their original checks; the 11 child resource
samples retain the telemetry failure. A settlement-review fixture initially
tried hashing an intercepted output receipt that did not exist. The failed
review is retained; a separately corrected review intercepted only that output
hash and passed before actual cleanup. No task or original acceptance replay.

The native external driver already rejects a latched guard failure, but its
report omitted the reason when startup raised before a session existed. One
report assignment now records `monitor.guard.reason` after monitor closure.
The regression exercises the real monitor and driver failure/finally path with
missing telemetry followed by a recovered final sample; a separate unrelated
preflight failure retains a null guard reason. No native server, browser, model
or external request runs in that test. Guard logic, query deadlines, emergency
stops, admission and completion predicates are unchanged. Old frozen receipts
are not rewritten.

| Test-feedback V2 failure and reporting evidence | SHA-256 |
| --- | --- |
| Original failed result | `eb697808be910f122570beb2c5ec485d7007f422db507bfc20ba0c855338d930` |
| Driver | `b872de9f76f4eb1671b2db8a2e39fb17f77c6dfc0db228971e99e05dfc75d26a` |
| Barrier | `9a90a9387a285eb79282e271f5266797322e01bd76ac3fa7fc88a4975febe31f` |
| Passed settlement review | `0aee550977be9b1773851379ac8514f19a91febccace130322cae1e4f09b4d71` |
| Settlement | `6fc6f2909e02e504f94ba53d7acd454cd11cc9b8c8dc5e0235a9194a3b9a4443` |
| Reporting diagnosis | `7afcf11863272c25bebe7f87a12212740a1eba20c17536c01363b9777cefd795` |

CI 37351882965 for docs `5b62b15` passed and its full job/step record was retained
once. The next prospective control will isolate native shell exit/output
reporting without a browser, using a fresh fixed public probe rather than
replaying the failed workflow. It will not demonstrate model repairability or
benchmark quality. PR #242 remains draft; broader gates and final scope are open.

## Fresh native shell exit control launched

The guard-reason reporting fix at `4a37ce8` passed 220 setup checks, 215 research
checks (two skips), 87 Node checks, native and frozen offline checks, clean-source
package smoke, 17 documentation entry-point/link checks and one-commit secret
scanning with zero findings. The receipt writer initially expected one package
JSON record; the successful log contains separate build and package-check
records. That writer failure is retained. The corrected writer used the retained
successful output without rerunning any check.

A fresh frozen source retains all 414 tracked files and pins the 98 research
runtime files. Only the driver reporting assignment and its regression differ
in that runtime map; all five packaged plugin assets remain identical. The new
control isolates root shell exit/output reporting without starting a browser.
It uses a fresh public trusted probe that writes distinct stdout/stderr markers
and exits seven. Two canned responses request that exact command once, then
stop. The native shell tool must complete with integer exit seven and both exact
output lines; the patch must be empty, the trusted probe unchanged, and no skill,
subagent or browser action may occur. Full canonical Agent request metadata,
owned-session settlement and all existing guard finals remain required.

This is a different prospective mechanism, not a replay of the failed
write/check/revise/check control. The artifact callback reads and hashes the
trusted probe; it never executes candidate code. The existing native engine,
Agent catalog, permissions, admission, local-only boundary and three APFS phases
remain unchanged. Runtime must stay unloaded and idle at 103/520655/21219.
There is no model forwarding, benchmark task, independent functional grade,
model-repair claim or quality score.

Seven groups of author checks passed, including the full preflight and prior
chain, exact source compatibility, original dispatcher/main/guard operations,
fixed public probe outputs, complete synthetic native evidence with negative
cases, actual capped two-response HTTP/SSE dispatch and failure preservation.
Nine launcher checks passed separately. The job was bootstrapped once; process
40084 was verified with proc_pidpath, exact arguments and executable hash.

| Shell exit control V1 artifact | SHA-256 |
| --- | --- |
| Code validation | `e1af7c32da3631e663d5ff649a423cb3d71903fa5037f9a0ed040c6458227123` |
| Frozen source proof | `8ddc0ef3ccbeb9c1c5d51ba1d5af7e9ce6c66cb907df4128f353bd60494e57d8` |
| Runner | `d14b095ccec869896203a0392f1c7ba79ec4a29b391c615bcb94043d9a5986da` |
| Predeclaration | `e18816194fe0df06d461486458e260d1337cba19dda7e3d865d86274d8a5dcd9` |
| Manifest | `388011c879f7006c2b1d3726a2a21dc3d9280570757d55a5090eae1850c1e79f` |
| Author review | `a284f6e0bac9ff130acb7021695d18051d13de7884d8d60dc8f979e52aa0aea4` |
| Launcher review | `83e9e5f784cf05ae8b75f3a97eab0da046bd758d84a982470d02327760e7a216` |
| Launch | `51b62704dadaf87949af167d2a9632c6b4fb9e0d55d73b3dad96eb0a193dfb64` |
| Activation | `1fda410c1515b9556d293319c50c45d2b7e5aa4541e46c94134d0000739841d8` |

Outcome is unknown at launch. The next wake will inspect compact state and leave
an active or safely waiting worker alone. Code and launch-document CI will be
inspected once at the next meaningful terminal. PR #242 remains draft, all old
failures remain failed, and broader research gates and final scope remain open.

## Empty-patch barrier failure and prospective correction

The browser-free shell control remains a strict failure. Its one native shell
call completed with integer exit seven and both exact public stdout/stderr
markers. Two canned responses completed in 8.068 seconds; no model request or
browser occurred. The captured patch was exactly zero bytes. All three volume
phases detached, but the later Git `apply --check` returned 128 on that empty
file, so the artifact callback never ran. Runtime remained unloaded and idle at
103/520655/21219. The 12 parent, five native and four capture resource samples
were normal with zero sampled swap growth and complete telemetry.

The barrier now treats only a zero-byte copied patch as an unchanged baseline.
It still validates and applies every nonempty patch with the original sandboxed
Git commands. A regression uses real sandboxed Git to check an empty patch,
malformed and whitespace-only patches, and a valid edit. This changes artifact
application, not task acceptance, tests, grading or emergency stops. Original
frozen sources and the failed control remain unchanged.

The frozen control also had three unexercised evidence-checker mistakes. Its
synthetic fixture omitted native model `variant: default`, invented a top-level
driver `session_id`, and copied the nine-tool UI catalog into a browser-free
protocol. The actual non-UI catalog contains ten tools, including `webfetch`;
the existing UI configuration explicitly denies that tool. The first settlement
review caught that catalog mismatch before any cleanup mutation. Its failure
and original settler are retained. Separate failure projection requires the
actual ten-tool metadata and exact recorded native shape; it cannot upgrade the
original failure. Future protocols must declare the correct shapes before they
run. No permission or tool-catalog behavior changed.

CI 37353184466 for code `4a37ce8` and CI 37354190481 for docs `5a92cf3`
passed and their full job/step records were retained once. No task, grader or
original acceptance function was replayed. PR #242 remains draft; native shell
observations do not establish model repairability or broader product quality.

## Shell failure settled; fresh read-only capture control launched

Separate shell-control settlement passed without upgrading the failed result.
All 67 pinned files stayed unchanged before and after removal of the exact
inactive exit-one job. Both whole images remain retained and detached, three
owned mounts are empty, and the owned native process and canned listener are
absent. Ten power observations were AC at 90%; all parent/native/capture guard
finals passed. The first settlement review's mistaken nine-tool expectation and
its unexecuted settler are retained. The subsequent projection requires the
actual ten-tool catalog, model variant and owned-session roster, plus the
original empty-patch failure. It never calls original acceptance or grading.

The empty-patch fix at `f14be06` passed 220 setup checks, 216 research checks
(two skips), 87 Node checks, native/frozen offline checks, the targeted real
sandboxed Git regression, clean-source package smoke, documentation/link/diff
checks and zero-finding secret scanning. A receipt writer incorrectly expected
both package JSON records to contain `version`; the build record contains
`source_dirty`, while the installed-package record contains `version`. That
writer failure is retained. The corrected writer checked each actual schema
using the successful logs without rerunning the checks.

A fresh no-model control reads a different public data fixture once through the
native read tool and stops. It requires an empty patch to pass through all three
APFS phases to the unchanged-byte callback, with no shell, write, skill,
subagent, browser or model request. The declaration uses the complete observed
ten-tool non-UI catalog, `variant: default` model metadata and the actual
owned-session roster. These are prospective corrections to the new protocol;
the failed shell protocol and its review remain immutable. The new source changes
only empty-patch application and its regression in the 98-file runtime map; all
five plugin assets are identical.

Seven groups of author checks passed, including full prior-chain/source/runtime
checks, the exact two-line source reversal, original dispatcher/guards/main
operations, actual native metadata shapes, complete synthetic evidence with
negative cases, capped HTTP/SSE dispatch, data-only callback checks and failure
preservation. Nine separate launcher checks passed before one bootstrap.
Process 64800 was verified with its executable hash, proc_pidpath and exact
arguments. Runtime must remain unloaded and idle at 103/520655/21219; all
admission and emergency stops remain unchanged.

| Read-only capture control V1 artifact | SHA-256 |
| --- | --- |
| Shell failure settlement | `58a7c6918a6b9d9935ff5d8c643e7fa25c51049119493f0008527b8bdff70400` |
| Code validation | `89454c93cecd0f5f80f21e5ee04771b166c44f80247d54fa219f884b2e97bfe8` |
| Frozen source proof | `c1aa41b3702d905f78927e9fb39fcbe74bda7dd32136db928e31214be8a333d1` |
| Runner | `9a42e3a83ecd605699224bbbfa755fe1258985237c3a20597b1193d7889d6f3e` |
| Predeclaration | `ebb61fe03d995e3ea9ed9f51fe1861e7bdcbf40399ae1686bc21ef172c0bb0b6` |
| Manifest | `694d22d9aa30b7136d2a65147fbad6b2c9b9dc1c70522194f5d918dfd36587dd` |
| Author review | `ad9d5d5d0f0fc6c73d2c4ad2af8ebdf466db26216e7f4f073788a3904a4c28c5` |
| Launcher review | `9c05f17f93afb1edc7f0653aba098681c30fec2a7f2f7db6f80dc85361951c20` |
| Launch | `3ca4536df5855aa8580549b42cc4fc97549d67f914de8807bfddd3d7c16904d1` |
| Activation | `ad35b5306d778cc1cc3d50a1babf4d0bfda9ddacd6e3e9b7f20e18bd4c05740e` |

Outcome is unknown at launch. No model behavior, repairability, benchmark quality
or production qualification follows from this control. New code and launch-doc
CI will be inspected once at the next meaningful terminal. PR #242 remains
draft; broader gates and final truthful scope remain open.

## Read-only capture passed; local Python test workflow launched

The fresh read-only capture control passed. Its single native read returned the
three declared public-data lines, and two canned responses completed with no
model or browser. The zero-byte patch reached the unchanged-file callback; all
three APFS phases detached. Separate evidence review verified the complete
non-UI request metadata, root context/model/ownership, initial policy inventory,
empty capture, callback result, all guard finals and exact runtime counters.
All 62 pinned files stayed unchanged before and after removal of the inactive
exit-zero job. Two whole images remain retained, three owned mounts are empty,
and the owned native process and relay listener are absent. The 12 parent,
five native and four capture samples were normal with zero sampled swap growth;
ten power observations were AC at 90%. Runtime stayed unloaded and idle at
103/520655/21219. This qualifies the observed empty-patch mechanism, not model
quality or endurance. The earlier shell failure remains failed.

Code CI 37355472376 (`f14be06`) and documentation CI 37356016340 (`fe175e6`)
passed; their full job/step records were inspected and retained once. No product
code changed in this checkpoint.

A fresh ordinary Python project now tests a different workflow: read public
requirements, run seven public tests against an intentionally unimplemented
stub, implement only `rollup.py`, and finish with a successful test run after
the latest write. Only local OpenCode/oMLX supplies implementation. The single
root may read the three project files, write/edit the implementation, and run
one exact unittest command. Tests and requirements must remain byte-identical.
There is no browser or mandatory unrelated skill. The artifact callback only
compares trusted file hashes and records implementation bytes; it never executes
candidate code. Native test observations are public development evidence, not
an independent functional grade or protected benchmark score.

Static review retired the first unrun rollup declaration: it had copied canned
request-record fields into the real-model checker. The new V2 declaration binds
the original real relay's numeric/thinking fields, canonical ten-tool non-UI
schema, sampler and timestamp shape. No task or admission ran under V1; its
sealed files and retirement remain retained. Eight groups of author checks
passed for V2, including a complete synthetic test sequence, 23 negative cases,
data-only callback checks and actual controller success/failure/conflict paths
with operations intercepted. Four isolated historical checks were exercised
with prospective live counters; their source predicates reverse exactly to the
original ASTs, while fixed historical counters and source bindings stay intact.
These checks are not independent-author review or real task success.

Nine separate launcher checks passed before one bootstrap. Process 83658 was
verified by exact arguments, proc_pidpath and executable hash. The original
300-second CLI/request limits, 128-call cap, 8192 output cap, before-forward
sampler/schema validation, accounting before unload, exact owned emergency stop,
resource and power stops, and safe admission remain unchanged. Outcome is
unknown at launch. Inspect compact state on the next scheduled wake and leave
an active or safely waiting worker alone.

| Current evidence | SHA-256 |
| --- | --- |
| Read-only result | `1836b317b7955753c9aa3eaa9ea5ca8b52dd1e45750828da9e4e70936b0964eb` |
| Read-only settlement | `21ec6e56f44d3a0c08c862de7974d6944b27fc8e21d514e644352749674cb9e7` |
| Read-only settlement review | `9a5d0a9c01a47d8d0966765cb027173da044e3274e5d4782266eca02f1f3911e` |
| Unrun rollup V1 retirement | `6586e33598c17455c36b7c57f2da7a2d918125e81f53e79fc70e974bd6ec06fb` |
| Rollup V2 runner | `3f4b615281a9f6bb325c6dc3f8bba758e56158b42643e8110fa87f8c495f53ee` |
| Rollup V2 predeclaration | `79e6ea48f011cf07fa6bf49c723783d2d04588e58189d0eee2de97d2c7fb5d26` |
| Rollup V2 author review | `31584634e8fca205364e85f5a5926e82b89a27edb8e331a64e895903d0a6438d` |
| Rollup V2 launcher review | `6a5e3f5f4a5bec6fe67b81fa21c53a7701189fded7f08d8408fe69cda7204936` |
| Rollup V2 launch | `ec8679a98e0312272a5b2f360b58baf4298ebea4d1bc1a2f9f24521d23ca95aa` |

PR #242 remains draft. Broader development, fresh protected validation, sustained
coding/UI, full-context reasoning, endurance and final truthful production scope
remain open. No merge, release, tag, version or owner-install change follows.

### Rollup workflow failure and bounded native feedback control (2026-10-05)

The fresh local-model Python rollup workflow **strictly failed**. The native
session finished and later public test runs reported success, but the retained
trace contains six file-tool errors, extra shell commands, concurrent tool
starts contrary to its declared chronology, and truncated baseline test output.
The first two reads omitted the leading slash from a complete project path;
three further reads and one write used `/workspace` and were denied. The model
subsequently wrote through a shell command outside the declared command scope.
Those failures remain failures. The implementation and model answer were not
judged by Codex, and no task, grader or original acceptance function was replayed.

The 17 native tool records include a baseline test exit of 1 with seven errors
and `truncated=true`, then two test exits of 0 with seven tests and `OK`.
The sole 2,118-byte module patch matched capture. The data-only callback observed
unchanged public test/requirement files and a 1,877-byte implementation; it did
not execute candidate code or provide an independent functional grade. Thirteen
local requests reconciled exactly to 97,771 prompt and 2,595 completion tokens.
The original controller unloaded the model once, leaving the same runtime
unloaded and idle at 116 requests, 618,426 prompt tokens and 23,814 completion
tokens. All 64 parent, 56 native and four capture resource samples were complete
with normal sampled pressure and no sampled swap growth. All 58 power samples
reported AC power with a minimum battery level of 90 percent. This is not
endurance evidence.

A separate settlement required the exact failed tool records and checked the
remaining boundary, metadata, ownership, context, patch, guard and usage
predicates. Seven author-review groups and 19 negative cases passed before the
sole inactive exit-1 job was removed. All 69 pinned evidence files and both whole
disk images remained unchanged; all three owned mounts were empty and the owned
native process, broker and relay were absent. The settlement is a cleanup and
evidence result, not a diagnostic pass. Its SHA256 is
`912d5fd29e0d12db600e3869daa51798a21918411093ee7d9f4ecabd18204380`;
the separate review SHA256 is
`be6195fa8c2ee723d530af368a7153773683ebdc1594b71caa75e243954e7857`.
Documentation CI run `37357709462` passed; its complete job and step record was
inspected and retained once.

The next declared mechanism control addresses relative file paths and bounded
test feedback directly. A fresh public fixture contains 40 pending records and
a trusted standard-library unittest checker. Five canned native tool actions
read `./records.txt`, run `python3 -B check_records.py`, write the fixed ready
records through the native write tool, rerun the same check, and read the same
relative path. A sixth canned response stops the session. The checker reports
all 40 failing or passing record identifiers in one bounded summary, without
changing native output limits. Both check outputs must be nontruncated with exact
exit codes and summaries. Every tool must complete in the declared order.
The data-only artifact callback checks the final public bytes and unchanged
checker, and never executes candidate code. This control uses no model inference,
no browser, no benchmark, no candidate implementation and no independent grade.

The control retains the existing native engine, full ten-tool non-UI catalog,
sampler metadata, permission policy, resource and power emergency stops, query
deadlines, local-only boundary and APFS capture phases. Runtime counters must
remain at 116 throughout, with no start, load, unload, stop or restart. The full
prior evidence chain is checked with explicit current counters while historical
counter facts remain unchanged. This is a fresh fixture and protocol; the failed
rollup task and earlier failed test-feedback tasks will not be replayed.

Seven protocol-review groups and nine separately reviewed launcher checks passed
before one launchd bootstrap. The protocol review exercised the trusted public
checker against fixed pending, ready and invalid data; full synthetic native
exports, bounded HTTP/SSE dispatch, negative cases and the data-only callback
were checked without running a native task, browser, APFS trial or model.
The durable job is `dev.kryn.native-bounded-feedback-control-20261005-v1`;
its outcome is **unknown at launch**. The runner SHA256 is
`fed8fe032564aba93af738ae91754888c6f3f0b7922c6f8c88d664c11e10775d`,
protocol review SHA256 is
`aa7180853b45c216ff069b0c932c42120fca72a877fb0a88d26023cf3ef41d47`,
and launcher review SHA256 is
`ccb181f1440fb188d62e86b7574ac61660e299ddec0a9617d9a64faa4a9460c8`.

No product code, version or owner-install change accompanies this checkpoint.
Broader development, valid fresh/protected validation, sustained coding and UI,
full-context reasoning, endurance and final truthful production scope remain
open. PR #242 remains draft; none of these observations qualify a merge or a
frontier-quality claim.

### Bounded feedback passed; fresh local Python codec workflow (2026-10-05)

The fixed no-model relative-path and bounded-feedback control **passed**. One
native root completed `read ./records.txt`, the fixed checker, a native write to
`./records.txt`, the same checker and the same read. Six canned responses produced
no model requests. Both native check outputs were nontruncated: the first exited
1 with all 40 failed record identifiers; the second exited 0 with all 40 tests
passing. Their retained outputs were 740 and 133 bytes. The 805-byte sole data
patch matched capture, and the data-only callback verified the fixed final bytes
and unchanged trusted checker. It never executed candidate code. This establishes
an observed mechanism, not model repairability or an independent functional grade.

All 13 parent, five native and four capture resource samples were complete with
normal sampled pressure and zero sampled swap growth. Absolute swap remained
nonzero. All 11 power samples reported AC power and a minimum battery level of
90 percent. Runtime stayed unloaded and idle at 116 requests, 618,426 prompt tokens
and 23,814 completion tokens, without any runtime operation. No browser started.
A separate settlement review passed six author-check groups and 20 negative
projections before removal of the exact inactive exit-0 job. All 62 pinned files
and both whole disk images remained unchanged, three owned mounts were empty,
and the owned native process, broker and relay were absent. Settlement SHA256:
`1681622e80956ba9929ec073dae938ae8a891e27183f9f25a09411ece4745721`.
Review SHA256:
`b892eef7214719962531cfe7a72af996c4fd45d0e44283b78f117fd947589bb5`.
No task, grader or original acceptance function was replayed. Documentation CI
run `37360022367` passed and its full job/step record was inspected and retained once.

A fresh local-model project now asks OpenCode/oMLX to implement a small Python
escaped line codec from public requirements and two unimplemented function stubs.
Ten public tests and a trusted standard-library checker are supplied. The checker
reports every failed and errored test ID in one bounded JSON summary, without
changing native output limits. The prompt gives explicit `./` paths. The baseline
check must run before any write, all ten tests must initially error, only the
implementation module may change, and the final native tool must be a successful
check after the latest write. Concurrent reads are prospectively allowed; writes
and checks must be ordered after every preceding tool. This criterion follows the
native tool behavior and the dependencies of this new task. It does not alter the
failed rollup protocol or upgrade its result.

The candidate tests run only inside the existing native candidate boundary.
The artifact callback checks regular UTF-8 module bytes and unchanged
README/test/checker hashes without executing candidate code. Separate evidence
checks require the sole module patch to match capture. Native
public-test observations are distinct from independent functional grading. Codex
does not supply an implementation or judge the model answer. There is no benchmark,
hidden validation, quality score, causal repairability or endurance claim.

The same source, native engine, ten-tool non-UI catalog, sampler, permissions,
resource stops, query deadlines and APFS boundaries remain in use. The existing
controller reconciles exact native usage and request counters before one unload
if needed; owned-generation failures retain the original emergency stop, and
concurrent-inference conflicts permit no runtime operation. A small isolated
counter adapter retains the entire original source/evidence chain and changes
only explicit live-counter arguments; historical counter facts stay unchanged.

Eight protocol-review groups and nine separate launcher checks passed before one
launchd bootstrap. Synthetic exports cover bounded summaries, exact commands,
relative paths, concurrent-read behavior, ordered writes/tests, ownership,
metadata and failure handling. The trusted checker was exercised with fixed
synthetic unittest results only; no native task, browser, APFS trial, model or
candidate implementation ran during review. Job
`dev.kryn.native-linecodec-readiness-20261005-v1` has an **unknown outcome at launch**.
Runner SHA256:
`acce7ba5c781ec8ad1f78b4049502b68bfacf5cb9e49eb27ab040c2c0192f50d`.
Protocol review SHA256:
`b912265098f7ef96abe9518d88bfcd13f469c82009e0a1e59b1c61c2db9f8dda`.
Launcher review SHA256:
`0c38f5a32cffc69922de4d6699a3da525e3f571b6d405f3bc2eb09927274bd77`.

No product code, version or owner-install change accompanies this checkpoint.
All earlier failures remain recorded. Broader development, fresh/protected
validation, sustained coding/UI, full-context reasoning, endurance and final
truthful production scope remain open. PR #242 remains draft.
