# KRYN

**Release status: NOT READY.** The launcher is installed and its source kit is tested, but the selected model repeatedly hit the memory guard on the 48 GiB Mac. The representative daily coding workflow could not start under its required resource condition. Sustained context qualification, the completed MTP comparison, and continuous improvement also remain incomplete. This is an experimental source snapshot, not a qualified release or a frontier-equivalent assistant.

KRYN is a small launcher, configuration, verification and improvement layer around OpenCode. OpenCode remains the interactive coding agent; oMLX runs the model on this Mac. There is no replacement agent loop or new TUI.

## Daily use

The experimental installed command is:

~~~sh
cd /path/to/your/project
kryn
~~~

If the existing PATH does not include your user bin directory, use "$HOME/.local/bin/kryn". No shell profile edit is required. Start in an ordinary project directory, rather than your home folder.

| Command | Behavior |
|---|---|
| kryn | Check the exact local profile, start oMLX if needed, check native routing/tools, then open OpenCode in Plan. |
| kryn init | Verify an existing installation; before first installation, use the source kit's bootstrap instead. |
| kryn doctor | Check release integrity, runtime/profile compatibility, dependencies, disk and MCP readiness. No model generation. |
| kryn doctor --deep | Also stream through every pinned model file and verify SHA256. |
| kryn status | Show local runtime and improvement status. A stopped runtime is reported as unavailable. |
| kryn stop | Stop only the verified owned, idle oMLX runtime. |
| kryn bench | Run guarded local protocol smoke. This makes real model requests and does not establish coding quality. |
| kryn improve status | Show local outcome retention, inactive/active skill and incomplete automation status. |
| kryn improve | Show improvement status. Use `kryn improve --help` for explicit operator controls. |

Close OpenCode normally when finished. The private native client and browser children should exit; the model server can remain warm until stopped. KRYN blocks overlapping foreground sessions. Never work around a memory stop by disabling the guard.

This release pass ends with the model server stopped to free memory. `kryn` can start it again, but successful UI startup does not establish that a model request will meet the resource guard. No further app closing or installation action is required from you to complete this handoff.

## First installation and reproduction

The tested machine is an Apple M4 Max, 40 GPU cores, 48 GiB unified memory, macOS 26.6.2 build 25G83. Other hardware is unqualified. The installer checks native Apple Silicon, macOS 26/27, at least 48 GiB memory and 140 GiB free disk. More memory does not by itself establish compatibility.

Prerequisites are native Python 3.13+, ARM64 Node 22.23.1 with adjacent npm, uv, Git, Google Chrome, and internet access. The currently tested Chrome is 153.0.8010.53. The repository contains setup code and dependency hashes, not applications or model weights.

~~~sh
./bootstrap
./bootstrap --apply
~~~

The first command checks installation prerequisites and may record compact metadata in KRYN's owned outcome directory; it does not install dependencies or replace configuration. The second explicitly applies the existing installer. Set KRYN_PYTHON to a Python 3.13+ executable if needed; pass --node and --uv for existing nondefault installations. Downloads use exact revisions and verified cached artifacts. A changed or unowned destination is refused, rather than silently overwritten.

On this already installed Mac, init verifies the owned installation. Do not rerun the core installer over customized runtime settings. A first-open macOS approval may still be required on another Mac. Disposable configuration tests are distinct from a complete second-machine installation. The existing Mac has approximately 115 GiB free after retaining both model versions and evidence; it does not currently meet the installer's 140 GiB fresh-install threshold. The existing-installation preflight passed without downloading or overwriting anything.

Offline source checks:

~~~sh
python3.13 -E -B -m unittest discover -s setup -p 'test_*.py'
python3.13 -E -B tools/localai.py --self-check
~~~

The frozen evaluation suite is in evals/. Keep its checks and original failed outcomes. Use fresh disposable projects for model trials.

## Architecture and exact profile

~~~mermaid
flowchart LR
    User[You] --> K[KRYN launcher and guard]
    K --> O[OpenCode native TUI]
    O --> L[oMLX on loopback]
    L --> Q[Local Qwen 27B]
    O --> P[Project files, Git, shell and tests]
    O --> S[Exa search and source fetch]
    O --> B[Playwright with isolated Chrome]
    K --> R[Local outcome records]
