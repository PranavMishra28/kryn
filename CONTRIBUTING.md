# Developing KRYN

KRYN currently supports native Apple Silicon macOS 26/27. Use Python 3.13+ and Node. The pinned `uv` version is 0.11.16. Work on a branch and keep the installed application separate from the source checkout.

From the repository root:

| Command | Contract |
|---|---|
| `make check` | Documentation links, Python and JavaScript regressions, native-trial self-check, frozen evaluation definition and grader self-tests. Same command runs in CI. No model starts. |
| `make package-smoke` | Build the curated wheel and install it into an isolated temporary environment outside the checkout; verify manifest and version. Requires `uv`. |
| `make package-smoke BUILD_FLAGS=--candidate` | Smoke a dirty working tree with the package's explicit candidate marker; never publish this build. |
| `make eval-prepare TASK=02 RUN=bug-trial-1` | Prepare a fresh disposable acceptance workspace; prints the workspace and prompt. |
| `make eval-grade RUN=bug-trial-1` | Grade that run. A pass still needs any operator evidence specified in [evals/README.md](evals/README.md). |
| `python3 -B evals/observe.py grade bug-trial-1` | Run the frozen grader and retain a uniquely named, source-bound copy of its result under the run's private evidence directory. |
| `python3 -B evals/observe.py browser bug-trial-1 --url http://127.0.0.1:PORT/ --db evals/runs/bug-trial-1/evidence/disposable.db` | Run the independent browser checker against an already running disposable server and record the exact result. Add Task 06 scopes `--stored-html`, `--visible-controls`, or `--quoted-import` when intended. |
| `python3 -B evals/observe.py status bug-trial-1 --compact` | Show bounded source-matched grade/browser outcomes by check scope and prior failure symptoms after edits or restart. Frozen grader tracebacks stay in raw reports under `evals/runs/`. |
| `kryn doctor` | Inspect an installed copy on a supported Mac. `kryn doctor --deep` also hashes model and browser files. |

`make check` is offline and safe for CI. Live evaluations require an installed KRYN and an independently reviewed run; follow [evals/README.md](evals/README.md) and keep private transcripts out of Git. Do not refresh `evals/frozen.sha256.json` to make a candidate pass. Historical failures belong in `evals/history/`.
The installed 9B/96K profile is frozen for supervised v1. For later matched model, context, provider or harness research, use the [evaluation protocol](docs/evaluation.md) and change one factor at a time. The [supervised v1 contract](docs/v1-qualification.md) owns product-release decisions.
The evaluation runner, browser checker and frozen fixtures live in this source repository; they are not installed with the user wheel.

Use [current gates](plan.md) for decisions and the [historical evidence index](docs/history.md) for primary receipts and immutable earlier narratives. The optional [External Requests runbook](docs/external-requests.md) is separate from the installed package.

`observe.py` records what its check process saw; it does not make a model-produced artifact autonomous or replace operator review. Its compact output uses opaque evidence IDs instead of private grader paths. A source match does not prove the server, database, or browser state is unchanged. Runs under the same macOS account are **not** an evaluator security boundary because candidate shell tools may read that account's files. Use an explicitly KRYN-owned isolated environment for independent holdout evidence; do not use an unrelated project's account. Until then, label same-account checks as diagnostics rather than protected holdout results.

When Chrome records an unhandled page JavaScript exception, the next browser check reports it before secondary UI symptoms. Inspect the private raw browser report or run a source syntax check for the exact error; arbitrary page exception text is not copied into the bounded status.

`tools/run_native_trial.py` freezes the complete managed product-plugin file set before a disposable native turn. A changed or missing module refuses the trial before inference; use a fresh run rather than reusing a frozen input directory after changing the installed package. Its probe-only `--thinking-budget` override must leave at least 2,048 output tokens and cannot turn thinking on for Fast; invalid combinations stop before a trial stage is created.

For a sole alternate local model, pass all four probe-only `--replacement-model-id`, `--replacement-context`, `--replacement-output` and `--replacement-guard-gib` flags with `--guard-resources`. The driver changes only its isolated OpenCode config, verifies the runtime's exact model/guard and advertised context before prompting, and records the effective values. It does not start or restore oMLX; the operator must own that lifecycle as described below.

Older model-screen procedures and raw outcomes remain in [historical evidence](docs/history.md). Do not change the owner's runtime settings or weaken the resource guard for a v1 qualification run.

For a change, identify the owning layer from [AGENTS.md](AGENTS.md), reproduce the behavior, add a targeted regression where it checks a real contract, run relevant checks, then inspect the actual diff. Update the user docs and [plan.md](plan.md) when the behavior or its qualification status changes. Follow the [release runbook](docs/releasing.md) for final-artifact checks, owner install/update/rollback, security review and publication. Do not publish capability claims beyond evidence.
