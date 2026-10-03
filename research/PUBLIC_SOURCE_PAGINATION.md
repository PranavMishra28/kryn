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