~~~

| Component | Selected version |
|---|---|
| Harness | OpenCode 2.0.10 ARM64 |
| Runtime | oMLX 0.6.4, app build 2529 |
| Model | gcoli/Qwen3.8-27B-oQ5e-mtp |
| Exact model revision | fb646bbfbdce4caa26fa2262f0ef7953708f66d9 |
| Browser tools | Playwright MCP 0.0.82; its pinned dependency includes Playwright 1.64.0-alpha-1789764292000 |
| Search | Exa keyless MCP: search, advanced search and fetch |
| Node | 22.23.1 ARM64 |

The experimental profile is Fast by default, nominal 32K harness context, up to 8K output, early native compaction, one active generation, a 30 GiB oMLX application ceiling, 8 GiB SSD prefix cache and no extra hot cache. **32K sustained work is not qualified. 64K is deliberately rejected for this release.** The runtime checks text input and output limits separately; image tokens and helper prompts also consume memory. The application ceiling is not a system-wide memory reservation.

MTP is OFF. Small earlier activation tests do not prove a useful task speedup. The latest coding comparison failed in its OFF baseline, so the ON arm was not admitted and the required A/B remains incomplete.

Fast disables thinking. Low, Medium and Xhigh request different reasoning-effort hints; they are not numeric compute guarantees. Helper agents may have separate presets. More reasoning can be slower without improving correctness.

## Working with OpenCode

Use Plan to inspect and discuss a change; use Build to edit and test. Browse is a separate native primary agent with browser/search tools. Build exposes the smaller coding tool set. Switch roles using OpenCode's native agent control.

The native commands /review, /audit, /research and /handoff request read-only review, a fresh reviewer, cited research and persistent task state respectively. Actual tests and observed browser behavior remain authoritative. Fresh review is supplementary, and project configuration is trusted: an untrusted project can redefine native behavior.

Work one useful milestone at a time. Ask for explicit acceptance checks, inspect the diff, run the real checks, and preserve unresolved facts in TASK.md before a handoff. Automatic compaction can lose or misstate important task instructions; it is not perfect memory.

Project AGENTS.md, native .opencode/skills and explicit project .agents/skills/.claude/skills paths remain supported. Unrelated global skill catalogs are excluded because they previously overwhelmed context. Explicit native plan files may use ~/.opencode/plan.

## Memory, privacy and boundaries

The daily guard reuses the evaluation policy: three normal samples before inference, monitoring every two seconds, cancellation after two warning samples, immediately on critical/missing telemetry or runtime identity drift, and after more than 512 MiB additional swap. Any observed warning fails evaluation acceptance. These are conservative engineering thresholds, not proof that a warning has damaged hardware.

The guard interrupts work on the owned native server and closes its client, then checks runtime idle. It does not kill personal applications. macOS pressure depends on the whole machine. Cold model loading and long desktop/browser sessions have both hit this guard. Closing other apps did not yet produce a passing cold-load comparison; do not advertise normal-app or cold-start stability from the synthetic cache successes.

Inference is configured only to the loopback model, with cloud providers disabled and effective provider inventory checked. There are no normal metered cloud-model charges. Local inference still uses hardware, electricity, disk and time. Exa and websites are online, quota-limited services; queries and page interaction leave the Mac. Do not put private task details into public search.

A separate isolated Chrome session is used; personal Chrome profiles are not reused. Page-provided WebMCP and unsafe browser code are disabled. Ordinary shell descendants have a project/owned-state write boundary. Native file tools, MCP, formatters, persistent PTYs, reads and network are outside that OS boundary. This is not a complete hostile-project sandbox.

## Local improvement

~~~mermaid
flowchart LR
    O[Compact outcomes] --> H[Repeated-failure hypothesis]
    H --> C[Isolated fixed skill candidate]
    C --> E[Matched development, validation and hidden checks]
    E --> G{Objective promotion gate}
    G -->|Fails or missing proof| X[Reject or hold]
    G -->|Passes| V[Versioned owned skill]
    V --> M[Monitor]
    M -->|Regression| R[Rollback]
