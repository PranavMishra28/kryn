# Run-quality audit and workflow controls

Audited 2026-09-21. This is a failure analysis of one owner coding session and a small regression probe, not a claim of frontier capability or production application readiness. Private prompts, screenshots, source, session identifiers and logs are excluded from this report.

## What happened

The application-building session ran for about 102 minutes. Its 365 assistant responses all selected **Think**. The native transcript contains 378 tool invocations: 178 shell, 99 read, 43 write, 29 edit, 14 glob, 12 webfetch and 3 grep. There were 30 tool errors and 41 nonzero shell exits; nonzero exits are evidence to inspect, not necessarily independent bugs. All 32 automatic compactions completed. None of the assistant responses ended with `finish=length`.

There were **no browser calls, no reviewer/delegated calls, and no npm/yarn/pnpm/bun test, build or lint commands** in that transcript. The observer's lower counts (371 calls, 69 errors) are not used as the authoritative totals: its after-tool hook misses some failures before execution. Zero recorded checks alone would not prove that no checks ran; the native commands were inspected as well.

The final response claimed both servers were running. OpenCode's `succeeded` outcome means the execution ended normally; it does not verify application requirements. Curling a health route or receiving HTML is insufficient evidence of working authentication, styling, database persistence or messaging.

## Reproduced application failures

| Finding | Evidence and consequence |
|---|---|
| Styles never loaded | The root Next layout does not import `globals.css`. Login and registration use Tailwind classes but render as unstyled browser defaults. Both pages were inspected in a temporary browser preview without changing application source. |
| Login cannot work | The login page calls `login` from the Zustand store, but the store exports no such action. A dummy login submission displayed `Login failed. Please try again.` |
| Registration contract is broken | Registration calls the same nonexistent login action instead of the separate register API. It collects `name`; the backend requires `firstName`. |
| Other API contracts are broken | Store methods use `api.authAPI` although `api` is the Axios instance and the helper is a separate export. The socket client still defaults to port 5000 after the backend moved to 3001. |
| A required database was bypassed | MongoDB was unavailable. The generated development server was changed to continue without it, while `/api/health` unconditionally returned success. This makes the health check misleading. |
| Requirements were lost | The final home page is a static welcome page with authentication links. The requested swipe flow is not delivered there. |
| Broken command verification | The run repeatedly contacted macOS AirTunes on port 5000, restarted background commands, and used commands such as `curl -s ... | head` that can obscure failures. |

The supplied screenshot path was unavailable. The browser observations above came from the actual application files. The application source was left unchanged so these failures remain a reproducible test of KRYN's output.

## Harness contributions and changes

1. **npm cache:** ordinary shell writes were restricted, but npm still targeted `~/.npm`, outside that boundary. It emitted a misleading root-owned-cache diagnosis and the model attempted unrelated permission repairs. Native child processes now receive `NPM_CONFIG_CACHE` inside the already permitted KRYN cache. Background evaluation receives a separate disposable cache. No home-directory write grant was added.
2. **UI verification:** Build could not use browser tools or delegate to the primary-only Browse role. Browse is now available both directly and as a native child, with the same restricted browser/research surface. Build may delegate to it; the existing one-foreground-child limit remains. Browser actions keep their permission prompts.
3. **Automatic approvals:** `kryn --auto` passes the pinned OpenCode flag through for one interactive launch. It accepts all non-denied native requests, not only edits. Default launches still prompt; hard denials and shell containment remain. This is not a sandbox for untrusted projects. `--continue --auto` resumes with the same explicit opt-in.
4. **Effort controls:** Fast disables thinking; Medium, High and XHigh use oMLX `thinking_budget` caps of 1,024, 3,072 and 6,144 tokens. High is the new coding/review default. Legacy Think remains for saved sessions. The native `/effort` picker and Ctrl+T expose these independently of Build/Plan/Browse/Audit.
5. **Completion guidance:** Build receives explicit instructions to deliver one runnable slice, use native background shell support, validate required services, preserve acceptance criteria, delegate actual browser flows, and change approach after repeated failures. The guidance is appended through existing context hooks; it does not replace OpenCode’s native tool-aware system prompt. This is guidance, not a deterministic completion gate. A local model may still ignore it.

