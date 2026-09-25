# KRYN

A local coding workspace for Apple Silicon. KRYN connects OpenCode's terminal interface to Qwen running through oMLX, with coding, planning, review, browser and search tools in one installation.

[Release v0.1.10](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10) · [Security](SECURITY.md) · [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Contributing or working on KRYN with a coding agent? Start with the [repository map](AGENTS.md), [development commands](CONTRIBUTING.md) and [current evidence ledger](plan.md).

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

KRYN starts its local model server automatically, prints a short readiness line after runtime, tool, and memory preflight checks, then opens the OpenCode terminal interface. A tool count of less than the total means one or more integrations did not connect; run `kryn doctor` for details. The line does not mean the model weights are loaded or a task has passed. Type your request and press **Enter**. New sessions start in **Agent** mode. For example:

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
| **Agent** | Edit code, run approved commands and verify results; thinking on by default. |

Agent roles and reasoning effort are separate. **Ask/Plan/Agent** are the new everyday choices; **Ctrl+T** cycles effort, and **`/effort`** opens the variant picker. Ask starts in Fast; Plan and Agent start with bounded thinking. Browse, Reviewer and Audit remain selectable for existing read-only sessions and specialist use. OpenCode remembers choices per agent/model, so check the displayed selection when resuming. Old Build sessions remain available; the native picker may select equivalent Agent when resuming them. A future migration must resolve this before the picker can contain only three primary roles.

| Choice in OpenCode | Actual model behavior | Use |
|---|---|---|
| **Default** | Thinking on, capped at 3,072 thinking tokens | Normal coding, debugging and review. |
| **Fast** | Thinking off | Simple edits, quick questions and browser interaction. |

There are only **two choices**. OpenCode always supplies a `Default` entry for the base model; KRYN makes that entry mean bounded thinking and adds only `Fast`. Medium/High/XHigh were our artificial budget presets, not distinct Qwen capabilities or measured quality levels, so they have been removed. There is no duplicate `Think` entry.

Qwen exposes `enable_thinking`; oMLX additionally supports a thinking-token cap. Thinking and the answer share the 8,192-token output limit. The cap keeps reasoning from consuming the whole response; it is not a guarantee of intelligence or runtime. “Show reasoning” in `/settings` changes visibility only, not whether the model thinks. Saved conversations remain available; removed effort selections fall back to Default in the native picker. Check the selection before continuing an older session.

Edits normally proceed without a separate approval; shell and browser actions can ask. For a trusted project, explicitly opt into native automatic approvals for one launch:

```sh
cd "/absolute/path/to/your/project" && kryn --auto
# Resume with the same opt-in:
kryn --continue --auto
```

`--auto` accepts **all native permission requests that are not explicitly denied**, including browser, network and external-file requests. It is broader than “accept edits.” Explicit denials and the ordinary shell write boundary remain; native file tools and browser/MCP are outside that shell boundary. A launch without a permission option returns to prompts. See [Security](SECURITY.md).

To change approvals **while KRYN is running**, start with:

```sh
kryn --permissions interactive
```

Then open **`/settings` → Permissions** and use **←/→** or **Enter** to switch between `prompt` and `auto accept`. This mode honors OpenCode’s saved setting, including any saved `autoaccept`, and saves later changes. Ordinary `kryn` pins prompts; `kryn --auto` (also `--permissions auto`) pins autoaccept for that launch. Those pinned modes intentionally override the settings menu. Reasoning visibility, appearance and other display settings remain available through `/settings` in every mode.

Run **`kryn controls`** in your shell for a quick reference without starting the model or logging in.

The terminal prompt footer now shows **Permissions: Ask/Auto**. `(locked)` means the launch option pins that mode. Click it or use `/permissions` to open native settings. To change the mode there, launch with `kryn --permissions interactive`. The indicator reads the native setting, including JSONC comments, and does not implement a second approval system. In the browser GUI, **Cmd+Shift+P** opens the native command palette; search for **Auto-accept permissions** to find its toggle.

Type these commands **inside KRYN**, then press Enter:

| Command | Purpose |
|---|---|
| `/agents` | Switch between Ask, Plan and Agent without starting a different conversation. |
| `/effort` | Switch Default (thinking) / Fast (no thinking), independently of the agent role. |
| `/settings` | Display controls, reasoning visibility and permissions (see launch modes above). |
| `/permissions` | Open native settings from the terminal permission indicator. |
| `/web` | Show the local graphical interface address and temporary login credentials. |
| `/status` | Inspect native tool and service status. |
| `/deliver your task` | Request a small runnable milestone with explicit acceptance checks. |
| `/audit` | Run a bounded read-only review through the Audit role. Switch to Agent before fixing findings. |
| `/research your topic` | Research a topic with search and source links. |
| `/handoff` | Request a summary of completed work, checks and next steps. |
| `/sessions` | Choose a saved session to resume. Relaunch from the same project first. |
| `/exit` | Close the terminal interface and return to your shell. |

After exiting, run `kryn stop` in Terminal if you also want to stop the idle model server. Otherwise, model weights unload after five idle minutes. One local generation runs at a time.

### Switch between terminal and GUI

Both interfaces use the **same local OpenCode server, model, tools and saved sessions**. No separate desktop application or paid service is required.

1. From your project folder, run `kryn --web` (or `kryn --gui`). Add `--continue` to resume, and `--permissions interactive` if you want the terminal permission toggle. The browser opens alongside the terminal.
2. In the terminal, enter **`/web`**. Click the masked password to reveal it. In the browser’s sign-in dialog, use username **`opencode`** and that temporary password. Do not save it; it changes each launch.
3. Select the same project and saved session in the GUI. Use **Cmd+Tab** to switch between browser and terminal. The GUI provides the conversation, effort picker, context usage, files and review controls; the terminal retains its native command palette and mode picker.
4. Keep the terminal running. Finish or interrupt a turn before submitting from the other interface. Unsent drafts are separate. `/exit` shuts down the owned server, disconnects the GUI and cancels remaining owned work; saved sessions remain available to `kryn --continue`.

To open the GUI after an ordinary launch, use `/web` and copy its **plain local address** into your browser. Use an address such as `http://127.0.0.1:PORT/`, without credentials or query parameters. The pinned upstream client’s credential-bearing link can cause a `BrowserAttachments` error; its token-only link can leave assets waiting for authentication. KRYN’s `--web` opens the clean address and uses the browser’s normal sign-in dialog. If a credential-bearing link was already opened, navigate to the plain address, reload the page, and reopen the session.

Final browser checks verified Default/Fast switching and one native automatic approval, but the complete permission-toggle roundtrip remains unqualified because reopening the command palette timed out in the test. The terminal controls were exercised separately.

The GUI has its own permission preferences. A terminal running with `--auto` can still approve requests for the same session while you use the GUI. Use a normal prompted launch when you want explicit approvals in both interfaces. Select the project KRYN was launched in; to work on another project, exit and relaunch there so the shell write boundary follows it. Treat the pairing password, link and QR code as private.

In the GUI, hover over the prompt area to reveal the **Default** effort button beside the model, then choose Default or Fast. It is also reachable with Tab and Enter; the pinned upstream interface hides it when neither hovered nor focused.

## First installation

The v0.1.10 installer fetches public release assets over HTTPS without a GitHub account. This is a prerelease while installed-product qualification continues.

Requirements:

- Native Apple Silicon, macOS 26 or 27, and at least **48 GiB unified memory**. Release validation used an M4 Max with 48 GiB.
- `python3` and `curl` available in Terminal; Google Chrome installed at `/Applications/Google Chrome.app`.
- Internet access for installation. Allow space for roughly **8.22 GB of model files**, dependencies, and the installer's **40 GiB free-space reserve**.

1. Download the tagged release, verify its checksums, and run the installer:

   ```sh
   (
     set -eu
     kryn_stage="$(mktemp -d "${TMPDIR:-/tmp}/kryn-install.XXXXXX")"
     cd "$kryn_stage"
     kryn_tag=v0.1.10
     kryn_base="https://github.com/PranavMishra28/kryn/releases/download/$kryn_tag"
     for kryn_asset in install-kryn.py "kryn-${kryn_tag#v}-py3-none-any.whl" SHA256SUMS; do
       curl --fail --location --proto '=https' --proto-redir '=https' \
         --output "$kryn_asset" "$kryn_base/$kryn_asset"
     done
     shasum -a 256 -c SHA256SUMS
     python3 install-kryn.py --tag "$kryn_tag"
   )
   ```

   The installer provisions the pinned model and runtime dependencies, including managed Python, Node, OpenCode, oMLX and browser tooling. Complete any normal macOS app approval when prompted.

   If the pinned oMLX publisher asset returns 404/410, the installer reports the failure and tries the unaffiliated SourceForge mirror. Both locations must match the same pinned SHA256; a checksum failure stops installation. The mirror's complete 805,799,490-byte image was verified against that pin during release validation.

2. Make the launcher available in this Terminal, check the installed version, then follow **Start coding** above:

   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   kryn --version
   ```

   Expected version: `KRYN 0.1.10`. If a new Terminal cannot find `kryn`, use `~/.local/bin/kryn` directly or add the export line to `~/.zshrc` once.

## Maintenance and troubleshooting

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
| `kryn update v0.1.10` | Install the exact public release tag through the verified updater. Substitute a newer published tag when available. |
| `kryn rollback` | Restore the previous retained installation after an update. |
| `kryn uninstall` | Deactivate owned command launchers; keep models, sessions, caches, settings and packages. |
| `kryn improve status` | Inspect experimental background improvement. |
| `kryn improve failures` | Inspect failure-triggered incidents awaiting regression checks. |
| `kryn report` | Read-only diagnostics of this project's latest session and its children. Add `--session SESSION_ID` for a specific session. |
| `kryn improve pause` | Pause background improvement. |
| `kryn stop` | Stop the verified, idle KRYN model server. Finish active work first. |

Updates and removal refuse changed or unowned files. `kryn uninstall` stops only the verified idle runtime and removes KRYN's four owned launcher aliases; it does not erase data, runtime settings, the oMLX app, or GitHub credentials. Rerun the verified tagged installer from **First installation** to reactivate or repair a missing owned launcher or guidance file. Repeating deactivation through the retained package is a no-op. There is no automatic disk purge.

Package updates with unchanged client code preserve distinct backups for each prior launcher, including when the package interpreter changes. Interrupted activation and rollback retain recovery journals. Rerun the current verified release installer to recover, especially if a rollback already restored an older launcher whose package predates this recovery fix. Do not delete transaction journals or edit activation files during recovery; unrelated changes are preserved by refusing the operation.

If memory protection stops a session, KRYN cancels its work, retains the native session and completed file writes, and stops its verified idle model server to release memory. Check `kryn status`; once `memory.pressure` is `normal`, run `kryn --continue` from the same project. The server starts automatically. Memory pressure can recur if the desktop workload leaves insufficient room for the model. If search or browser services are unavailable, local coding can still launch; inspect their connection status with `kryn doctor`.

Application state, sessions, caches and installed packages live under `~/Library/Application Support/LocalAI`; the oMLX application lives under `~/Applications/oMLX.app`, with settings in `~/.omlx`. Keep private session data out of bug reports and commits.

`kryn report` separates uncached input, cache reads/writes, reported output and reasoning, with compaction usage reported separately. These are cumulative provider-reported counts, not unique conversation length. A zero reasoning count can mean the provider omitted the breakdown, leaving reasoning included in output. Missing usage remains unmeasured; a cache hit does not prove a correct answer. The report includes no prompts, source, command text or tool output. Unrecognized tool and status names are grouped as `unknown`, since malformed model output can put private arguments into those fields.

## Configuration and release scope

The pinned stack is **OpenCode 2.0.10**, **oMLX 0.6.4**, **Qwen3.5-9B-6bit**, **Playwright MCP 0.0.82** and keyless Exa search. The model profile uses a **49,152-token context**, **8,192-token output limit**, **16 GiB model memory ceiling** and one active generation. Exact model hashes and tool settings are in [the accepted profile](setup/accepted-profile.json) and [the client template](setup/opencode.template.json).

Automatic compaction reserves room for output: the 49,152-token window leaves roughly 40,960 tokens for active context before native estimation triggers a summary. It retains up to 4,096 tokens of recent user context alongside a structured checkpoint. The complete session history and written files remain on disk; summaries are not lossless, so the agent is instructed to reconcile them with files and check results. Compaction uses a separate 2,048-token fast summary budget.

npm uses KRYN’s managed writable cache, so ordinary dependency installation does not require modifying `~/.npm` or running `sudo`. Agent, including saved legacy Build sessions, can delegate rendered UI checks to one foreground Browse child. KRYN attaches up to 6,000 characters of the current user request to that handoff so functional acceptance criteria are not lost in a visual-only summary. This text stays in memory outside the native conversation and survives compaction during the running client; it does not recover older criteria after a restart. Agent is also instructed to finish a runnable slice and validate required services. These instructions improve the workflow but are not an enforced correctness gate.

Persistent development servers should use the native shell tool's `background:true` option in a separate call, with no trailing `&`. KRYN rejects a plain trailing background operator and gives the model that repair instruction, keeping ordinary checks in foreground calls. This guard does not parse complex shell syntax or contain deliberately detached processes.

KRYN warns after three consecutive foreground shell calls return the same command result, then denies another identical call through native permissions. Two denied retries interrupt that stuck session. Changed evidence, a different action or a new user prompt resets detection. This catches the observed repeated-request loop; it is not general loop detection, and does not cover every background or parser-unrecognized command.

Each file write is limited to 12,000 UTF-8 bytes; larger components should use smaller files or edits. If a top-level Agent or saved legacy Build response still hits the output limit, KRYN asks OpenCode to continue from saved state, at most twice per user prompt. Incomplete tool-call text is never executed as code. Continued work retains normal permission checks.

Inference runs locally without a paid inference API. Search queries and browser traffic use external services with their own availability and quotas; electricity, storage and hardware still have costs. See [Security](SECURITY.md) for data and permission boundaries.

Version 0.1.10 is the first public-installation prerelease. It adds Agent and Ask primary modes, a guarded startup header, and compatibility with the tested Chrome 154 line. The [earlier v0.1.9 qualification](evals/history/2026-09-22-production/qualification.json) records 172 setup tests, 21 helper tests, 39 JavaScript tests and 18 grader self-test cases passing. Native probes verified durable failed-check tracking across restart and blocking an unchanged fourth shell call after a warning. The 8,192-token cache probe returned correct original and changed facts on cold and reused paths. These are mechanism checks, not proof of general engineering quality or v0.1.10 installed acceptance.

The same-model comparison completed both bug-fix repeats in each of minimal OpenCode, incumbent KRYN and candidate KRYN. No arm completed the feature task within its 240-second budget. The external Requests trial timed out and still failed both bug cases. Qwen3.8-27B oQ4 and Qwen3-Coder-30B-A3B Q4 failed the memory-pressure qualification and were rolled back; the 9B profile remains selected. The comparison establishes no statistical harness uplift or frontier parity.

The final staged application trial completed Plan, backend, UI and edge-case stages, then passed native compaction with history preserved. Saved-session continuation timed out; after AC power disconnected, the fresh review stopped at the experiment's 20% battery reserve, 24.2 minutes into the workload. Backend checks passed, but the independent browser check failed because a successful save did not clear the form. Application acceptance failed. An earlier 6.5-minute battery-limited attempt is retained separately; neither qualifies the planned 45–60 minute sustained run.

The earlier [v0.1.7 qualification](evals/history/2026-09-22/qualification.json) records 80.2 minutes of operator-staged engineering work. The primary session, including its child, reached a maximum recorded assistant prompt of 40,812 tokens and eight completed native compactions. Host pressure remained normal with no incremental swap growth during that workload. However, seven of eleven stages timed out: backend checks passed, while the generated UI still lacked accessible status feedback and the fresh review did not finish. The overall application acceptance failed; larger context does not establish frontier-level task quality.

After that run, a Browse permission fix enabled native reads of saved, truncated web results. Separate tests verified the read scope and actual model calls; autonomous research still chose an outdated release, while a follow-up supplied with canonical source URLs returned the requested facts. Build-mode compaction, provider outage, restart and saved-session recall passed a separate lifecycle test. These narrowly scoped results do not turn the failed application or research trials into passes. Review generated changes and run your project's checks. Background improvement remains experimental, with no established learning benefit. Earlier results remain in [evaluation history](evals/history/2026-09-21).

## Improvement from actual failures

No scheduled review is required. The local plugin records an incident when a native execution fails, work is interrupted, a recognized check fails, a tool fails, or a review exhausts its tool budget. Check-specific incidents recognize simple test/build commands, including Python startup flags; compound shell expressions remain shell events, but cannot count as passed checks. Successful exits alone create no incident. These private records contain counts and native session references, not prompts, code, screenshots or tool output. Retention is bounded to 30 days and 500 incidents. `kryn improve failures` lists them; `kryn report` reads the authoritative native transcript metadata, including child sessions and failures that happen before after-tool hooks.

A bounded private ledger preserves observed test/build/lint/typecheck outcomes and native result references across compaction and restart. Failed or unfinished checks remain unresolved until the same command in the same directory produces a completed result. Old successful exits are historical observations; they do not prove current correctness or require rerunning just to clear a counter. The ledger records up to 64 simple check identities and marks missing history or provenance as partial. It cannot infer every requirement, prove browser flows from tool-call counts, or turn an assistant’s “done” into verified acceptance.

The engineering loop is **failure → reproducible regression → candidate change → independent checks → adoption or rejection**. Keep the failing case and validate actual production behavior. Passing a build, copying implementation into a test, or trusting a model-written report is insufficient. The current failure audit and regressions are in [the follow-up evaluation](evals/history/2026-09-21/failure-driven.md).

Reviewer runs now end their tool phase after 48 attempts or two compactions, then must return findings and explicitly unreviewed scope. If the model still emits unavailable tool calls for two more steps, KRYN interrupts that Reviewer and records an incomplete review. This limit applies to Reviewer, not Build; large reviews should use focused follow-ups. It bounds the observed repeated-reading loop without increasing the memory or context limits.

Incident capture is automatic; implementing and accepting a new harness fix still requires evidence and engineering review. The older local instruction-optimization experiment remains restricted to disposable JSON tasks. Fresh installations and the validated installation start paused; `kryn improve resume` explicitly opts into that experiment. Failure incident capture does not require it. It has not established an improvement in application-building quality. KRYN does not automatically rewrite its runtime, permissions, test answers or model weights after an error, and frontier parity has not been demonstrated.

## External Requests regression

[The external evaluator](evals/external_requests.py) reproduces one [SWE-bench Verified instance](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/tree/c104f840cc67f8b6eec6f759ebc8b2693d585d4a), `psf__requests-6028`, against [Requests commit 0192aac](https://github.com/psf/requests/tree/0192aac24123735b3eaf9b08df46429bb770c283). This optional evaluator is separate from the installed KRYN package. It calls no model and changes no inference settings. Prerequisites are Python 3.10+, Git and `uv`; initialization creates an isolated Python 3.10.16 environment with the exact dependency versions embedded in the adapter.

Run these from the repository root, choosing a new state directory outside the checkout:

```sh
kryn_eval_state="$HOME/kryn-evals/requests-6028"
python3 -B evals/external_requests.py --state "$kryn_eval_state" init
python3 -B evals/external_requests.py --state "$kryn_eval_state" selftest
python3 -B evals/external_requests.py --state "$kryn_eval_state" prepare trial-1
```

The last command prints a fresh Git workspace containing only upstream source and the exact issue as `TASK.md`. In a separate terminal, enter that workspace, put the evaluator's `venv/bin` first on `PATH`, start your normal harness, and submit `TASK.md` verbatim. Give the candidate access only to its workspace. Keep the state directory's `oracle/`, `grades/`, reference solutions and other attempts out of its context. These ordinary filesystem directories are **not a security sandbox**.

After the attempt ends, grade it from the repository root:

```sh
python3 -B evals/external_requests.py --state "$kryn_eval_state" grade "$kryn_eval_state/workspaces/trial-1"
```

Initialization verifies the source archive, exact problem/test/reference hashes and all 102 frozen fixture inputs. The Hugging Face rows API is not revision-addressable, so changed fields fail their fixed hashes instead of silently updating the task. `init --source-archive PATH --instance-json PATH` can use cached official inputs under the same checks. Existing nonempty state and workspace labels are never overwritten. A failed initialization remains for inspection; use a fresh state directory to retry.

Grading copies the candidate outside its workspace, checks preserved original tests/configuration, rejects added `conftest.py` files and symlinks, applies the unchanged official test patch, and runs the focused and adjacent test module. Case and skip identities must match the frozen reference. Only the grader workspace and owned virtual-environment prefixes in test names become `<workspace>` and `<venv>`; the latter removes one absolute `pytest.__file__` parameter path. No assertion or skip changes. `selftest` requires the original bug to fail both official regression cases, the reference to pass 5 focused cases and 203 adjacent cases with 11 upstream skips, and modified tests to be rejected before execution. Reports and raw pytest output remain under the chosen state directory. Exit 0 means PASS, 1 means a graded failure, and 2 means a setup/error condition.

This is a native macOS adaptation of one public 2022 task, not the official SWE-bench Docker score, a representative benchmark, or demonstrably uncontaminated training data. A passing fixture grade does not establish model completion, tool correctness or resource safety; retain those separate native-run checks.

## Repository layout

- `src/kryn/`: packaged launcher, verified installation, updates and rollback.
- `setup/`: pinned configuration, model profile and installation checks.
- `tools/`: resource supervision, native client adapter, workflow hooks and evaluation utilities. OpenCode owns the agent loop and both interfaces.
- `evals/`: task definitions and redacted validation history. Private transcripts, credentials and generated test workspaces stay outside Git.

## License and distribution

KRYN's source is licensed under [MIT](LICENSE). Upstream applications, model weights, dependencies and online services retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md).

Releases contain a KRYN wheel, `install-kryn.py` and `SHA256SUMS`. The curated [package builder](build_package.py) excludes model weights, credentials and private task traces. Install from a tagged release using the steps above. Release checksums and payload hashes provide integrity checks through authenticated GitHub distribution; KRYN artifacts are not independently signed or notarized.
