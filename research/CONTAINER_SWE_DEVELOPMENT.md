# Dependency-ready SWE development worker

This prospective execution profile is **development instrumentation**, not a
product change or a correction to the completed v3 score. It moves OpenCode and
the task's tools into a Linux/amd64 container with the official historical
repository dependencies. That changes the OS, toolchain and execution boundary;
results must have separate experiment provenance. No model generation has been
admitted by this document.

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

The existing memory guard is retained. Independent pressure sampling, the
120-W/40%-battery admission rule, AC/25%-battery stops, 12-GiB disk floor,
4-GiB writable-container cap and 8-GiB evidence cap also apply. Caffeinate is
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
Only the sized-inspect subprocess now pins API 1.45. Missing or invalid values
still fail closed; the 4-GiB limit and every other guard remain unchanged.
Original interrupted and failed recovery attempts remain unscored. See the
campaign report for the read-only receipts and remaining live admission gate.
