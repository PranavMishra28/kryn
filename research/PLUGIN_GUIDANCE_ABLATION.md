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
