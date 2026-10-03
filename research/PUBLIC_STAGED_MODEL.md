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

Frozen fixture SHA-256: `b7209bb5bac3ead98fa6b5f8d15e9346c803f520d6edc27af7e61125b1ad4630`.
Reference SHA-256: `2f1eb648830b588129537e54b811784dc7b203b73b90cf75ddc0fc77f95d3626`.
Stage 1/2/3 oracle SHA-256 respectively:
`c88aee5abe7f4fe0bf181152db1480c6b3e1bca7bd223db8174f294e2f5be36f`,
`5ca38a3a0499df2e855f0a024e37f3b84229be202c66963abcfdb3bc1c5e26c8`,
`bb03e6bb0f12883c8acac0b6067feb0ac032326a61615c5696621518e1ba3748`.
The no-model preflight passed all seed/reference/stale-rule controls twice before
generation; the private receipts remain in `/private/tmp/kryn-public-staged-preflight-20261003-0{1,2}`.

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
