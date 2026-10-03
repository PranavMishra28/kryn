# Terminal-Bench / Harbor development calibration

Frozen at 2026-10-03T01:13:10Z, before any KRYN model generation on this task.
This is an adapter and grader calibration on **one public sample task**, not a
representative Terminal-Bench score, a protected holdout, or evidence of
frontier equivalence. Released KRYN v1.0.0 remains installed and unchanged.

## Pinned inputs and decision

| Item | Frozen value |
| --- | --- |
| Official harness | `harbor-framework/harbor@fd1521a1da6250d9ed8fc7505caa0b7a72f36c4b`, Harbor 0.23.0, Python 3.12.13 |
| Registry | `laude-institute/harbor@fd1521a1da6250d9ed8fc7505caa0b7a72f36c4b`, `terminal-bench-sample@2.0` |
| Task | `log-summary-date-ranges`, `laude-institute/terminal-bench-2-0-sample@7e917f35c281188532772312d4ad91ca9274febc`, `sample/log-summary-date-ranges` |
| Original task TOML / instruction SHA-256 | `aa6b5d0875c05fbd1eb4fe258fdcf2f57c96e757e794ccab73106f5a8b8121ce` / `c1d4516ad4ec2238209740eaf01291df9ab48b0028a3fc5df383c6f831453484` |
| Pinned task TOML SHA-256 | `66edfdf4d98ca70dbeb424fa692b0978f3a8ebf29bb5d24a622ade2631bf125d` (only `docker_image` tag changed to digest) |
| Official task image | `ghcr.io/laude-institute/terminal-bench/log-summary-date-ranges@sha256:277e7926a960bd0c9db733f50ce9861635abad6f5281910a33759d89e52bf9ab` |
| KRYN worker | `@opencode/cli@2.0.10`, KRYN's shipped policy/agent configuration and product plugin; Qwen3.5-9B-6bit on the owner's unchanged guarded oMLX runtime |
| Adapter / guarded runner SHA-256 | `6314ee5119b17e6932c46bc5b0256aba579a47cd8a10129ec3d9c9b27cfc248d` / `d5bafda66e65eeaf9f0b948ab7654ef2c8f8249888f1cc77757c8dcf333d4cce` |
| Shipped config / product plugin source SHA-256 | `fc1b6db212ff6646917f254d27b38cb03dae225e5bd57449812bce304f7729bd` / `24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f` |
| Agent budget | One 900-second generation, one heavyweight local model request at a time, no operator repair |

The [official Harbor guide](https://github.com/harbor-framework/docs/blob/main/examples/terminal-bench.mdx)
identifies Harbor as Terminal-Bench's evaluator. Harbor's bundled OpenCode
adapter installs `opencode-ai`, whereas KRYN pins the separate `@opencode/cli`
2.0.10 package. The small research adapter therefore installs that exact
package and uploads the product plugin; OpenCode itself still runs the agent
loop, and Harbor still runs the task and verifier. The task container lacks the
owner's browser and search MCP, so this measures KRYN's **terminal profile**,
not its full interactive product. The Docker task boundary substitutes for the
Mac shell sandbox; this difference must remain explicit.

The candidate talks through a one-model, two-route inference relay reused from
KRYN's prior external adapter. A local container forwarder gives the product
plugin its required loopback URL. No paid provider or extra model is used. The
unchanged 22-GiB oMLX process ceiling and KRYN daily-use host guard apply:
critical pressure, missing telemetry, changed listener, or more than 512 MiB
whole-probe swap growth aborts the trial. Warning pressure alone does not
abort this daily-use policy. Guard cancellation closes the relay and cancels
Harbor's owned trial; an accepted result also requires the runtime to settle.

The gold-solution preflight, before candidate generation, returned official
`reward: 1.0` with no grader error in trial
`kryn-harbor-oracle-20261002`. It establishes that this pinned task/image is
gradeable; it is not KRYN performance. The KRYN calibration is strictly
accepted only if the native worker completes, Harbor reports reward 1.0, the
relay records actual local inference, the guard is clean, and the runtime is
idle. Any setup/guard/timeout/oracle failure is recorded, not silently retried
after generation. One success or failure here cannot support a same-model
harness uplift claim; a native OpenCode arm and a predeclared broader subset
would be required.

The task and its tests are public development data. Harbor uploads verifier
material after the agent phase; the candidate receives neither the local task
source directory nor host credentials as a mount. Docker Desktop can still
reach other host-loopback services through `host.docker.internal`, so this
calibration does **not** qualify as a sealed security boundary or protected
holdout. The earlier inspected `regex-log` sample is excluded from this
calibration. Raw trial logs and resource samples remain under ignored
`/private/tmp/kryn-harbor-calibration/`.
