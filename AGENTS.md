# KRYN repository map

KRYN packages an OpenCode client, an oMLX runtime, and a pinned local model for Apple Silicon. Keep the existing harness and native session engine; change the layer that owns the behavior.

- User operation, installation, current limits: [README.md](README.md). Trust boundaries and release integrity: [SECURITY.md](SECURITY.md).
- Package entry and transactional activation: `src/kryn/cli.py`, `src/kryn/installer.py`, `install-kryn.py`. Pinned dependency and model setup: `setup/setup.py`, `setup/accepted-profile.json`.
- Runtime supervision and client launch: `tools/localai.py`, `tools/native_client.py`. OpenCode agents, tools and permissions: `setup/opencode.template.json`, `tools/kryn_plugin.mjs`, `tools/kryn_tui.tsx`.
- Incident capture and optional learning: `tools/improvement.py`, `tools/learning.py`. Evaluation contracts and historical outcomes: [evals/README.md](evals/README.md), `evals/tasks.json`, `evals/history/`.
- Development and verification commands: [CONTRIBUTING.md](CONTRIBUTING.md). Current requirement/evidence ledger: [plan.md](plan.md).

Use the smallest relevant check while editing; run `make check` and `make package-smoke` before proposing a release. Preserve failed evaluation results and private user state. Do not treat a unit test, generated report, or successful tool call as proof of application acceptance. Scope extra instructions to the affected directory; `setup/AGENTS.md` is installed into the user's OpenCode environment and is a product input, not this repository's development policy.
