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

## Sixteen-turn continuity passed; native UI boundary is the next gate

The preregistered 16-turn diagnostic passed in 185.682 seconds: one actual CLI,
15 native API prompts, all exact inputs and completed native generations,
`shell` then 15 reads, the sole 264-byte fixture patch, and no recorded policy
mutations or compaction. All 32 local requests reconciled with 190,611 prompt
and 3,026 completion tokens. Runtime counters advanced from 4/18,833/291 to
36/209,444/3,317; one guarded unload left the same runtime unloaded and idle.
Parent/worker logs contain 91/88 normal resource samples and 80/79 valid power
samples, all AC at 90%, with zero sampled swap growth and final checks present.

Separate settlement verified 3,125 retained files unchanged, the full archive
and exact capture, all 16 per-turn exports, frozen source/baseline/prior pins,
current runtime counters, and all owned container/network IDs, names and labels
absent. Only the exact inactive successful job was removed. The 13-check author
review intercepted output and job removal before separate execution. It was not
independent-author review. No started task or original runner was replayed.

| Private evidence | SHA-256 |
| --- | --- |
| 16-turn result | `2fdad85d519d45134559adba47f9b1d51f69ac97c12229946b1ee236b0608556` |
| Native driver | `38824cdb5e2a3cef3ffe21b2cb1a36b6e2e22c46cd0785e5c9c9983a0e34840a` |
| Settlement | `a1154a9e176c4e8e484e4141dd5716ff61eaf88a7a73e917f23c40ffdee5cad6` |
| Settlement author review | `f756c7b0e7d2a9d66874b27116f91c60726cdf338423eed978ff1aa35d2f26fe` |

This is bounded synthetic read continuity. It does not establish coding/UI
quality, second-CLI compatibility, reasoning across the configured context,
long-duration endurance, benchmark improvement or production qualification.
More read-only turns would not close those gates.

The next prospective control exercises the existing native macOS Agent→Browse
path and separate Chromium container, using a new public fixture and six canned
requests with zero model inference. It reuses the original write/delegate/
navigate/snapshot sequence, native engine, browser image and three-phase APFS
barrier. The frozen candidate source supplies the KRYN plugin. A battery-capable
parent HostGuard additionally propagates cancellation into both existing native
resource monitors, retaining their memory thresholds and latched failures.
Admission retains 60 seconds of cooldown and three green observations; the native
CLI remains bounded at 120 seconds. No benchmark or official grader is involved;
the existing synthetic marker callback checks boundary mechanics only. This
control cannot establish live model UI quality or explain the earlier CI failure.

CI **37322172389** passed at `7aa1d42`; observation SHA-256
`81b4d449e5eb277308d6cc977d15e735da12b682ec3971ae7783c18bdc45b169`.
The earlier failed CI remains failed, with an unproven cause and no replay.
PR #242 remains draft, with broader development, fresh/protected validation,
coding/UI, full-context reasoning, long-duration endurance and final scope open.

The first UI-control author review stopped before a trial or container started:
a retained-prior read-only `docker ps` timed out at 15 seconds. Failure receipt:
`974ee5f94c6c202acf2f7224d75dad7dcd6752d8e7e579df938eea0aa18d9711`.
A separate local Docker API ping and owner-filtered list completed in 1.596
seconds, finding no owned worker containers; receipt:
`0e6711ff880bc8d2648b039771040bc7e6f19a434d37c372be7424a1a2679156`.
The runner was unchanged. This later observation does not establish the cause
of the timeout or upgrade the failed review.

A separate review after that health observation passed 13 author checks,
including actual linked-guard normal/stop/latch behavior, the boundary wrapper's
fixed receipt/source selection, and rejection of incomplete generation, browser,
relay or detach evidence. The first failed review is pinned. A separate launcher
review passed nine checks before one `RunAtLoad=true`, `KeepAlive=false` bootstrap.
The control is now launched; no outcome is claimed at launch.

| Native UI control | SHA-256 |
| --- | --- |
| Runner | `ea526362fb2102d35ad545d1efe3a3d225a99f158d8c0866d3976e8bff2e76fb` |
| Manifest | `9f3e7edbd813f774262c4eac3761daac92e19c7e447a2295c0b781655a1cb756` |
| Predeclaration | `5a1569b49fde99d3855bd98530c8d51941c5669411494a86b0ad901c709498d8` |
| Separate author review | `e6b1259e5341f18d1afcd32dd59aaa18a91d00723aad957a5be69235a2b9fce3` |
| Launcher review | `dc7d3cb3caf6f6be93fd2f72ee6c27789c2fb2a3bbb166e0afda42439ea1ba08` |

