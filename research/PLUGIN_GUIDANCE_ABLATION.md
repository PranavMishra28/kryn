# Product-plugin ablation with KRYN guidance held constant

Frozen before modifying the research driver or making a model request for
this experiment. This is a **public development** diagnosis on already-seen
TaskboardLite 03, not a protected H1 result or a product promotion. Prior
matched Task03 pairs were native OpenCode 2/2 accepted and KRYN 0/2. KRYN's
failed turns included a timeout and a preserved-test edit, but those traces
do not identify whether the product plugin or guidance caused the difference.

**G1:** removing only KRYN's product plugin while retaining its managed
`AGENTS.md` and agent guidance improves strict Task03 acceptance or reduces
unproductive tool/repair behavior. Compare full KRYN (K) with guidance-only
(G). G retains the same model, runtime, 96K configured context, Default
variant, MCP/browser/search tools, effective permissions, agent descriptions,
task prompt, fixture, grader, 900-second turn cap and unchanged daily-use
guard. Its sole intended difference is absence of `kryn.product`; the
research audit plugin is present in both arms. The driver must prove the
product plugin is absent in G and active in K, and reject unequal first-wire
tool schema or effective permissions. No owner installation changes.

Use two fresh pairs in G→K then K→G order, one attempt per arm per pair, with
no operator repair. Warm/idle model state and AC/battery state are recorded;
a pair with mismatched provenance is diagnostic only. A guard stop, timeout,
false completion, changed preserved file, failed frozen Task03 grader or
failed supplemental report/CLI/HTTP probe is strict failure. Record native
completion, grader assertions, requests, tool calls/errors, token/cache
counts, wall time, memory pressure and swap. If the first pair is stopped by
the unchanged occupied-host guard, do not repeat an identical condition to
seek a pass.

This development screen suggests plugin harm only if G is strictly accepted
in at least one more trial than K across valid pairs, without a compensating
G regression or unmatched controls. Two pairs cannot establish population
uplift; any positive result would require a fresh independently graded task,
cost comparison and one-variable product candidate before promotion. A tie,
guard stop or inconsistent pattern is inconclusive. Preserve every raw
attempt, including failures. Do not edit the plugin, installed profile,
resource guard, graders or release gates for this screen.

## Completed result (2026-10-03)

Both reverse-order pairs passed the fail-closed matched-controls comparator.
The model was loaded and idle before each arm; all four turns used AC power,
the same 900-second limit, Default sampler, 41 first-wire tools and effective
permissions. The wire-tool-schema SHA-256 was
`3fcb5b056c05da695548bfe35da9002b628b51df87a2e2aca80e78906da9e085`
and the effective-permission SHA-256 was
`b37bfbfc38edfc3975f9b458d62b6f40c08ae80e4355022de00b1be4394413ff`
for every arm. A setup-only warmup loaded the model before pair 1. Neither
pair had a guard stop or sampled swap growth. The second G turn had warning
pressure, which the unchanged daily-use guard permits.

| Order | Guidance-only (G) | Full KRYN (K) |
| --- | --- | --- |
| Pair 1, G then K | **Failed**, 58.455 s, 11 tools. Asked an unnecessary clarification already settled by the task; the unattended question was dismissed. Frozen and supplemental graders failed. | **Accepted**, 376.673 s, 36 tools. Completed; frozen and supplemental graders passed, preserved files unchanged. |
| Pair 2, K then G | **Accepted**, 523.142 s, 54 tools. Completed; both graders passed, preserved files unchanged. | **Failed strict completion**, 908.209 s, 51 tools. Timed out at the frozen 900-second cap; both graders passed on the resulting code and preserved files were unchanged. |

Strict acceptance was **G 1/2, K 1/2**. The first G failure and second K
timeout are different failure modes; neither establishes that the product
plugin helps or hurts. The K timeout trace includes two correctly denied
check commands whose pipelines hid exit status and one read-before-edit denial.
These added repair steps, but the trace does not establish that removing the
guards would have produced a completed, accepted turn. The K arms used 87 tool
calls and 1,284.882 driver seconds total; G used 65 calls and 581.597 seconds.
These are observations from four attempts on one already-seen task, not
reliable cost or quality estimates. The earlier unchanged-product Task03 pilot
had K 0/2, while this one had K 1/2, illustrating run-to-run variation.

Compact fail-closed receipts are in
[history/development.jsonl](history/development.jsonl) under
`plugin-g1-p{1,2}-{guidance,kryn}-20261003`. Raw traces and independent grades
remain in ignored local `evals/runs/`; the owner-only 244-file raw manifest
has SHA-256
`4b5ba5a7ad200eabe9942234ae0c73970810b6fc2b9d7d7026ea2cab0ec545b5`.
This screen **does not pass G1's promotion threshold**. Keep the released
product plugin, installed profile and guard unchanged. The guidance-only arm
is research instrumentation for reproducing this negative result, not a new
user-facing profile. No H1 or frontier-adjacency claim follows from this
public development screen.
