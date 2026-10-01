# KRYN

A coding workspace for Apple Silicon: OpenCode's terminal and browser interfaces, a local Qwen model through oMLX, and coding, planning, review, browser and search tools. Other OpenCode providers are optional and selected by you.

**v0.2.0 is a public preview for supervised local coding.** It retains the local 9B model, native OpenCode agents and tools, and a guarded 96K context setting. A small owner coding task and launcher/recovery checks passed; the larger independent coding/UI task, accurate autonomous review, truthful compaction summaries and sustained-use gates did not. Review generated changes and run your own checks. See [current status and gates](plan.md). No production-quality, autonomous improvement or frontier-parity claim follows from the results.

| Start here | Contents |
|---|---|
| [Use KRYN](docs/usage.md) | Modes, permissions, models, terminal/GUI, sessions, diagnostics and recovery |
| [Current status](plan.md) · [Architecture](docs/architecture.md) | Supervised v1 gates, ownership and trust boundaries |
| [Develop KRYN](CONTRIBUTING.md) · [Release runbook](docs/releasing.md) | Owning layers, focused checks and final-artifact release steps |
| [Supervised v1 qualification](docs/v1-qualification.md) · [Research evaluations](docs/evaluation.md) | Product release checks and separate autonomous experiments |
| [Security](SECURITY.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Changelog](CHANGELOG.md) | Trust boundaries, distribution and changes |

## Quick start

From your project folder in Terminal:

```sh
cd "/absolute/path/to/your/project" && kryn
```

Type a request and press Enter. New sessions use **Agent**; **Ctrl+X**, then **A** chooses Ask, Plan or Agent. Plan handles research with the selected model and effort. **Ctrl+T** cycles Default (bounded thinking) and Fast for local Qwen. **Ctrl+P** opens the command palette. Agent can delegate Explore, Browse or Reviewer work. Local generations run one at a time to protect memory. Use `/models` for native provider selection, `/settings` for permissions and display, `/report` for observed session evidence, `/sessions` to resume, and `/exit` to leave. `kryn controls` shows an offline reference. The unreleased source build also adds `/call TASK` for one bounded General child; the tagged v0.2.0 installer does not provide that command.

Review permission prompts and generated changes. Explicit `kryn --auto` accepts all native requests not denied, including browser/network actions; see [permission scope](docs/usage.md#models-and-providers). `kryn --web` opens the companion GUI; `/web` displays its temporary credentials. `kryn --continue` resumes from the same project. Saved sessions remain on disk; compaction summaries can be inaccurate.

## First installation

The v0.2.0 preview installer fetches public release assets over HTTPS without a GitHub account.

Requirements:

- Native Apple Silicon, macOS 26 or 27, and at least **48 GiB unified memory**. Release validation used an M4 Max with 48 GiB. Run the installer from the logged-in macOS account with its normal `HOME`; a `HOME` override cannot isolate the oMLX app.
- `python3` and `curl` available in Terminal; Google Chrome installed at `/Applications/Google Chrome.app`.
- Internet access for installation. Allow space for roughly **8.22 GB of model files**, dependencies, and the installer's **40 GiB free-space reserve**.

1. Download the pinned installer and run it. The installer fetches and verifies the release wheel and its checksums:

   ```sh
   (
     set -eu
     kryn_installer="$(mktemp "${TMPDIR:-/tmp}/kryn-install.XXXXXX")"
     trap 'rm -f "$kryn_installer"' EXIT
     curl --fail --location --proto '=https' --proto-redir '=https' \
       --output "$kryn_installer" \
       https://github.com/PranavMishra28/kryn/releases/download/v0.2.0/install-kryn.py
     printf '%s  %s\n' b66e4332b4951c4abbe37c59db6865f076117e4ebc8d4588ad6a180929bc55b5 "$kryn_installer" | shasum -a 256 -c -
     python3 "$kryn_installer" --tag v0.2.0
   )
   ```

   The installer provisions the pinned model and runtime dependencies, including managed Python, Node, OpenCode, oMLX and browser tooling. Complete any normal macOS app approval when prompted.

   If the pinned oMLX publisher asset returns 404/410, the installer reports the failure and tries the unaffiliated SourceForge mirror. Both locations must match the same pinned SHA256; a checksum failure stops installation. The mirror's complete 805,799,490-byte image was verified against that pin during release validation.

2. Make the launcher available in this Terminal, check the installed version, then follow **Start coding** above:

   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   kryn --version
   ```

   Expected version: `KRYN 0.2.0`. If a new Terminal cannot find `kryn`, use `~/.local/bin/kryn` directly or add the export line to `~/.zshrc` once.

## Updates and recovery

The v0.2.0 client checks for a newer checksum-verified KRYN release at startup and while idle. It offers **Update and restart / Later** once per release, or on demand through `/update`. Acceptance closes the client, verifies the same release hash again, uses the existing transactional installer, then resumes the project. Active turns defer the dialog; no update replaces a running generation. `kryn update --check` is the read-only Terminal equivalent. Network failures, same-version private builds and older releases produce no offer. The older public v0.1.10 client needs a manual version update; its in-session notice was not yet present.

Run `kryn update vX.Y.Z` in Terminal for an exact newer published KRYN tag. The updater verifies release checksums and package contents before transactional activation; `kryn rollback` restores the retained previous installation. Finish work and exit KRYN before updating. Do not install an unverified main commit or independently update the pinned OpenCode binary. Current same-version private candidates are not a public update channel.

`kryn status` and `kryn doctor` inspect the installed system; `kryn doctor --deep` also hashes installed model/browser files. `kryn uninstall` deactivates owned launchers while retaining models, sessions, settings and packages. [Maintenance and recovery](docs/usage.md#maintenance-and-troubleshooting) covers interrupted transactions, repair and memory-pressure recovery.

## Current profile and learning limits

The preview pins OpenCode **2.0.10**, oMLX **0.6.4**, Qwen3.5-9B-6bit, **96K** context tokens, **8,192** output tokens, a **22 GiB** oMLX ceiling and one active generation. This larger setting is guarded but has not been proved to improve coding quality or sustain every desktop workload; if the guard stops work, the session remains available to resume. Exact settings are in the [accepted profile](setup/accepted-profile.json) and [client template](setup/opencode.template.json).

Per-run incident capture retains bounded private failure metadata and check receipts for diagnosis. It does not repair code or qualify a change. The optional disposable-task learning worker remains paused; cross-project automatic promotion has no established benefit and still needs independent reproduction, protected holdouts, matched repeated trials and monitored rollback. See [current learning gates](plan.md#incident-capture-and-promotion).

## License and distribution

KRYN's source is licensed under [MIT](LICENSE). Upstream applications, model weights, dependencies and online services retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md).

Releases contain a KRYN wheel, `install-kryn.py` and `SHA256SUMS`. The curated [package builder](build_package.py) excludes model weights, credentials and private task traces. Install from a tagged release using the steps above. Release checksums and payload hashes provide integrity checks through authenticated GitHub distribution; KRYN artifacts are not independently signed or notarized.