## Native UI source failure settled; corrected control launched

The first native Agent/Browse boundary control failed before relay, browser or
native-session construction. `run_external_patch.run` reads the source Git HEAD
while constructing its report; the frozen source export had no Git metadata.
The barrier retained that `rev-parse HEAD` failure and detached the candidate
volume. No read-only capture or synthetic grading phase started. The wrapper
then attempted to read an absent driver, retaining a second `FileNotFoundError`.
Its returned receipt also named the canned helper's unused random directory,
while the boundary wrapper had selected a different directory. All three facts
remain recorded; the original control is failed and will not be replayed.

Original result SHA-256 is
`24b1710aacfb93f6213d8f9c03ce9fe1378cde0cd5515b76ac2120c944980708`;
trial result is
`bfa78d09a5022555a2518ad6d9e5fdceba32cdfc49c693e8875a93fa2d68bbd9`;
barrier is
`d1f53a680c847e3274b033a4b350cc7dbe18213dc4a6dcd24b9fb739055923c7`.
Separate settlement
`38bc9fc4ca6307b1432c6a22fc84945186888511dd69e07a794c18291bf90dc9`
passed after 12 author checks and separate execution. It verified all 26 retained
files unchanged, preserved the detached candidate image, checked actual image
and mount absence, empty native evidence and the original error's source
ordering, then removed only the inactive exit-1 job. Four normal resource and
three valid AC/90% power observations passed their final checks. Runtime 85947
remained unloaded and idle at 36 requests, 209,444 prompt and 3,317 completion
tokens. Settlement did not upgrade the failed diagnostic.

A separate source preparation retained an authentic detached `59ce852` checkout.
Its first whole-export equality assertion failed: exactly two research documents
differed from the earlier export. Failure
`da4ea1bbc25b2442c2cf1fe8563e8c1ebc0de79efdf48990370cf3bdccbf514f`
is preserved. A distinct source identity verification
`b866ff1465458cd9b8e17a2ea7053972b6273401d564267d111f2b6c670778ba`
proved all 414 tracked blobs against the actual Git commit and all 98 runtime
files against the original frozen map; the five plugin assets also match.
Only the two documentation differences are recorded as exceptions to complete
export equality. The original export and failed preparation were not rewritten.

The next preparation caught mixed old/new module imports before creating any
campaign, fixture, predeclaration or attempt. Its runner is retired unrun;
failure SHA-256 is
`75d39c1705dbac5517c34531d69256095a067e21f4f732fde6b030c216e20a6c`.
The fresh V3 control consistently imports the verified Git source and uses one
preregistered receipt throughout the canned trial and its export lookup. Its
wrapper preserves a trial error before reading a driver. The copied canned
trial's AST differs only in that receipt and explicit wrapper/source arguments;
the native engine, canned sequence, barrier, renderer and acceptance remain
unchanged. This is a prospective new fixture, not a replay or acceptance change.

V3 runner SHA-256 is
`689c7ef2cf42ef8fbacb587001d2b43bd8c0f7168ef2f3396137494c645a90fd`;
predeclaration is
`e40afe3d112b385e517beb6e2898b50e611e51a4093e32515aa3f47f3ebc4006`;
manifest is
`fa298690feeeb4015e81456277fc38cc732b4f43e55e55aef8a2e3f30af611a9`.
Fourteen author checks include the real native source-provenance lookup stopped
before relay creation, a complete trial mock that reads exports from the same
receipt, failure reporting, guard latching and rejection cases. Review
`8113f19fe02890c8bfa66b2e4a62e605ef224d9ad0dc881e9adfcbdad4553867`
passed before a separate nine-check launcher review and one launchd bootstrap.
Launch receipt
`d12f71a5da483c11397acd9364f3eafc93214b3a41fdac838ec81757c53785ef`
records the initially verified PID 10252. No outcome is claimed at launch.

