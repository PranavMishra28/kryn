# KRYN current status — 28 September 2026

**Public releases, tags and version bumps remain paused.** The published prerelease is [v0.1.10](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10), source `e9c90ff6fe41cae6ef17f7fecdd2e2adf2f54246`. The owner has a private guarded 96K build; the prior 96K and 64K private builds are retained for recovery. Neither main nor a same-version private candidate is a public update channel.

`Implemented` means code exists; `mechanism checked` means a narrow test ran; `qualified` requires representative installed use. Recheck evidence after a relevant edit. A successful process, unit test, generated report or model claim is not application acceptance.

The [latest owner activation receipt](evals/history/2026-09-28-private96-22g-install.json) records private source `f08d45cd87b4452a592c5f7df3295ebeda7cb7d8`: clean wheel, guarded smoke, deep doctor, rollback to the previous 16 GiB 96K profile and reinstall. These are narrow operation checks. The [earlier activation](evals/history/2026-09-27-private96-final-install.json) tested rollback to 64K and the native `/update` current-status dialog; those results retain their original source scope.

[Use/install](README.md) · [Detailed controls](docs/usage.md) · [Develop/check](CONTRIBUTING.md) · [Evaluation contracts](evals/README.md) · [Historical evidence](docs/history.md)

## Active gates

| Gate | Evidence and current decision | Required next check |
|---|---|---|
| Public installation and recovery | Published v0.1.10 passed anonymous asset checks and existing-owner install/update/rollback/uninstall/reactivation, with guarded inference. [Release receipt](evals/history/2026-09-25-v010/qualification.json). **Narrow owner qualification only.** | Clean install and recovery in an explicitly KRYN-owned isolated environment. |
| Private owner operation | The installed 96K/22 GiB build passed guarded inference smoke, deep doctor and rollback to the previous 96K/16 GiB build followed by reinstall. [Install receipt](evals/history/2026-09-28-private96-22g-install.json). The prior 64K recovery was tested before this change. **96K remains experimental.** | Representative coding/UI use and sustained resource checks; preserve the recovery builds. |
| Coding/UI completion and truthful continuity | Fresh [Task12](evals/history/2026-09-27-task12-sliced-backend-ui-failure.json) passed backend checks but **failed** the Save contract, timed out twice and misreported browser evidence after compaction/restart. The later [reading-list resume](evals/history/2026-09-27-reading-list-resume.json) crossed two compactions but overclaimed live tab sync and repeated stale server status; app repairs were external. An independent audit of a subsequent private CRUD/CSV app reproduced a 500 on edit, rejected BOM input, partial writes after failed import, a broken priority-only filter, an inert note control and orphan notes despite the model's final success claim. A narrow native-shell fix now converts plain trailing `&` launches to owned background jobs; its unit regression passes, but installed use is pending. **Application-quality gate remains failed.** | Bounded model-produced coding/UI completion, independent browser and source review, accurate repeated compaction/restart and final handoff. Rerun a frozen coding/UI task with actual assertions; do not count generated test descriptions or a successful final answer as acceptance. |
| Native controls and lifecycle | Installed terminal permissions and native model selection passed narrowly; a free-provider interactive turn worked, while automation was rejected. [Receipt](evals/history/2026-09-27-controls-models-owner64.json). Background job lifetime and managed ARM Node fixes are recorded in the [reading-list receipt](evals/history/2026-09-27-reading-list-resume.json). | Full GUI permission roundtrip and representative end-to-end use remain unqualified; mechanism checks do not close the coding gate. |
| Useful context tier and endurance | Public 49,152 context. A private 96K live session hit the 16 GiB oMLX prefill guard after four compactions; [incident and guarded probes](evals/history/2026-09-28-private96-memory-incident.json) show 90K at a temporary 20 GiB ceiling and 94K at 22 GiB with correct synthetic retrieval, normal pressure and zero observed swap growth. Installed private source selects 22 GiB with the host guard. A prior [73,728-token cold probe](evals/history/2026-09-27-private96-light-probe.json) took 315.5 seconds. 128K previously encountered host pressure. No matched useful-tier comparison or 45–60-minute green active run. **Unqualified.** | Compare representative coding/UI quality and warm correctness; run sustained active work. |
| Independent holdout | A prior second-account run used an unrelated project's account. Those observations are [excluded from KRYN qualification](evals/history/2026-09-27-unrelated-account-scope-correction.json). **Unqualified.** | Explicitly KRYN-owned isolation with evaluator answers, private user state and other projects inaccessible to the candidate. Do not reuse that account. |

