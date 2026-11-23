# Test KRYN yourself

Start with the supervised session below. It exercises real coding, tests, browser
behavior and saved-session recovery using **KRYN's OpenCode**, without Codex.
Budget 45–60 minutes of useful work; setup and waiting do not count. The model
may finish sooner, need correction or stop under its resource guard. An hour on
the clock is not a pass by itself.

## What is already done, and what remains

The published v1.0.0 has [artifact-bound supervised qualification](../plan.md).
PR #242 has additional product fixes, offline checks and source review. Its
later research attempts do **not** establish the same live qualification:

| Your remaining check for the PR candidate | What to observe |
| --- | --- |
| Coding and browser work | Correct behavior, preserved existing tests/data, a reviewed diff and actual browser success/error paths. |
| Continuity | Two real compactions and a process restart; original goal, failed checks and an external file change survive. |
| Active endurance | 45–60 minutes of useful coding/checking/review under the unchanged guard; record interruptions and corrections. |
| Final artifact | Test the exact built wheel, then owner installation, saved-session reopen, rollback and reactivation. |

The experimental 4B profile fit short runs but missed tool and instruction
protocols. It has not replaced the installed 9B profile. Public test recovery is
useful evidence; it does not erase a failed attempt or establish frontier parity.

## 1. Know which copy you are testing

Run in Terminal:

```sh
kryn --version
kryn status
kryn doctor
```

For deeper dependency/model integrity checking, use `kryn doctor --deep`.
A stopped runtime can be reported unavailable; opening KRYN starts its owned
runtime. Keep the Mac open and adequately powered. Do not disable the guard,
change models mid-comparison or close other people's applications to force a pass.

**A source checkout does not update the installed launcher.** Running `kryn` now
tests the installed artifact. Record the source commit separately with
`git rev-parse HEAD`. To qualify the PR's artifact, first follow the private-wheel
installation stage in [the release procedure](releasing.md). Use the normal owner
account and `HOME`; changing `HOME` does not isolate the oMLX application.

## 2. Prepare a fresh project

In the KRYN source checkout, with Python 3.13+ available:

```sh
KRYN_REPO="$PWD"
KRYN_RUN="owner-task12-$(date -u +%Y%m%dT%H%M%SZ)"
export KRYN_REPO KRYN_RUN
printf 'Repository: %s\nRun: %s\n' "$KRYN_REPO" "$KRYN_RUN"
python3 -B evals/bench.py prepare 12 "$KRYN_RUN" &&
  cd "$KRYN_REPO/evals/runs/$KRYN_RUN/workspace" &&
  kryn
```

Keep that Terminal open so its variables remain available after you exit KRYN.
Preparation refuses an existing run ID. The project is disposable and its
evidence stays ignored by Git. Give OpenCode only this workspace, never the
parent evaluator, reference solution or previous answers. Same-account fixtures
are development diagnostics, not a protected holdout against a hostile agent.

Inside KRYN, confirm `/models` selects local Qwen. Use Agent for implementation
and Plan for planning. Paste:

```text
Read TASK.md and follow its stages. First record a short plan and completion
criteria, then build and verify the requested app. Work through routine steps
without asking me to choose implementation details. Use only this disposable
workspace; do not inspect parent directories, evaluator code or old runs.
Preserve existing tests and seed data. Run real checks and inspect the diff.
Use a Browse child to exercise the running UI at normal and narrow widths.
Ask me when the controlled HTTP failure is ready to inject, and before the
handoff/compaction stage. Record failures and corrections honestly. Do not
change the model, permissions, resource limits or installation. Stop when
the requested work is complete or blocked; do not wait to fill a time target.
```

Approve only actions you intend. This starts an ordinary native session, not a
new autonomous evaluation loop. Local Reviewer findings need your confirmation.

Suggested pacing: 5–10 minutes planning, 20–25 building and checking, 10–15
browser/recovery work, then 10 minutes reviewing and resuming. Record actual
active time rather than treating this suggested schedule as a result.

## 3. Exercise the UI and inject a recoverable failure

The fixture README supplies its server command. If you run the server yourself,
use a **second Terminal** in the printed workspace:

```sh
python3 -B -m taskboard_lite.server \
  --db owner-test.db --seed data/entries.csv --port 0 --port-file owner-port.txt
```

Use the printed loopback URL. Port 0 chooses an unused port. Keep that Terminal
for ownership and stop this server with Ctrl+C when done. If OpenCode already
started a server, use that server and its exact disposable DB instead of starting
another. Never kill a process just because its port matches.

