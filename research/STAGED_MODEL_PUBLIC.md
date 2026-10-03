# Public staged local-model development screen

Preregistered before writing the runner or sending a model request. Released
v1.0.0 and its 9B/96K/22-GiB guarded profile stay unchanged. This is a single
public KRYN-arm mechanics-and-quality screen, not H1 or a protected holdout.

**S2 hypothesis:** the real local model can complete a three-stage coding task
in one owned OpenCode session across two completed native compactions and two
actual server restarts, retaining earlier criteria while repairing a newly
introduced failing check. The changed variable from the passing canned S1
screen is real guarded inference and a frozen coding task; the same native
session/restart functions are reused.

The task is a tiny `Tracker` module. Stage 1 adds item creation and listing
with validation and monotonically increasing IDs. Stage 2 adds completion and
snapshot behavior without restating every stage-1 criterion. After the second
compaction and restart, the trusted runner adds a separate legacy-ID parser
with a deliberately failing public test; stage 3 asks the Agent to repair that
failure while preserving previous behavior. Prompt bytes, seed files, injected
files, independent oracle and runner are committed before generation.

One attempt passes only if all three Agent turns finish, two compactions and
two restarts preserve the exact session/model/workspace identity, the injected
test fails before stage 3 and passes after it, a separate trusted oracle
accepts all stage-1/2/3 requirements, no tracked test is deleted or rewritten,
all three user prompts and compactions remain in raw history, the unchanged
resource guard does not stop the run, telemetry is complete, and the candidate
APFS volume detaches. The runner must record tool, token, time, power, memory
and swap evidence. A failed criterion is a failed screen even if the Agent
claims completion. Do not retry the same resource-gated condition.

The fixture and oracle are development material. The trusted oracle runs only
after the model is stopped; the Agent's sandbox must deny direct access to its
source file. Unlike the protected Agent-to-grader barrier, this public screen
does not use a separate grading volume. It therefore cannot count as a sealed
holdout result or establish long-horizon production reliability. If it passes,
the next gate is a matched native/KRYN screen on fresh tasks with separate
grading volumes; if it fails, retain the raw receipt and diagnose the first
blocking stage without rewriting the acceptance criteria.

## Frozen attempt and independent review

At clean source commit `7325b0926d4128fbf9eedda3c30f12ec0f182a83`,
the current-source no-model S1 control passed in both arms. The one guarded
real-model KRYN attempt then completed all three turns in 197.3 seconds and
26 inference requests. Two native compactions completed; the actual server
restarted twice with new PIDs while retaining the same session, model,
workspace and all three user prompts. The injected public test failed before
stage 3 and passed afterward. Both tracked tests stayed byte-identical; the
candidate volume detached. Telemetry was complete with normal sampled
pressure, no guard stop and zero swap growth.

The **frozen screen failed** because the independent oracle rejected `# 3`
as a legacy ID while the Agent's code accepted it. Both visible tests passed,
and the Agent claimed it had implemented the parser correctly. The raw
`result.json` SHA-256 is
`c2597338cd6da128c84cf36480226d0728c831a3590f6408d09ae167467a6ac8`.
Its 61-file owner-only evidence archive, including the detached APFS image,
hashes to `f4c89f9b12e7d3861ea937ee668e6f4b3e3642f3a02e037f59e903717e3bb048`;
the index hashes to `e42fdcc0471af4b3921b0d902c10e9b7347fa4e4ea2465369110e7962103a213`.

Independent review also found that the stage-3 prompt said “optional leading
`#` and surrounding whitespace” without explicitly forbidding whitespace
between `#` and digits. That makes the rejected edge ambiguous. The oracle
and reference choose the stricter grammar, but this observation **cannot**
establish a model-quality failure on a clearly specified requirement. An
initial postmortem overcalled it false completion; a preserved, superseding
owner-only review (`independent-review-v2.json`, SHA-256
`b77d30665c1206ed1d8ff718b2cd3ca4e03dbf2d6de08b5c8ba3f116f4a69e4f`)
corrects the inference without changing the frozen result. The exact task is
retired from any protected use. The process and continuity mechanics passed;
independent coding quality and H1 remain unqualified. No product change follows.
