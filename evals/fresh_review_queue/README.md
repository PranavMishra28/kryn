# Independent review-queue acceptance

This fresh task is separate from the frozen Task01–12 suite. It reuses that suite's working TaskboardLite fixture as a seed and leaves its manifest, Task12 oracle and all historical runs unchanged. The verifier and review template stay outside the candidate workspace. Do not disclose this directory or the grader to the candidate; give it only the path to the prepared workspace and its `TASK.md`.

From `evals/fresh_review_queue`:

```sh
python3 -B suite.py verify
python3 -B suite.py selftest
python3 -B suite.py prepare trial-1
# Run the installed KRYN agent in the workspace path printed by prepare.
python3 -B suite.py grade trial-1
```

`prepare` refuses an existing run ID. `grade` writes a new timestamped directory under `runs/ID/evidence/` with server logs, API results and the independent browser report/screenshots; it never edits the candidate workspace. Browser checks need the installed Playwright module and Chrome already used by `tools/browser_check.mjs`. A missing browser dependency is an evaluation error, not a model failure. The server is held by the grader process through every browser action and terminated in `finally`.

Prepared workspaces live in a separate OS temporary directory; `runs/ID/run.json` records the path for grading. This keeps the oracle tree out of the workspace path. The candidate still runs as the same OS user, so filesystem permissions alone do not prevent a deliberate search for the evaluator; keep the workspace instructions and run trace under review.

Pre-candidate oracle validation found that Playwright's exact label matcher rejected a valid select nested inside its `Review status` label because option text joined the accessible name. It also exposed asynchronous render checks that needed to wait for the row and an expected browser console message for the injected 503. The browser checker now accepts the nested label, waits for the actual row state and excludes only that expected 503 message from unexpected console errors. These corrected the checker only; no task criterion was relaxed. The failed positive-probe receipts stay in the ignored validation run.

The API/source/browser checks are automatic. The separate `runs/ID/review.template.json` lists operator criteria for actual Plan/Build separation, fresh read-only review, truthful final report, two native compactions, process restart and active duration. Copy it to `review.json` only after independent inspection; each PASS or FAIL needs evidence files under the run's external `evidence/` directory. Without that review, a mechanically passing run is PARTIAL. For a shorter task trial, mark long-workflow criteria NOT_TESTED and retain the partial result. Follow `LONG_RUN.md` for the full continuity/endurance trial. Do not edit the verifier after seeing a candidate outcome; version a corrected oracle and rerun matched trials if a defect is found.