At 1280×800 and 390×844, inspect upload, edit, exact project filtering, export and
reload persistence. Try invalid input and duplicate imports: no partial writes
should remain. Inspect the console and take screenshots of what actually ran.

For the command above, create the one-shot failure marker from a third Terminal
in that same workspace, immediately before a new entry submission:

```sh
touch owner-test.fail-next
```

The next supported mutation should return HTTP 503. Check that the error is
visible, input survives, and retry saves **exactly one** row. The marker is derived
from the DB name; another server DB requires its corresponding `.fail-next` file.
Save screenshots and observations under the run's external `evidence/` directory.

Before finishing Task12, ask for a fresh read-only review, use the native
compaction action, exit and run `kryn --continue` from this same workspace. Ask
for one bounded follow-up change and rerun the checks. Retain that project's
handoff and resumed work; the separate failure probe below does not substitute
for Task12's own continuity requirement. Also ask Browse to search for and open
one official documentation page; inspect that the actual page supports the
answer. A configured search tool alone is not a successful search.

## 4. Check compaction, restart and stale information

Do this in a separate disposable recovery project so the intentional failure
does not change Task12's frozen tests. In a new Terminal:

```sh
KRYN_RECOVERY="$(mktemp -d /private/tmp/kryn-owner-recovery.XXXXXX)"
cd "$KRYN_RECOVERY"
git init -q
printf 'print("OWNER_INTENTIONAL_FAILURE")\nraise SystemExit(7)\n' > test_owner_failure.py
printf 'Destination: North depot\n' > OWNER_NOTE.md
kryn
```

Tell OpenCode:

```text
Goal: inspect recovery state. Read OWNER_NOTE.md and run
python3 -B test_owner_failure.py. This failure is intentional; do not repair
or edit anything. Report the current destination, failed check and exact
next action. Keep completion UNVERIFIED. We will compact and restart.
```

Use Ctrl+P and the native session-compaction action. Ask it to restate the
original goal and failed check, then perform a second actual compaction. Save
the session ID and `/report` output. Exit through `/exit`. Back in that Terminal:

```sh
printf 'Destination: South depot\n' > OWNER_NOTE.md
kryn --continue
```

Ask it to read current files and run the same check again. It should observe
South depot and exit 7, preserve the original goal and avoid claiming success.
Verify the same session resumed and a fresh process started. A fluent summary
alone is insufficient. If no compaction occurred, mark this check **NOT TESTED**.

For safe runtime recovery, exit the client, run `kryn stop`, then
`kryn --continue` in this project. This tests an orderly idle stop and restart;
it does **not** simulate a crash during inference. Do not force memory pressure,
kill arbitrary PIDs or corrupt installation files for a failure-injection test.
If the guard naturally stops work, retain the report and resume only when safe.

## 5. Grade and record the session

Back in the first Terminal, after `/exit`:

```sh
kryn report --brief > "../evidence/session-report.txt"
cd "$KRYN_REPO"
python3 -B evals/observe.py grade "$KRYN_RUN"
python3 -B evals/observe.py status "$KRYN_RUN" --compact
```

The observer saves a new source-bound receipt for each check. Read the result;
an error setting up the evaluator is different from a failed model task. Task12
remains **PARTIAL** until you fill its external `review.template.json` into
`review.json` after checking the required browser, recovery, review and duration
evidence. See [fixture instructions](../evals/README.md). Record your name as
reviewer; OpenCode must not attest its own independent acceptance.

Keep a small log under `evidence/owner-notes.md`:

```text
Artifact/version and source commit:
Model/context and local route:
Start/end; active minutes; waiting minutes:
Coding and browser checks; screenshots:
Compaction/session IDs and restart observation:
Expected injected failures and observed results:
Unexpected failures; guard stops; operator corrections:
Final outcome: PASS / FAIL / PARTIAL / NOT TESTED
```

For longer testing, repeat on fresh projects across several days with your normal
desktop workload, not an endless loop over one solved fixture. Keep cold/warm
starts, power changes and interventions separate. A successful hour is useful
evidence, not proof of reliability over days.

## 6. Ask OpenCode to fix a demonstrated problem

Save the original failed receipt first. In the affected project's session, paste:

```text
Here is the observed failure: [paste the exact check output]. Reproduce it
with the smallest relevant check. Fix the layer that owns the behavior, without
weakening tests, permissions, resource guards or acceptance rules. Preserve the
original failed evidence. Show the diff, run the relevant regression and state
what remains untested. Do not publish, install or change versions.
```