6. **Acceptance criteria at handoff:** a live trial showed Build dropping functional login requirements from its Browse prompt. The existing prompt/tool hooks now attach a bounded copy of the current user request to Build → Browse handoffs. It is held in memory, not written to metadata trackers, preserved across in-process compaction, and replaced by the next user request. Long requests retain the first and last 3,000 characters with an explicit omission marker. It does not reconstruct historical criteria after restarting.

No context, output, memory, concurrency or swap threshold was increased. The failing session did not hit the output limit, and compaction was already operating. More context would not repair these integration contracts or establish functional success.

## Validation

- Offline checks cover routing, the new reasoning variants, explicit versus default approvals, saved sessions, managed npm cache, role permissions and existing lifecycle/security boundaries.
- A real native shell installed a pinned npm dependency successfully using the managed cache. Native inventory accepted all configured models and agents.
- Local streaming requests verified thinking-budget behavior: 32 and 128 tokens limited the reasoning segment; Fast produced none. The 32-token run continued explanatory text in its answer and hit the 768-token test output limit. The 128-token run answered the arithmetic question correctly; Fast answered incorrectly. This tiny probe proves controls, not an accuracy ranking. Small budgets can harm output.
- The disposable UI regression trial starts from missing CSS and a broken login contract. Its first run edited the two affected files, passed both existing API tests, and delegated to Browse. Browse stopped at the expected permission prompt; the operator interrupted only that owned trial. A subsequent trial explicitly approved browser operations for the disposable localhost fixture. Browse navigated, inspected snapshots/console/network, resized and took screenshots. However, Build passed only visual criteria to Browse. Independent browser testing caught a missing `await` in the generated response handling: valid login produced no welcome; invalid login displayed the error. This run hit its 300-second limit without completing the repair. It is a failed functional trial, despite passing API tests and a visual review. The handoff preservation change above directly addresses the demonstrated loss of criteria.

- The final isolated handoff probe verified the new hook with a renamed candidate plugin and the installed plugin disabled, avoiding duplicate plugin IDs. The persisted Browse user message contained the preserved request and acceptance marker. Browse inspected the page and returned the correct heading. This is a handoff/tooling pass, not a successful application-repair trial.
- That probe initially failed the driver's cleanup qualification: native OpenCode returns a `next` cursor even on its last nonempty child-session page. The driver incorrectly treated this as truncation. It now follows bounded, ownership-checked pagination until an empty page, refusing cycles or more than 64 sessions. Offline pagination/cycle checks pass; a read-only recheck of the actual parent and child proved both idle. The original failed driver record is retained rather than rewritten.
- Final automated validation: 155 installer/launcher/package tests, 21 lifecycle tests and 23 Node plugin/audit tests, plus the native trial driver's self-check. Live resource samples for the isolated handoff stayed green with zero additional swap; these short measurements do not establish long-run stability.

The prior full application is still broken; this release does not retrospectively repair or validate it. No unattended application-building success is claimed. Larger-model selection needs a separate acceptance-task comparison within the same memory limits; adding tool names or relabeling reasoning does not establish an intelligence improvement.

## Using the controls

```sh
cd /path/to/a/trusted/project
kryn                 # normal permission prompts
kryn --auto          # opt-in automatic native approvals for this launch
kryn --continue --auto
```

Inside KRYN use `/effort` or Ctrl+T for Fast/Medium/High/XHigh, and `/agents` for Build/Plan/Browse/Audit. Existing sessions may retain Think. Ask for an observable milestone, then require its tests and browser flows before expanding scope. For a UI, start with registration → login → one persisted action, including a failure state and a narrow viewport.

## Source verification

