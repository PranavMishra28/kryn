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
abort this daily-use policy. The runner is wired to close the relay and cancel
Harbor's owned trial on a guard stop; that cancellation path did not fire in
this calibration. An accepted result also requires the runtime to settle.

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

## Recorded result, 2026-10-03

The preregistered one-shot KRYN trial was
`kryn-harbor-candidate-20261002`. Harbor identified the agent as
`kryn-opencode`, version `opencode v2.0.10`, with `local/qwen`; the product
plugin created its container-owned state. The inference-only relay recorded
12 local requests. OpenCode exited normally after 109.192 seconds of agent
work, 11 tool calls, 97,553 new input tokens, 75,776 cache-read tokens and
2,610 output tokens. Host telemetry was complete across 56 samples, remained
at normal or warning pressure, saw AC power only and zero swap growth. The
unchanged guard did not stop the trial, and the model runtime settled idle.

**Official reward: 0.0; strict acceptance: fail.** Harbor's verifier found
the CSV and accepted its header and first 12 period/severity rows, but the
three `total` counts were wrong. The emitted `total,ERROR` was `20151`
against the verifier's `14160`; `total,WARNING` and `total,INFO` were also
inflated. The worker's generated script added each file to `total` explicitly
and then added it again when iterating all periods, which included `total`.
It inspected sample daily counts and the output file but never tested the
aggregate invariant; its final message asserted the results were accurate.
That is a false completion claim about a simple aggregation bug, not a Docker,
relay, model-protocol or memory-guard failure. The worker was not retried on
this task.

The compact machine-readable receipt is
`history/harbor_calibration.jsonl`. The candidate trial's 19-file SHA-256
manifest hashes to
`2da5412e24cb4d068cc277d076c635cc11bd1186e10f1971d82b10f44f423437`;
the gold preflight manifest hashes to
`93c4e4da6fbd2506d08ae1a9d3fc1fbd6ce1ee1b908db448a533322feec69919`.
Full raw evidence remains local and ignored. This single public failure shows
that a working official grader connection does not imply task reliability.
It leaves the external-transfer, protected holdout, same-model uplift and
frontier-adjacency gates unqualified.

## Post-hoc native-control diagnostic, frozen 2026-10-03T01:27:01Z

The KRYN failure above was inspected before this control was chosen. A single
native OpenCode run on the **same public task** can diagnose whether its 9B
worker also makes the aggregation error, but selection after seeing KRYN's
result prevents a causal H1 or benchmark-uplift claim. There is no second KRYN
attempt. The only arm change is removal of KRYN's product plugin and extra
agent system guidance, matching the native-control definition in
`tools/run_native_trial.py`; the main agent description, model, sampler,
CLI, container image, task, visible tools, permissions, timeout and unchanged
daily-use resource guard remain the same. Native and KRYN container configs
have identical provider, MCP, permissions, main agent and every other
non-treatment field in an offline diff. Their SHA-256 hashes after rendering
are respectively `bc28c1be7db60dac1c059d1d7f326b36dba2bb163523a0d59585e0587e640c24`
and `c652945d5aed398a131fc623a60d6c768b5f670811bd3454cdf2eb691223f4c5`.
The amended adapter SHA-256 is
`f371cb7e5c46fc7e9804a6a8f70f8b5758c037d0b7b92fb68cf73e3a42ce7676`;
the guarded runner SHA-256 is
`ff0de868f797a638582ea25c408a95b0da7d9fa5e3ce0ea33874eec59f50c3c6`.
The base source commit is `9f7dc5b1941dba26b8413f513f74f3c8a7319b3a`.

Run exactly one fresh native trial named `native-harbor-control-20261002`
with `--arm native` and the original task and trials directory above. Require
normal OpenCode completion, the official Harbor reward, actual Qwen inference,
a clean guard verdict and runtime settlement. Before comparing behavior,
also compare the first nonempty wire tool-schema hash, tool count and numeric
sampler fields from both relay logs; a mismatch invalidates the matched-tool
interpretation. Record completion, reward, code trajectory, false-completion
claim, runtime, tokens, resource samples and any guard stop. A failure or
guard stop is a result, not a reason to retry. No product change is promoted
from this one post-hoc diagnostic.

### Environment-only amendment, frozen 2026-10-03T01:47:31Z

The first native trial exited during `apt-get install` with intermittent
`deb.debian.org` DNS failure. It made **zero** inference requests, never
started the model guard, and has no grader result. Its 11-file raw evidence
manifest SHA-256 is
`3f89fc64a72d527c98ed4b79abde24c9b128ffa40ff8ea998e2e1307e9be7772`.
This is an adapter-environment failure, retained as a distinct failed trial;
it is not an unsuccessful model generation. Docker DNS now resolves again.
To test the already declared native control without hiding this fault, run a
new `native-harbor-preflight-20261002` **install-only** trial first. If that
setup passes, run one new `native-harbor-control2-20261002` generation with
identical task, adapter, model, config, guard and evaluation rules. If the
preflight or generation setup fails again, stop this Harbor control screen
and change approach. Do not aggregate either setup trial as an agent success
or silently replace its evidence. This amendment was committed before any
native-model generation on this task.

To reproduce the adapter check, install Harbor from the pinned commit in a
disposable Python 3.12 environment, download
`terminal-bench-sample@2.0` with `harbor datasets download`, and pin the
copied task's `docker_image` to the digest above. Before model generation,
run its gold oracle with `harbor trials start -p <task> -a oracle`; it must
return reward 1.0. Then run one fresh trial with:

```sh
PYTHONPATH=<KRYN checkout> <Harbor venv>/bin/python -B \
  <KRYN checkout>/research/run_harbor_calibration.py \
  <pinned task> <private trials directory> <fresh trial name>
```

The runner imports Harbor only in this optional research environment; KRYN's
production package has no Harbor dependency. Its trial result and guard
summary are in the private trials directory. Preserve failed runs rather
than reusing a trial name or treating the sample as a full benchmark score.
