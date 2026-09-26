# TaskboardLite acceptance fixtures

Suite `2026-09-19.2`, authored 2026-09-19. This is a small disposable acceptance/regression suite, not a frontier benchmark. It never invokes an LLM. The reference implementation uses Python's standard library, SQLite and plain browser files. No dependency installation is required for preparation or automatic grading. Real browser/runtime evidence needs the installed LocalAI stack.

## Prepare and grade

From this directory, using the same native Python as the implementation:

```sh
python3 -B bench.py verify
python3 -B bench.py prepare 02 baseline-02-trial1
```

The second command returns JSON with `workspace`, `prompt` and `run`. Run OpenCode in that workspace and submit `TASK.md` verbatim. The candidate may inspect only its workspace, not this parent directory, reference answers, other trials or external graders. Run the normal user harness, with its real settings and permissions. Do not substitute a custom agent loop.

After the attempt ends, from the evaluator directory:

```sh
python3 -B bench.py grade baseline-02-trial1
```

Results are saved to `runs/baseline-02-trial1/grade.json`. Exit 0 means PASS; exit 1 means FAIL or PARTIAL; exit 2 means an evaluation setup/error condition. Check the JSON rather than assuming every nonzero exit denotes a model failure. No command overwrites an existing prepared run. Use a new run ID for every trial. Keep all failed runs.

`prepare` makes a fresh Git repository, fixture snapshot, prompt, evidence directory and operator review template. Existing tests and original seed CSV must remain unchanged. Each coding task is independently seeded: earlier answers/commits never carry into tasks 1–5. The source `fixture/` is the known working reference, and must never be given to the candidate as a solution.

The SHA256 manifest covers runner, graders, prompts, fixture and reference material. `verify`, `prepare` and `grade` refuse altered definitions. This detects accidental or candidate edits; it is not a privileged security boundary. Do not regenerate the manifest after seeing a candidate fail. Correcting a defective test requires a new version and rerunning both arms.

## Automated and operator checks

| Task | Automatic checks | Independent operator evidence still required |
|---|---|---|
| 01 comprehension | Exact factual JSON, totals, original project hashes, no added ordinary files except operator-copied answer | Plan remains read-only; evaluator copies literal returned JSON without repairs |
| 02 bug | Existing tests, original fixture, half-open boundaries, zero/empty/invalid cases | None |
| 03 feature | Report/CLI/API project filtering and preservation | None |
| 04 refactor | CSV corpus, CLI/API errors and atomicity; shared validator imports; no duplicate entrypoint definitions | None |
| 05 debugging | BOM reproduction plus existing/CSV/API cases | Final diagnosis is retained for inspection, not phrase-matched |
| 06 browser | Backend persistence/error contracts and existing tests | Isolated profile; form/reload; accessible error; 503 retry; screenshots at both sizes; console/network |
| 07 research | Frozen official version/date/URL facts | Live search and retrieval; source actually supports caveat; real quota/error behavior |
| 08 vision | Exact image answer JSON | Actual image in model request; tools-disabled image turn; repaired button bounds/clickability |
| 09 endurance | Ten externally recorded CSV/test checkpoints and final state | Ten separately released turns; complete structured file/shell/test tool results |
| 10 context | Maintenance behavior plus distributed constraint summary | Measured active token count; memory/swap/cache/stream evidence; actual compaction and retained requirements |
| 11 outage | Preserved fixture only; no automatic routing claim | Owned runtime stopped; bounded local failure; complete inference-destination evidence; restart recovery |
| 12 project | Import/edit/filter/export/atomicity contracts and original-data preservation | Plan/Build stages, browser upload/reload/edit/filter/export, injected recovery, fresh review, real compaction/handoff and duration |

Tasks with outstanding operator checks remain PARTIAL even if all code checks pass. Complete `review.template.json` as `review.json` outside the candidate workspace only after inspecting real evidence. Set a check to PASS or FAIL, identify the independent `reviewer`, explain the observation and list files such as `evidence/browser-trace.txt`. Files must reside under that run's external `evidence/` directory. Copy actual artifacts there before attesting. The grader validates records/files, not their truth; never accept the candidate's own success declaration as this review.

For task 01, retain the raw chat response externally and copy its literal JSON object to `workspace/answer.json` as the evaluator. Do not correct keys, values or spelling. Invalid/non-JSON responses fail; do not grant the Plan agent edit permissions to create the answer. Confirm from the trace that the candidate made no writes. The automatic hash check allows only the operator-created answer file.

