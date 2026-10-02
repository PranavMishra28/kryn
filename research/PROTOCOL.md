# KRYN harness research protocol (preregistered 2026-10-02)

This protocol is a research plan, not a claim that KRYN is frontier-adjacent. Released
v1.0.0 (`4038a77ebea5f421b08b055c9aa768dcf12a890b`) remains the production
control. Research runs use disposable workspaces and a separate candidate checkout;
they must not change the installed profile, resource guard, graders, or release gates.

## Claim and experimental arms

**H1:** with Qwen3.5-9B-6bit on the same Mac, KRYN increases independently accepted
engineering work over OpenCode's native execution loop. Arm A is OpenCode with the
same local provider, oMLX runtime, 96K configured context, output and reasoning
settings, MCP tools, shell boundary, and effective permissions, but with the KRYN
product plugin and global KRYN guidance absent. Arm B adds those two KRYN components.
The fixture's own `AGENTS.md` is identical in both arms. A tool-catalog or effective
permission mismatch invalidates the pair; it is not silently counted as a loss or
win. The main comparison is a *whole policy/state-layer* ablation, not attribution
to one hook. Subcomponent attribution requires later one-variable ablations.

The first runner validation uses public TaskboardLite tasks 02 and 03. They were used
for prior tuning and are **development data only**. Older September comparisons had
49K context, an earlier plugin, and too few trials; their outcomes cannot establish
uplift for v1.0.0. Do not select changes from a holdout outcome.

## Three evaluation layers

1. **Development:** public TaskboardLite plus prior failure reproductions. Run two
   repetitions per arm on 02 and 03 in interleaved AB/BA order. A clean, fully
   instrumented pair validates the runner; a functional grade is only one endpoint.
2. **Protected internal holdout:** commission 30 fresh tasks, three per category:
   repository bugs, multi-file features, API compatibility, UI/browser, persistence,
   refactoring, failure recovery, long sessions, context/restart, and current external
   information. Freeze task text, base commits, oracle hashes, reference solutions,
   time limits, and a hash of the full task roster *before* candidate tuning. Confirm
   each reference passes and the broken seed fails. Keep grader material outside the
   candidate process's readable filesystem and network boundary; same-account
   path hiding alone does **not** qualify. Randomize pair order with a recorded seed;
   run two repetitions per arm per task. Once used for tuning, retire a task from the
   sealed set. If this boundary cannot be demonstrated, holdout results are labeled
   development data and H1 remains unqualified.
3. **External:** run predeclared small subsets of SWE-bench Verified and Lite through
   the [official evaluator](https://github.com/SWE-bench/SWE-bench/blob/main/docs/reference/cli.md),
   and Terminal-Bench 2.0 through [Harbor](https://github.com/harbor-framework/docs/blob/main/examples/terminal-bench.mdx).
   Pin evaluator commit, dataset revision, Docker image digests, task IDs, command,
   and timeouts before generation. KRYN must produce patches/terminal actions through
   its real OpenCode loop; external software grades the result. A subset is never
   called an official full-suite score. Docker is installed but its daemon was not
   running at preregistration; the external gate is pending, not passed.

## Endpoints and decision rules

Primary endpoint: fraction of trials with every frozen acceptance criterion passed
by an independent grader, native completion, no operator repair, and a clean
resource-guard verdict. A timeout, guard abort, unverified browser/API criterion, or
partial task scores zero. Also retain per-criterion results; a task's own claim never
decides acceptance. Count false completion separately when the agent says it is done
but the independent oracle rejects it.

Record wall time, model generations, tool calls/errors, input/output/cache tokens,
compactions, restarts, interventions, memory pressure, and swap growth. Missing
telemetry is `null`, never zero. Report accepted trials per occupied-host hour,
including failed attempts. Use a task-clustered paired bootstrap (10,000 resamples)
for a 95% interval on the KRYN-minus-native acceptance difference; show raw counts
and paired discordance. H1 is supported only if the point estimate improves by at
least 15 percentage points, its 95% lower bound exceeds zero, false completion does
not increase, and accepted work/hour is at least 1.10 times Arm A. Otherwise report
`NO DEMONSTRATED UPLIFT`, including uncertainty; do not tune these thresholds later.

Each candidate must state one mechanism and one changed variable before editing.
Promote only if development improves, a fresh validation set does not regress,
protected/external results support transfer, accepted work/hour does not fall,
and v1's package/rollback tests pass. Reject task-specific answer keys and any
change to grader, security policy, provider authorization, or memory guard for score.
Keep every failed receipt. A validation task used to choose a candidate is retired
from final holdout analysis. After two failed attempts at one mechanism, change
mechanism rather than lengthening prompts.

## Research ladder and limits

First establish the matched v1 comparison. Only then test, one at a time: (1)
context selection; (2) verifier-driven repair; (3) stale-check/continuity behavior;
(4) adaptive reasoning; (5) cross-project strategy memory. Give each at most two
small candidates. Freeze the strongest supported harness before comparing a bounded
model shortlist. Any model replacement must pass the same occupied 48-GiB guard and
the original product's browser, restart, install, and rollback gates. Run six
independent long-horizon sequences with two compactions, two restarts, changed repo
state, injected check failure, and UI/API verification; plot success against useful
task duration, not idle time. A frontier-agent comparator requires the user's
separate choice of provider and budget; no paid inference is authorized here.

The research artifact must disclose the exact model/runtime hashes, hardware and
power state, task selection, config and tool/permission hashes, all attempts,
grader/source hashes, confidence interval method, failures, and non-matched factors.
These rules follow the need to control benchmark overfitting identified by
[RRSI](https://github.com/google-research/rrsi), while the duration analysis uses
the [METR time-horizon method](https://metr.org/time-horizons/) as a guide. Neither
source establishes KRYN's performance.

No "frontier-adjacent" claim is permitted until all eight gates in the user goal
pass, including a matched authorized frontier comparator. `NO IMPROVEMENT` is a
valid research result. The next public release is out of scope for this protocol.
