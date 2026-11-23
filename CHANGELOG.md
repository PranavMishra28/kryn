# Changelog

## Unreleased

Security (reported privately by @kennysarnoski-jarvis):

- Package launchers and the installer start KRYN with `python -I` instead of `-E`, so a `kryn.py` or stdlib-named file in the directory you launch from can no longer run before KRYN.
- The plugin's own Git reads (status, changed files, review diffs) run under a Seatbelt profile with no network, no writes, and exec limited to the one git binary it resolves at startup (not the `/usr/bin/git` or `xcrun` shims). A clean filter planted in `.git/config` by an Agent shell step can no longer run outside the shell write boundary.
- The direct process signal guard now sees `kill`, `pkill` and `killall` after shell keywords (`then`, `do`, `else`, `!`), variable assignments, wrappers (`env`, `timeout`, `nohup`, `exec`, `time`, `nice`, `builtin`) and `xargs` options that take an argument.

Fixes from the same review (#243), by @kennysarnoski-jarvis:

- Pass uv a constraints path without spaces during model download (#244).
- Publish improvement records atomically and skip partial ones (#245).
- Return no snapshot for an unreadable project file (#246).

## v1.0.0 — supervised local coding workspace

- Keeps OpenCode as the native session, agent, permission, model and tool engine, with a local Qwen3.5-9B-6bit default through oMLX, configured guarded 96K context, terminal and authenticated loopback GUI, browser/search integrations and bounded child delegation.
- Provides Ask, Plan and Agent primary modes, truthful Default/Fast local effort, editable native approvals and explicit locked launch overrides.
- Retains task criteria, observed check exits and changed-file evidence through native compaction and restart; stale evidence is not promoted to a pass.
- Ships transactional installation, verified updates, rollback and retained-session recovery. The product scope is supervised coding; autonomous UI acceptance and local Reviewer accuracy remain research limitations.

The [supervised qualification contract](docs/v1-qualification.md) defines the release scope; the [status ledger](plan.md) records measured evidence and limitations.

## v0.2.0 — public preview

- Keeps OpenCode as the native session and agent harness, with Ask, Plan, Agent, foreground subagents, local Qwen, optional provider choice, browser/search tools, and terminal/GUI handoff.
- Adds guarded 96K local context, bounded continuity evidence for changed and non-ignored new files, saved request anchors, check lineage, and a concise machine-owned `/report` view that never treats execution success as task acceptance.
- Provides verified release notices, manual update and rollback, a bounded failure backlog, and a paused opt-in improvement worker limited to disposable JSON CLI trials.
- Tightens Browse's native permission rules and checks package/runtime version agreement before building a wheel.

This preview is for supervised coding. The latest independent long coding/UI task failed full browser acceptance, fresh review and truthful handoff. Useful 96K quality, successful sustained work and autonomous application-building improvement are unqualified. See [current evidence](plan.md) before relying on it for unattended work.

## Earlier prereleases

The 0.1.x prereleases and tags were retired on 1 October 2026 after their assets, release metadata, refs and abandoned worktrees were archived privately. The v0.2.0 release/tag was retired on 2 October after public v1 installation and after its assets and metadata were privately archived and hash-checked. Historical failures and fixes remain indexed in [the evidence history](docs/history.md).