One KRYN arm, six canned calls, zero real model requests, the original 120-second
CLI bound, exact browser image, APFS barrier and linked parent/child guards are
still required. There is no model load, unload, restart or inference operation
in this control. It qualifies neither UI task quality nor production readiness.
CI **37324458958** passed at `fabcf06`; observation SHA-256 is
`68bd0e43c9a9734ad5c695b09031b0fcae4b2de42c19db6069db576bc08b23fc`.
Earlier failed CI and controls remain failed without reruns.

## Native UI interpreter failure settled; supported-runtime control launched

V3 failed before a native OpenCode process or model request started. The research
launcher used Python 3.11, but the native engine requires Python >=3.13 and uses
`TemporaryDirectory(delete=False)` to retain scratch when shutdown is unproved.
The native driver, barrier, trial result and wrapper consistently retained the
unsupported `delete` argument error. This is a controller-interpreter mismatch;
the native retention mechanism was not changed.

A browser container had started and its original cleanup reported success,
including container absence and listener closure. The candidate image detached;
no session export, capture or grading phase started. The browser ID/port and an
explicit relay-settlement field were not retained, so no replacement receipts
are invented. Zero canned requests and unchanged unloaded runtime counters
(36 requests, 209,444 prompt, 3,317 completion) are preserved. Original result:
`3034f952b1da6bd7ba8f3a5a80ba927bd0db1f1ea47d6056a6d638a2595865b7`;
driver: `8a242beaab8632726578edd9bebcf7375caef86f7aa7013409f4de579c490a6a`.

Separate settlement
`3c3f695aa2cb31737cee356e5524f9522cad80fb19301dd268e270edc1b83e44`
verified 38 unchanged files, actual browser-name/process and image/mount absence,
the preserved candidate image, eight normal parent and four normal child
resource samples, and six AC/90% power samples. Original power predicates ran in
an isolated process with their original frozen source binding. Sampled swap
growth was zero; absolute swap remained nonzero. Fifteen author checks preceded
separate execution removing only the inactive job. The first review's copied
launch-directory error failed before mutation and remains retained. A separate
15-second Docker inventory timeout is also preserved; a local API ping and exact
browser-name query subsequently completed in 0.011 seconds. Its cause remains
unproven. Settlement does not upgrade the failed control.

A supported-interpreter mechanism preflight exercised real native background
preparation under existing Python 3.14.6 through retained-directory allocation,
isolated configuration, Seatbelt generation and log setup, intercepting only
process creation. It also checked that garbage collection preserves a
`delete=False` directory and that original cleanup removes owned scratch when
no process started. No native process, browser, APFS trial or model ran.
The first preflight failed because historical evaluator package metadata was
unavailable in Python 3.14; the second failed on an invalid synthetic broker-token
length. Both are retained. The final preflight uses the existing Python 3.11
venv solely for isolated read-only historical evaluator checks, and a fixture
matching the original broker's original identity-length requirement. The mechanism preflight
receipt has SHA-256:
`9881c06c643469b3a9acbf549a233f9f4d8d74ffc6f256a8043c7641ce2d3753`.
No dependencies were installed or owner settings changed.

Fresh V4 binds the native controller, browser and adapter to the existing pinned
Python 3.14.6 executable and keeps historical evaluator checks isolated in their
original environment. It uses a new seed and receipt, the same frozen Git-source
runtime/plugin bytes, exact browser image, six-call canned sequence, 120-second
CLI bound, original APFS barrier, acceptance and linked guards. Nineteen author
checks and a separate nine-check launcher review passed before one bootstrap.
The immediate activation comparison failed because macOS executes framework
Python through its sibling `Python.app` binary. A separate observation verified
actual argv, `proc_pidpath`, both executable hashes and the one registered PID;
no second bootstrap occurred. Both observations remain retained.

| V4 artifact | SHA-256 |
| --- | --- |
| Runner | `810c5d498133b2aabed835420b173c1753d3efd15b896938a7cfe1215691191f` |
| Predeclaration | `a95c9eeffa89c251d9d0bd3efeb51af57a21bb32a4369e562a7b84ea40732a5c` |
| Manifest | `cba06ff4a090400deb3321d41ccb3bbe97d5f1b701cf9e2416551b8cbd5ad7cf` |
| Author review | `9b3552e8ef7cd02c56e78e4d400329a9f5ae3d0cc24e70366c38c4278934c356` |
| Launch | `dd73ca85bb175178d422b482a22a77ab127271b0e5f5b6c2de51a50f8ff622ca` |
| Separate activation observation | `3cf5e08fcd4b6ece7aa7173341ee96ff2c15bec57a02c82f7cbc22072cf778b7` |

