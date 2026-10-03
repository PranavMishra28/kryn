# Research-only fixed-page browser gateway

This prototype exposes one self-contained `index.html` from a disposable
candidate checkout to a local OpenCode MCP adapter. The adapter exposes eight
browser operations and forwards requests to a broker. Chromium runs in a
separate container with no host mounts, network, or Docker socket. The browser
has no grader, reference, source snapshot, or host path. Nothing here changes
the installed product browser profile or permits a protected model turn.

The adapter accepts only `http://candidate.invalid/index.html` with an optional
single bounded nonempty `q` query. The broker holds a trusted checkout directory
fd and, on every explicit page open, opens
`index.html` itself with `O_NOFOLLOW|O_NONBLOCK`. It verifies regular type,
candidate device, and a 1 MiB cap, then sends the checked immutable buffer to
the worker. A caller with the broker token cannot supply page bytes or a path.
The browser worker allows inline
script and style for this single-file task and denies all other requests. It
provides URL-aware snapshot, CSS-selector click and input fill, history Back,
a small keyboard set, screenshot, and viewport resize. Empty or malformed
queries fail closed. The broker uses an exact local Docker image ID and verifies
no mounts, no network, read-only root, non-root execution, dropped capabilities,
positive process and memory limits; it owns container cleanup. The trial config removes
search MCP and denies search/web fetch identically in both arms.
The fill and Back tools use OpenCode's existing `browser_fill_form` and
`browser_navigate_back` names, preserving KRYN's current Browse allowlist.

Build the worker image from this directory with `docker build --pull=false -t
kryn-ui-worker:research-interactions .`, then use the resulting exact image ID with
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

The original UI 01 preflight passed 34/34 checks. The interaction extension
passed 37/37 no-model checks using image
`sha256:7ba09f30619fa01ff7687b9fac5569b161ad23b9624aaa1199fc99c199731d64`.
Its private receipt is
`/private/tmp/kryn-ui-interactions-preflight-20261003-final/receipt.json`, SHA-256
`db59076d9f92127e9ee480217a4ce80c88724a8a733cedfebf6f0b6a42c4b8af`.
Checks include the UI 01 reference ArrowRight interaction, form fill,
query/Back navigation, URL-aware snapshots, Unicode query round-trip,
malformed-query denial,
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
That unqualified no-model attempt was retained and its code reverted.

OpenCode's actual MCP tool dispatch initially failed because it adds optional
`_meta` to `tools/call` parameters; the adapter's exact-key check rejected the
call. The adapter now accepts only the two ordinary keys plus optional object
`_meta`. The clean-source synthetic inference canary at
`/private/tmp/kryn-ui-interactions-synthetic-20261003-final/result.json`
(SHA-256 `9466f8e7dac6051789295a517a3283eac5f5752d87f5f5145df9ab7846faf749`)
passes in both real OpenCode arms: each starts from a separate clean checkout,
all eight inference requests expose the same complete tool catalog with exactly
the eight expected browser tools. Navigation, fill, click, snapshot, Back,
snapshot, and query navigation all complete with the expected visible states.
It made **zero real model requests** and is not an
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
failure-recovery tasks (04–06). None is admitted. The extension now supplies
the missing fill, query navigation, Back, and URL-aware snapshots. An owner-only
no-model reference smoke at
`/Users/pranav/Documents/Codex/kryn-research-private/ui-interaction-receipt-20261003/receipt.json`
(SHA-256 `fdd2474882f118e3ed4bc23945eecda266d3d866a74d6f2940256fcd49186d54`)
passes 01: 6/6, 02: 13/13, and 03: 6/6 interaction checks on separate APFS
volumes. The first attempt was invalidated by a source/image race and preserved.
The valid receipt does not assert all focus/ARIA or normalized-value behavior,
and is neither an Agent run nor a hidden-grader score. The current
Agent-to-grader entrypoint also does not own a UI broker lifecycle or select
the Browse agent. Drafts 07–09 are one-shot tasks rather than long sessions;
10–12 lack real staged turns, compaction, restart and stage-one acceptance;
13–15 use fictional synthetic sources rather than current external
information. The audit and probe hashes are in the compact history index,
with raw no-model receipts in the owner-only experiment archive. No protected
task was run or relabeled to fill the roster.

Remaining gates: bind the broker to the candidate volume and run matched Agent
and independent-grader phases; establish guarded live model quality on a
representative occupied host with a materially different, preregistered resource
approach; freeze a valid 30-task roster before protected candidate use. An
independent code review found no P1/P2 boundary defect in this extension, but
the tested no-model paths do not establish protected isolation end to end. The
synthetic check proves OpenCode routed these tools, not that a model chose them.
The Dockerfile pins its base image and npm
package lock, but `apk add chromium` resolves from a mutable Alpine repository;
the exact tested output image ID, not a rebuild from this Dockerfile, is the
executable identity used in the receipt.
