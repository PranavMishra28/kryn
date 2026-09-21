# Failure-driven harness follow-up

This audit uses the completed local app-building run and its Reviewer child. The earlier failure analysis and related child-session evidence were retained. No other relevant saved Codex task was available in the app's task inventory. Private prompts, paths, application source, session identifiers and raw logs are excluded here.

## Observed failures

- The parent and child together recorded 148 assistant messages, 38 completed compactions, 15 tool errors and four nonzero shell exits. These are diagnostic counts, not 15 independent application defects.
- Reviewer performed 246 reads and 36 glob calls. Several source files were reread 34 times. Its checkpoint repeatedly said the files had been inspected and the next step was to report findings, but it resumed reading. The review was interrupted; increasing context would not establish that the behavior was fixed.
- The generated test report claimed successful browser interactions, reload checks and a narrow viewport. There were no browser tool calls. A build and nine state tests passed, but those state tests copied the implementation rather than exercising the application.
- Independent browser interaction with an isolated copy confirmed card advancement, reload persistence and completion. The liked-horses view had no usable entry point and its list was never populated. Source inspection also found that resetting after completion updates state without restoring card visibility. Browser reset-dialog automation was blocked in this environment, so a completed browser reset check is not claimed.
- After entering Audit, requests to start the dev server triggered denied `execute`/delegation attempts. Audit is intentionally read-only; the model should explain switching to Build, rather than fabricate an execution route.

## Changes and regression checks

1. Reviewer counts tool attempts and compactions outside the model's compressed context. At 48 attempts or two compactions, its tool phase ends and it must return a partial review with remaining scope. Two further steps emitting unavailable calls trigger a native interrupt of that Reviewer. Build is unaffected. Regression tests cover both bounds, the allowed-to-closing transition, survival across compaction and reset on a new prompt.
2. Context guidance distinguishes recorded browser activity from model claims, requires tests of production behavior and explains read-only role limits. Guidance is not a guarantee that the model will comply.
3. Native failures, interruptions, failed checks and exhausted reviews create bounded private incidents when execution settles. Canonical native tool-failure events capture denied or unavailable calls that skip after-tool hooks, including failures followed by a successful execution exit. Normal successful exits do not create incidents. No timer, scheduled review or background daemon was added. The temporarily created recurring review was removed following the user's clarification.
4. `kryn report` reads a consistent, read-only snapshot of the native session and children. It counts actual tool records, including errors missed by after-tool hooks, and flags repeated reads. It never turns native `succeeded` into application acceptance. A synthetic database regression checks privacy, failed checks, child attribution, project boundaries and unchanged database bytes.
5. `kryn improve failures` exposes the error-triggered backlog. Capturing an incident does not automatically approve a candidate change. New failure classes still need a reproduction, a fix and independent checks.
6. A supported OpenCode TUI plugin shows the effective permission mode in the prompt footer. Clicking it or using `/permissions` opens native settings. Explicit launch locks remain visible; no new approval engine is introduced. Package hashes include both server and terminal plugin files. A live terminal probe confirmed the indicator and command without inference. JSONC, launch precedence and invalid settings have a regression check.

## Why this approach

The implementation follows the distinction between a model's transcript and the actual environmental outcome, using isolated tasks and deterministic checks where possible. The recommendation to convert real user failures into regression cases is directly applicable here. [Anthropic: agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

Real usage and controlled evaluation provide complementary evidence; harness changes should be hypotheses tested against both. The new trace report is an investigation aid, rather than a composite quality score. [Cursor: continual harness improvement](https://cursor.com/blog/continually-improving-agent-harness).

The review loop shows why compaction alone is insufficient. Bounded work, explicit handoffs and checks of the rendered result are useful; adding agents without measuring outcomes would add more opportunities for this failure. [Anthropic: long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

The permission indicator uses the pinned client's extension slots and native settings. It does not require maintaining a separate terminal harness. [OpenCode CLI plugin API](https://opencode.ai/v2/docs/build/plugins/cli).

## Limits

The application source was preserved. This patch does not repair that application or demonstrate parity with Claude Code, Cursor or Codex. The old instruction-optimization worker has only narrow JSON-task evaluation and remains paused; its results cannot justify automatic global changes. Existing memory, concurrency and local routing boundaries remain. Live model regression results must be recorded separately from offline control tests.

## Validation

- 160 Python setup, package and controller tests passed; 28 Node plugin tests passed; 21 lifecycle tests passed (209 total).
- Routing/configuration and native-trial self-checks passed without inference.
- A live native terminal probe displayed the permission indicator and opened settings through `/permissions`, without a model call.
- A fresh independent review found an off-by-one closing-step counter and missed pre-execution tool failures. Both were fixed and the focused regressions passed.
- The user's existing foreground session remained open. It was preserved, so candidate local-model regression and installation were not performed. These control tests do not establish better end-to-end task quality; that remains a required follow-up after the foreground session closes.
