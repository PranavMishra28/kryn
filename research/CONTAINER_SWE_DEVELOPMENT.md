# Dependency-ready SWE development worker

This prospective execution profile is **development instrumentation**, not a
product change or a correction to the completed v3 score. It moves OpenCode and
the task's tools into a Linux/amd64 container with the official historical
repository dependencies. That changes the OS, toolchain and execution boundary;
results must have separate experiment provenance. Later bounded admissions and
outcomes are recorded below; they do not authorize arbitrary new model generation.

## Worker boundary

`container_config.py` shares the existing Harbor adapter's OpenCode configuration
without importing the Harbor SDK. The Harbor adapter retains its original
configuration. The SWE profile explicitly prepends the image's `testbed` Python
environment and selects its pinned Node binary. Native and KRYN use the same
OpenCode release, tool paths, model route and permissions; the existing native
control removes KRYN guidance and product hooks.
Live SWE generation must use the admitted `/opt/kryn-plugin` placement and
protection check. The unchanged Harbor install path under `/tmp` is not covered
by this worker admission.

Tools are installed in a trusted preparation phase, before isolation or agent
work. The private build receipt pins the official base image, downloaded CLI and
Node bytes, installed packages, and resulting image ID. Preparation resets to
the frozen source commit, verifies an equal Git tree, and replaces history with
a single source snapshot. Root setup files and caches are removed. The worker
has no benchmark oracle, host mounts, Docker socket or credentials.

`container_worker.py` owns containers and networks using both random names and
owner labels. The non-root worker has a private internal network, no additional
capabilities, no privilege escalation, no forwarded ports, and fixed 2-GiB
memory/swap, two-CPU and process limits. A separate fixed-target TCP sidecar
forwards only to the host's bounded loopback inference endpoint. OpenCode still
uses its loopback model URL. The admission probe uses **canned HTTP responses**;
it cannot invoke oMLX. A future generation runner must use the existing pinned
local-only attestation and bounded `InferenceRelay`, with no remote fallback.

An internal Docker network alone is not proof of isolation. The no-model probe
checks both observed host address families, the actual bridge gateways, public
TCP, external DNS, a private host file and the Docker socket. A bridge control
must reach the IPv4 host marker, public TCP and DNS. An advertised but unroutable
IPv6 address is recorded explicitly, not counted as a successful positive
control. The worker must reach the intended canned endpoint and deny the other
destinations.

The existing memory guard is retained. An omitted or `ac-only` frozen
`power_policy` retains the 120-W/40%-battery admission rule and AC-loss/25%-battery
stops. A separately frozen `battery-capable` profile accepts known AC or battery
power, admits at 40% or above, and stops at 25% or below. Unknown telemetry fails
closed. This prospective option requires its own no-model pipeline admission
and model preregistration; it cannot relabel an existing campaign.
Generation, controller, recovery and grading use the same policy. Bounded power
receipts include admission, runtime and final observations; battery-capable
adjudication requires them to cover resource sampling and satisfy the frozen
thresholds. All profiles retain independent pressure sampling, the 12-GiB disk
floor, 4-GiB writable-container cap and 8-GiB evidence cap. Caffeinate is
owned only during active work. Docker stdout/stderr share a strict streaming
8-MiB cap. Interrupted creation is reconciled by reserved owner/name; uncertain
ownership fails cleanup rather than claiming success.

## Source handoff and admission evidence

The worker and relay must be stopped before export. `container_export.py`
imports only bounded regular-file data from the saved TAR. It never executes
candidate Git configuration or extracts candidate `.git` data. It checks the
sealed config hash, rejects ambiguous/traversing paths, hardlinks, special files,
sparse payloads and excessive data. Only unchanged tracked links from the trusted
baseline can be restored, after their in-tree regular targets are validated.
The trusted baseline `.git` is then supplied to the existing networkless patch
collector. The official grader remains a separate post-settlement phase.

