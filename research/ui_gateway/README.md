# Research-only UI 01 browser gateway

This prototype exposes one self-contained `index.html` from a disposable
candidate checkout to a local OpenCode MCP adapter. The adapter accepts only six
browser operations and sends an `open` request to a broker. Chromium runs in a
separate container with no host mounts, network, or Docker socket. The browser
has no grader, reference, source snapshot, or host path. Nothing here changes
the installed product browser profile or permits a protected model turn.

The adapter uses a fixed `http://candidate.invalid/index.html` URL. The broker
holds a trusted checkout directory fd and, on every navigation, opens
`index.html` itself with `O_NOFOLLOW|O_NONBLOCK`. It verifies regular type,
candidate device, and a 1 MiB cap, then sends the checked immutable buffer to
the worker. A caller with the broker token cannot supply page bytes or a path.
The browser worker allows inline
script and style for this single-file task and denies all other requests. It
provides snapshot, CSS-selector click, a small keyboard set, screenshot, and
viewport resize. The broker uses an exact local Docker image ID and verifies
no mounts, no network, read-only root, non-root execution, dropped capabilities,
positive process and memory limits; it owns container cleanup. The trial config removes
search MCP and denies search/web fetch identically in both arms.

Build the worker image from this directory with `docker build --pull=false -t
kryn-ui-worker:research-20261003 .`, then use the resulting exact image ID with
`python3 -B preflight.py --draft PRIVATE_DRAFT --image sha256:IMAGE_ID --output NEW_PRIVATE_DIR`.
The preflight uses a disposable APFS candidate volume, a host-side hidden
canary, the actual Seatbelt profile, direct MCP calls, and no-model OpenCode
startup for native and KRYN arms. An optional research background setting admits
the broker as a third explicit loopback port alongside distinct inference and
native ports. The preflight runs a live dummy inference listener; it makes no
model request. Ordinary installed `NativeServer` behavior is unchanged. Both
OpenCode arms start from the clean seed checkout with a fresh browser worker before any
reference bytes are loaded. A blank-worker check follows startup; the reference
keyboard control runs afterward and the seed page is reloaded before cleanup.

The latest local no-model run used image
`sha256:16c1133894770bceab9f2f3a9bfac4e7ec1b3dde1fe2f0f6a7063ba49b3436a2`.
Its private receipt is
`/private/tmp/kryn-ui-gateway-preflight-21/receipt.json`, SHA-256
`04da92d905067d249f9f0646c61027aad0f7b5af2a6a78983ef0cc43d591de88`.
All 34 no-model checks passed, including a reference ArrowRight interaction,
hidden-file and hardlink denial, malicious page file/network attempts, symlink
swap, FIFO, oversize entry, rejection of caller-supplied HTML, zero-limit and
root and container-escape attestation mutants, startup-timeout reaping, clean seed state
and blank browser through both-arm MCP connection/config parity, seed restoration,
distinct inference/browser ports, malformed and duplicate port rejection,
permitted dummy inference access, denied fourth-port access, container cleanup,
and volume detachment. The receipt explicitly retains
`protected_eligible=false` and `model_gateway_qualified=false`.

An exploratory registry-RPC check at
`/private/tmp/kryn-ui-gateway-preflight-15/receipt.json` failed with HTTP 400:
this research config does not enable the optional inference-audit tool-list RPC.
That unqualified no-model attempt was retained and its code reverted; the 34-check
receipt above remains the last passing preflight.

OpenCode's actual MCP tool dispatch initially failed because it adds optional
`_meta` to `tools/call` parameters; the adapter's exact-key check rejected the
call. The adapter now accepts only the two ordinary keys plus optional object
`_meta`. The clean-source synthetic inference canary at
`/private/tmp/kryn-ui-synthetic-wire-20261003-09/result.json` (SHA-256
`ea62469be0ad810c3a87c6445d71e23a11d273c52358a1fcc1273e1ba46a764b`)
passes in both real OpenCode arms: each starts from a separate clean checkout,
all four requests expose the same eight-tool catalog, and navigation, click,
and snapshot all complete with the changed
`Activated` page state. It made **zero real model requests** and is not an
agent-quality or protected score. An earlier synthetic run exposed a full Browse
tool-catalog mismatch: native exposed `glob`, `grep`, and `skill` while KRYN's
product policy hid them. Identical per-arm Browse deny rules now hide those tools
in native too; the clean-source `06` receipt confirms equal full wire catalogs.

One public live 9B Browse turn at
`/private/tmp/kryn-ui-public-dispatch-20261003-01/result.json` (SHA-256
`edb461946d841d48a1158e503fe6d244d62892420e7de54699fd4c972128227f`)
hit the unchanged sustained-host-memory warning on its first request before a
browser call. It was diagnostic from a dirty research source, lasted 12.8 s,
showed pressure 1→2 and zero swap growth, then settled its session/runtime and
container. It cannot establish live dispatch or model quality; repeating that
same resource-gated turn is not justified.

The preregistered deferred-worker candidate started the same image only on
the first authorized browser operation. Its clean-source no-model preflight
passed 36/36 checks, and a synthetic OpenCode dispatch passed in both arms
with equal full tool catalogs. The first browser call took 0.688 seconds,
including worker startup. In the single live 9B attempt, the worker remained
absent before inference, yet the unchanged two-warning host guard again
stopped model prefill before any browser call. Pressure reached warning,
sampled runtime footprint reached 10.75 GB, swap did not grow, and the owned
session and container settled. The candidate is **rejected**: removing the
worker's idle footprint was insufficient for this occupied-host gate. The
eager diagnostic came from dirty research source and the two host states were
not matched, so this does not measure a causal resource saving or model quality.
Compact provenance is in [`../history/ui_gateway.jsonl`](../history/ui_gateway.jsonl);
the owner-only archive contains the candidate patch and all raw receipts. No
deferred-worker code was merged or installed.

An independent no-model audit of the 15 owner-only UI drafts found only six
semantically valid category slots: three UI/browser tasks (01–03) and three
failure-recovery tasks (04–06). None is admitted. This gateway has enough
operations for task 01's interaction screen, but task 02 needs input fill and
task 03 additionally needs query navigation, Back, and URL-aware snapshots.
An actual worker negative control reached `?q=RIVER` and got
`PAGE_LEFT_FIXED_ORIGIN` from both open and snapshot. The current
Agent-to-grader entrypoint also does not own a UI broker lifecycle or select
the Browse agent. Drafts 07–09 are one-shot tasks rather than long sessions;
10–12 lack real staged turns, compaction, restart and stage-one acceptance;
13–15 use fictional synthetic sources rather than current external
information. The audit and probe hashes are in the compact history index,
with raw no-model receipts in the owner-only experiment archive. No protected
task was run or relabeled to fill the roster.

Remaining gates: establish guarded live model quality on a representative
occupied host with a materially different, preregistered resource approach;
add bounded fill/query/history operations and bind the broker to the candidate
volume before real UI admission; review the container and broker security independently;
freeze a valid 30-task roster before any protected candidate run. The current
synthetic check proves OpenCode routed these tools, not that a model chose them.
The Dockerfile pins its base image and npm
package lock, but `apk add chromium` resolves from a mutable Alpine repository;
the exact tested output image ID, not a rebuild from this Dockerfile, is the
executable identity used in the receipt.