A repaired application can become a supervised success with the intervention
recorded. It does not rewrite the original autonomous failure. A KRYN product fix
belongs in the source checkout and PR, followed by focused checks, `make check`
and `make package-smoke`; changing the disposable app does not fix KRYN itself.

## 7. Larger external benchmarks

These are separate projects, not slash commands or guaranteed one-hour tests.
Start with one fresh task, one local generation at a time, and verify the grading
environment before spending a full run. Do not feed gold patches or verifier
material to the candidate. Preserve setup failures and incomplete attempts.

### Terminal-Bench through Harbor

[Harbor is Terminal-Bench's official harness](https://github.com/harbor-framework/docs/blob/main/examples/terminal-bench.mdx).
KRYN supplies a guarded adapter that runs its pinned OpenCode terminal profile.
Harbor's ordinary `opencode` adapter is a different integration. The shipped
research wrapper targets the installed 9B/22-GiB profile, not the private 4B
experiment; do not relabel one as the other.

Follow the [pinned Harbor preparation](../research/HARBOR_CALIBRATION.md) for the
task/image and isolated Python 3.12 environment. Once those exist and the owned
local runtime is idle, set the three actual paths below and run:

```sh
KRYN_REPO=/absolute/path/to/kryn
KRYN_HARBOR_PYTHON=/absolute/path/to/harbor-venv/bin/python
KRYN_HARBOR_TASK=/absolute/path/to/pinned-task
KRYN_TRIALS="$(mktemp -d /private/tmp/kryn-owner-harbor.XXXXXX)"
PYTHONPATH="$KRYN_REPO" "$KRYN_HARBOR_PYTHON" -B \
  "$KRYN_REPO/research/run_harbor_calibration.py" \
  "$KRYN_HARBOR_TASK" "$KRYN_TRIALS" "owner-$(date -u +%Y%m%dT%H%M%SZ)"
```

This runs one local candidate and official verifier, with a 900-second agent
limit; setup and container cleanup can take longer. It is not a hard whole-job
deadline. Use a new name for each attempt, inspect reward and guard receipts,
and never present a public sample as the full benchmark. The [subset report](../research/HARBOR_SUBSET.md)
explains the platform, tooling and local-network limitations.

### SWE-bench official grading

SWE-bench evaluates patches against real repository tests. Its evaluator does
**not** make OpenCode generate those patches. Each prediction must come from a
fresh issue/base checkout with its issue prompt, isolated tools and retained
trace. KRYN's [external protocol](../research/EXTERNAL.md) describes generation
and its [campaign result](../research/LOCAL_CAMPAIGN_2026-10-04.md) records the
failed and excluded attempts; there is no full-suite score or demonstrated uplift.

With Docker and a dedicated Python environment containing the evaluator pinned
in that protocol, grade an existing `predictions.jsonl` from its directory:

```sh
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path predictions.jsonl \
  --max_workers 1 --timeout 1800 \
  --run_id "owner-verified-$(date -u +%Y%m%dT%H%M%SZ)"
```

Each line needs `instance_id`, `model_name_or_path` and `model_patch`. This command
performs local grading only; it sends no task to a paid provider. Match the
dataset to your predictions. ARM image availability and Docker disk/memory can
block evaluation; record that as infrastructure failure. See the [official
evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/) for inputs
and result interpretation. Do not start a full suite on the occupied Mac merely
because a small local task passed.

## 8. Final installation and release decision

After you accept the source candidate, follow [the release runbook](releasing.md)
to build a clean wheel, record hashes, install those exact bytes on the owner
account, reopen a saved project, check terminal and GUI, roll back and reactivate.
Record any waived test as waived with a reason, never as passed. Offline package
smoke is not an owner installation test.

Use a disposable project to check Ask/Plan/Agent, Default/Fast, `/models`,
`/settings`, a permission denial, `kryn --web`, `/sessions` and `/report`. Record
the artifact hash with each result. Never publish the GUI's temporary password.
With the client closed and a known prior installation retained, the rollback
sequence is:

```sh
kryn rollback
kryn --version
kryn doctor --deep
# From the same disposable project:
kryn --continue
```

Then exit and reactivate the exact retained candidate using its installation
command from the release runbook; repeat startup and saved-session checks.
Test `kryn uninstall` only when you are ready to deactivate the launchers and
have the verified installer available to reactivate them. It should preserve
your sessions, models and settings. Do not delete those directories as cleanup.

There is one public v1.0.0. Its published bytes remain immutable. This PR does not
silently replace that wheel or move its tag. Your source experiments and private
candidate installs can still use version 1.0.0, with source/artifact hashes recorded
so they cannot be confused with the public release.