A frozen no-model screen passed in both OpenCode arms: dependencies imported;
read and shell calls completed; tracked and new-file changes produced identical
patch hashes; full tool schemas matched; four original source links survived;
and owned containers/networks settled. The result receipt is
`b0709a6c6f9736b037b188f76139aaffeed43fe93b923d3c33be391f2ba393d6`;
the manifest is
`c9aba9f2c87ddbb559204d9cb403772e60a83ac981e7b5acf8403de3b4cc0fe1`.
Raw source snapshots, image receipts, TARs, tool events and resource samples are
private. This is plumbing evidence, **not accepted engineering work**.
The final frozen screen enforces the all-tool/zero-exit predicate during
execution and verifies that the worker cannot rewrite KRYN policy files or
their parent directory. It uses an owned native OpenCode server and checks its
project-scoped plugin registry before and after the turn: `kryn.product` is
active from the admitted `/opt` path in KRYN and absent in the native control.
The source manifest binds the complete local Python tree and plugin payloads.
Independent admission review passed 40 checks and all 84 frozen source hashes;
its receipt is
`31d12772133995ed2f13ca01c31d54a7daf699514d87313f7ca648c299e3c74b`.
It does not qualify model generation, official grading, or resistance to an
agent altering the native server through its same-UID loopback API. Later
bounded server-log retention is covered by offline tests and must be pinned
in any new live execution.

Unsuccessful preparation and admission receipts remain retained. They exposed an
incorrect assumption about the image's initial HEAD, Docker warnings corrupting
an ID when stderr was merged with stdout, legitimate baseline symlinks, and an
unroutable advertised IPv6 address, and an incorrect assumption that Docker
copy would assign UID 0 rather than retaining the source UID. Policy protection
checks actual write denial and non-worker ownership. Concurrent source edits also made one
exploratory attempt unsuitable as frozen evidence. The passing screen used an
immutable source snapshot. Canned title/summary requests no longer consume
primary tool actions. A later activation probe first failed because it omitted
the existing native API directory/authentication contract; the corrected probe
passed and the failed receipt is retained. Final predicates reject any extra failed tool or nonzero
shell exit; successful tool calls alone cannot satisfy application acceptance.

## Remaining gates

The isolated official-grader handoff now passes two separately frozen no-model
controls. The exact exported canary remains unresolved, and the official
reference patch resolves; both have zero official infrastructure/errors, parsed
coverage of every expected test, normal sampled host memory and no swap growth.
Owned containers settled. Their manifest SHA-256 values are respectively
`5d40c467b99182dbe71333e4377a87f09cf9c8927edbdf4333e90518a0080c57`
and `262c78b5a17e659e4cbcbbbc02a5c4b32a4bdb061b450fc64f65ad58d10c16d3`.
Independent handoff review passed 59 checks, including re-parsing observed test
IDs and verifying the evaluator, wheel, source, submitted/applied patch and
ownership hashes. Its private receipt is
`66758d20ed582edd04a0b88ad2f4029c2c6aa0060107a2fd7889ef26c929c047`.

`container_grader.py` reuses the pinned official evaluator's patch application,
tests, parser and score. Its parent supplies and settles an owned container;
the upstream default networking and extra capability are not used. The grader
has no network or mounts, drops all capabilities, and keeps the fixed 2-GiB,
two-CPU and PID limits. Only this trusted grader runs as root; the Agent stays
UID 10001. Evaluator package bytes must match an independently frozen map before
grading, and worker/relay absence is checked against pinned ownership receipts.

The first preparation failed because a mutable image tag was absent; the pinned
registry digest is now used. The first executed negative control failed with an
official infrastructure error: setup's isolated pip build tried to fetch
setuptools. Both failures remain retained. The correction supplies hash-verified
offline wheels matching the image's installed setuptools 75.1.0 and wheel 0.44.0,
with `PIP_NO_INDEX` and a fixed local wheel directory. No network access, official
test edit or score override was introduced. These controls qualify transport
and grading readiness only, not a successful model-generated repair.

