# Research-only fixed-page browser gateway

This prototype exposes one self-contained `index.html` from a disposable
candidate checkout to a local OpenCode MCP adapter. The adapter exposes eight
browser operations and forwards requests to a broker. Chromium runs in a
separate container with no host mounts, network, or Docker socket. The browser
has no grader, reference, source snapshot, or host path. Nothing here changes
the installed product browser profile or admits a protected task by itself.

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
`/private/tmp/kryn-ui-interactions-preflight-20261003-c0233ae/receipt.json`, SHA-256
`f6486ec7348b9c55de3ba0e623875924b2c228c505f7852d32d3322ea978aa4b`.
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
`/private/tmp/kryn-ui-interactions-synthetic-20261003-c0233ae/result.json`
(SHA-256 `2608349c188655171e8f439449438271cf2628b44f38626d9e6a2300470a8081`)
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
`/Users/pranav/Documents/Codex/kryn-research-private/ui-interaction-receipt-20261003-final/receipt.json`
(SHA-256 `1e3dfb6e81d3470b4a85557939b983176d3965e23f557b4b42abe1ef0a1fa1c1`)
passes 01: 6/6, 02: 13/13, and 03: 6/6 interaction checks on separate APFS
volumes at clean source commit `c0233ae9dd13a42f9eb03589b454aa9c7a775d3e`.
The first attempt was invalidated by a source/image race and preserved.
The valid receipt does not assert all focus/ARIA or normalized-value behavior,
and is neither an Agent run nor a hidden-grader score. The current
Agent-to-grader entrypoint now has an optional research-only pinned browser
image. It starts the broker after resource admission, waits for the native MCP,
and requires exact container absence and a closed listener before candidate
detachment and read-only patch capture. A failed readiness response must also
clean up the exact container identity allocated before startup. Agent remains
the root and can delegate Browse as a foreground child. The runner uses the
existing paginated owned-session settlement because OpenCode 2.0.10 returns a
`next` cursor even on a nonempty final child page. The installed product is
unchanged.

The reproducible zero-model mechanics probe is `barrier_canned.py`:

```sh
python3 -B research/ui_gateway/barrier_canned.py \
  --seed /private/tmp/clean-public-ui-seed \
  --tool-venv /private/tmp/pinned-research-tools \
  --image sha256:EXACT_LOCAL_BROWSER_IMAGE_ID \
  --output /private/tmp/new-ui-barrier-receipt
```

The seed must be a clean Git checkout with `index.html`; the output must not
exist. Both arms use the same canned inference sequence: Agent writes a public
nonce, delegates Browse, and Browse navigates and snapshots. The barrier then
shuts down the broker, detaches the candidate volume, captures a patch through
a separate read-only mount, and grades a fresh clone. It records per-role tool
catalogs, child ownership, actual browser output, resource samples and the
grader verdict. The paired canary and the 41-check APFS/Seatbelt preflight
passed locally, including a negative probe with a started container and bad
readiness. These are no-model boundary tests, not evidence that the local model
can select or execute the workflow under occupied-host pressure.

Owner-only UI v2 control drafts strengthen focus/ARIA and normalized-value
checks; six other drafts now specify real staged turns and restart. They remain
unsealed and unscored. Drafts 13–15 still use fictional synthetic sources,
not current external information. No protected task was run or relabeled to
fill the roster. The audit and probe hashes are in the compact history index;
raw no-model receipts stay outside the runtime package.

An additional no-model oracle audit found three false acceptances in those
unsealed UI drafts. The tab grader accepted a reference with every `tabpanel`
role removed; the bakery grader accepted an invalid quantity still displayed
as `oops`; and the station grader accepted a positive spaced search that failed
to match. Corrected owner-only drafts pass their references and reject those
mutants. A second alignment screen found that the tab and station graders also
rejected valid implementations solely because of renamed internal IDs or a
URL query that preserved surrounding spaces. Their corrected drafts accept
both valid alternatives and still reject broken variants. All screens used a
pinned local Chrome executable and **zero model requests**. The original
drafts and every raw receipt are retained; the newest drafts remain
`protected_status=false` until the model-facing browser gateway and complete
roster qualify. Freeze and archive hashes are in
[`../history/ui_gateway.jsonl`](../history/ui_gateway.jsonl).

Remaining gates: independently admit a valid 30-task roster, establish guarded
live model quality on a representative occupied host with a materially different,
preregistered resource approach, and run actual protected staged turns with
independent scoring. The tested no-model paths establish lifecycle mechanics,
not protected isolation and model quality end to end. The canned check proves
OpenCode routed these tools, not that a model chose them.
The Dockerfile pins its base image and npm
package lock, but `apk add chromium` resolves from a mutable Alpine repository;
the exact tested output image ID, not a rebuild from this Dockerfile, is the
executable identity used in the receipt.
