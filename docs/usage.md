# Using KRYN

[Install and quick start](../README.md) · [Current qualification and release gates](../plan.md)

These controls describe current source. The published v0.1.10 prerelease predates later changes; see the current status for that distinction.

## Start coding

If KRYN is already installed, open **Terminal**, replace the path below with your project's folder, and run:

```sh
cd "/absolute/path/to/your/project" && kryn
```

For a new project, this example creates a folder and opens it:

```sh
mkdir -p "$HOME/Developer/my-app"
cd "$HOME/Developer/my-app" && kryn
```

KRYN shows a small `◇ K R Y N` startup display while it checks the installation, connects the local model, and opens OpenCode. It then prints a readiness line and opens the full-screen terminal interface. A tool count of less than the total means one or more integrations did not connect; run `kryn doctor` for details. The line does not mean the model weights are loaded or a task has passed. Type your request and press **Enter**. New sessions start in **Agent** mode. For example:

```text
Inspect this project, explain how to run it, and implement a small todo app with tests. Run the tests and report the results.
```

Review permission prompts before approving commands. The first response after the model has unloaded takes longer because the weights must load again. Launch from your project folder, rather than your home directory or the KRYN source checkout.

### Modes and everyday controls

Press **Ctrl+X**, release it, then press **A** to choose an agent. Use the arrow keys and **Enter** to select it. **Ctrl+P** opens the command palette.

| Mode | Use it for |
|---|---|
| **Ask** | Inspect and answer using read and search tools, without edits or commands. |
| **Plan** | Inspect code and produce an actionable plan; only native OpenCode plan files may be written. |
| **Agent** | Edit code, run approved commands and use browser tools to verify rendered results; thinking on by default. |

Agent roles and reasoning effort are separate. **Ask/Plan/Agent** are the visible primary choices; **Ctrl+T** cycles effort, and **`/effort`** opens the variant picker. The local Qwen default uses bounded thinking; choose Fast when you want it. Browser and review work remain available through child agents and `/review` or `/audit`, without adding picker modes. Old saved Build/Audit sessions retain their native IDs; choose Agent for new coding work.

| Choice in OpenCode | Actual model behavior | Use |
|---|---|---|
| **Default** | Thinking on, capped at 3,072 thinking tokens | Normal coding, debugging and review. |
| **Fast** | Thinking off | Simple edits, quick questions and browser interaction. |

For local Qwen there are only **two choices**. OpenCode supplies `Default` for the base model; KRYN makes that entry mean bounded thinking and adds only `Fast`. Medium/High/XHigh were artificial Qwen budget presets, not distinct model capabilities or measured quality levels, so they have been removed. Other providers expose their own native variants, if any.

Qwen exposes `enable_thinking`; oMLX additionally supports a thinking-token cap. Thinking and the answer share the 8,192-token output limit. The cap keeps reasoning from consuming the whole response; it is not a guarantee of intelligence or runtime. “Show reasoning” in `/settings` changes visibility only, not whether the model thinks. Saved conversations remain available; removed effort selections fall back to Default in the native picker. Check the selection before continuing an older session.

### Models and providers

