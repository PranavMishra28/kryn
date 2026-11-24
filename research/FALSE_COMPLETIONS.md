# False completions in the research log

An index, not a new experiment. A **false completion** is a run whose final
message claimed the work was done while an independent check (hidden grader,
official Harbor verifier, Docker oracle or development acceptance checker)
disagreed. This file lists every one documented in `research/*.md` as of
2026-11-23, with the line that records it. Nothing here changes a receipt.

Fifteen instances on ten tasks: nine from KRYN arms (the v1 plugin, rejected
candidates, or the development acceptance controller) and six from plain
OpenCode on the same Qwen3.5-9B-6bit model. These are counted instances, not a
rate: KRYN ran more trials, some experiments compared only KRYN variants, and
recording was not uniform across experiments. All tasks are development data;
none is a sealed holdout. Release-qualification observations outside this
folder, such as #277, are not counted.

| # | Task | Arm | What the check found | Record |
| ---: | --- | --- | --- | --- |
| 1 | Terminal-Bench log summary | KRYN v1 | `total,ERROR` 20151, expected 14160 | [HARBOR_CALIBRATION.md:77](HARBOR_CALIBRATION.md) |
| 2 | Terminal-Bench log summary | Plain OpenCode | `last_30_days,ERROR` 5991, expected 9594 | [HARBOR_CALIBRATION.md:164](HARBOR_CALIBRATION.md) |
| 3 | Staged slug task | KRYN v1 | distinct titles could get the same slug | [STAGED_CONTINUITY.md:151](STAGED_CONTINUITY.md) |
| 4 | Staged slug task | Plain OpenCode | suffixes started at 1, task said 2; reused a slug | [STAGED_CONTINUITY.md:152](STAGED_CONTINUITY.md) |
| 5 | Retired newsletter, stage two | KRYN, rejected post-edit signal | accepted `http:///missing` and `https://` | [STAGED_CONTINUITY.md:187](STAGED_CONTINUITY.md) |
| 6 | TaskboardLite Task03 | KRYN v1 | appended 61 lines to protected `test_existing.py` | [H1_PROVENANCE_PILOT.md:69](H1_PROVENANCE_PILOT.md) |
| 7 | TaskboardLite Task02 | KRYN, rejected C1 | equal start/end range wrong; own test deleted | [CACHE_ABLATION.md:90](CACHE_ABLATION.md) |
| 8 | Terminal-Bench polyglot C/Python | KRYN Fast, rejected W1 hook | compiled `cmain` left beside the sole allowed source | [WRITE_LOOP.md:80](WRITE_LOOP.md) |
| 9 | Task06 Cancel Edit | KRYN, development controller (control) | browser flow still failing after two repairs | [VERIFICATION_FEEDBACK.md:112](VERIFICATION_FEEDBACK.md) |
| 10 | Task06 Cancel Edit | KRYN, development controller (rejected V1) | browser and Cancel Edit flows still failing | [VERIFICATION_FEEDBACK.md:125](VERIFICATION_FEEDBACK.md) |
| 11 | Public rate-limit task | KRYN v1 | waits of 60 then 120 s; one 60 s wait allowed | [PUBLIC_SOURCE_RATE_LIMIT.md:74](PUBLIC_SOURCE_RATE_LIMIT.md) |
| 12 | Public rate-limit task | Plain OpenCode | same extra 120 s wait | [PUBLIC_SOURCE_RATE_LIMIT.md:74](PUBLIC_SOURCE_RATE_LIMIT.md) |
| 13 | Retired ledger task, matched pair | Plain OpenCode | `category_totals` never exported | [LEDGER_CATEGORIES_PAIR.md:111](LEDGER_CATEGORIES_PAIR.md) |
| 14 | Retired ledger task, replication | Plain OpenCode | `Decimal` used without import; grader `NameError` | [LEDGER_CATEGORIES_PAIR.md:183](LEDGER_CATEGORIES_PAIR.md) |
| 15 | Public pagination task, first pair | Plain OpenCode | stopped on empty data with a next link; missed `LiNk` | [PUBLIC_SOURCE_PAGINATION.md:82](PUBLIC_SOURCE_PAGINATION.md) |

Compact receipts that carry an explicit flag: `history/cache_ablation.jsonl`,
`history/harbor_calibration.jsonl`, `history/staged_continuity.jsonl`,
`history/verification_feedback.jsonl`, `history/write_loop.jsonl` and
`history/development.jsonl` (ledger pair and replication, pagination, rate
limit). Rows 5 and 6 are recorded in the notes only.

## Patterns

The grouping is editorial; a few rows could sit in two groups.

- **Missed an edge case** (rows 3, 4, 5, 11, 12, 15): the agent's own check
  passed and did not exercise the boundary the grader tested.
- **Never cross-checked the numbers** (1, 2).
- **Never tried the public API** (13, 14).
- **Changed the tests** (6, 7). Separately, the criterion-repair run deleted the
  338-line `test_backoff.py` after a grader pass; it is not a false completion
  because the grader accepted it ([CRITERION_REPAIR.md:68](CRITERION_REPAIR.md)).
- **Said done after being shown the failure** (9, 10).
- **Left the build behind** (8).
