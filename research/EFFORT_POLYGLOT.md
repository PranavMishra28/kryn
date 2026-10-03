# Default/Fast mode screen on a fresh public coding task

Frozen 2026-10-03T02:13:39Z before local-model generation on this task.
This is a one-task **development** mode calibration, not an adaptive-effort
controller, a Terminal-Bench score, a protected holdout, or evidence of H1.
Released v1.0.0 and the owner's installed profile remain unchanged.

## Hypothesis and inputs

**E1:** for a bounded coding task, the existing Fast variant can improve
independently accepted work per occupied-host hour versus Default without a
quality or resource regression. The only treatment is KRYN's existing model
variant selected for the top-level OpenCode Agent. Fast bundles disabled
thinking with different temperature, top-p and presence penalty, so the
experiment compares the **product modes**, not thinking in isolation. The
same Qwen3.5-9B-6bit/oMLX, OpenCode 2.0.10, KRYN product policy/plugin, 96K
model configuration, tools, effective permissions, container, task, 900-second
agent cap, inference relay and unchanged daily-use guard apply to both arms.

The task is `polyglot-c-py` from public `terminal-bench-sample@2.0`, source
`laude-institute/terminal-bench-2-0-sample@7e917f35c281188532772312d4ad91ca9274febc`.
It was selected by its **metadata only** (`medium`, `software-engineering`,
`coding`, 60-minute expert estimate), before its instruction was read. The
solution and verifier implementation were not inspected. The original task
TOML SHA-256 is
`edfe39960b6c3e5300a6020bf017d6af6f4d43719cd17c06a0258958e3f0d40b`;
the instruction SHA-256 is
`a57c0c0e1232113113cd29a154ea7e0ac9ea45e4aedc16958fbc6bc753a4ef96`.
The copied task differs only in replacing its image tag with pinned
`ghcr.io/laude-institute/terminal-bench/polyglot-c-py@sha256:bd39e1fdf35f41986bb485a5ebd6835139ffe711b73a1ccde2bb271ce5d73c16`;
its TOML SHA-256 is
`7ebc3a3c4910cf71ea2ce757f231402c7111d858dcfdf2a9cc58ebcb70f5796d`.
The official Harbor 0.23.0 evaluator is pinned at
`harbor-framework/harbor@fd1521a1da6250d9ed8fc7505caa0b7a72f36c4b`.
Its oracle preflight, with no KRYN inference, returned reward 1.0 and no
grader error; the eight-file raw manifest SHA-256 is
`0e3df270ed28cb4b62750f0ff688a38dc07a948ad3a0b633cc44e23ed520d358`.

The research-only adapter SHA-256 is
`a8f49b8262914745955b1cc3c6f552493a07551b3909bbd35cefd54097c94258`;
the guarded runner SHA-256 is
`e175deae2b5d85275973b2c8fe3e4b179a59e3ecbcb170f6e28d0815bdf94b07`.
The product config SHA-256 is
`fc1b6db212ff6646917f254d27b38cb03dae225e5bd57449812bce304f7729bd`;
the base source is `6ebece61774479a66943c98b4933480c7d1a73ed`.
The deterministic order seed `kryn-effort-polyglot-20261002-v1` has SHA-256
`fd582880defceea30e9c6d192c5a42dfa7cef00c9aa7e05382a11ea93b7f34ec`;
its even parity fixes **Default first, Fast second**.

## Frozen procedure and decision

1. Run an install-only preflight through the exact adapter. If it fails,
   record an environment fault and do not generate.
2. Run one fresh guarded Harbor KRYN trial per mode, serially, on disposable
   containers in the fixed order. Use trial names `effort-polyglot-default-20261002`
   and `effort-polyglot-fast-20261002`. Stop on an unchanged resource-guard
   stop; do not retry model generation on the same arm.
3. Check first nonempty wire requests: same model, tool schema and count;
   only the declared variant's numeric sampler/thinking controls may differ.
   An unintended mismatch invalidates the pair. Grade solely by the official
   Harbor verifier, plus native completion, actual inference, clean guard and
   idle runtime. An agent's claim is not acceptance.
4. Record complete trial time (setup, generation, verification), agent time,
   requests, tools/errors, input/output/cache tokens, false completion,
   memory pressure, swap and power. Missing values remain `null`.

The **development screen** is positive only if Fast strictly passes while
Default strictly fails, or both strictly pass with Fast at most 80% of Default's
full-trial wall time and no more generated output tokens. Fast must have no
extra guard stop or false completion. A tie with failure, Fast quality loss,
unmatched wire or resource stop rejects this mode screen. A single positive
public task would trigger a predeclared fresh-task replication and a genuine
fixed-Default versus adaptive policy comparison; it cannot change the
production default or support a frontier claim by itself. Sequential cache
warmth and power differences will be disclosed rather than hidden.

### Environment interruption amendment, 2026-10-03T02:35Z

The first Default trial reached 16 local-model requests, then Docker Desktop
requested a graceful shutdown at 02:28:48Z during the agent turn. Harbor could
not add its tests because the Docker socket disappeared. Its result has no
official reward and cannot count as a coding failure or a completed comparison.
The unchanged resource guard did not stop it. The raw trial is retained under
`/private/tmp/kryn-harbor-effort-polyglot-20261002/trials/effort-polyglot-default-20261002`.
Docker was restarted and its API is healthy. The frozen Fast arm may run once
as a one-arm diagnostic, but **no outcome of it can make this pair a positive
or negative Default/Fast screen**. There will be no retry of this Default arm.
A future mode comparison needs a newly preregistered task and two graded arms.
