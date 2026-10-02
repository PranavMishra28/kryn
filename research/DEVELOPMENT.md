# First observable-control development pilot (2026-10-02)

This is public TaskboardLite development data, not a protected holdout or evidence
of frontier-level capability. The fixed model was Qwen3.5-9B-6bit through oMLX
with the v1.0.0 96K profile, default reasoning, the same 41 wire tools and effective
permissions, a warm runtime, AC power and the unchanged daily-use resource guard.
The final two pairs were launched with a 15-minute turn limit; the driver did not
persist that limit or invocation-time binary/profile hashes, so none of these
pairs qualifies as fully auditable matched evidence. `history/development.jsonl`
indexes every attempt; raw
traces remain in ignored `evals/runs/` on the test host.

| Task | Order | Native OpenCode | KRYN |
| --- | --- | --- | --- |
| 02 | KRYN then native | PASS, 99.409 s | PASS, 199.202 s |
| 02 | Native then KRYN | PASS, 200.670 s | PASS, 308.151 s |
| 03 | Native then KRYN | PASS, 290.811 s | FAIL, 60.286 s |
| 03 | KRYN then native | FAIL, 461.041 s | PASS, 705.321 s |

Acceptance includes the frozen grader, the pre-existing Task02 date-boundary
probe or Task03's additional report/CLI/HTTP edge-case probe, native completion,
zero operator interventions and clean resource telemetry. All four pairs matched
on **recorded** prompt, model, sampling settings, tool IDs and full wire schema,
effective permissions, guard, warm state and power. The comparator now requires
invocation-time source, binary, profile and timeout provenance and labels the
pilot's missing fields as unverified. All eight runs observed normal host
pressure, zero swap growth and complete telemetry.

Both arms accepted **3/4**. Native used **1,051.931 s** total and delivered
**10.27 accepted trials/hour**; KRYN used **1,272.960 s** and delivered **8.48/hour**.
KRYN consumed 395,905 new input tokens versus 182,109 for native. The observed
pilot provides no evidence of an uplift and falls short of the preregistered
accepted-work/hour threshold. Four repetitions across two previously seen tasks,
with incomplete invocation provenance, cannot estimate transfer or settle H1;
no inferential interval is reported.

The two Task03 failures differ. KRYN first tried unavailable `browse`, then asked
for confirmation of already-specified requirements; the unattended question ended
the turn before edits. Native's second run implemented the behavior but added tests
inside `test_existing.py`, violating the explicit requirement to leave existing
tests unchanged. In KRYN's accepted Task03 run, repeated edits to its own tests
extended the repair trajectory; the independent grader, not those tests, decided
acceptance.

The second Task02 pair used metadata-only prompt auditing. Native kept one
system-prompt fingerprint across 15 requests, starting at 6,277 bytes. KRYN
started at 12,332 bytes and used eight fingerprints across 22 requests, with seven
changes. Some changes coincided with lower cached-token counts and higher new
input-token counts. This identifies a **cache-efficiency hypothesis**, not a
proven causal mechanism or a reason to remove verification without ablation.

Two earlier Task02 attempts are excluded from the matched result: the first native
trial was stopped by the stricter research host-memory preflight, and the first
warm pair had unequal wire tool schemas because the control initially omitted
agent descriptions. The second native run in that unmatched pair also failed the
pre-existing date-boundary probe despite a frozen-grader PASS. All are retained in
the ledger as diagnostic attempts.

The next gates are a full protected candidate run using the user-facing `agent`
role, fresh sealed tasks and a grader beyond the candidate's filesystem/network
boundary; then official, pinned external subsets and one-variable ablations.
The macOS read-boundary canary passed, but that alone does not qualify a protected
holdout. The Docker daemon is not running, so official evaluator runs are pending.
Released v1.0.0 and the owner installation were not changed by this pilot.

## Isolated native-process preflight

One additional **public** `collections` fixture ran through the existing
`NativeServer(background=...)` path with the OpenCode process and its descendants
inside the macOS read/network boundary. The trusted parent kept the oracle outside
that boundary and graded the resulting program afterward: 3/3 checks passed in
84.965 s, with 12 local inference requests, normal sampled pressure, zero swap
growth, and verified native settlement. The separate direct/symlink grader-read
canary also passed, and the owned OpenCode server and CLI had exited afterward.
This qualifies a real sandboxed runner path, **not** a protected holdout task or
an H1 result; the fixture is previously visible development data.

The current idle learner initially refused the installed default `local/qwen`
reference because it requires an explicit variant; this preflight used a disposable
`local/qwen#fast` config and a disposable resumed control. No installed learning
control or production profile changed. Default-variant support and a full sealed
candidate/grader run remain unqualified.

### Default-variant learner candidate

The installed `local/qwen` reference failed before dispatch with
`Learning requires the selected explicit local model variant`. A separate
two-line candidate accepts that native reference as OpenCode's `default`
variant while preserving the existing explicit-variant validation. In a
disposable resumed learner state, its real sandboxed OpenCode turn on the
public `records` fixture completed and passed the external 3/3 black-box
checks in 68.437 s, with 12 local inference requests, normal sampled host
pressure, and zero swap growth. The default-variant path is a functional
repair, not evidence that autonomous learner promotions improve engineering
quality; selection, protected validation and rollback remain required.
