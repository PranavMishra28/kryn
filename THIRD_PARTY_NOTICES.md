# Third-party components

KRYN's wheel contains KRYN source, configuration, lockfiles and evaluation material. It does not bundle third-party model weights, applications, runtime binaries, Node dependency trees or Chrome profiles. The installer downloads verified upstream artifacts and preserves their supplied licenses. Their terms remain separate from KRYN's [MIT license](LICENSE).

| Component | License and provenance |
|---|---|
| OpenCode 2.0.10 | MIT, confirmed in installed `@opencode/cli-darwin-arm64` package metadata; [pinned upstream source](https://github.com/anomalyco/opencode/tree/b8cedc1a7a5e2916bbb65dc1d4b620729c261638). |
| oMLX 0.6.4, app build 2529 | [Apache-2.0 at the pinned tag](https://github.com/jundot/omlx/blob/v0.6.4/LICENSE). Its bundled MLX dependencies retain their own upstream notices. |
| Qwen3.5-9B six-bit MLX conversion | Apache-2.0 declared by the [exact conversion card](https://huggingface.co/mlx-community/Qwen3.5-9B-6bit/blob/76fe4065e622cf34990d3c13ef80ec8531c9a0f7/README.md); [original Qwen model license](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/LICENSE). The card identifies Qwen/Qwen3.5-9B as the conversion source; its metadata also names the Base model. KRYN pins the quantized artifact bytes and does not claim to have retrained it. |
| Historical Qwen3.8-27B Q4 profile | Apache-2.0 declared by the [pinned conversion card](https://huggingface.co/gcoli/Qwen3.8-27B-oQ4e-mtp/blob/c41ed507f1b16320942a1e9ce340e71d2692dee2/README.md); [base-model license](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/LICENSE). Retained historical results are not current-profile qualification. |
| Playwright MCP 0.0.82 and Playwright dependencies | Apache-2.0, confirmed in installed metadata/LICENSE; [upstream](https://github.com/microsoft/playwright-mcp). The frozen npm lockfile records dependency versions and integrity digests. |
| Exa | Online service, not redistributed; subject to service terms and endpoint quotas. [Official MCP documentation](https://exa.ai/docs/get-started/exa-mcp). |
| Google Chrome | Separately installed proprietary browser; not redistributed. [Chrome terms](https://www.google.com/chrome/terms/). |
| Node.js | Separately provisioned runtime; compatible 22.x releases or pinned 22.23.1 fallback. [Upstream license and bundled notices](https://github.com/nodejs/node/blob/v22.23.1/LICENSE). |
| CPython | uv-managed runtime; [Python license](https://docs.python.org/3/license.html) and bundled dependency notices apply. Runtime bytes are not included in KRYN's wheel. |
| uv 0.11.16 fallback | Separately downloaded original-publisher artifact; [MIT/Apache-2.0 licensing](https://github.com/astral-sh/uv/tree/0.11.16). |
| hatchling 1.32.4 | MIT; [upstream](https://github.com/pypa/hatch). Build dependency only, not needed by the installed runtime. |
| GitHub CLI | Separately installed prerequisite; [MIT license](https://github.com/cli/cli/blob/trunk/LICENSE). GitHub's service terms govern release access. |

The oMLX download can fall back to the [unaffiliated SourceForge mirror](https://sourceforge.net/projects/omlx.mirror/files/v0.6.4/) when the publisher asset is missing. KRYN requires the original pinned image hash from either source; the mirror is a transport fallback, not a new runtime or publisher endorsement.

The memory telemetry helper is loaded from the user's pinned oMLX installation after a source-hash check; it is not copied into KRYN. Model and dependency manifests retain artifact identities and hashes. Downloaded runtimes and applications can include additional third-party notices; their distributed license files remain authoritative.

KRYN's disposable evaluation fixtures are project-authored. Public Terminal-Bench/Harbor sources inspected during feasibility research stay in private research evidence and are not shipped in the wheel; no official benchmark run or score is claimed. Reference URLs and service access do not grant redistribution rights to fetched pages or user content.