The official Docker SDK output path now streams attached exec results through
an 8-MiB limit and caps raw socket reads at 64 KiB, before a large frame can be
allocated. Overflow closes the transport, writes a breach receipt, and fails
the parent even if the official evaluator catches the exception. Official
patch application, tests, parser and scoring remain unchanged. A frozen live
no-model control preserved exact 7-MiB output and rejected 9-MiB output in both
streaming and byte-return modes. Owned resources settled, all six resource
samples were complete, and swap did not grow. Its result receipt is
`2ec6f9c342736594eb62b16d33eed7d2effe8078e3ecfbdc1d5804716620a5ca`.
Focused tests also exercise the pinned Docker 7.2.0 multiplexed-frame path.

Before generation, freeze a separate development experiment's source, exposed
task selection, image, prompt, arm order, sampler, complete wire controls,
budgets and independent adjudication.
Record the actual OpenCode exit code directly. An interrupted or unsafe arm
remains unscored and cannot be silently replayed.

Read-only review found that the shell inherits the native server's authentication
environment and can reach its loopback session-mutation API. This is shared
OpenCode behavior, not a demonstrated container-specific escape. Protecting
plugin files alone does not freeze agent, model or session permissions.
`container_admission.py --policy-probe` now qualifies a fixed, canned shell
control in both native and KRYN: agent, model variant and permissions change
and restore; a continuous public SSE observer captures all six transitions
inside the local shell call. Native inventories still verify protected plugin
activation/absence, matching tool schemas, and exact exported patches. The
local plugin cannot be updated through the package-only updater; the control
checks the rejection and unchanged inventory.
An independent audit verifies all 88 frozen source hashes, the raw event
ordering, restored values, exact patches, both arms' 12 normal-pressure samples,
unchanged swap, and actual owned-resource absence. Its receipt is
`377db2002c366371332b73639fba5875002e8ea78dc7e0a88f949bcf3bb0ba9c`.

The first policy probe failed and is retained: the pinned CLI does not enable
durable event persistence, so its historical log returned only a sync marker;
an omitted permission list also differed from the restored empty list. The
corrected control subscribes to `/api/event`, waits for `server.connected`
before starting work, and requires a post-turn sentinel and native watermarks.
It fails on disconnect, overflow, missing sentinel or unexpected transitions.
Public event sequences omit private usage records; gaps do **not** prove lost
events. These receipts establish the observed API behavior, not absence of all
transient changes or protection against same-UID interference with the server
or observer files. Environment and global configuration changes are not covered
by the six-event control. Future trials must retain this scope and record the
actual relay model and wire settings independently; no new framework or stronger
isolation claim follows from the control.

The first study should test whether ready dependencies reduce observed tool
failures and timeouts. A reused public task is development-only. Require genuine
accepted work before fresh validation, holdout or long-horizon promotion. Do not
combine this profile with the v3 macOS score, infer general uplift from a canary,
or treat worker admission as production/autonomous qualification.

## Native generation and candidate handoff

`container_generation.py` now drives one frozen native OpenCode arm using the
admitted worker. It records the direct CLI exit, exports the root and owned
child sessions, and checks their native completion and settlement. Timeout is a
separate failure even when the CLI wrapper can be stopped cleanly. The stopped
worker's partial source is exported before disposal when safety permits. An
unsafe export retains the exact stopped worker and ownership receipt; it does
not claim cleanup or permit official grading.

The relay records every actual inference control, including `thinking_budget`.
Primary requests must match the frozen sampler digest and exact tool-schema
allowlist. OpenCode's root and general child have different native catalogs;
both are pinned, with the same sampler. Unknown catalogs or sampler changes
fail closed. Every supplied output-token limit is bounded; a request with neither
token field receives an explicit bounded default before forwarding and hashing.
Only one generated choice is allowed. Rejection receipts prevent a valid earlier
request from making a later rejected run appear complete.

The first canned child controls failed the new single-catalog predicate even
though both native sessions completed. They remain failed evidence. The corrected
controls use the two observed catalogs. Policy capture now detects root-session
changes from the first tool input through the final watermark, including changes
restored between tool calls, and checks the final agent/model/permissions snapshot.
It retains the public-stream and same-UID limitations above. Retention-inspection
errors are persisted while cleanup of other owned resources continues.