The worker was verified active at launch; no outcome is claimed here. This is a
no-model boundary control, not UI quality, benchmark or production qualification.
CI **37326329635** passed at `0aab7ce`; compact terminal observation:
`f09d192253ca629ca8ca5b05685e6105f3295bc6017fc8602f21d6fd4b533243`.
Earlier failed CI remains failed. Broader development, fresh/protected validation,
coding/UI, full-context reasoning, long-duration endurance and final scope stay
open; the single PR remains draft.

## Native UI control passed and settled; first local-model UI diagnostic

The supported-runtime V4 control passed: native CLI exit 0, one successful Agent
root and one owned Browse child, six canned calls, completed write/delegate/
navigate/snapshot actions and a sole 320-byte `index.html` patch. The full native
user input matched the 75-byte prompt, including its final newline. The readonly
capture matched the patch hash, and the fresh synthetic marker grader accepted.
Candidate, capture and grader phases all detached. This used **zero model
inference** and no official benchmark grader.

Separate settlement verified all 68 retained files unchanged, including both
sparse images, three empty owned mount directories on the host device, actual
browser-name and broker-process absence, and the original listener-close
predicate. The browser's exact ID and port were not retained. Thirteen parent,
six native and four capture resource samples were normal; all eleven parent
power observations were AC/90%. Sampled swap growth was zero, with nonzero
absolute swap. Runtime PID 85947 remained unloaded and idle at exactly 36
requests, 209,444 prompt and 3,317 completion tokens. Only the inactive exit-0
launch job was removed.

The initial plugin-directory argument correction and two settlement-review
failures (a copied trial path and a check incorrectly stripping the prompt's
newline) are retained. None executed the settlement mutation. The corrected
settler passed 15 author checks with only job removal/output intercepted before
separate execution. The original control was neither replayed nor regraded.

| Completed V4 artifact | SHA-256 |
| --- | --- |
| Result | `5d6a534548c5173718a83bdcb9755cfbb731c6c951271fca6763e52514a3be8f` |
| Native driver | `277048a362dfedd0b75a83aba5d7791d73f85e0b1a1a79838845e64329ea0614` |
| Barrier | `a8c038f996d105cf87529a3e4910f31ab471c93dd98a1c2ca3f78446ebb29fed` |
| Patch | `cda756570193e12b84ebd197ac8e3d08a3eea22c8e4769c1403cf0fad851d649` |
| Settlement | `42322ae4a36807199e7b1971be79acc975ffda79d27dc8dddea43c7970c0e365` |
| Settlement author review | `c8733199e84a546a83f2eea28d5ba8213101a8b5a9d981518425e37cda8dcdbb` |

This native path retains initial agent/plugin policy inventories, complete
request metadata and exported session chronology. It does not retain the
container path's continuous policy snapshots or full wire records, nor prove
absence of private event gaps. The pass qualifies this canned boundary only.

A fresh local-model Agent/Browse V2 diagnostic now uses a new public fixture,
existing native engine/plugin and browser image, Python 3.14, original three-phase
APFS barrier and parent-to-child guard cancellation. One CLI is bounded to 300
seconds; the original 128-request limit, 300-second request timeout, 8,192-token
output limit and complete admitted sampler/tool-schema digests remain enforced.
The original relay rejects mismatched control or either role's schema digest
before forwarding to the fixed local oMLX endpoint. Exact native usage must
reconcile runtime counters before one guarded unload; failures retain the
original exact-owned emergency stop. Concurrent inference conflicts prevent
unload or stop of potentially shared work. No benchmark task or old UI arm is
replayed, and no resource stop is weakened.

The first prospective model draft was retired **unrun** during static review:
the canned recorder's spaced-JSON schema digest differs from the real relay's
compact canonical digest. V2 binds the already-retained canonical digest from
the same shared function; no schema or acceptance exception was added. Sixteen
author checks covered actual boundary argument binding, exact synthetic grader,
acceptance rejection cases, native usage accounting, successful unload, failure
stop and conflict handling. A separate nine-check launcher review preceded one
bootstrap; actual framework-app executable hash, `proc_pidpath` and exact argv
verified PID 26951. No outcome is claimed at launch.

