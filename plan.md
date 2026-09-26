# KRYN execution ledger — 2026-09-25


The added Agent live-file-read instruction failed a three-turn early screen: turn 3 edited before reading. The instruction was reverted. The owner was restored to the previous private 64K source `7f99d6f` with package check, guarded protocol smoke and doctor passing. Full long-workflow qualification remains open.


| Requirement | Current implementation / evidence | Remaining acceptance gate | Status |
|---|---|---|---|
| Agent-ready repository | [PR #4](https://github.com/PranavMishra28/kryn/pull/4) merged at `8cb55bd`; `make check` and clean package smoke passed locally and in CI; independent diff review found no issue | Format/static commands, focused runbooks and fresh-agent navigation/use | In progress |
| Native experience | `tools/localai.py`, `tools/kryn_tui.tsx`, `setup/opencode.template.json`; v0.1.10 candidate installed, external-project TUI opened with Agent and 2/2 tools connected. [Candidate qualification](evals/history/2026-09-25-v010/qualification.json). Saved Build remains equivalent; Browse/Reviewer/Audit stay visible because hiding saved read-only roles would silently switch them to Agent on TUI continuation. Chrome 154 launched and handled a click through pinned Playwright; v0.1.10 doctor accepted it. | Safely migrate saved role selection, then reduce the picker to Ask/Plan/Agent; terminal/GUI continuation and denied writes; full permission-toggle roundtrip | In progress; GUI permission roundtrip unqualified |
| Public installation | [v0.1.10 prerelease](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10) from `e9c90ff` is published. Anonymous asset download and SHA256 passed; public install, rollback/update, uninstall/reactivation and repair of a missing owned launcher passed on the owner's existing installation, followed by guarded inference, deep doctor and external-project TUI launch. [Evidence](evals/history/2026-09-25-v010/qualification.json). | Prove non-owner clean install and offline recovery | In progress; existing-owner release path qualified narrowly |

A two-turn screen rejected the dynamic `pytest unavailable` hint: the resumed Agent retried pytest despite the recorded failure, then passed the original tests through direct Python execution. The hint was reverted. The owner was restored to private 64K source `7f99d6f`, with package check, guarded protocol smoke and doctor passing. Detailed evidence is retained in the PR branch.

