# Public official-source pagination task (preregistered 2026-10-03)

Start from clean `main` `62cf99accf9c9e4864d3a3773ad635b6f7bb42fc`.
This is **public development calibration**, never a protected H1 result. The
research-only exact-file channel passed a zero-model Agent/Docker handoff, but
no live model has yet used it for coding. The released v1.0.0 product, model,
resource guard, tool catalog and permissions are unchanged.

The external source is GitHub's official REST pagination guide at `github/docs`
commit `2bd66de8cea336061c9ea060c9b37385136e6ab3`, path
`content/rest/using-the-rest-api/using-pagination-in-the-rest-api.md`, frozen
at 10,088 bytes and SHA-256
`418bdf281d74a89c7dabedc4af53a6f7b286f2416e7670d9cc71453db08d8640`.
Only that file is readable to the Agent; its provenance sibling and grader are
not. The source's [official page](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
documents `link` next URLs, omitted links, opaque cursor parameters and array,
empty, or object-wrapped page payloads.

**Task:** implement a small Python `collect_pages(fetch, first_url)` function.
`fetch` is a supplied callback returning a response with `data` and `headers`;
the function must collect items until no next link remains. It must follow the
link URL as given, handle the documented payload shapes, tolerate header-case
variation, and stop a repeated URL rather than loop forever. The prompt will
tell the Agent to consult the source and disclose that long native shell output
can be truncated; both arms receive identical text.

The frozen public grader uses a separate host oracle and runs candidate code
in pinned, networkless, read-only, non-root Docker with only the candidate
checkout mounted. Cases include a single page, mixed-order links, opaque
`after` cursor, object-wrapped items, no-content pages, missing next link,
header-case variation and a repeated next URL. Before generation the broken
seed must fail, a reference solution pass, and a deliberate one-page-only
partial fail, each on a fresh Docker-visible clone. Capture exact seed,
prompt, source, grader, image and patch hashes.

Then run one **native-first** pair with the real local Qwen3.5-9B-6bit model
through the same `run_candidate_to_grader` barrier, with a 900-second cap per
arm and the unchanged daily-use guard. Score strict independent acceptance,
native completion, source use, false completion, wall time, requests/tokens,
tool calls, memory pressure and swap. A resource abort, timeout, absent source
read, unmatched tool/permission contract, or failed grade is a recorded failure;
no retry to chase a pass. This single public pair may diagnose the runner and
worker. It cannot establish generalization, confidence intervals, protected
uplift or frontier adjacency.

The first offline control attempt from `8368ea46173e581fcfd603cbdbab7757a415a358`
failed **all three controls** before generation: the Docker CLI lacked `-i`,
so the isolated worker received empty stdin and raised `JSONDecodeError`.
The failed receipt is retained at
`/private/tmp/kryn-public-pagination-20261003-01/fixture.json`, SHA-256
`09248df70df5e177e9997827d2619057f3455fb743862c7`. This is a grader
transport defect, not a model result. The correction adds Docker's stdin flag;
the task, source, cases and reference remain unchanged.

## Frozen controls and first live pair

The corrected offline controls from clean `f8232a3b939009fb94276bf5f934a220c4d987c0`
passed: the seed failed four of six cases, the reference passed all six, and
the one-page partial failed four. All Docker workers exited and containers
were removed. The fixture receipt is
`/private/tmp/kryn-public-pagination-20261003-02/fixture.json`, SHA-256
`76ae8751cdf66e50166344f622db884640bb49c520c4b979c350c4298cea41e3`.
The seed commit was `fc2ad7d009d7c2abb7b3a523f4850b2892370769`, prompt
SHA-256 `5bbf552855582b4d91187e42a9ab6414c98be4f2c6842b018793d61ce4db0387`,
reference patch SHA-256
`6589b1c3977f36b373b9c4a9c0c472c534846178e97208edff19fb4ae04f0a41`,
and partial patch SHA-256
`ec46d8122c77136fd38c371d4fe59411d3d94c4b8cc8cd53213ec992a921b902`.
`make check` passed before generation.