- [Pinned OpenCode permission mode](https://github.com/anomalyco/opencode/blob/b8cedc1a7a5e2916bbb65dc1d4b620729c261638/packages/tui/src/context/permission.tsx): `args.auto` selects autoaccept; the session route replies once to pending non-denied permissions.
- [Pinned native variant controls](https://github.com/anomalyco/opencode/blob/b8cedc1a7a5e2916bbb65dc1d4b620729c261638/packages/tui/src/app.tsx): `/variants` aliases `/thinking` and `/effort`; Ctrl+T is the configured variant cycle key.
- Installed oMLX 0.6.4: `api/openai_models.py` accepts `thinking_budget`; `engine/vlm.py` passes it through; `scheduler.py` installs `ThinkingBudgetProcessor`. The pinned Qwen template checks `enable_thinking`, not OpenAI reasoning-effort labels.
- [Codex approval controls](https://learn.chatgpt.com/docs/agent-approvals-security) and [model controls](https://learn.chatgpt.com/docs/models): Codex separates permissions from model/reasoning settings. KRYN uses native OpenCode controls and local budgets; it does not reproduce Codex's model capability or sandbox semantics.


## Terminal and graphical controls follow-up (0.1.4)

The default CLI environment overlays `session.permissions=prompt`. Upstream's native settings writer merges that overlay last, so its Permissions switch could save a value but never activate it. `--permissions interactive` now removes only that overlay for the foreground terminal. The normal launch still pins prompts; `--auto` / `--permissions auto` pins native autoaccept. Interactive mode explicitly honors saved native preferences. No model-mediated permission tool or additional agent loop was added.

`kryn controls` provides an offline reference. `kryn --web` / `--gui` opens the existing server's clean loopback address alongside the terminal, after resource preflight. It does not pass credentials in a URL, expose a LAN listener or replace the native server. The browser uses its Basic-auth prompt; temporary credentials are available through native `/web`. The terminal continues supervising memory and owns shutdown. If opening the browser fails, terminal work continues.

Live GUI investigation reproduced `BrowserAttachments context must be used within a context provider` after following a credential-bearing URL with both the pinned 2.0.10 and official 2.0.12 binary. The latter was downloaded with npm SHA-512 verification, tried in a separate native process, and was not adopted. Opening and reloading a clean address after browser authentication resolved the session view on 2.0.10. Token-only startup left subresources waiting for authentication. This is why the launcher opens a plain URL, and the README specifies normal browser login rather than the upstream credential-bearing hyperlink. Native browser-dialog automation was unavailable in this environment; the test browser established Basic authentication first, then reloaded the canonical URL. No claim is made that automatic sign-in was tested or implemented.

On the pinned 2.0.10 server, the GUI opened the API-created Plan session, exposed all five local effort presets, accepted a switch from Medium to Fast, and answered `KRYN_GUI_READY` to a harmless no-tools prompt in about 15 seconds. The same session ID remained in the native database. Unauthenticated API access returned 401. This validates GUI-to-local-model connectivity, not application-building quality or every native GUI feature. Resource telemetry stayed normal during the check.

Validation: 159 Python setup/package/launcher tests, 21 lifecycle tests and 23 Node hook/audit tests pass (203 total). Added regressions cover explicit permission modes, incompatible flags, offline help, browser launch only after a green preflight, a credential-free URL, and preservation of guarded terminal operation when the OS browser opener fails. The model, tool surfaces, context/output limits and shell boundary are unchanged. No new dependency or custom UI was added.

### Effort simplification

The user requested removal of artificial effort tiers. The final configuration has one explicit variant (`fast`) and the native `Default` entry. Default enables thinking with a 3,072-token cap; Fast disables thinking and sets the cap to zero. Qwen's actual control is thinking on/off; oMLX's additional budget is a resource control, not evidence for Medium/High/XHigh quality tiers. OpenCode's variant picker always inserts Default, so adding a separate Think variant would recreate the duplication. Build/review/research use the base model; Plan/Browse retain Fast defaults. Reasoning display remains an independent setting.

Known old local variants are accepted only when validating ownership of saved sessions and cleaning them up. They are not accepted in new configuration or advertised in the picker. The native TUI filters a removed session variant to the base selection before the next prompt. The noninteractive trial driver now accepts Default/Fast and can apply a budget to the base model as well as a variant.
