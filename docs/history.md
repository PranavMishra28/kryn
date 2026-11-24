# Historical evidence

[Current status](../plan.md) owns today's decisions. Primary receipts, including failed results, remain in [`evals/history/`](../evals/history); frozen evaluation inputs remain under `evals/`.

The superseded narratives are preserved in immutable Git history at `84eb07fffc095dd39545b862936d3d471b8a1e8e`:

- [Complete historical execution ledger](https://github.com/PranavMishra28/kryn/blob/84eb07fffc095dd39545b862936d3d471b8a1e8e/plan.md)
- [Former README and trial narrative](https://github.com/PranavMishra28/kryn/blob/84eb07fffc095dd39545b862936d3d471b8a1e8e/README.md#configuration-and-release-scope)

The detailed September 28–30 gate narrative replaced by the concise current status is preserved at [commit `26cc908`](https://github.com/PranavMishra28/kryn/blob/26cc908/plan.md).

The autonomous-gate table and final model-screen narrative preceding the supervised-v1 decision are preserved at [commit `aef8188`](https://github.com/PranavMishra28/kryn/blob/aef8188/plan.md). The current [supervised gate table](../plan.md) does not erase those failures.

These pages are historical evidence, not current instructions. Their dated next actions, installed revisions and references to an unrelated account are superseded by current status. Read either locally with `git show 84eb07f:plan.md` or `git show 84eb07f:README.md`.

The navigation cleanup verified that all 93 distinct receipt destinations linked by those originals still exist, and that every original `evals/history` file is unchanged. Duplicated narrative copies were removed from the current tree; no failed receipt or frozen fixture was removed.

On 1 October 2026, the owner retired eleven 0.1.x GitHub prereleases/tags and stale branches after saving release metadata, all release assets, a verified all-refs Git bundle and archived dirty worktrees outside the public repository. On 2 October, the [v1.0.0 release](https://github.com/PranavMishra28/kryn/releases/tag/v1.0.0) passed its public installer check, so the v0.2.0 preview release/tag was retired after its wheel, installer, checksums, metadata and source commit were archived and hash-checked privately. Only `main` and `v1.0.0` remain public; historical commits and failed evaluation receipts remain in Git. The [final v1 qualification receipt](../evals/history/2026-10-02-v1-final-qualification.json) records the released scope and limitations.

On 23 November 2026, v1.0.1 was qualified and published from commit `8270896` ([receipt](../evals/history/2026-11-23-v1.0.1-qualification.json)). The anonymously downloaded release assets matched `SHA256SUMS`, and the README install command from a clean shell verified the installer pin and reported 1.0.1 active. GHSA-r7pr-6rq7-5qc7, GHSA-r3c3-r8jr-p4gh and GHSA-3w3x-jj67-49v4 were published with patched version 1.0.1.
