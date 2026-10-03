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
`/private/tmp/kryn-ui-gateway-preflight-19/receipt.json`, SHA-256
`27422fc97134fb2129a1b9be4dc8f932f6a49a0dd865bb5f04554f47b3221d69`.
All 33 no-model checks passed, including a reference ArrowRight interaction,
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
That unqualified no-model attempt was retained and its code reverted; the 32-check
receipt above remains the last passing preflight.

OpenCode's actual MCP tool dispatch initially failed because it adds optional
`_meta` to `tools/call` parameters; the adapter's exact-key check rejected the
call. The adapter now accepts only the two ordinary keys plus optional object
`_meta`. The clean-source synthetic inference canary at
`/private/tmp/kryn-ui-synthetic-wire-20261003-07/result.json` (SHA-256
`0efb2f70cd01c6a3a0c9cd302c12c2aff3a9be9f9ac631727d1c0536c684a6b8`)
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

Remaining gates: independently review the optional third-port change and the
new synthetic dispatch path; establish guarded live model quality on a
representative occupied host;
review the container and broker security independently;
freeze a valid 30-task roster before any protected candidate run. The current
synthetic check proves OpenCode routed these tools, not that a model chose them.
The Dockerfile pins its base image and npm
package lock, but `apk add chromium` resolves from a mutable Alpine repository;
the exact tested output image ID, not a rebuild from this Dockerfile, is the
executable identity used in the receipt.
