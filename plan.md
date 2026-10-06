# KRYN v1.0.0 status

KRYN v1.0.0 is [published](https://github.com/PranavMishra28/kryn/releases/tag/v1.0.0), anonymously installable, and active on the qualification Mac. It is a local-first **human-supervised coding workspace** for native Apple Silicon macOS 26/27 with at least 48 GiB unified memory. The released wheel came from commit `4038a77ebea5f421b08b055c9aa768dcf12a890b` and has SHA-256 `3356318cc8335c65e14d88d8c0acd64bbf49ed288f34ab342c83f09caaeb54b1`. [Install and use it](README.md) · [Qualification contract](docs/v1-qualification.md) · [Final bounded receipt](evals/history/2026-10-02-v1-final-qualification.json).

OpenCode 2.0.10 owns sessions, agents, models, permissions, tools and the terminal/GUI interface. KRYN owns installation, local routing, guards, continuity and evidence. oMLX 0.6.4 serves Qwen3.5-9B-6bit with a **configured 96K limit** and one heavyweight local generation at a time. Other OpenCode providers remain explicit user choices. No paid provider is configured by KRYN.

## Unreleased research candidate

[PR #242](https://github.com/PranavMishra28/kryn/pull/242) remains draft. Its latest
strict coding loads stopped on memory pressure, and a three-hour conservative
reserve admission ended without starting the runtime. Candidate daily-use,
continuity, active endurance and final-artifact lifecycle gates remain unmet.
The installed release's passes below do not transfer to this candidate. See the
[current campaign decision](research/LOCAL_CAMPAIGN_2026-10-04.md) for the measured
supervised ceiling, preserved failures and exact settlement receipts.

## Released supervised gates

The [final receipt](evals/history/2026-10-02-v1-final-qualification.json) is source and wheel bound. Raw private traces are retained outside Git. These outcomes include independent checks; model completion prose is never acceptance evidence.

| Gate | Final outcome |
|---|---|
| Coding/edit/test | **Pass, supervised.** Final-wheel Task02 passed the frozen grader 2/2 and independent date/range checks; Agent read before editing, ran imported-code checks and inspected the current diff in a saved-session follow-up. |
| Browser/search | **Pass, supervised.** Native tools exercised a disposable local app success and error, searched and opened official documentation, and connected in `doctor --deep`. Independent normal/narrow browser checks passed. |
| Unsupported claims | **Pass, refusal mechanism.** A deliberate exit-7 check remained failed through three controller rounds; the model's completion text did not become an accepted result. |
| Compaction/restart | **Pass, supervised.** Three real compactions and fresh processes continued one saved project; failed checks, unverified status and changed-file staleness remained visible for operator review. |
| Resource safety | **Pass within the safe physical screen.** Warning pressure occurred in one continuation with zero swap growth and no abort; offline exact-wheel regressions cover critical pressure, missing telemetry, swap and listener refusal. A live critical-pressure event was deliberately not forced. |
| Sustained use | **Pass after disclosed operator correction.** 48.123 active minutes across Plan, Agent, browser, verification, compaction and review; final Task12 backend 2/2, real-server tests 5/5, browser 11/11 and extra holdouts passed. Two Agent UI attempts failed before the operator corrected the disposable project. |
| Installed controls | **Pass on an extant project.** Terminal and authenticated GUI startup, model and Default/Fast pickers, Ask/Plan/Agent, permission roundtrips and explicit launch lock were checked. An old session referring to a deleted temporary directory showed empty GUI models; selecting an extant project restored them. |
| Final artifact and supply chain | **Pass on the owner installation.** Same-hash package smoke, clean wheel manifest, anonymous HTTPS download, public installer activation, saved-session reopen, update/rollback, uninstall/reactivation and healthy deep diagnostics passed. The separate macOS-account install was waived. Final 212 Python/85 Node tests and dependency/secret reviews passed with disclosed historical hash-shaped scanner findings. |

This release does **not** qualify unattended application engineering, accurate independent local Reviewer judgment, frontier parity, or useful reasoning across every configured context token. Frozen autonomous/UI results remain separate [research evidence](docs/evaluation.md); Task12 needed human correction. The 35B model was unsuitable for the normally occupied 48-GiB daily-use envelope, a 14B/49K profile did not clear sustained UI work, and shorter context did not demonstrate enough accepted-work benefit to replace this guarded 96K configuration. [Model decision](evals/history/2026-10-01-daily-envelope-model-decision.json) · [Historical evidence](docs/history.md).

Future improvements should follow a reproduced failure, a bounded fix, and independent acceptance rather than automatically rewriting the harness after each session. See [architecture](docs/architecture.md), [usage](docs/usage.md), [security](SECURITY.md), and [release procedure](docs/releasing.md).
