# KRYN current status — 27 September 2026

**Public releases, tags and version bumps remain paused.** The published prerelease is [v0.1.10](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10), source `e9c90ff6fe41cae6ef17f7fecdd2e2adf2f54246`. Current source sets a private guarded 96K candidate; the last qualified owner installation was 64K. Neither main nor a same-version private candidate is a public update channel.

`Implemented` means code exists; `mechanism checked` means a narrow test ran; `qualified` requires representative installed use. Recheck evidence after a relevant edit. A successful process, unit test, generated report or model claim is not application acceptance.

The latest owner activation receipt was inspected read-only during this cleanup: private source `094fd9b9459315780f90b7c6038d7044ab63db44`, with package and deployment using the same stable retained interpreter. The owner/main chat reported deep doctor passing after that move; this slice did not repeat inference, reinstall or change that installation. Earlier installed qualification receipts below retain their original source scope.

[Use/install](README.md) · [Detailed controls](docs/usage.md) · [Develop/check](CONTRIBUTING.md) · [Evaluation contracts](evals/README.md) · [Historical evidence](docs/history.md)

## Active gates

| Gate | Evidence and current decision | Required next check |
|---|---|---|
| Public installation and recovery | Published v0.1.10 passed anonymous asset checks and existing-owner install/update/rollback/uninstall/reactivation, with guarded inference. [Release receipt](evals/history/2026-09-25-v010/qualification.json). **Narrow owner qualification only.** | Clean install and recovery in an explicitly KRYN-owned isolated environment. |
| Private owner operation | Exact-source rollback/reinstall, guarded inference and deep doctor passed for the private 64K candidate. [Lineage receipt](evals/history/2026-09-27-current-main64-lineage-install.json), [controls/models receipt](evals/history/2026-09-27-controls-models-owner64.json). **64K remains experimental.** | Qualify materially changed installed behavior; documentation changes alone need no reinstall. |
| Coding/UI completion and truthful continuity | Fresh [Task12](evals/history/2026-09-27-task12-sliced-backend-ui-failure.json) passed backend checks but **failed** the Save contract, timed out twice and misreported browser evidence after compaction/restart. The later [reading-list resume](evals/history/2026-09-27-reading-list-resume.json) crossed two compactions but overclaimed live tab sync and repeated stale server status; app repairs were external. **Failed.** | Bounded model-produced coding/UI completion, independent browser and source review, accurate repeated compaction/restart and final handoff. Change the failed model/workflow approach before another full qualification attempt. |
| Native controls and lifecycle | Installed terminal permissions and native model selection passed narrowly; a free-provider interactive turn worked, while automation was rejected. [Receipt](evals/history/2026-09-27-controls-models-owner64.json). Background job lifetime and managed ARM Node fixes are recorded in the [reading-list receipt](evals/history/2026-09-27-reading-list-resume.json). | Full GUI permission roundtrip and representative end-to-end use remain unqualified; mechanism checks do not close the coding gate. |
| Useful context tier and endurance | Public 49,152 context; current private source selects 96K with the same 16 GiB ceiling and host guard. Earlier 96K had only a synthetic screen; 128K encountered host pressure. No matched useful-tier comparison or 45–60-minute green active run. [Task12 evidence](evals/history/2026-09-27-task12-private64-failed-long-workflow.json), [latest limits](evals/history/2026-09-27-reading-list-resume.json). **Unqualified.** | Light 96K smoke, then compare feasible tiers on representative coding/UI work and sustained active work. Keep guard and rollback. |
| Independent holdout | A prior second-account run used an unrelated project's account. Those observations are [excluded from KRYN qualification](evals/history/2026-09-27-unrelated-account-scope-correction.json). **Unqualified.** | Explicitly KRYN-owned isolation with evaluator answers, private user state and other projects inaccessible to the candidate. Do not reuse that account. |

The next blocker is bounded coding/UI completion with truthful evidence and restart continuity. Useful-tier, endurance and isolated clean-install gates follow. No gold-master, frontier-equivalence or statistical harness-uplift claim is supported.

## Update awareness

Current source checks for newer published KRYN tags through the existing checksum-verifying release downloader. The idle-time dialog and `/update` show the exact release version, wheel-manifest source commit and short release-note excerpt. Same-version private builds and unbuilt main commits are never advertised as updates. Checksum verification uses GitHub distribution, not independent signing or application-quality qualification.

Current source offers **Update and restart / Later** for a verified newer published release. Acceptance exits the native client, rechecks the exact tag and wheel hash, installs through the existing transaction, then resumes the project. Active turns defer the dialog. Offline tests cover this handoff; installed TUI acceptance and a real future-release activation/rollback are still unqualified. `kryn rollback` remains the recovery path, and pinned OpenCode is not independently updated. Public release pause remains in force.

The [prior update-awareness receipt](evals/history/2026-09-27-update-awareness.json) records offline failure/version/idle/dismissal checks, anonymous verification of the actual v0.1.10 wheel, and an isolated OpenCode 2.0.10 TUI test with a synthetic future release. New offline handoff checks cover exact-hash revalidation, client exit and resume arguments. They do not prove that the installed TUI can close, activate and restart against a real newer release. Those lifecycle checks remain gates.

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