Candidate grading binds the exact generation manifest, task, prompt, arm,
completion receipt, ownership receipt and patch before using the same official
evaluator. A valid grade and a resolved patch are separate fields. The grader
never emits strict agent acceptance: interrupted or timed-out generation cannot
be promoted by an official patch result.

The separately frozen generation/hand-off control results and their independent
receipt are recorded in the campaign report. No real model generation is admitted
by canned controls alone.

`container_controller.py` sequences one native/KRYN pair with durable stage
receipts and the existing power, memory, disk and runtime admission. An interrupted
stage is never launched again. `container_recovery.py` stops only resources whose
recorded ownership and image match, exports stopped candidate work when safe, and
records interruption as unscored. Recovery does not change the original receipt.
A clean empty patch is a terminal no-change failure. `container_adjudication.py`
independently checks native root/child completion, actual wire settings, policy
events, official grader evidence and resource absence. A resolved patch cannot
upgrade an incomplete agent run. Synthetic controls have a distinct terminal
receipt and cannot enter real-model scoring.

The first controller canary exposed a Python-version mismatch in TAR import and
an omitted route-control container in the recovery ownership rules. That failed
attempt is retained. The importer now clears member metadata during explicit
iteration on Python 3.11; recovery recognizes the route-control's exact pinned
image. CI also runs research regressions under the evaluator's Python version.
Current-source normal controls and separately observed crash recovery now pass
independent admission. The original crash observer's stale-PID lookup failed and
remains failed; its read-only addendum verifies the actual restart without another
kill or arm replay. The separate real-development preregistration and dedicated
launchd controller are recorded in the campaign report. No quality result follows
from admission. The completed v3 supervisor remains untouched; new Linux
development cannot be mixed with its scores or called protected work.

The first real development pair subsequently passed strict independent acceptance
in both arms, with complete official test coverage and settled resources. It was
a tie; KRYN took longer in this single run. The campaign report records the
receipts and limits. Prospective pairs can freeze either native/KRYN order;
adjudication checks the observed chronology and excludes order violations.
Repetitions and reused public tasks remain explicitly exposed development work.
No general uplift, frontier equivalence or production promotion follows from
this one accepted pair.

The subsequent power-interrupted control exposed an API compatibility issue:
Docker Desktop's API 1.56 inspection omitted requested writable sizes for its
stopped worker, while API 1.45 returned exact bytes for the same ID and owner.
The initial correction pinned sized inspection to API 1.45. A later stopped
Sphinx worker still omitted both size fields at that version, including through
a direct daemon request. The prospective usage query now uses the same local
daemon's API 1.45 container-list endpoint with size enabled and exact ID/owner
filters. It requires exactly one matching identity and an explicit nonnegative
integer byte count. Missing or invalid values still fail closed; the 4-GiB limit
and every other guard remain unchanged. No absent size is interpreted as zero.
Original interrupted and failed recovery attempts remain unscored. See the
campaign report for the read-only receipts, completed unscored salvage and
remaining prospective admission gates.


The separate Sphinx salvage subsequently preserved the stopped worker's complete
export and settled its resources. Settlement verified the original 220 campaign
files, the export member inventory and archive, all resource and power records,
and actual owned-resource absence before removing the three inactive jobs.
The original campaign remains `needs_action` and unscored; KRYN and the unused
terminal auditor are retired. Cleanup does not create a matched result.

A later guarded pytest layout screen measured the cached image's ignored,
untracked 590-byte runtime version file and its exact hash. The installed
package imports from the repository; `setuptools-scm` is absent. The screen passed
with normal resources and verified cleanup, but qualifies only package metadata.
A separately reviewed no-model preparation now preserves just that measured file
across cleanup, keeps the original Git tree exact and checks the package import.
It does not reinstall or regenerate metadata. Repository controls and loaded-model
memory readiness remain required before another real comparison.

That preparation passed with the exact original Git tree, all 1,007 baseline
files and the preserved version metadata. The subsequent pytest canned controls
failed in both arms before a model request or official grade: Docker copied the
sealed host policy probe's owner-only mode into a nonroot worker. The independent
audit withheld admission. Complete exports and unchanged receipts were verified,
owned resources were absent, and the inactive controller job was removed.