| Prospective model V2 artifact | SHA-256 |
| --- | --- |
| Runner | `983f5004794e9b8058096de562495b9a77cf47e214f68a5e074b4ac05d6fcc7d` |
| Predeclaration | `6d26de956148141a4217992db0f2ef0607db69d43fd7b97d2479f7923a34593c` |
| Manifest | `11de1823269056138c86a0141581eb6face0a8edeb80076303375ab600880fb2` |
| Author review | `beafff1c147a885c49ad3993e8bbdfa33263abf644a7904ab6b8de2cd78cc8f9` |
| Launch | `d736786c92c55c318a256c57c9d334be0d39d1f7aa1987f09ab74137fcf6100a` |
| Activation | `013c4b834b0179b842fa68ddf6f86ece3b23d72fb5b59e6b585488a14417dec6` |

CI **37328203434** passed at `1963cc4`; all job/step conclusions are archived by
observation `dc32564d28bd1b5486670145daea4c05eacab968812b42e647084af009662fa7`.
Previous failures remain unchanged. Broader development, fresh/protected
validation, sustained coding/UI, full-context reasoning, long-duration endurance
and final production scope remain open. The single PR stays draft.

## Native local-model V2 strict failure, settlement and fresh skill-first V3

The V2 CLI exited 0 after 86.601 seconds; nine local requests produced one Agent
root and two Browse children, all with successful native completion. The
three-phase barrier completed in 96.357 seconds, captured the sole 322-byte
`index.html` patch and passed the fresh synthetic marker check. This is not an
official benchmark grade. The original diagnostic remains **failed**: its first
failing assertion requires exactly one child. Root tool order was write,
subagent, skill (`opencode`), subagent. One Browse child used no tools; the other
completed navigation and snapshot with the declared public marker visible.
The write content matched exactly, but its absolute workspace path also differs
from the original literal relative-path predicate. A separate read-only check
reproduced the original assertion failure without changing its acceptance.

The nine native assistant usages reconcile exactly to 38,721 prompt and 2,984
completion tokens. After one original guarded unload, runtime PID 85947 was
unloaded and idle at 45 requests, 248,165 prompt and 6,301 completion tokens.
No emergency stop or resource intervention occurred. Forty-nine parent, 42
native and four capture resource samples were normal; 43 power observations
were AC/90%. Sampled swap growth was zero, with nonzero absolute swap.

Separate settlement verified all 70 retained files unchanged before and after
removing only the exact inactive exit-1 launch job. Both images remain preserved
and detached; three owned mount directories are empty on the host device. The
actual browser name and broker process are absent. The original close predicate
proves listener closure; exact browser ID/port were not retained. Source, seed,
plugin, tool, image, exported ownership, initial inventories, request metadata,
usage and all guard finals were checked. Continuous native policy snapshots,
full wire receipts and absence of private event gaps are not claimed.

A copied receipt-field name in the first settlement script was corrected during
static inspection before review/execution. The original script and correction
receipt remain pinned. The corrected script passed 15 author checks with only
job removal/output intercepted, then executed separately. No model request,
task, grader, APFS operation or runtime mutation occurred during settlement.

| Failed V2 artifact | SHA-256 |
| --- | --- |
| Result | `c29dce497a9d0d57d4936c26f0da9bd02c31c1b7d7d1fa3814a09b8e919be6df` |
| Driver | `3603c1aaafd9517137aa78e291e87ebc8fca9d6bdae27ece2363a28c34f374e5` |
| Barrier | `4eac860713e3e6f262775ce2155057c2d07b72381d0239492f983dc1dd2cdb70` |
| Settlement | `87a1915c5257011ae56252e7c456431cbe2dcc6194f52160457eae148e197b3a` |
| Settlement review | `ec88db6e7058da9ae734fb8ce51973eb85f2553fea73af4c605982b5f1aabfbe` |
| Retained static correction | `5cc578fed7197557486014b19bae2834ca58d71429a0e970fc86773762fe159b` |

