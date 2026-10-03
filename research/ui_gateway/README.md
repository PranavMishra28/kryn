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
startup for native and KRYN arms. It intentionally substitutes the broker port
for the inference port; this cannot support a model turn. Both OpenCode arms
start from the clean seed checkout with a fresh browser worker before any
reference bytes are loaded. A blank-worker check follows startup; the reference
keyboard control runs afterward and the seed page is reloaded before cleanup.

The final local no-model run used image
`sha256:16c1133894770bceab9f2f3a9bfac4e7ec1b3dde1fe2f0f6a7063ba49b3436a2`.
Its private receipt is
`/private/tmp/kryn-ui-gateway-preflight-08/receipt.json`, SHA-256
`bf7173ebf76d6d2fbd9b93334ed97cfdd03a3a4ba6a9d92755172b8f972e7e17`.
All 26 no-model checks passed, including a reference ArrowRight interaction,
hidden-file and hardlink denial, malicious page file/network attempts, symlink
swap, FIFO, oversize entry, rejection of caller-supplied HTML, zero-limit and
root container attestation mutants, startup-timeout reaping, clean seed state
and blank browser through both-arm MCP connection/config parity, seed restoration,
container cleanup, and volume detachment. The receipt explicitly retains
`protected_eligible=false` and `model_gateway_qualified=false`.

Remaining gates: add and independently review an explicit third loopback port
in the research-only NativeServer boundary while keeping inference and native
ports intact; prove the model-facing OpenCode tool catalog and tool dispatch
through a separate public compatibility turn or a supported no-model native
tool invocation path; review the container and broker security independently;
freeze a valid 30-task roster before any protected candidate run. The current
OpenCode startup check proves the browser MCP server connected in both arms,
not that a model invoked its tools. The Dockerfile pins its base image and npm
package lock, but `apk add chromium` resolves from a mutable Alpine repository;
the exact tested output image ID, not a rebuild from this Dockerfile, is the
executable identity used in the receipt.