~~~

Outcome collection is local and contains enums, counts, timings and release/profile hashes, not prompts, source, credentials, URLs or project paths. A normal TUI exit is recorded as unverified, not task success. At each outcome write, owned records older than 30 days or beyond the newest 500 are pruned; unknown files are preserved.

Start with observation; these commands do not invoke a model:

~~~sh
kryn improve status
kryn improve observe
# Only when observe returns this candidate_hypothesis:
kryn improve propose verify_before_summary
~~~

`observe` groups repeated failures in the latest 20 retained outcomes by release/profile. `propose` refuses without a matching repeated failure; its other fixed hypotheses are `bounded_milestone` and `check_tool_contract`. Save the returned candidate ID. A proposal creates an isolated skill and does not activate it.

Evaluation is an explicit operator workflow using the included frozen [suite](evals/README.md):

1. Prepare six fresh runs: a control and skill candidate for each of development, validation and hidden, using three distinct automatically graded tasks. Before any model request, register both arms with `kryn improve register CANDIDATE SPLIT /absolute/run/run.json`.
2. Collect the real native runs separately with the existing evaluation driver. The control prompt must be the exact frozen task; construct the treatment with `tools/improvement.py`'s `skill_prompt(task_text, candidate_id, hypothesis)`. Require fresh sessions, matched model/role/tools/runtime conditions, complete routing/resource evidence and unchanged original checks. The improvement commands do not run these model trials for you.
3. Write a JSON array of exactly three pair objects, one per split. Each object has this shape: `{"split":"development","baseline":"/absolute/control-run","candidate":"/absolute/skill-run","stage":"improvement"}`. `stage` must match the retained native evidence directory in both arms. Supply the real validation and hidden pairs too; this file contains paths, never PASS claims.

With those prerequisites met, replace the placeholders below with the returned ID and actual absolute paths:

~~~sh
kryn improve evaluate CANDIDATE --plan /absolute/pairs.json --suite /absolute/kryn/evals
kryn improve promote CANDIDATE --plan /absolute/pairs.json --suite /absolute/kryn/evals
kryn improve monitor /absolute/later-run --stage improvement --suite /absolute/kryn/evals
kryn improve reject CANDIDATE --reason no_benefit
kryn improve rollback
~~~

These are separate decisions, not a script to run blindly. `promote` reruns the objective evaluator; it cannot consume caller-written PASS JSON. All candidate cases must pass, and the validation control must fail to establish an objective improvement. A promoted version becomes available to the next native launch. `monitor` explicitly checks a later matched run and restores the previous skill version on an objective regression; `rollback` restores that skill pointer only, not the model or runtime profile. `--simulation` is for fixture tests and cannot activate a daily skill.

Only the designated owned skill artifact may change; provider, credentials, permissions, model downloads and external-action authorization are outside optimization. **No autonomous reflection, model-trial scheduling or continuous regression monitoring is implemented. No live improvement benefit has been established.** Fixture demonstrations test the controls, not long-term learning. Optional improvement work refuses to start while foreground work holds the shared exclusive lease; a new foreground operation also refuses overlap. This is mutual exclusion, not preemption. There is no root daemon or scheduled model shopper.

Native OpenCode sessions can contain private prompts and code. They are retained locally as user work. Temporary raw evaluation traces are retained locally until audited and are excluded from distribution; do not upload them. Outcome retention does not delete native sessions.

## Measured on this Mac

The final installed client is `156185af1a020a28`. These checks used the actual `kryn` command:

| Release check | Result and scope |
|---|---|
| Installation and dependencies | `init`, `status`, `doctor` and the packaged bootstrap preflight passed against the existing installation. |
| Deep model verification | `doctor --deep` passed in 10.176 seconds; every pinned model file was rehashed. Both MCP services connected. |
| Fresh project launch with model loaded | Failed resource preflight in 1.977 seconds, before TUI/prompt/model dispatch. All 16 seed files stayed unchanged. |
| Controlled local outage | An owned loopback 503 server held the model port, preventing launcher auto-start. Actual `kryn` and `kryn bench` refused clearly; only health GET requests reached the test endpoint. |
| Recovery without inference | After removing the test endpoint, actual `kryn` restarted oMLX and opened OpenCode. Plan/Fast, Build/Fast and Reviewer/Xhigh were observed. Normal exit was recorded as incomplete, not task success. Owned client processes and temporary directories were removed. |
| Outcome and promotion controls | Real startup failures were recorded without task content. Unsupported skill proposal was refused. No skill is active. |
| Source kit | 97 offline tests passed, including actual bootstrap/fake-account cases and deterministic promotion/rejection/rollback fixtures. This is not live skill improvement. |

