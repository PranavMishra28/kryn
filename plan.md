# KRYN current status — 28 September 2026

**Public releases, tags and version bumps remain paused.** The published prerelease is [v0.1.10](https://github.com/PranavMishra28/kryn/releases/tag/v0.1.10), source `e9c90ff6fe41cae6ef17f7fecdd2e2adf2f54246`. The owner has a private guarded 96K build from `23b9876`; the prior private build remains available through rollback. Neither main nor a same-version private candidate is a public update channel.

`Implemented` means code exists; `mechanism checked` means a narrow test ran; `qualified` requires representative installed use. Recheck evidence after a relevant edit. A successful process, unit test, generated report or model claim is not application acceptance.

The [latest private activation](evals/history/2026-09-28-private23-report-gui.json) records installed source `23b9876`: clean wheel, rollback/reinstall, guarded inference smoke, deep doctor, and a narrow authenticated GUI permission roundtrip. The [prior gate receipt](evals/history/2026-09-28-green-quality-gates.json) includes normal terminal launch. These are owner-machine operation checks, not application-quality or isolated-install qualification. The [earlier activation](evals/history/2026-09-27-private96-final-install.json) tested rollback to 64K and the native `/update` current-status dialog.

[Use/install](README.md) · [Detailed controls](docs/usage.md) · [Develop/check](CONTRIBUTING.md) · [Evaluation contracts](evals/README.md) · [Historical evidence](docs/history.md)

## Active gates

| Gate | Evidence and current decision | Required next check |
|---|---|---|
| Public installation and recovery | Published v0.1.10 passed anonymous asset checks and existing-owner install/update/rollback/uninstall/reactivation, with guarded inference. [Release receipt](evals/history/2026-09-25-v010/qualification.json). **Narrow owner qualification only.** | Clean install and recovery in an explicitly KRYN-owned isolated environment. |
| Private owner operation | Installed guarded 96K/22 GiB source `23b9876` passed clean wheel activation, rollback to `f74b389` and reinstall, guarded protocol smoke and deep doctor with 2/2 tools connected. [Latest receipt](evals/history/2026-09-28-private23-report-gui.json). **96K remains experimental.** | Representative successful coding/UI use and sustained active resource checks on this source; preserve recovery builds. |
| Coding/UI completion and truthful continuity | New [Task02/06/12 trials](evals/history/2026-09-28-green-quality-gates.json) proved native children and two compactions on Task02, but Task02's resumed answer omitted a failed check. Task06 failed manual 503 retry. Task12 passed backend 2/2 and several browser flows, yet failed upload and filtered export before and after a bounded assisted repair; its fresh Reviewer misdiagnosed the upload failure. Plan/Build separation and native Task12 compaction passed, but Build and handoff timed out and checkpoint claims were wrong. Prior [Task12](evals/history/2026-09-27-task12-sliced-backend-ui-failure.json) and [reading-list](evals/history/2026-09-27-reading-list-resume.json) failures remain historical evidence. **Application-quality and semantic-continuity gates remain failed.** | Change approach after these repeated UI failures; prove one fresh frozen task with complete independent browser/source acceptance and truthful compaction/restart before considering promotion. |
| Native controls and lifecycle | Installed terminal launch, editable permissions, native model selection and local browser/search connections passed narrowly. An authenticated GUI Auto-accept toggle survived reload, then was restored; this used the source NativeServer adapter with installed config, not the `kryn --web` launcher. Fresh Explore/Reviewer children completed in Task02; Task12's fresh Reviewer was inaccurate. Independent read tools overlapped, but model generations remain serialized for memory safety. [Latest receipt](evals/history/2026-09-28-private23-report-gui.json), [controls receipt](evals/history/2026-09-27-controls-models-owner64.json). | Test installed launcher terminal/GUI handoff and representative end-to-end use; mechanism checks do not close the coding gate. |
| Useful context tier and endurance | Public 49,152 context. Installed private 96K uses a 22 GiB ceiling and host guard; the new long Task12 stages stayed locally routed with normal pressure and zero observed swap but failed application acceptance and reached only about 45K active input at the sampled step. Earlier [near-full synthetic probes](evals/history/2026-09-28-private96-memory-incident.json) and [73,728-token cold probe](evals/history/2026-09-27-private96-light-probe.json) retain their narrow scope. 128K previously encountered host pressure. No matched useful-tier comparison or 45–60-minute successful active run. **Unqualified.** | Compare representative coding/UI quality and warm correctness across feasible tiers; run successful sustained active work. |
| Independent holdout | A prior second-account run used an unrelated project's account. Those observations are [excluded from KRYN qualification](evals/history/2026-09-27-unrelated-account-scope-correction.json). **Unqualified.** | Explicitly KRYN-owned isolation with evaluator answers, private user state and other projects inaccessible to the candidate. Do not reuse that account. |

The next blocker is bounded coding/UI completion with truthful evidence and restart continuity. An [operator-only Task12 oracle](evals/history/2026-09-28-task12-operator-oracle.json) passed the frozen browser path after removing a duplicated client CSV parser/exporter, retaining the selected upload, and binding the edit ID correctly. The same source still exposes an inert Delete control outside those ten checks. This confirms the model-produced failure and the limits of a browser-only pass; it does **not** qualify KRYN. Useful-tier, endurance and isolated clean-install gates follow. No gold-master, frontier-equivalence or statistical harness-uplift claim is supported.

The [new Task06 and Task12 trial receipt](evals/history/2026-09-28-green-quality-gates.json) preserves the failed browser checks and inaccurate model-review claims. KRYN now rejects a multiline detached-server probe that had made a server appear live only during one shell call. That guard passed unit and package checks; an installed model-produced UI completion on this source is still unqualified.

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