Admission and generation now share one installer that stages identical probe
bytes with read-only access for all users before copying into the worker. The
sealed host source stays unchanged. An isolated container diagnostic reproduced
the original unreadable copy and verified identical readable, nonwritable probe
bytes and a protected parent under the actual nonroot user. Its resources and
cleanup passed. The original failed controls remain failed.

An explicit source/image compatibility check then permitted new corrected-source
pytest canned controls. Both KRYN and native completed the CLI and root/child
sessions with six synthetic calls and the expected negative official grade,
covering two fail-to-pass and 86 pass-to-pass tests. The preregistered audit passed
all eight guard logs, including final samples; 94 resource observations were
normal, and all 77 power observations were on AC. The 256 evidence receipts
remained unchanged through verified ownership settlement and inactive-job removal.
These controls establish pipeline validity, with no model-quality score.

The separate positive reference control passed under the same source and image
in 14.244 seconds, with full two fail-to-pass and 86 pass-to-pass coverage. Its
preregistered audit and settlement verified eight normal resource observations,
six valid power observations, final guards, 57 unchanged pinned files and actual
owned-resource absence before removing the inactive job. The reference patch
remains private. The official grader runs as root inside its offline container;
candidate workers use UID 10001. Neither control provides a model-quality score.

A subsequent no-generation diagnostic loaded the local model, observed it idle
for 180.214 seconds and unloaded it. All 13 loaded-status observations preserved
the inference counters and reported 8,597,826,742 bytes of model memory. The 87
resource observations had normal pressure and no sampled swap growth; all 75
power observations were on AC. Settlement verified unchanged inputs and receipts,
the original runtime idle and unloaded, and removal of the inactive job. This
qualifies only the observed idle interval.

Two later fixed synthetic text requests passed, first without a worker and then
with an idle isolated OpenCode/KRYN worker present. Actual prompt/completion
usage was 14,381/340 and 14,383/573 tokens, with exact runtime-counter
reconciliation, normal sampled pressure, zero sampled swap growth and final
model unload. Their separate settlements preserved 43 and 100 pinned files and
removed only inactive jobs. Neither request exercised agent tools or a benchmark.

The subsequent real synthetic root/general-child tool diagnostic failed at the
900-second CLI timeout. The root created its temporary fixture; the child read
outside the project remained unfinished. Three local requests used 14,376 prompt
tokens including cache reads and 601 completion tokens. Both sessions were
interrupted and exported, with an empty repository patch. All 840 parent/child
resource observations had normal pressure and zero sampled swap growth. The
wrapper rejected the subsequently unloaded idle state and stopped the owned
runtime. Separate settlement verified the complete archive, 1,299 unchanged
files and actual resource absence before removing the inactive job. The failed
result remains failed.

External-directory approval is a supported hypothesis; the failed run did not
capture the child's pending permission request. A separate canned diagnostic
captured an external-directory approval on its exact owned child, linked to the
unfinished read. It changed no policy and sent no permission reply. Its declared
cold start restored the same runtime profile; request and token counters stayed
zero. Settlement preserved 1,297 files and removed the inactive job.

A subsequent in-project canned control failed at its 90-second timeout. The
child read completed, but its shell hash/delete action remained unfinished. Four
canned calls left only the known synthetic fixture patch. No pending permission
was captured for this attempt, so shell approval remains a supported hypothesis.
All guard finals passed, the runtime remained unloaded idle with zero requests,
and settlement preserved 1,286 files plus the complete export before removing
the inactive job. Neither failure was replayed or upgraded.

The read-only-child local-model diagnostic completed both owned sessions and
returned CLI success in 51.744 seconds. All five local requests reconciled to
23,809 prompt and 626 completion tokens, and only the exact 258-byte fixture
patch remained. Its original acceptance still **failed**: the root changed
Python literal quote style in the shell command, violating the declared exact
text predicate. Separate diagnosis verified canonical shell arguments and
identical Python AST; it does not upgrade the original result. Settlement
verified 1,301 unchanged files, the complete export, 53 normal resource and 45
valid AC power observations, and exact resource absence. The runtime was
unloaded idle and the inactive job was removed.

