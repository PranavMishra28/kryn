# Public staged coding calibration (preregistered 2026-10-03)

This is a **development** screen of the released v1.0.0 harness. It is not a
protected holdout, a product promotion, or evidence of frontier equivalence.
The experiment changes no product code, installed profile, model, context tier,
provider, guard threshold, or release setting.

## Question and controls

Can the pinned local Qwen3.5-9B-6bit complete a small three-stage Python coding
task through its real OpenCode Agent loop when the *same* session undergoes two
manual compactions, two actual server-process restarts, and a trusted edit to a
tracked rule file? Compare minimal/native OpenCode and KRYN. The only arm
variable is KRYN's product plugin and guidance; both use the same model,
runtime, 96K configured context, shell/tool environment, permissions, prompt,
fixture, guard, and grader. No browser is required for this public task.

Arm order is determined before generation by SHA-256 of
`kryn-public-staged-20261003-v1`: first byte odd means KRYN then native. The
frozen digest starts `17c88b0c`, so **KRYN runs first**. Use one attempt per
arm. A guard stop, timeout, incomplete generation, or missing independent
acceptance is a failure; do not rerun the same condition to obtain a pass.

## Frozen task

The seed Git repository has only `solve.py`, which reads one JSON object from
stdin and writes `{"error":"missing"}`, and tracked `rules.json`, initially
`{"separator":"-"}`. Keep the JSON-lines-independent one-request/one-response
CLI contract and use the Python standard library only. The exact successive
user prompts are:

1. `Read solve.py and rules.json first. Implement the normalize operation: input {"op":"normalize","text":string}; output {"value": text.strip().casefold()}. Preserve internal whitespace. Keep JSON stdin/stdout. Run a relevant check before declaring completion.`
2. `Continue the same task. Add the slug operation: input {"op":"slug","text":string}; output {"value":normalized text with every maximal Unicode-whitespace run replaced by the current separator from rules.json}. Preserve punctuation. Keep normalize working. Read the current files and run a relevant check.`
3. `The tracked rules.json was changed by the task owner after your previous turn. Read it again before editing. Add the unique operation: input {"op":"unique","items":[strings]}; output {"values":[unique slugs in input order]}. Form each base slug with the current separator; on collisions append that separator and the smallest integer starting at 2 that is not already used. Preserve normalize and slug, including their current-rule behavior. Run a relevant check.`

After stage 2 and its compaction/restart, the trusted controller replaces the
tracked `rules.json` contents with `{"separator":"_"}`. The agent receives no
literal new separator in the stage-3 prompt. This deliberate Git change tests
whether its action follows current source rather than a stale checkpoint.

The independent development oracle exercises stage 1's trim/casefold/Unicode
and retained inner whitespace; stage 2's Unicode whitespace collapse, empty
input and punctuation plus all stage-1 cases; stage 3's changed separator,
duplicate and naturally suffixed collisions, plus all prior cases. The exact
JSON cases and reference solution are versioned in
`research/public_staged_fixture.py`; freeze their SHA-256 before first model
request. Seed must fail and reference must pass every applicable stage. A
stale-separator negative control must fail stage 3. Oracle data stays outside
the candidate volume; this does not qualify it as a protected holdout.

## Acceptance and reporting

Each arm must complete three native Agent turns in one root session; finish
two manual compactions and two real server restarts with new PIDs and policy
active; retain the same session/model/workspace identity and raw turn history;
and pass the independent stage oracle after *each* turn. The model must perform
at least one source-reading tool action before its first edit in each stage.
The resource guard must stay green, telemetry complete, no sampled swap growth
above its unchanged threshold, and the candidate volume must detach. Record
tool schema, config/permissions, model/runtime identity, source and prompt
hashes, CLI events, exported session, failed checks, requests/tokens, wall time,
pressure and swap, and any intervention. A pair with unequal first-wire tool
schema or effective permissions is unmatched, not an uplift observation.

This one pair is a calibration, never an estimate of H1 or long-horizon
reliability. Even two passing arms provide no uplift evidence. Passing allows
considering a larger qualified staged runner; any failure remains in the
append-only development history. The v1.0.0 product stays unchanged.
