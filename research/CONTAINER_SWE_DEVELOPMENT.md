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

Before any generation, exercise the exported-patch handoff to the isolated
official grader, then freeze
a separate development experiment's source, exposed task selection, image,
prompt, arm order, sampler, complete wire controls, budgets and adjudication.
Record the actual OpenCode exit code directly. An interrupted or unsafe arm
remains unscored and cannot be silently replayed.

The first study should test whether ready dependencies reduce observed tool
failures and timeouts. A reused public task is development-only. Require genuine
accepted work before fresh validation, holdout or long-horizon promotion. Do not
combine this profile with the v3 macOS score, infer general uplift from a canary,
or treat worker admission as production/autonomous qualification.