A subsequent fixed synthetic text request with an idle isolated worker passed
at 57,406 actual input tokens, zero cached tokens and 3,080 completion tokens in
148.345 seconds. Runtime counters reconciled exactly; one unload returned the
same runtime to idle. All 74 resource observations had normal pressure and zero
sampled swap growth, and all 64 power observations were valid and on AC.
Settlement verified the full raw response privately, worker isolation and
protected plugin, 107 unchanged pinned files and actual container absence before
removing the inactive job. This qualifies one larger-input memory observation.

The near-context request also passed: 86,078 actual input tokens, zero cached
tokens and 1,029 completion tokens in 160.914 seconds. Exact counters reconciled,
one unload returned the same runtime to idle, and all 80 resource and 69 power
observations were normal and on AC, with zero sampled swap growth. Separate
settlement verified full response equality privately, all worker/plugin
boundaries, 114 unchanged files and actual container absence before removing
only the pinned inactive job. This remains a single synthetic memory observation;
it does not establish useful reasoning across the configured context or endurance.

The separate child-shell control captured one pending shell permission on its
owned general child and linked the request to the exact unfinished native tool
call and message. The root creation and child read completed; the shell and
parent delegation were interrupted at the declared 60-second timeout. Four
canned calls left the exact 280-byte fixture patch. No permission was answered,
policy changed or model request made. The original runtime stayed unloaded idle
with unchanged counters. All 80 resource and 69 power observations passed on AC
with zero sampled swap growth. Settlement verified the complete export, 1,295
unchanged files and actual owned-resource absence, then removed only the pinned
inactive job. This diagnoses this new control; historical failures stay failed.
The first preparation's review failure remains preserved as retired unrun.

The parent-resume local-model diagnostic passed in 66.199 seconds. The parent
created a fixture, delegated its read to one general child, then resumed its
shell to verify the hash and write a completion receipt. CLI and both native
sessions completed; only the exact 538-byte two-file patch remained. Both shell
commands met the prospectively declared argument/Python-AST criterion. Six local
requests reconciled exactly to 31,964 prompt and 928 completion tokens. One
unload returned the original runtime to idle. All 66 resource observations were
normal, all 57 power observations were valid AC, and sampled swap growth was
zero. Separate settlement verified the complete archive, 1,301 unchanged files
and actual resource absence, then removed only the inactive job. The earlier
literal-match failure remains failed. This establishes this synthetic
parent/child/parent path, not general child-shell execution or coding quality.

A separate prospective admission decision now permits one bounded development
pair on the previously exposed, preselected pytest task. It binds the settled
repository negative/positive controls, source/image compatibility, synthetic
memory observations through 86,078 input tokens and the completed parent-resume
path. It rechecks 1,725 evidence files, current source/baseline and exact idle
runtime counters. This is a limited author decision to gather development
evidence; historical memory-pressure causes and broad workload headroom remain
unknown. A failed review fixture is preserved; no inference ran during review.

The prepared pair is KRYN then native, with the same model, original problem
prompt, policies, wire controls, 900-second arms, 360-second requests and
128-request limit. The frozen controller, worker, recovery and official grader
remain unchanged. A small private wrapper only forbids runtime restart and
stops before any subsequent arm after an unscored outcome. Initial admission
retains at least 60 seconds of cooldown and three green observations; all
resource emergency stops remain enforced. Started arms and graders are never
replayed. The preregistered deterministic pair audit was conditional on a complete
adjudicated pair; the incomplete outcome below retired it unrun.
The admission and protocol reviews passed 12 and 16 author checks respectively;
these are not independent-author reviews. The terminal outcome is recorded below.
Fresh/protected validation, sustained coding/UI, continuity/endurance and final
production scope remain open.


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


## Local model CLI/API continuity passed; bounded 16-turn protocol launched

The new local model diagnostic passed: one actual native CLI followed by one
native prompt API call on the same owned root completed in 45.705 seconds.
The exact 952-byte first input created a new fixture and retained a future read
instruction. The exact 135-byte follow-up omitted its path and contents; the
native model used the required read tool. The two turns used `shell`, then
`read`, produced only the declared 248-byte fixture patch, and completed both
native generations with no compaction or recorded policy mutations. The original
continuous policy classifier and snapshots passed. This establishes this bounded
synthetic continuity path, not second-CLI compatibility or general coding quality.

