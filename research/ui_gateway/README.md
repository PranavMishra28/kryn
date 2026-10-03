# Research-only UI 01 browser gateway

This prototype exposes one self-contained `index.html` from a disposable
candidate checkout to a local OpenCode MCP adapter. The adapter accepts only six
browser operations and sends checked page bytes to a broker. Chromium runs in a
separate container with no host mounts, network, or Docker socket. The browser
has no grader, reference, source snapshot, or host path. Nothing here changes
the installed product browser profile or permits a protected model turn.

The adapter uses a fixed `http://candidate.invalid/index.html` URL. On every
navigation it opens `index.html` relative to a canonical checkout directory fd
with `O_NOFOLLOW|O_NONBLOCK`, verifies regular type, candidate device, and a
1 MiB cap, and sends an immutable buffer. The browser worker allows inline
script and style for this single-file task and denies all other requests. It
provides snapshot, CSS-selector click, a small keyboard set, screenshot, and
viewport resize. The broker uses an exact local Docker image ID and verifies
no mounts, no network, read-only root, non-root execution, dropped capabilities,
process and memory limits; it owns container cleanup. The trial config removes
search MCP and denies search/web fetch identically in both arms.

Build the worker image from this directory with `docker build --pull=false -t
kryn-ui-worker:research-20261003 .`, then use the resulting exact image ID with
`python3 -B preflight.py --draft PRIVATE_DRAFT --image sha256:IMAGE_ID --output NEW_PRIVATE_DIR`.
The preflight uses a disposable APFS candidate volume, a host-side hidden
canary, the actual Seatbelt profile, direct MCP calls, and no-model OpenCode
startup for native and KRYN arms. It intentionally substitutes the broker port
for the inference port; this cannot support a model turn.

The final local no-model run used image
`sha256:16c1133894770bceab9f2f3a9bfac4e7ec1b3dde1fe2f0f6a7063ba49b3436a2`.
Its private receipt is
`/private/tmp/kryn-ui-gateway-preflight-05/receipt.json`, SHA-256
`9d17eaf3f3b919f5db8b44a183ebde77643ef4dc897cb816e6d659e26bb276b7`.
All 20 no-model checks passed, including a reference ArrowRight interaction,
hidden-file and hardlink denial, malicious page file/network attempts, symlink
swap, FIFO, oversize entry, both-arm MCP connection/config parity, container
cleanup, and volume detachment. The receipt explicitly retains
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
