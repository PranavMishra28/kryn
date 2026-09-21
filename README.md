# KRYN

A private local coding workspace for Apple Silicon. KRYN connects OpenCode's terminal interface to Qwen running through oMLX, with coding, planning, review, browser and search tools in one installation.

[Release v0.1.2](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.2) · [Security](SECURITY.md) · [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

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
| **Build** | Editing code and running approved commands; thinking enabled. |
| **Plan** | Inspecting code and discussing a plan before implementation; fast mode. |
| **Browse** | Web search and interaction with an isolated Chrome session; fast mode. Select this mode explicitly for browser work. |
| **Audit** | Read-only review, configured to request one fresh Reviewer. Switch back to Build explicitly before making fixes or running tests. |

Type these commands **inside KRYN**, then press Enter:

| Command | Purpose |
|---|---|
| `/audit` | Enter Audit mode and review current work. |
| `/research your topic` | Research a topic with search and source links. |
| `/handoff` | Request a summary of completed work, checks and next steps. |
| `/sessions` | Choose a saved session to resume. Relaunch from the same project first. |
| `/exit` | Close the terminal interface and return to your shell. |

After exiting, run `kryn stop` in Terminal if you also want to stop the idle model server. Otherwise, model weights unload after five idle minutes. One local generation runs at a time.

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
     gh release download v0.1.2 --repo PranavMishra28/kryn \
       --pattern install-kryn.py --pattern '*.whl' --pattern SHA256SUMS
     shasum -a 256 -c SHA256SUMS
     python3 install-kryn.py --tag v0.1.2
   )
   ```

   The installer provisions the pinned model and runtime dependencies, including managed Python, Node, OpenCode, oMLX and browser tooling. Complete any normal macOS app approval when prompted.

3. Make the launcher available in this Terminal, check the installed version, then follow **Start coding** above:

   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   kryn --version
   ```

   Expected version: `KRYN 0.1.2`. If a new Terminal cannot find `kryn`, use `~/.local/bin/kryn` directly or add the export line to `~/.zshrc` once.

## Maintenance and troubleshooting

Run these commands in **Terminal**, outside the KRYN interface:

| Command | Purpose |
|---|---|
| `kryn --continue` | Open the latest saved session in this project. |
| `kryn --session SESSION_ID` | Open a specific saved session belonging to this project. |
| `kryn status` | Inspect host memory pressure, runtime, owner session and background improvement state. |
| `kryn doctor` | Check configuration, dependencies, runtime health and tool connections. A stopped server is reported as unavailable; launching KRYN starts it. |
| `kryn doctor --deep` | Also verify installed model and browser dependency files; slower, without inference. |
| `kryn login` | Renew the owner session online. A verified session permits seven days of offline startup. |
| `kryn update v0.1.2` | Install the exact release tag through the verified updater. Substitute a newer published tag when available. |
| `kryn rollback` | Restore the previous retained installation after an update. |
| `kryn improve status` | Inspect experimental background improvement. |
| `kryn improve pause` | Pause background improvement. |
| `kryn stop` | Stop the verified, idle KRYN model server. Finish active work first. |

If memory protection stops a session, KRYN cancels its work, retains the native session and completed file writes, and stops its verified idle model server to release memory. Check `kryn status`; once `memory.pressure` is `normal`, run `kryn --continue` from the same project. The server starts automatically. Memory pressure can recur if the desktop workload leaves insufficient room for the model. If search or browser services are unavailable, local coding can still launch; inspect their connection status with `kryn doctor`.

Application state, sessions, caches and installed packages live under `~/Library/Application Support/LocalAI`; the oMLX application lives under `~/Applications/oMLX.app`, with settings in `~/.omlx`. Keep private session data out of bug reports and commits.

## Configuration and release scope

The pinned stack is **OpenCode 2.0.10**, **oMLX 0.6.4**, **Qwen3.5-9B-6bit**, **Playwright MCP 0.0.82** and keyless Exa search. The model profile uses a **24,576-token context**, **8,192-token output limit**, **12 GiB model memory ceiling** and one active generation. Exact model hashes and tool settings are in [the accepted profile](setup/accepted-profile.json) and [the client template](setup/opencode.template.json).

Automatic compaction reserves room for output and retains up to 4,096 tokens of recent user context alongside a structured checkpoint. The complete session history and written files remain on disk; summaries are not lossless, so the agent is instructed to reconcile them with files and check results. Compaction uses a separate 2,048-token fast summary budget.

Each file write is limited to 12,000 UTF-8 bytes; larger components should use smaller files or edits. If a top-level Build response still hits the output limit, KRYN asks OpenCode to continue from saved state, at most twice per user prompt. Incomplete tool-call text is never executed as code. Continued work retains normal permission checks.

Inference runs locally without a paid inference API. Search queries and browser traffic use external services with their own availability and quotas; electricity, storage and hardware still have costs. See [Security](SECURITY.md) for data and permission boundaries.

Version 0.1.2 is a prerelease for owner testing. Earlier task evaluations include failed tests, incomplete browser work and missed review steps; larger context and recovery do not establish frontier-level task quality. Review generated changes and run your project's checks. Background improvement is experimental; a measured learning benefit has not been established. Detailed results remain in [evaluation history](evals/history/2026-09-21).

## License and distribution

KRYN's source is licensed under [MIT](LICENSE). Upstream applications, model weights, dependencies and online services retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md).

Private releases contain a KRYN wheel, `install-kryn.py` and `SHA256SUMS`. The curated [package builder](build_package.py) excludes model weights, credentials and private task traces. Install from a tagged release using the steps above. Release checksums and payload hashes provide integrity checks through authenticated GitHub distribution; KRYN artifacts are not independently signed or notarized.