Four local requests and native usage exactly matched runtime counters:
0 → 4 requests, 0 → 18,833 prompt tokens and 0 → 291 completion tokens. The same
owned runtime was loaded and idle afterward, unloaded once by the original
accounting guard, and verified unloaded and idle. Parent and worker logs contain
25/22 normal resource samples and 21/19 valid power samples, all AC at 90%, with
zero sampled swap growth and final checks present. Absolute swap was nonzero;
this is neither a battery-at-load nor a long-duration memory qualification.

A separate settlement verified all 1,407 retained files unchanged, the full
5,753,856-byte archive and exact 561-entry capture, all owned container/network
IDs, names and labels absent, all frozen source/baseline/prior pins, exact CLI/API
receipts and exports, and current unloaded runtime counters. Only the exact
inactive successful launchd job was removed. Its author review exercised the
actual settlement with output and job removal intercepted before separate
execution; it was not an independent-author review. No request, task or original
runner was replayed.

| Private evidence | SHA-256 |
| --- | --- |
| Model CLI/API result | `32bcad0b832739f90096a32d97115d2dc8d29b1cce5f5c0eb0ba0d43e3e17ad6` |
| Native driver | `3361da81fe867b31fcdb9b8f1d1fe4d255ec5348a564f66841bd4fdb073a79b2` |
| Separate settlement | `5cbcdde91e4b8bef7f86da1ff40c8195b4844faa5d36ded07373e1d9307b68dd` |
| Settlement author review | `1d2caa48dee38fb49b0fe4a389d1c9b4d4ac1cdec3921f36864bae87a41b0280` |

The next prospective protocol uses a new root and fixture, one actual CLI and
15 sequential native API prompts. All 16 inputs are unique; each follow-up omits
the fixture path/content and must perform one read from the first turn's retained
instruction. Acceptance requires all 16 exports and native completions, exact
input hashes, `shell` followed by 15 reads, 32 accounted local model requests,
the sole declared 264-byte fixture patch, no compaction, unchanged full policy
and resource gates, and settled ownership. Native OpenCode owns every generation.
Only the private hook's input sequence and receipt directories changed; its
CLI 300-second, combined 600-second, POST 5-second and native settlement
30-second bounds are unchanged. Model accounting, guarded conditional unload,
exact-owned emergency stop and automatic resource admission remain unchanged.

The first author review failed before launch because its comparison treated the
new admission receipt name as a logic change. That failure is retained; the
runner did not change. A separate corrected review passed 55 checks, including
all 15 mocked POSTs, exact 16-turn acceptance, middle-request failure, incomplete
last generation, ownership, policy drift, input bounds and original runtime
guards. No container or model ran during review. A separate launcher review
passed nine checks; launchd was bootstrapped once with `KeepAlive=false`.
No outcome for this 16-turn run is claimed at launch.

| Prospective evidence | SHA-256 |
| --- | --- |
| 16-turn runner | `38c2f49a8525005bb92e23db88d585f340f50f75a02d2efe5951128da6c06112` |
| Manifest | `326f99c8ffe0e137b615aaa1ae57d5f49b0b34972b48260e74b530eeba5e0459` |
| Predeclaration | `11d342262b94cb68fdd6609eccc584f88f81227eb3511dfc61acc9e907290f8f` |
| First review failure | `bda3d074570e4476ede388f42d6e9abe223f67fb3fa21751ba6e08b1d31bdef2` |
| Corrected author review | `42cbdf607e67c3108bf927552aeaf36cb8a3587048acd60a3908b99007528836` |

Changed-commit CI run **37320571511** passed at `0442f5b`. The earlier failed
**37319186002** remains failed and was not rerun; its cause remains unproven.
The single PR stays draft. Broader development, fresh protected validation,
coding/UI, full-context reasoning, long-duration endurance and final production
scope remain open. Neither synthetic result establishes comparative uplift.
