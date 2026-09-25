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
| `kryn doctor` | Inspect an installed copy on a supported Mac. `kryn doctor --deep` also hashes model and browser files. |

`make check` is offline and safe for CI. Live evaluations require an installed KRYN and an independently reviewed run; follow [evals/README.md](evals/README.md) and keep private transcripts out of Git. Do not refresh `evals/frozen.sha256.json` to make a candidate pass. Historical failures belong in `evals/history/`.

For a change, identify the owning layer from [AGENTS.md](AGENTS.md), reproduce the behavior, add a targeted regression where it checks a real contract, run relevant checks, then inspect the actual diff. Update the user docs and [plan.md](plan.md) when the behavior or its qualification status changes. A release additionally needs package smoke, a clean external installation/update/rollback check, live product qualification, and review of [SECURITY.md](SECURITY.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Do not publish capability claims beyond evidence.