The next blocker is bounded coding/UI completion with truthful evidence and restart continuity. Useful-tier, endurance and isolated clean-install gates follow. No gold-master, frontier-equivalence or statistical harness-uplift claim is supported.

The installed private 96K build also failed a fresh [frozen Task06 coding/UI trial](evals/history/2026-09-28-private96-task06-feedback.json): backend tests passed, but an independent browser check caught an automatic POST after the injected 503, before manual retry. A feedback repair corrected that flow, then timed out and failed the 390px overflow check. Both turns kept local routing, normal memory pressure and zero observed swap growth. The trial driver now admits OpenCode's built-in free catalog while still requiring local Qwen inference; KRYN's background-shell adapter handles the observed quoted/redirection launch. These mechanism changes need installed use and do not pass the coding/UI gate.

## Update awareness

Current source checks for newer published KRYN tags through the existing checksum-verifying release downloader. The idle-time dialog and `/update` show the exact release version, wheel-manifest source commit and short release-note excerpt. Same-version private builds and unbuilt main commits are never advertised as updates. Checksum verification uses GitHub distribution, not independent signing or application-quality qualification.

Current source offers **Update and restart / Later** for a verified newer published release. Acceptance exits the native client, rechecks the exact tag and wheel hash, installs through the existing transaction, then resumes the project. Active turns defer the dialog. Offline tests cover this handoff; installed TUI acceptance and a real future-release activation/rollback are still unqualified. `kryn rollback` remains the recovery path, and pinned OpenCode is not independently updated. Public release pause remains in force.

The [prior update-awareness receipt](evals/history/2026-09-27-update-awareness.json) records offline failure/version/idle/dismissal checks, anonymous verification of the actual v0.1.10 wheel, and an isolated OpenCode 2.0.10 TUI test with a synthetic future release. New offline handoff checks cover exact-hash revalidation, client exit and resume arguments; the installed native `/update` current-status dialog passed. A real newer release does not exist, so accepted activation/restart remains unqualified.

## Incident capture and promotion

Per-run capture records bounded private metadata when execution, recognized checks or tools fail, work is interrupted, or review exhausts its budget. Counts, session references and check receipts support reproduction across compaction/restart; they omit prompts, source and raw output. A later success does not erase the prior failed check receipt. `kryn improve failures` and `kryn report` expose diagnostics. [Mechanics and limits](docs/usage.md#improvement-from-actual-failures), [lineage regression](evals/history/2026-09-27-check-failure-lineage.json).

Capture does not itself learn, repair or promote a change. The optional worker remains **paused**, limited to disposable JSON tasks, with no established application-building benefit. Cross-project automatic promotion still requires:

- Independent reproduction and a frozen regression, with failing results retained.
- Matched repeated candidate/baseline trials on representative projects, showing actual benefit without correctness or resource regression.
- Protected unseen holdouts in KRYN-owned isolation, accurate browser/source review and truthful completion evidence; same-account checks are diagnostics.
- Reviewed scope and permissions, monitored installed use, preserved sessions and verified rollback before adoption.

The small worker suite does not qualify those broader gates. This cleanup does not enable or widen it.

## Historical evidence

The [historical evidence index](docs/history.md) links the exact former ledger and README in immutable Git history. Duplicated obsolete narrative is absent from the current tree; every original receipt in `evals/history/` and every frozen fixture remains in place. The active decisions above supersede historical advice, especially references to the unrelated account.