Two cold-load OFF comparisons also stopped after 14.833 and 16.175 seconds, including the attempt after other applications were closed. No ON comparison followed. The installed `bench` outage behavior is verified; its successful inference path was not rerun after these resource failures. No new representative coding/browser/review/handoff result is claimed.

These are retained engineering results from prior isolated drivers, not proof that the final daily product passed:

| Check | Observation |
|---|---|
| Tool endurance | Ten sequential turns, 45 tools, 744.212 seconds; one launch recovery, no intervention in the model trajectory. |
| Recovery project tests | 28 tests passed in an 834.018-second coding stage; test-quality/reporting weaknesses remain. |
| Mobile browser recovery | 698.952 seconds; actual 503, retained inputs, single successful retry and persisted row. Reporting was partial. |
| Desktop at 30 GiB | Guard stopped the session after 391.248 seconds. |
| Desktop at 28 GiB | Guard stopped the session after 688.897 seconds; substantial form progress, incomplete final reporting. |
| 24K synthetic cache sequence | 133.914/18.934/116.829/15.309 seconds; reuse worked, zero observed swap growth. This is not sustained 32K qualification. |

The original representative project failed and a separate recovery remained incomplete. Historical failures, operator interventions, misleading model claims and incomplete streams are preserved. Optional macOS computer control, office modules and local image generation are not installed or qualified. No frontier-equivalence claim is made.

Upstream capabilities and licensing are documented in [third-party notices](THIRD_PARTY_NOTICES.md); they are not measurements from this Mac.

The remaining blocking work is to isolate the cold-load/host-pressure problem, qualify a stable profile through the actual complete workflow and sustained context, complete the matched MTP check, and implement and validate the automatic improvement cycle. Allow 60–90 minutes for the next bounded memory diagnosis; if resolved, the retained 12–14 minute coding/browser stages and repeated comparisons imply at least another 2–4 hours of qualification. Automatic improvement requires additional engineering. There is no defensible guaranteed completion time before the memory cause is known.

## Updating, rollback and uninstall

No automatic update command is provided. Change one pinned component at a time, preserve the previous release, verify hashes/signatures, rerun the relevant smoke and representative tests, and compare completed-task quality and resources. Never promote a configuration because its files merely look correct.

Owned runtime/model/client state lives under ~/Library/Application Support/LocalAI. The app is ~/Applications/oMLX.app; runtime settings are in ~/.omlx; the launcher aliases are ~/.local/bin/kryn and ~/.local/bin/localai. Content-addressed client releases and private pre-change backups are retained under LocalAI/client and LocalAI/backups.

A rollback restores the exact backed-up owned configuration/profile/launcher bytes and modes, after verifying the installation still matches the release being replaced. Keep model weights and sessions unless removal is intended. Never overwrite changed user files during rollback.

For uninstall, finish foreground work, run kryn stop, quit the owned app, and verify its process/listener are gone. Preserve useful sessions and backups, then remove only the verified KRYN-owned app, namespace and unchanged launcher files. Preserve existing Ollama, Intel OpenCode, personal browser profiles and all unrelated configuration. ~/.omlx and app-created support/symlink entries require ownership inspection; never remove the entire shared ~/Library/Application Support/oMLX directory or sweep temporary folders.

The [release manifest](RELEASE_MANIFEST.json) binds this source snapshot, profile, dependency and evaluation versions. [Sanitized results](RESULTS.json) retain measurements and evidence hashes; full private traces remain on the original Mac and are required for independent replay/audit of those historical runs. Raw engineering history, personal paths, model weights, caches, browser profiles and credentials are not part of the private source package.
