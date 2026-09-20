# Third-party components

KRYN's source package does not bundle model weights, applications, Node packages or Chrome profiles. Installation downloads pinned artifacts and preserves their supplied licenses. Their terms remain separate from KRYN's own source license.

| Component | License / source |
|---|---|
| OpenCode 2.0.10 | MIT, confirmed in the installed @opencode/cli-darwin-arm64 package metadata; [upstream](https://github.com/anomalyco/opencode). |
| oMLX 0.6.4 | [Apache License 2.0 at the pinned tag](https://github.com/jundot/omlx/blob/v0.6.4/LICENSE). |
| Qwen3.8-27B quantization | Model card declares Apache-2.0; [pinned quantization card](https://huggingface.co/gcoli/Qwen3.8-27B-oQ5e-mtp/blob/fb646bbfbdce4caa26fa2262f0ef7953708f66d9/README.md), [base-model license](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/LICENSE). |
| Playwright MCP 0.0.82 | Apache-2.0, confirmed in the installed package metadata and LICENSE; [upstream](https://github.com/microsoft/playwright-mcp). |
| Exa | Remote service, subject to its service terms and free endpoint quotas; [documentation](https://exa.ai/docs/get-started/exa-mcp). |
| Google Chrome | Separately installed proprietary browser; not redistributed. |
| Python / Node / uv | Separately installed runtimes, not redistributed by this package. |

The memory telemetry helper is loaded from the user's pinned oMLX installation after a source-hash check; it is not copied into KRYN. Dependency lockfiles retain package identities and integrity hashes.
