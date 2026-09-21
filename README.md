# KRYN

A private local coding workspace for Apple Silicon. KRYN connects OpenCode's terminal interface to Qwen running through oMLX, with coding, planning, review, browser and search tools in one installation.

[Release v0.1.6](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.6) · [Security](SECURITY.md) · [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

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

KRYN starts its local model server automatically and opens the OpenCode terminal interface. Wait for startup, then type your request and press **Enter**. New sessions start in **Build** mode. For example:

```text
Inspect this project, explain how to run it, and implement a small todo app with tests. Run the tests and report the results.
```

Review permission prompts before approving commands. The first response after the model has unloaded takes longer because the weights must load again. Launch from your project folder, rather than your home directory or the KRYN source checkout.

### Modes and everyday controls

Press **Ctrl+X**, release it, then press **A** to choose an agent. Use the arrow keys and **Enter** to select it. **Ctrl+P** opens the command palette.

| Mode | Use it for |
|---|---|
| **Build** | Editing code and running approved commands; thinking on by default. |
| **Plan** | Inspecting code and discussing a plan before implementation; fast mode. |
| **Browse** | Web search and interaction with an isolated Chrome session; fast mode. Build can delegate UI checks to Browse; you can also select it directly. |
| **Audit** | Read-only review, configured to request one fresh Reviewer. Switch back to Build explicitly before making fixes or running tests. |

Agent roles and reasoning effort are separate. **Build/Plan/Browse/Audit** choose the tools and task; **Ctrl+T** cycles effort, and **`/effort`** opens the variant picker. The native UI remembers choices per agent/model, so check the displayed selection when resuming.

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

The terminal prompt footer now shows **Permissions: Ask/Auto**. `(locked)` means the launch option pins that mode. Click it or use `/permissions` to open native settings. To change the mode there, launch with `kryn --permissions interactive`. The indicator reads the native setting, including JSONC comments, and does not implement a second approval system. The browser GUI continues to use its native Settings permission control.

Type these commands **inside KRYN**, then press Enter:

| Command | Purpose |
|---|---|
| `/agents` | Switch the agent role without starting a different conversation. |
| `/effort` | Switch Default (thinking) / Fast (no thinking), independently of the agent role. |
| `/settings` | Display controls, reasoning visibility and permissions (see launch modes above). |
| `/permissions` | Open native settings from the terminal permission indicator. |
| `/web` | Show the local graphical interface address and temporary login credentials. |
| `/status` | Inspect native tool and service status. |
| `/deliver your task` | Request a small runnable milestone with explicit acceptance checks. |
| `/audit` | Enter Audit mode and review current work. |
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

The GUI has its own permission preferences. A terminal running with `--auto` can still approve requests for the same session while you use the GUI. Use a normal prompted launch when you want explicit approvals in both interfaces. Select the project KRYN was launched in; to work on another project, exit and relaunch there so the shell write boundary follows it. Treat the pairing password, link and QR code as private.

## First installation

The current release is for the verified owner of this private repository. Repository access alone does not authorize another GitHub account to run it.

Requirements:

- Native Apple Silicon, macOS 26 or 27, and at least **48 GiB unified memory**. Release validation used an M4 Max with 48 GiB.
- `python3` and GitHub CLI (`gh`) available in Terminal; Google Chrome installed at `/Applications/Google Chrome.app`.
- Internet access for installation and GitHub login. Allow space for roughly **8.22 GB of model files**, dependencies, and the installer's **40 GiB free-space reserve**.

1. Sign in to the authorized GitHub account. Credentials must be stored in **macOS Keychain**; plaintext tokens and token environment overrides are refused.

   ```sh
   gh auth login --hostname github.com --web
   ```

2. Download the private release, verify its checksums, and run the installer:

   ```sh
   (
     set -eu
     kryn_stage="$(mktemp -d "${TMPDIR:-/tmp}/kryn-install.XXXXXX")"
     cd "$kryn_stage"
     gh release download v0.1.6 --repo PranavMishra28/kryn \
       --pattern install-kryn.py --pattern '*.whl' --pattern SHA256SUMS
     shasum -a 256 -c SHA256SUMS
     python3 install-kryn.py --tag v0.1.6
   )
   ```

   The installer provisions the pinned model and runtime dependencies, including managed Python, Node, OpenCode, oMLX and browser tooling. Complete any normal macOS app approval when prompted.

3. Make the launcher available in this Terminal, check the installed version, then follow **Start coding** above:

   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   kryn --version
   ```

   Expected version: `KRYN 0.1.6`. If a new Terminal cannot find `kryn`, use `~/.local/bin/kryn` directly or add the export line to `~/.zshrc` once.

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
| `kryn login` | Renew the owner session online. A verified session permits seven days of offline startup. |
| `kryn update v0.1.6` | Install the exact release tag through the verified updater. Substitute a newer published tag when available. |
| `kryn rollback` | Restore the previous retained installation after an update. |
| `kryn improve status` | Inspect experimental background improvement. |
| `kryn improve failures` | Inspect failure-triggered incidents awaiting regression checks. |
| `kryn report` | Read-only diagnostics of this project's latest session and its children. Add `--session SESSION_ID` for a specific session. |
| `kryn improve pause` | Pause background improvement. |
| `kryn stop` | Stop the verified, idle KRYN model server. Finish active work first. |

If memory protection stops a session, KRYN cancels its work, retains the native session and completed file writes, and stops its verified idle model server to release memory. Check `kryn status`; once `memory.pressure` is `normal`, run `kryn --continue` from the same project. The server starts automatically. Memory pressure can recur if the desktop workload leaves insufficient room for the model. If search or browser services are unavailable, local coding can still launch; inspect their connection status with `kryn doctor`.

Application state, sessions, caches and installed packages live under `~/Library/Application Support/LocalAI`; the oMLX application lives under `~/Applications/oMLX.app`, with settings in `~/.omlx`. Keep private session data out of bug reports and commits.

## Configuration and release scope

The pinned stack is **OpenCode 2.0.10**, **oMLX 0.6.4**, **Qwen3.5-9B-6bit**, **Playwright MCP 0.0.82** and keyless Exa search. The model profile uses a **24,576-token context**, **8,192-token output limit**, **12 GiB model memory ceiling** and one active generation. Exact model hashes and tool settings are in [the accepted profile](setup/accepted-profile.json) and [the client template](setup/opencode.template.json).

Automatic compaction reserves room for output and retains up to 4,096 tokens of recent user context alongside a structured checkpoint. The complete session history and written files remain on disk; summaries are not lossless, so the agent is instructed to reconcile them with files and check results. Compaction uses a separate 2,048-token fast summary budget.

npm uses KRYN’s managed writable cache, so ordinary dependency installation does not require modifying `~/.npm` or running `sudo`. Build can delegate rendered UI checks to one foreground Browse child. KRYN attaches up to 6,000 characters of the current user request to that handoff so functional acceptance criteria are not lost in a visual-only summary. This text stays in memory outside the native conversation and survives compaction during the running client; it does not recover older criteria after a restart. Build is also instructed to finish a runnable slice and validate required services. These instructions improve the workflow but are not an enforced correctness gate.

Each file write is limited to 12,000 UTF-8 bytes; larger components should use smaller files or edits. If a top-level Build response still hits the output limit, KRYN asks OpenCode to continue from saved state, at most twice per user prompt. Incomplete tool-call text is never executed as code. Continued work retains normal permission checks.

Inference runs locally without a paid inference API. Search queries and browser traffic use external services with their own availability and quotas; electricity, storage and hardware still have costs. See [Security](SECURITY.md) for data and permission boundaries.

Version 0.1.6 is a prerelease for owner testing. Earlier task evaluations include failed tests, incomplete browser work and missed review steps; larger context and recovery do not establish frontier-level task quality. Review generated changes and run your project's checks. Background improvement is experimental; a measured learning benefit has not been established. Detailed results remain in [evaluation history](evals/history/2026-09-21) and the [run-quality audit](evals/history/2026-09-21/run-quality.md).

## Improvement from actual failures

No scheduled review is required. The local plugin records an incident when a native execution fails, work is interrupted, a check fails, a tool fails, or a review exhausts its tool budget. Successful exits alone create no incident. These private records contain counts and native session references, not prompts, code, screenshots or tool output. Retention is bounded to 30 days and 500 incidents. `kryn improve failures` lists them; `kryn report` reads the authoritative native transcript metadata, including child sessions and failures that happen before after-tool hooks.

The engineering loop is **failure → reproducible regression → candidate change → independent checks → adoption or rejection**. Keep the failing case and validate actual production behavior. Passing a build, copying implementation into a test, or trusting a model-written report is insufficient. The current failure audit and regressions are in [the follow-up evaluation](evals/history/2026-09-21/failure-driven.md).

Reviewer runs now end their tool phase after 48 attempts or two compactions, then must return findings and explicitly unreviewed scope. If the model still emits unavailable tool calls for two more steps, KRYN interrupts that Reviewer and records an incomplete review. This limit applies to Reviewer, not Build; large reviews should use focused follow-ups. It bounds the observed repeated-reading loop without increasing the memory or context limits.

Incident capture is automatic; implementing and accepting a new harness fix still requires evidence and engineering review. The older local instruction-optimization experiment remains restricted to disposable JSON tasks and paused on the validated installation. It has not established an improvement in application-building quality. KRYN does not automatically rewrite its runtime, permissions, test answers or model weights after an error, and frontier parity has not been demonstrated.

## Repository layout

- `src/kryn/`: packaged launcher, verified installation, updates and rollback.
- `setup/`: pinned configuration, model profile and installation checks.
- `tools/`: resource supervision, native client adapter, workflow hooks and evaluation utilities. OpenCode owns the agent loop and both interfaces.
- `evals/`: task definitions and redacted validation history. Private transcripts, credentials and generated test workspaces stay outside Git.

## License and distribution

KRYN's source is licensed under [MIT](LICENSE). Upstream applications, model weights, dependencies and online services retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md).

Private releases contain a KRYN wheel, `install-kryn.py` and `SHA256SUMS`. The curated [package builder](build_package.py) excludes model weights, credentials and private task traces. Install from a tagged release using the steps above. Release checksums and payload hashes provide integrity checks through authenticated GitHub distribution; KRYN artifacts are not independently signed or notarized.