The native-first live pair used the same Qwen3.5-9B-6bit, 8192 output cap,
sampling values, ten-tool wire schema hash
`1b56b6b37c804f7fd30cd60d131476c6a619cda5269ac2ccf9d2fc8a5d34a81e`,
and effective permissions in both arms. AC power, normal sampled pressure,
zero sampled swap growth, complete telemetry and clean APFS detachment were
observed. **Neither arm passed strict acceptance.** The frozen raw pair receipt
is `/private/tmp/kryn-public-pagination-20261003-02/pair.json`, SHA-256
`de64c7aa614c03d94bc2795173765f0ae06a1847639c4a2d77a585cd1d19f2fe`.

| Arm | Outcome | Evidence |
| --- | --- | --- |
| Native | Completed in 119.984 s; independent Docker grader rejected 2/6 cases. | The model's own check exited 0, but `None` data with a next link stopped early and mixed-case `LiNk` was missed. Its final text claimed both behaviors were covered. Nine model requests; session-export totals: 19,898 input, 4,217 output, 45,056 cached-read tokens. |
| KRYN | Ended after 20.501 s before edit or grading. | Native `read` returned `Permission denied: external_directory`; the Agent then tried an unrelated `raw.githubusercontent.com/simonw/...` URL through `webfetch`, which the noninteractive permission policy rejected. Three model requests; 4,238 input, 308 output, 10,240 cached-read tokens. |

Both arms first tried the native `read` tool on the pinned source and were
denied by the **OpenCode permission layer**, although the research Seatbelt
profile allowed the exact file. Native recovered with `shell cat`, but that
tool reported `truncated: true` and supplied only its tail. KRYN did not use
the permitted shell route. [OpenCode V2's permissions documentation](https://opencode.ai/v2/docs/permissions)
confirms that external paths need an `external_directory` rule as well as a
`read` rule; the current research config denies every external directory.
This is a source-delivery defect in the experimental adapter, plus a visible
worker recovery failure, not evidence about frontier capability.

The raw pair incorrectly says `tool_catalogs_equal: false`: the recorder read
a nonexistent `tools` field from relay requests. Without rerunning the model,
a read-only audit of both `driver.json` and session exports found one identical
wire contract across all requests in both arms. The corrected code now uses
`tool_count` and `tool_schema_sha256` along with model, sampling and thinking
settings. The separate audit is
`/private/tmp/kryn-public-pagination-20261003-02/pair-audit.json`, SHA-256
`92db46fbff5e9b995d536b6eacb3d35c541bf5551cf5c5397f69f4ebe7b53014`.
Neither raw receipt was rewritten or reclassified as a pass.

**Decision:** retain this pair as a failed public diagnostic. The next
one-variable candidate is a narrow, read-only OpenCode permission path for
the already-allowed exact source file; it must pass no-model read, edit-denial,
and sibling-denial checks before another live task. Reusing this public fixture
after that change is development work only. Protected H1 and current-source
category admission remain closed.

## Post-permission public diagnostic preregistration

The exact-source native-read canary passed both arms at `2ad0e741` (receipt
SHA-256 `bfe8669cd917c5f23a9e323750bb89d7bca6ed540208aa75c7bfc2776c504b93`).
From `main` `88f175e`, repeat this **same public development task once** with
the only behavioral change being the research adapter's external-file
permission. Recreate the seed, prompt, source and grader controls and verify
their hashes against the first pair before generation. Keep native-first arm
order, Qwen3.5-9B-6bit, 8192 output cap, tool catalog, agent variants,
900-second cap, same daily-use guard and same host occupancy policy. Do not
relax any resource threshold. A resource abort stops the pair.

Primary diagnostic: does KRYN now complete a native source `read` and reach a
candidate patch? Strict task success still requires all six independent Docker
cases, no false completion, matched permissions/wire contracts, complete
telemetry and cleanup. Record request/token counts, tool failures, wall time,
pressure, swap and source-use evidence. The original failed pair remains
immutable; a better result here is **not** a protected effect size because this
task has been used to diagnose the adapter. If both arms still fail, classify
the remaining worker/verification failures rather than adding prompt rules.