Fresh model V3 prospectively declares loading the `opencode` skill first,
followed by write and exactly one Browse delegation. The only accepted write
paths are `index.html` or the exact absolute `index.html` beneath the recorded
candidate workspace. Exact page content, one child, navigation/snapshot order,
wire schemas, sampler, original guards, native ownership, APFS isolation and
usage accounting remain required. The old V2 result remains failed. This new
public fixture is bounded by the same 300-second CLI/request limits and
128-request cap. Original admission, relay, query and main behavior are
structurally unchanged apart from descriptive scope text and the explicit
accounting baseline; no native engine, image, dependency or guard changed.

Eighteen author checks exercised the actual acceptance against synthetic native
exports, including outside-path and wrong-skill rejection, and the original
success/unload, generation-failure/stop and concurrency-conflict paths. Nine
separate launcher checks passed before one bootstrap. Actual framework-app
executable hash, `proc_pidpath` and exact argv verified PID 31363. No result is
claimed at launch.

| Prospective V3 artifact | SHA-256 |
| --- | --- |
| Runner | `03cbfd479fbed2b4d722e0465b867df786f0e3d9acca68bfded76e05e55d0f12` |
| Predeclaration | `4332ecd00875e87a777df2e473a9e8099721674e355510b262e658ac7a08ea24` |
| Manifest | `e9cf111c07187322878bb9549660cdd00dccf98cd6db9f9c1087246066a1c679` |
| Author review | `10ee3aad87abc73801910bab7bed1d541f5a59e2c4ff1a4e37e2ea5da1899914` |
| Launch | `451a4d83b3b5f18501ba60d0d07a6154284506a1f50632671837e6a8166c6986` |
| Activation | `f1f9ab04e4c03b32bfc60c4dd8a83b7423d5366afdafb14e1d87bdb16cadae9c` |

CI **37329916187** passed at `8289c25`, with full job/step conclusions pinned by
observation `8c72364b43e599cbda9d9534c5d7aee7804eb415650620e59214f20f5d684d76`.
Earlier failed research and CI remain failed. Broader development, valid fresh
protected validation, sustained coding/UI, full-context reasoning, long-duration
endurance and final production scope remain open; PR #242 stays draft.


## Local-model native UI V3 completed; prospective browser receipt fix

The fresh skill-first V3 protocol passed unchanged: one Agent root with
skill/write/subagent, one Browse child with navigation/snapshot, exact prompt,
page and bounded workspace path, CLI exit 0 and seven locally routed requests.
The native driver took 60.795 seconds; the full three-phase APFS barrier took
70.748 seconds. Its sole 322-byte index patch exactly matched readonly capture,
and the fresh synthetic marker grader passed. This is no official benchmark
score, UI quality judgment, full-context reasoning or endurance claim.

Usage was exactly seven requests, 31,406 prompt and 1,824 completion tokens,
matching counters 45 → 52, 248,165 → 279,571 and 6,301 → 8,125. The original
single unload left PID 85947 unloaded and idle. All 37 parent, 30 native and
four capture samples were normal; 33 AC/90% power observations covered both
children and final samples. Sampled swap growth was zero; absolute swap was
nonzero. Separate reviewed settlement verified all 67 files unchanged, both
preserved detached images, three empty owned mount paths on the actual host
device and exact browser/broker absence, then removed the sole inactive exit-0
job. The runner, review and settlement were each executed once.

| Completed V3 artifact | SHA-256 |
| --- | --- |
| Result | `1fea49626e8cde9e8deb0b4b44f762998148279c6a78ee585668eaf1861a21f6` |
| Driver | `71da250f4acf48feb7f9022f50db012ef904594f54d34be8d6d333dea136b81d` |
| Barrier | `0e65426a1d17ec91f339d6fbbbf11d54576cb6507bb3e6a9c7e3f9d9c79f0caa` |
| Patch | `64c7581336ee916a3cc52f227d584c8e5b0c31b7891396b7689dd74b49fbeb85` |
| Settlement review | `7e67bd0b137bf99db2c12ce211d0e3600afc9d8e0254f77130b109428a7da889` |
| Settlement | `5e731774b26c9402a13999121626c5a08fad1da9a1d6b686f6e5438801be5280` |