Qwen remains the installed local default. Inside KRYN, use **`/models`** to select another model for the current session. OpenCode may list public free models without a login; use **`/connect`** for providers that require an account or key. KRYN keeps its managed Qwen endpoint and resource guard exact while allowing those native choices. [OpenCode's provider guide](https://opencode.ai/v2/docs/providers) describes each provider's connection steps; availability, limits and reasoning variants depend on that provider. KRYN does not supply credentials or a free quota. External providers can receive your prompts and project data and may charge you; local Qwen remains available without one. One installed interactive free-model turn passed, while `opencode run` was rejected by that provider's free-tier rule; do not assume free models support automation. Custom project provider definitions are not yet admitted by KRYN's managed configuration overlay.

Edits normally proceed without a separate approval; shell and browser actions can ask. Agent can use the connected browser directly or delegate Browse; browser actions retain the normal Ask/Auto permission setting, and unsafe browser code remains denied. For a trusted project, explicitly opt into native automatic approvals for one launch:

```sh
cd "/absolute/path/to/your/project" && kryn --auto
# Resume with the same opt-in:
kryn --continue --auto
```

`--auto` accepts **all native permission requests that are not explicitly denied**, including browser, network and external-file requests. It is broader than “accept edits.” Explicit denials and the ordinary shell write boundary remain; native file tools and browser/MCP are outside that shell boundary. A launch without a permission option uses your saved native setting, initially prompts. See [Security](../SECURITY.md).

To change approvals **while KRYN is running**, open **`/settings` → Permissions** and use **←/→** or **Enter** to switch between `prompt` and `auto accept`. Ordinary `kryn` honors and saves this native setting. `kryn --auto` (also `--permissions auto`) pins autoaccept for that launch; `kryn --permissions ask` pins prompts. Those explicit launch overrides show `(locked)` and take precedence until the next launch. Reasoning visibility, appearance and other display settings remain available through `/settings` in every mode.

Run **`kryn controls`** in your shell for a quick reference without starting the model or logging in.

The terminal prompt footer shows **Permissions: Ask/Auto**. Click it or use `/permissions` to open native settings and change it. `(locked)` appears only with an explicit `--auto` or `--permissions ask/auto` launch override. The indicator reads the native setting, including JSONC comments, and does not implement a second approval system. In the browser GUI, **Cmd+Shift+P** opens the native command palette; search for **Auto-accept permissions** to find its toggle.

Type these commands **inside KRYN**, then press Enter:

| Command | Purpose |
|---|---|
| `/agents` | Switch between Ask, Plan and Agent without starting a different conversation. |
| `/effort` | Switch Default (thinking) / Fast (no thinking), independently of the agent role. |
| `/models` | Choose a model for this session through OpenCode's native picker. |
| `/connect` | Connect a provider that requires an account or key through OpenCode. |
| `/settings` | Display controls, reasoning visibility and permissions (see launch modes above). |
| `/permissions` | Open native settings from the terminal permission indicator. |
| `/web` | Show the local graphical interface address and temporary login credentials. |
| `/status` | Inspect native tool and service status. |
| `/update` | Check published KRYN releases; review the exact version/commit and choose Update instructions or Later. |
| `/share` | Open OpenCode's local session export. V2 cannot create a public share link; inspect the export before sending it. |
| `/deliver your task` | Request a small runnable milestone with explicit acceptance checks. |
| `/review` or `/audit` | Run a bounded read-only Reviewer child; your current mode stays selected. |
| `/research your topic` | Research a topic with search and source links. |
| `/handoff` | Request a summary of completed work, checks and next steps. |
| `/sessions` | Choose a saved session to resume. Relaunch from the same project first. |
| `/exit` | Close the terminal interface and return to your shell. |

After exiting, run `kryn stop` in Terminal if you also want to stop the idle model server. Otherwise, model weights unload after five idle minutes. One local generation runs at a time.

### Switch between terminal and GUI

Both interfaces use the **same OpenCode server, selected model, tools and saved sessions**. No separate desktop application or paid service is required for local Qwen.

1. From your project folder, run `kryn --web` (or `kryn --gui`). Add `--continue` to resume. The browser opens alongside the terminal.
2. In the terminal, enter **`/web`**. Click the masked password to reveal it. In the browser’s sign-in dialog, use username **`opencode`** and that temporary password. Do not save it; it changes each launch.
3. Select the same project and saved session in the GUI. Use **Cmd+Tab** to switch between browser and terminal. The GUI provides the conversation, effort picker, context usage, files and review controls; the terminal retains its native command palette and mode picker.
4. Keep the terminal running. Finish or interrupt a turn before submitting from the other interface. Unsent drafts are separate. `/exit` shuts down the owned server, disconnects the GUI and cancels remaining owned work; saved sessions remain available to `kryn --continue`.

To open the GUI after an ordinary launch, use `/web` and copy its **plain local address** into your browser. Use an address such as `http://127.0.0.1:PORT/`, without credentials or query parameters. The pinned upstream client’s credential-bearing link can cause a `BrowserAttachments` error; its token-only link can leave assets waiting for authentication. KRYN’s `--web` opens the clean address and uses the browser’s normal sign-in dialog. If a credential-bearing link was already opened, navigate to the plain address, reload the page, and reopen the session.

Final browser checks verified Default/Fast switching and one native automatic approval, but the complete permission-toggle roundtrip remains unqualified because reopening the command palette timed out in the test. The terminal controls were exercised separately.

The GUI has its own permission preferences. A terminal running with `--auto` can still approve requests for the same session while you use the GUI. Use a normal prompted launch when you want explicit approvals in both interfaces. Select the project KRYN was launched in; to work on another project, exit and relaunch there so the shell write boundary follows it. Treat the pairing password, link and QR code as private.

In the GUI, hover over the prompt area to reveal the **Default** effort button beside the model, then choose Default or Fast. It is also reachable with Tab and Enter; the pinned upstream interface hides it when neither hovered nor focused.

## Maintenance and troubleshooting

The packaged terminal checks public KRYN releases at startup and while idle, at most once every six hours. A newly verified release gets one toast per version and wheel hash across restarts. `/update` opens **Update instructions / Later**, showing the exact version, source commit and a short release-note excerpt. Later dismisses the offer; use `/update` whenever you want to review it again. No dialog opens automatically, and active sessions (including children) defer the check or notice. Repeated manual checks share in-flight work and a 30-second cooldown.

Discovery reads the 20 most recent published GitHub releases, including prereleases, and considers only an exact numerically newer KRYN tag. It downloads checksums and the wheel into temporary storage, reuses the verified updater's HTTPS/hash checks, validates the clean manifest and payload, then discards the download. Same-version private candidates, older tags and main commits are not updates. Network, rate-limit or integrity failures stay quiet until you explicitly check; `unavailable` does not mean up to date. These checks send no project content or credentials. Artifact integrity is not independent signing, host compatibility or application-quality qualification.

Update instructions give `kryn update vX.Y.Z` for Terminal after you finish work and exit KRYN. There is no one-click activation or mid-turn replacement. The existing transactional updater and `kryn rollback` retain recovery and native saved sessions; OpenCode is only changed through a reviewed KRYN package's pinned setup. Source-only launches without the installed package report update checking unavailable.

Run these commands in **Terminal**, outside the KRYN interface:

| Command | Purpose |
|---|---|
| `kryn controls` | Offline reference for modes, effort, approvals and GUI switching. |
| `kryn --web` | Open the graphical companion alongside the guarded terminal. |
| `kryn --continue` | Open the latest saved session in this project. |
| `kryn --session SESSION_ID` | Open a specific saved session belonging to this project. |
| `kryn status` | Inspect host memory pressure, runtime, owner session and background improvement state. |
| `kryn doctor` | Check configuration, dependencies, runtime health and tool connections. A stopped server is reported as unavailable; launching KRYN starts it. |
| `kryn doctor --deep` | Also verify installed model and browser dependency files; slower, without inference. |
| `kryn update --check` | Read-only JSON check for a newer checksum-verified published KRYN release. Network or integrity failures report `unavailable`. |
| `kryn update vX.Y.Z` | Install an exact newer published KRYN tag through the verified updater, after exiting the client. |
| `kryn rollback` | Restore the previous retained installation after an update. |
| `kryn uninstall` | Deactivate owned command launchers; keep models, sessions, caches, settings and packages. |
| `kryn improve status` | Inspect experimental background improvement. |
| `kryn improve failures` | Inspect failure-triggered incidents awaiting regression checks. |
| `kryn report` | Read-only diagnostics of this project's latest session and its children. Add `--session SESSION_ID` for a specific session. |
| `kryn improve pause` | Pause background improvement. |
| `kryn stop` | Stop the verified, idle KRYN model server. Finish active work first. |

Updates and removal refuse changed or unowned files. `kryn uninstall` stops only the verified idle runtime and removes KRYN's four owned launcher aliases; it does not erase data, runtime settings, the oMLX app, or GitHub credentials. Rerun the verified tagged installer from **First installation** to reactivate or repair a missing owned launcher or guidance file. Repeating deactivation through the retained package is a no-op. There is no automatic disk purge.

Package updates with unchanged client code preserve distinct backups for each prior launcher, including when the package interpreter changes. Interrupted activation and rollback retain recovery journals. Rerun the current verified release installer to recover, especially if a rollback already restored an older launcher whose package predates this recovery fix. Do not delete transaction journals or edit activation files during recovery; unrelated changes are preserved by refusing the operation.

Direct client deployment refuses to pair new client files with a different configured OpenCode plugin path. The verified package installer from **First installation** can update an unchanged older owned config transactionally. If that installer reports a customized config, review and restore the last owned config before retrying; it will not overwrite your changes.

If memory protection stops a session, KRYN cancels its work, retains the native session and completed file writes, and stops its verified idle model server to release memory. Check `kryn status`; once `memory.pressure` is `normal`, run `kryn --continue` from the same project. The server starts automatically. Memory pressure can recur if the desktop workload leaves insufficient room for the model. If search or browser services are unavailable, local coding can still launch; inspect their connection status with `kryn doctor`.

Application state, sessions, caches and installed packages live under `~/Library/Application Support/LocalAI`; the oMLX application lives under `~/Applications/oMLX.app`, with settings in `~/.omlx`. Keep private session data out of bug reports and commits.

`kryn report` separates uncached input, cache reads/writes, reported output and reasoning, with compaction usage reported separately. These are cumulative provider-reported counts, not unique conversation length. A zero reasoning count can mean the provider omitted the breakdown, leaving reasoning included in output. Missing usage remains unmeasured; a cache hit does not prove a correct answer. Its check counts cover simple test/build commands, direct Python test scripts, and Node syntax/browser-check scripts; compound shell commands do not count as verified checks. The report includes no prompts, source, command text or tool output. Unrecognized tool and status names are grouped as `unknown`, since malformed model output can put private arguments into those fields.

The report shows both the latest native outcome and counts of earlier execution outcomes from the saved session. A later successful read-only turn does not erase an interrupted coding turn. Those counts describe execution history, not application acceptance or the cause of an interruption.

## Configuration and release scope

The pinned stack is **OpenCode 2.0.10**, **oMLX 0.6.4**, **Qwen3.5-9B-6bit**, **Playwright MCP 0.0.82** and keyless Exa search. The public profile uses a **49,152-token context**, **8,192-token output limit**, **16 GiB model memory ceiling** and one active generation. The owner's installed same-version **64K** profile is a private guarded experiment, not the published default or a qualified quality improvement. Exact public model hashes and tool settings are in [the accepted profile](../setup/accepted-profile.json) and [the client template](../setup/opencode.template.json).

Automatic compaction reserves room for output: the 49,152-token window leaves roughly 40,960 tokens for active context before native estimation triggers a summary. It retains up to 4,096 tokens of recent user context alongside a structured checkpoint. The complete session history and written files remain on disk; summaries are not lossless, so the agent is instructed to reconcile them with files and check results. Compaction uses a separate 2,048-token fast summary budget.

npm uses KRYN’s managed writable cache, so ordinary dependency installation does not require modifying `~/.npm` or running `sudo`. Agent, including saved legacy Build sessions, can delegate rendered UI checks to one foreground Browse child. KRYN attaches up to 6,000 characters of the current user request to that handoff so functional acceptance criteria are not lost in a visual-only summary. This text stays in memory outside the native conversation and survives compaction during the running client; it does not recover older criteria after a restart. Agent is also instructed to finish a runnable slice and validate required services. These instructions improve the workflow but are not an enforced correctness gate.

Persistent development servers should use the native shell tool's `background:true` option in a separate call, with no trailing `&`. KRYN rejects a plain trailing background operator and gives the model that repair instruction, keeping ordinary checks in foreground calls. This guard does not parse complex shell syntax or contain deliberately detached processes.

Run tests as standalone commands. KRYN refuses simple test commands followed by `|| true`, `|| echo`, `| head`, or `| tail`, because those forms can hide the test's exit status. This is a narrow guard, not a shell parser.

Agent and saved Build also require a current native `read` before using native `edit` on an existing project file up to 1 MiB. This catches stale edits after a checkpoint or external file change. It does not cover shell writes, native `write`, symlinks or larger files.

KRYN warns after three consecutive foreground shell calls return the same command result, then denies another identical call through native permissions. Two denied retries interrupt that stuck session. Changed evidence, a different action or a new user prompt resets detection. This catches the observed repeated-request loop; it is not general loop detection, and does not cover every background or parser-unrecognized command.

Each file write is limited to 12,000 UTF-8 bytes; larger components should use smaller files or edits. If a top-level Agent or saved legacy Build response still hits the output limit, KRYN asks OpenCode to continue from saved state, at most twice per user prompt. Incomplete tool-call text is never executed as code. Continued work retains normal permission checks.

The default Qwen inference runs locally without a paid inference API. Optional providers use their own pricing and data policies. Search queries and browser traffic use external services with their own availability and quotas; electricity, storage and hardware still have costs. See [Security](../SECURITY.md) for data and permission boundaries.

## Improvement from actual failures

No scheduled review is required. The local plugin records an incident when a native execution fails, work is interrupted, a recognized check fails, a tool fails, or a review exhausts its tool budget. Check-specific incidents recognize simple test/build commands, including Python startup flags; compound shell expressions remain shell events, but cannot count as passed checks. Successful exits alone create no incident. These private records contain counts and native session references, not prompts, code, screenshots or tool output. The separate observed-check ledger retains a runner, exit code and fixed failure class across restart, without storing command arguments or raw output; those classes are hints, not proof of the cause or task acceptance. Retention is bounded to 30 days and 500 incidents. `kryn improve failures` lists them; `kryn report` reads the authoritative native transcript metadata, including child sessions and failures that happen before after-tool hooks.

A bounded private ledger preserves observed test/build/lint/typecheck outcomes and native result references across compaction and restart. Failed or unfinished checks remain unresolved until the same command in the same directory produces a completed result. After a failed check is rerun, one prior failure receipt remains visible alongside the latest result; neither result proves application acceptance. Old successful exits are historical observations; they do not prove current correctness or require rerunning just to clear a counter. The ledger records up to 64 simple check identities and marks missing history or provenance as partial. It cannot infer every requirement, prove browser flows from tool-call counts, or turn an assistant’s “done” into verified acceptance.

After a native edit or write of a regular JavaScript file (`.js`, `.mjs` or `.cjs`) under 1 MiB, KRYN runs the installed Node binary with `--check` and shows a bounded parser error in that tool result. The parser child clears inherited `NODE_OPTIONS` so a preload cannot execute during this check. It does not cover shell-based writes, TypeScript, runtime errors or browser behavior; run the application checks before claiming completion.

New sessions also retain the first and latest admitted user-request excerpts in a separate private continuity file (up to 12 requests and 30 KB). After native compaction, those excerpts are supplied as source-labeled context across restart, alongside a bounded current Git status and changed-file hashes. A fingerprint taken when compaction finishes marks the old checkpoint stale when those observed Git/file bytes change. The snapshot covers tracked changes in the launched project and can be unavailable or incomplete; it does not turn an assistant-written decision into a user decision or a passed check. Long individual requests and middle turns can be omitted with an explicit marker; the full native session history remains saved. Existing sessions created before this change have no retroactive request excerpts. This is a bounded continuity aid, not proof that the model correctly uses every requirement.

The engineering loop is **failure → reproducible regression → candidate change → independent checks → adoption or rejection**. Keep the failing case and validate actual production behavior. Passing a build, copying implementation into a test, or trusting a model-written report is insufficient. The current failure audit and regressions are in [the follow-up evaluation](../evals/history/2026-09-21/failure-driven.md).

Reviewer runs now end their tool phase after 48 attempts or two compactions, then must return findings and explicitly unreviewed scope. If the model still emits unavailable tool calls for two more steps, KRYN interrupts that Reviewer and records an incomplete review. This limit applies to Reviewer, not Build; large reviews should use focused follow-ups. It bounds the observed repeated-reading loop without increasing the memory or context limits.

Incident capture is automatic; implementing and accepting a new harness fix still requires evidence and engineering review. The older local instruction-optimization experiment remains restricted to disposable JSON tasks. Fresh installations and the validated installation start paused; `kryn improve resume` explicitly opts into that experiment. Failure incident capture does not require it. It has not established an improvement in application-building quality. KRYN does not automatically rewrite its runtime, permissions, test answers or model weights after an error, and frontier parity has not been demonstrated.
