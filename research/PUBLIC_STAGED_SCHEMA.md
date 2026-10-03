# Public staged-schema development screen

This is a development-only, single KRYN-arm screen of a three-turn coding task.
It cannot be counted toward the protected holdout, H1, or long-horizon acceptance.
The Task12 draft was exposed to the model and is retired from the future sealed
roster. Released v1.0.0, its guard, and the installed profile were unchanged.

The candidate edited `migration.py` as a target schema changed from v2 to v3 and
then gained a user note. The frozen protocol required two native compactions, an
OpenCode server restart, source checks, and an independent Docker grader after
each stage. The candidate workspace was on a separate APFS volume; only two
allowlisted regular files were copied into a host-visible grader workspace.
An initial zero-model preflight failed because Docker Desktop could not bind
mount that APFS image path. A separately preregistered host-copy preflight
passed, and the live run used that path. Both preflight receipts were retained.

The live 9B run completed three model turns, two compactions, one server restart,
and 13 model requests in 119 seconds. The final session export records 12 tool
calls, 21,508 input tokens, 4,232 output tokens, and 53,248 cache-read tokens.
Stage 1 and 2 passed independent grading.
The unchanged resource guard did not stop it; sampled pressure remained normal
and swap did not grow. The stage-three frozen grader returned FAIL. The complete
raw receipt is preserved, including that failed result, tool traces, copied
source hashes, guard samples, and the grader traceback.

Post-hoc review found a criterion mismatch, so the quality result is
**inconclusive**, not a demonstrated worker failure or a retroactive pass.
Stage three asked that a v2 record lacking `timezone` upgrade to v3, and the
target schema lists `active` as required. The candidate returned `active=True`
for an input lacking it, preserving the behavior introduced in stage one.
The grader's exact equality instead required `active` to be absent. The model's
first self-test made that same overstrict assumption and failed; its corrected
second self-test passed. An independent Docker probe reproduced the candidate's
output and verified that the input record, target bytes, and user note were
preserved. The model could not read the hidden grader.

An owner-only, **zero-model** oracle correction uses a schema-valid v2 input
with explicit `active=False` and checks that it remains false while `timezone`
is added. This admits the reference and the observed candidate implementation,
and rejects both the seed and a mutant that omits the timezone default. It does
not change the frozen FAIL. No attempt on this task is eligible for protected
scoring, and no product change is promoted from it.

Owner-only evidence is under
`~/Documents/Codex/kryn-research-private/experiments/staged-schema-public-20261003/`:

- `LIVE_SOURCE.json` SHA-256 `2b126729e0cb55d962cc3074de222fbbb24fd504b184f4e972a264875de55f4c`;
- frozen `result.json` SHA-256 `bdc9bc189455f9887afbff7e93c0227254288fe0f7024c52e17c3e3c2b1039b1`;
- post-hoc `REVIEW.json` SHA-256 `9ec0e3a67eafa12ff837c6325b535db6f1c4839a2a114e102a900f9636d8b497`;
- raw `RECEIPTS.json` index SHA-256 `8e88bb632b59d06841615fbd714685d9081fc80833fb198b1f45b16b0deebf25` (three verified archives, 93 files);
- corrected oracle preregistration `ORACLE_V3_SOURCE.json` SHA-256 `8d1ac1dc46c56453381281730c9d452a23299d2d106d68909fa42de0168b2b31`;
- zero-model corrected oracle `ORACLE_V3_RECEIPT.json` SHA-256 `004808521f2a0ddcb83f94f75cc3e4403c0e5df5fdd4f0cb79453a446ad114bb`.

The source and archives are private because they contain task/grader material.
The public research index records their digests and classification. A fresh,
unexposed staged task with an independently reviewed oracle is needed before
long-horizon quality can be scored.