The browser ID and port were not retained by this frozen source; only the exact
name and original shutdown/listener-close predicate are available. The new
prospective source retains Docker's inspected full container ID in the boundary
receipt and the broker port in the native driver. It requires one inspected
object with the requested exact name and a full ID. The explicit public receipt
field list still excludes authentication credentials. Tests reject empty or
ambiguous inventories, wrong names and missing/truncated IDs. Native engine,
permissions, isolation, resource guards, cleanup and grading are unchanged.
No frozen evidence is rewritten or upgraded.

CI **37331355910** passed at `5874201`; full job/step conclusions are pinned by
observation `5327a00f09d830e4e95a3158ab7c838beac92bde572b75f595300156a1fb789c`.
All prior failures remain retained. Broader development, fresh/protected
validation, sustained coding/UI, full-context reasoning, long-duration endurance
and final production scope remain open; PR #242 stays draft.


The new code at `37f2ed0` passed 220 setup, 214 research (two skips), 87 Node
and native/frozen offline checks; evaluator Python 3.11 passed 214 research
checks (one skip). Clean-source package smoke, documentation/link/diff checks
and one-commit secret scanning passed. Code validation is
`2a7bdf812882da11882d69f3bfb84a6399ffa19d6abdc77c27e8f21491226f32`.
A new authentic detached Git copy verifies all 414 tracked blobs and 98 source
hashes. Only the browser receipt implementation/test and the previously
validated unscored-reason implementation/test differ from the prior frozen
runtime; exact reversal proves all surrounding browser/driver code unchanged.
Source proof: `6f274c78ec3756d000ac8efcdaee194ebe9ca6190c773cbfd43a49afa88bbd99`.

A fresh canned native browser identity V3 control was bootstrapped once with
RunAtLoad true/KeepAlive false and verified framework-app process PID 40230.
It schedules six canned calls, no real model requests, a 120-second CLI and the
same three-phase APFS barrier, image, linked guards and battery-capable safe
admission. The original runtime must stay unloaded and idle at counters
52/279,571/8,125. In addition to the unchanged original acceptance, the new
control requires a credential-free receipt with full inspected container ID
and integer broker port, exact ID/name absence and closed listener. The CLI
Docker endpoint must match the known local Unix endpoint at admission and
absence checks; environment endpoint overrides are rejected. Twenty-one author
checks and nine separate launcher checks passed. Outcome is unknown at launch;
no qualification is claimed from activation.

Two drafts were retired before any attempt, native process, browser, APFS or
model operation. V1 copied stale final scope prose despite the explicit source
delta; V2 passed 19 author checks but later static review found that its absence
API endpoint lacked explicit binding to the CLI-selected endpoint. Fresh V3
adds that binding and negative checks, preserving both unrun drafts. No started
task or grader was replayed and no safety predicate was relaxed.

| Prospective browser identity control artifact | SHA-256 |
| --- | --- |
| Runner | `85894fc4113c84ed4cdef78612b9be8778dd957064e3b4385bb283c67cb27b85` |
| Predeclaration | `74daa840fa6fcae7308f64c8dfa58a8b1abada6a199f37ce0ffaf6f83b9708a7` |
| Manifest | `fa9bddc549cc262d4bfc164ed1901244102d349da3219319c971eed15b33559c` |
| Author review | `4df189842b3192a1d961efc739390bd47b32c50725af3d36e7f8e5314dffcc77` |
| Launcher review | `604f424801ff57032fc4d3e0dfbc4d616b516e7d9a6d4f4fd5845acbf50e0935` |
| Launch | `0b762c8adebda41fd3d21270871698a37aa69263b0baba5065fbf57f234773e2` |
| Activation | `f84f8748e0f1ff422beba37773dbcf579d0548ce5c0e5aaac6f4d903921630cb` |
| V1 retirement | `10de1a8f1f559bd8dccc083b0b1ff7d5bc25548d6cb20eaa4f4bbc48995fe716` |
| V2 retirement | `b3b70a7e3004ac50f90b8e2e0f58d489da312f550fb61bbdc3d3cf7eabd6b1b7` |


## Browser identity settlement and prospective counter interaction

Canned browser identity V3 passed and was separately settled. Native execution
completed in 9.320 seconds with CLI exit 0 and six canned calls; no model request
occurred. The three-phase barrier took 19.229 seconds, captured the sole 321-byte
page patch and accepted the fresh synthetic marker. Exact browser container
ID/name absence and closure of the recorded broker port were checked on the
CLI-bound local Docker endpoint. All 61 files, including two detached images,
remained unchanged before and after removing only the inactive exit-0 job.
Three owned mount paths were empty on the host device. Fifteen author checks
passed before separate settlement execution; no task or grader was replayed.

