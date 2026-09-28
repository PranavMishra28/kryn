# KRYN

A coding workspace for Apple Silicon: OpenCode's terminal and browser interfaces, a local Qwen model through oMLX, and coding, planning, review, browser and search tools. Other OpenCode providers are optional and selected by you.

**Public releases are paused.** The available [v0.1.10 prerelease](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10) is from `e9c90ff`; current source includes later fixes. Owner smoke and rollback checks pass narrowly, but full coding/UI completion and truthful compaction/restart remain failed. Clean KRYN-scoped installation, useful context-tier selection and sustained active work remain unqualified. See [current status and gates](plan.md), including the latest reading-list evidence. No production-quality, autonomous improvement or frontier-parity claim follows from the results.

| Start here | Contents |
|---|---|
| [Use KRYN](docs/usage.md) | Modes, permissions, models, terminal/GUI, sessions, diagnostics and recovery |
| [Current status](plan.md) | Active gates, exact evidence and next checks |
| [Develop KRYN](CONTRIBUTING.md) · [Repository map](AGENTS.md) | Owning layers, focused checks and package smoke |
| [Evaluation contracts](evals/README.md) · [External Requests](docs/external-requests.md) | Frozen checks and independent acceptance requirements |
| [Security](SECURITY.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) | Trust boundaries, distribution and upstream terms |

## Quick start

From your project folder in Terminal:

```sh
cd "/absolute/path/to/your/project" && kryn
```

Type a request and press Enter. New sessions use **Agent**; **Ctrl+X**, then **A** chooses Ask, Plan or Agent. **Ctrl+T** cycles Default (bounded thinking) and Fast for local Qwen. **Ctrl+P** opens the command palette. Use `/models` for native provider selection, `/settings` for permissions and display, `/sessions` to resume, and `/exit` to leave. `kryn controls` shows an offline reference.

Review permission prompts and generated changes. Explicit `kryn --auto` accepts all native requests not denied, including browser/network actions; see [permission scope](docs/usage.md#models-and-providers). `kryn --web` opens the companion GUI; `/web` displays its temporary credentials. `kryn --continue` resumes from the same project. Saved sessions remain on disk; compaction summaries can be inaccurate.

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

## Updates and recovery

Current packaged source checks for a newer checksum-verified KRYN release at startup and while idle, with one notice per release and no automatic dialogs. `/update` shows its exact version/commit and short change summary, then offers **Update instructions / Later**. `kryn update --check` is the read-only Terminal equivalent. Checks are throttled; network failures, same-version private builds and older releases produce no update offer. This behavior is not yet in the published v0.1.10 artifact.

Run `kryn update vX.Y.Z` in Terminal for an exact newer published KRYN tag. The updater verifies release checksums and package contents before transactional activation; `kryn rollback` restores the retained previous installation. Finish work and exit KRYN before updating. Do not install an unverified main commit or independently update the pinned OpenCode binary. Current same-version private candidates are not a public update channel.

`kryn status` and `kryn doctor` inspect the installed system; `kryn doctor --deep` also hashes installed model/browser files. `kryn uninstall` deactivates owned launchers while retaining models, sessions, settings and packages. [Maintenance and recovery](docs/usage.md#maintenance-and-troubleshooting) covers interrupted transactions, repair and memory-pressure recovery.

## Current profile and learning limits

The public profile pins OpenCode **2.0.10**, oMLX **0.6.4**, Qwen3.5-9B-6bit, **49,152** context tokens, **8,192** output tokens, a **16 GiB** model memory ceiling and one active generation. Owner 64K is a private guarded experiment. Exact settings remain in the [accepted profile](setup/accepted-profile.json) and [client template](setup/opencode.template.json).

Per-run incident capture retains bounded private failure metadata and check receipts for diagnosis. It does not repair code or qualify a change. The optional disposable-task learning worker remains paused; cross-project automatic promotion has no established benefit and still needs independent reproduction, protected holdouts, matched repeated trials and monitored rollback. See [current learning gates](plan.md#incident-capture-and-promotion).

## License and distribution

KRYN's source is licensed under [MIT](LICENSE). Upstream applications, model weights, dependencies and online services retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md).

Releases contain a KRYN wheel, `install-kryn.py` and `SHA256SUMS`. The curated [package builder](build_package.py) excludes model weights, credentials and private task traces. Install from a tagged release using the steps above. Release checksums and payload hashes provide integrity checks through authenticated GitHub distribution; KRYN artifacts are not independently signed or notarized.
