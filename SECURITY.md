# Security

## Reporting an issue

For the current private distribution, authorized repository members can open an [issue](https://github.com/PranavMishra28/kryn/issues/new) with a redacted security report. Confirm that the repository is still private before including vulnerability details. If it becomes public, use GitHub private vulnerability reporting if available, or contact the repository owner through an existing private channel; do not post exploit details publicly.

Include the KRYN version, macOS version, affected component, expected and observed behavior, and a minimal reproduction using disposable data. Omit tokens, credentials, private source code, session transcripts and raw browser profiles. Redact local paths and diagnostic output before sharing them.

This project currently distributes v0.1.2 as an owner-testing prerelease. There is no guaranteed response time or long-term maintenance commitment for older versions. Report issues against the latest published release when possible; security fixes will be identified in release notes.

## Trust and data boundaries

- **Owner access:** Installation and login verify the configured GitHub owner's numeric identity using GitHub CLI credentials in macOS Keychain. The seven-day offline identity cache contains no access token. It is an access policy, not tamper-resistant licensing or immediate remote revocation.
- **Local inference:** The configured model endpoint is `127.0.0.1:8000`. The managed configuration permits the local provider. This does not prevent tools from using the network: search queries reach Exa, and browser requests reach visited sites.
- **Project trust:** KRYN can read code, edit files and execute approved commands. Treat repository instructions, plugins, configuration and dependencies as trusted executable inputs. Ordinary shell writes are restricted to the project and owned state/temp/log paths. Native file tools, browser/MCP tools, formatters and persistent PTY sessions are outside that guard; reads and network access are not isolated. This is not a sandbox for hostile repositories.
- **Stored data:** Sessions, caches, browser output and diagnostic records can contain private material. Most KRYN state is under `~/Library/Application Support/LocalAI`; oMLX also uses `~/.omlx`. Review permission prompts and keep secrets out of prompts, reports and commits.

## Release integrity

Use an exact release tag and verify `SHA256SUMS` before running the downloaded installer, as shown in the [README](README.md#first-installation). The installer verifies the wheel; the package verifies its curated payload and pinned dependencies. These checks trust the authenticated GitHub repository and its release assets. Checksums do not protect against a compromised publisher replacing both an artifact and its checksum. KRYN does not currently provide independent artifact signatures, notarization or hosted build attestations.

Third-party components retain their own security policies and licenses; component identities and provenance are recorded in [Third-party notices](THIRD_PARTY_NOTICES.md).