Unlike the earlier AC observations, this control ran on battery at 90%.
Thirteen parent, six native and four capture samples were normal, with 11
battery power observations covering both children and finals. Sampled swap
growth was zero; absolute swap remained nonzero. The original runtime stayed
unloaded and idle at 52/279,571/8,125. This is no-model battery evidence only.

| Completed browser identity V3 artifact | SHA-256 |
| --- | --- |
| Result | `bc7927176dc34d1707a232ebda06b72fd53bfb0f41d65e770a28041cd37713d6` |
| Driver | `34e5d1e32d68f32a5b40517d7a4da9fe20ecd44bf76d4d3644ac8bfffe333bf2` |
| Barrier | `e610d85c880e18979313b78f392b6b6403cbe36a44fc36ccbb05b184d097835f` |
| Patch | `6589e9ba5757cc620c1ab20fe1961249bcba134d4ea891aa4cc0a51b2f47188c` |
| Settlement review | `7cefe899c023919c14927fedd5fbed34ef77fa58b3d55345971665d1e29608dd` |
| Settlement | `f803b76423658c576827a28c79459a321428144ba031807527bba192a3759181` |
| CI 37332655393 observation | `3483e4990828a35600d160aec143761b4fd938924a360178cff9010843fb2652` |
| CI 37336300276 observation | `d5efd96c38aa584b182a70d8af79dd5c4051c8354e589e30e3eba64f0f12cecf` |

Fresh `native-ui-interaction-readiness-20261005-v1` now asks local OpenCode/oMLX
to implement a counter in the single public page, with no supplied solution.
The root loads its skill, edits only `index.html` and delegates Browse. Exact
native browser inputs and nontruncated accessible snapshots must show counts
0, 1, 2, 0, 0 after open, increment, increment, reset and snapshot. Stale or
duplicate count lines, wrong selectors, missing markers and outside URLs fail.
The fresh applied-artifact callback only verifies bounded regular page bytes
and marker presence; interaction evidence is separately checked from native
tool outputs. No independent browser re-execution, official grade, quality
score or protected claim is made.

Twenty author checks covered the full current source/prior chain, actual trial
bindings, artifact and interaction negatives, original usage accounting, and
actual success/unload, failure/owned-stop and concurrency/no-operation branches
with execution boundaries intercepted. Nine launcher checks preceded one
bootstrap and verified framework-app PID 47067. Original native engine, browser
image and isolation, 512 MiB APFS phases, parent/child emergency stops and
battery-capable admission remain unchanged. One 300-second CLI, 300-second
requests and the original 128-request cap bound this new fixture. Outcome is
unknown at launch; prior results remain immutable.

| Prospective counter UI artifact | SHA-256 |
| --- | --- |
| Runner | `596363bd619e609ba4c2a7fa46e1f1a9a4ac36ad11b831ac8103e71c5f2b0689` |
| Predeclaration | `a536e4fbb98b19e9c6082b7adf5d5e251cb592779ffdcf9ceb5cf8a16da6ac3a` |
| Manifest | `440001efc0884b5c8dfc05a6d64e91d8fbfa3b18e55eb3aac48172279f11e673` |
| Author review | `4839363709a1b51c40fd85612f783d0e2e35295ebfe1484a71932a1952b30e63` |
| Launcher review | `78f1cf2d33bd25bb0d47b9e208064b852bbe962e973edc6e642d55432a2bed13` |
| Launch | `cba3005c5a8dee4d31ac9ae5f0c86690b1233ad1ff60fff2a2b6cf684d80b63f` |
| Activation | `403190dd40c711acb451e9937180535660160ed9ac2fb5e20ce338b73e9f1d6d` |

Both pending CI runs passed: 37332655393 at `37f2ed0`, and 37336300276 at
`9b9ab34`. Earlier failed CI/research evidence is preserved. Broader development,
valid fresh/protected validation, sustained coding/UI, full-context reasoning,
long-duration endurance and final truthful production scope remain open. PR
#242 remains draft; no release, version, tag, owner install or merge change.


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