For browser tasks, launch the candidate's server in its workspace, with a disposable DB and an unused loopback port. Use an isolated browser profile. At 390×844 and 1280×800: submit a valid new row, reload, verify database/API state; attempt invalid minutes; ensure visible accessible error; inspect button bounding boxes and screenshots; inspect console and network. Create `<db filename without .db>.fail-next` externally, submit once, observe actual 503 and retained form values, retry and verify exactly one new persisted row. A handled 503 network error is expected. Unhandled JavaScript exceptions are not. Record uploads using only a disposable CSV. For task 12 verify an import containing an invalid/duplicate row makes no partial writes, and exported CSV faithfully round-trips IDs, Unicode, commas, minutes and dates.

For task 08, attach `vision.png` to a tools-disabled model turn. The operator saves the actual returned JSON as `vision-answer.json`, then starts the repair phase. The image is a deterministic synthetic UI, not a real screenshot from this computer. Do not reveal `references/` or use OCR/DOM to answer the image questions.

Task 07 uses a historical fixed cutoff (`2026-09-19T00:00:00Z`) so comparisons have stable truth. Official release metadata was retrieved independently and is stored in `references/`. Live retrieval still needs evidence; archived pages alone cannot qualify working web search. Dates later than the cutoff are irrelevant. A 429 simulator can test retry/reporting policy but cannot certify Exa's live quotas.

## Endurance, context and project staging

For task 09, release this prompt for each N from 1 through 10: “Append row eNN,endurance,N,2026-09-03 to data/endurance.csv, then run existing tests, inspect the Git diff, and report the CSV count/minutes.” Use zero-padded IDs e01…e10. After each turn, the evaluator runs:

```sh
python3 -B bench.py checkpoint endurance-trial1 1
```

Advance the number each time. Checkpoints cannot be overwritten or recorded out of order. They independently inspect the intermediate CSV and rerun existing tests. Tool-message correctness still requires the actual client transcript.

For task 10, create the frozen-generator corpus before giving the task to the model:

```sh
python3 -B bench.py context context-32k-trial1 --records 1500
```

Adjust record count only in a fresh run and record exact model-tokenizer/server counts. Bytes and record count do not establish token counts. Use the same corpus per paired comparison. A 64K combined window with 16K output reservation leaves roughly 48K for active input; ≥64K cumulative history through native compaction is a different test. Do not treat synthetic load alone as task-12 sustained qualification. Classify a failed/incomplete stream as a failed trial even if a later retry succeeds.

For task 12, preserve one workspace across explicit Plan → Build → actual verification → fresh Audit → Handoff/compaction → resumed work stages. Keep stage transcripts externally. A new task-12 trial starts from a fresh seed, never an earlier solution. Record useful work duration; do not add idle time to manufacture a long-running success.

For a read-only Reviewer probe, supply exact project-relative source paths, the relevant task criterion and at most three requested findings per pass. Reviewer cannot run Git or test commands; provide any diff or check results in the handoff rather than asking it to execute them. Record unreviewed scope and independently verify each finding. Broad prompts on the local model timed out, while a three-file focused prompt returned findings quickly but still included unsupported claims; see [the retained A/B evidence](history/2026-09-25-context-candidate/task12v-review-diff-ab.json) and [the rejected tool-limit trial](history/2026-09-25-context-candidate/task12w-review-bound.json).

## Validation and comparison policy

```sh
python3 -B bench.py selftest
```

This executes automatic graders on known working copies and confirms deliberately broken seeds are rejected. It only starts short-lived, loopback stdlib fixture servers; every one is terminated in a finally block. It does not run a model, operate Chrome, stop any inference service or establish manual capabilities. Detailed results are in `.validation/fixture-validation.json` and are explicitly labeled **fixture validation, not model baseline**.

Freeze first, validate protocol integration, then establish 32K/8K MTP-off baseline before prompt/skill optimization. Keep raw per-trial commands, outputs, effective config/model hashes, elapsed time, interventions and unavailable telemetry marked unavailable. For MTP OFF/depth 3 use the same accepted context, sampler, tasks, model and runtime, three paired trials of 02/03/06/09 and one sustained run per arm. Alternate arm order; separate cold/warm cache conditions; hold foreground load and power conditions stable. Three repetitions expose obvious regressions but do not establish statistical superiority. Preserve every failure and time limit. Fresh same-model review is supplementary evidence.
