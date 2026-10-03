# Protected-holdout boundary correction

Frozen 2026-10-03 before changing the research sandbox. This is a research
isolation gate, not a product release or a holdout score. The previously
recorded direct-path/symlink preflight is insufficient: a trusted-parent
hardlink to a hidden oracle on the same filesystem, placed inside the allowed
workspace, can be read by the current candidate sandbox. A no-model local
canary reproduced that access. No protected task has been run or claimed.

**Hypothesis B1:** placing the grader on an encrypted APFS volume with a
different device ID, keeping its passphrase outside candidate argv/env/files,
and denying metadata as well as data reads in the whole-process Seatbelt
profile closes the tested alias paths while preserving OpenCode startup and
ordinary workspace reads. This changes only the research candidate's read
boundary and the boundary preflight. It does not alter the installed product,
model, resource guard, agent policy, grader, or any prior trial.

The acceptance screen is fixed before implementation:

1. A same-volume control must expose the hardlink weakness and fail the
   protected-boundary verdict. An encrypted separate-volume canary must show
   different device IDs, verify APFS image encryption, make a hardlink
   impossible, and deny direct, symlink, copy, `file://`, metadata, device and
   backing-image reads from the actual `background_boundary()` profile.
   Ordinary workspace reads must still work. Cleanup must detach the image.
2. Launch the pinned OpenCode server inside that exact hardened whole-process
   profile, with its real dependency allowlist, and verify the local API starts
   without a model request. Then run one disposable public fixture through the
   same sandbox while a fake hidden oracle is mounted. Candidate tool calls
   must be unable to read the oracle, and independent public grading must
   still work. This is a compatibility/security screen, not holdout evidence.
3. A real protected holdout remains closed until 30 fresh tasks, hidden
   oracles, clean seed failures, reference passes, partial-patch failures,
   exact hashes and a frozen roster are verified before candidate tuning.
   The candidate process and descendants must have no readable path or
   reachable service containing the grader. Any task exposed for debugging
   is retired from sealed analysis.

If the hardened profile breaks the real server or any oracle alias remains,
reject the candidate and keep all holdout results labeled development. An
encrypted image canary alone is not proof of a complete information boundary;
the full candidate process and task runner require separate verification.

## Completed boundary and public compatibility screens

The research boundary source was frozen and pushed as
`262f779811dcbc0bcc3fbf4037ebba6f0ca6c9a7` before the model call. The
profile now denies `file-read*`, explicitly allows metadata on dependency
ancestors needed by Python realpath, and adds the configured Node executable
to the isolated research runner's exact dependency list. The installed v1.0.0
profile and ordinary foreground shell boundary did not change. `make check`
and clean package smoke passed on that commit.

The no-model same-volume control failed as intended: direct and symlink reads
were denied, but a trusted-parent hardlink in the allowed workspace returned
the oracle bytes. The encrypted APFS image used a different device ID; its
canary passed workspace-read, encryption, hardlink-impossibility, direct,
symlink, copy, `file://`, metadata, raw-device and encrypted-backing-file
checks. The pinned OpenCode 2.0.10 server started in the same hardened profile
and loaded `kryn.product` with the external runner's dependency configuration.
The image detached cleanly. These probes are executable with
`python3 -B research/check_holdout_boundary.py same-volume` (expected exit 1)
and `python3 -B research/check_holdout_boundary.py encrypted-volume`
(expected exit 0). The negative control must also report
`negative_control_exposed: true`; exit 2 means the control itself failed and
cannot be counted as proof of a hardlink leak.

The preregistered public compatibility task then ran via
`research/run_boundary_public.py` with a fresh encrypted oracle mounted for
the entire Agent turn. The broken seed failed and the separate reference
passed the sandboxed independent grader before generation. The local model
made a one-line `len(values)` → `sum(values)` patch, the native Agent turn
completed in 85.707 seconds without intervention, and all three hidden-on-
volume cases passed after generation. The exact patch SHA-256 was
`0469ac99a377288e0d333a2368af9223bc17d5cdb56433a37ca087b55eaaafe2`.
The turn made 21 inference requests. The unchanged strict resource guard saw
normal sampled pressure, 0 sampled swap growth and AC power; its owned
sessions and runtime settled. The oracle image detached after grading. Raw
evidence, source checkout, encrypted image and a 58-file SHA-256 manifest are
under `/private/tmp/kryn-boundary-public-20261003-01/` on this Mac; the manifest
hash is `886318d070d7abfa4794c98e664501579e204cd8a0af17a11ba19bc07fab068d`.

The first script reported a pass, but independent review found defects that
invalidate that provisional public-workflow verdict. Its raw receipt remains
useful for diagnosis; the correction and later results follow.

## Independent-review correction before any protected task

Review of the first public receipt found that its model-side Python checks all
failed because the research PATH selected Apple's `python3` shim. It also found
that the public grader put `reference.py` inside its own candidate-readable
private root, that candidate stdout and descendants were not bounded, and that
the no-model canary could report success before image detachment. These are
public compatibility and grader-integrity defects, not a protected holdout
result. The one-line patch passed the independent cases, but the full prompt's
"run a check" requirement was **not** met; the earlier `passed` flag overstates
that turn.

The correction is fixed before repeating the model call: use the canonical
interpreter directory in the research PATH; place the reference on the
different-device encrypted volume and allow its exact file only for reference
preflight; bound candidate grader output and kill its process group; make
detachment part of both verdicts; and deny run-root listing while proving a
visible read and hidden read denial through the real OpenCode shell API. The
repeat must demonstrate a successful model-side Python check as well as the
independent grade. The first receipt stays available and is not silently
reclassified. These changes do not alter installed v1.0.0, H1 thresholds,
candidate task answer, model or resource guard.

The repaired encrypted-volume canary passed direct and alias denials, denied
listing the run root, and used OpenCode's `/api/shell` to read an allowed file
and fail to read the oracle. The same-volume hardlink control still failed as
intended. The candidate grader rejected a deliberate reference-file read and
oversized output; a spawned child was killed before grading returned. The
research PATH now permits `python3` through the canonical interpreter path.

Two fresh public turns preserve the mixed evidence:

| Run | Pinned source | Agent result | Independent result | Executable verdict |
| --- | --- | --- | --- | --- |
| `02` | `0cbbba579f0bb0754e7c9e1350f42b15514fe180` | Completed; `python3 solve.py` exit 0 on four sample arrays | Hidden cases pass; image detached | FAIL: receipt parser raised after grading because it looked for the shell exit in the wrong event field. Raw evidence supports the check and grade but the executable did not finish cleanly. |
| `03` | `5dbfbaef861bc5d7979ccd4c5fb11709322701dc` | Completed; its own object-shaped Python samples exited 0 | FAIL: it changed the pre-existing JSON array input into an object input; image detached | FAIL: the corrected runner returned a valid failed verdict. |

The `02` patch hash is
`0469ac99a377288e0d333a2368af9223bc17d5cdb56433a37ca087b55eaaafe2`;
the `03` patch hash is
`312a6868de7265caf54229d71c753c7d97990645e05b3c3c972af02ab2bf13f7`.
Raw receipts and SHA-256 manifests remain under
`/private/tmp/kryn-boundary-public-20261003-02/` (manifest
`adf6efc1f37303def135dbbd1ee71f76ba2f6d3edf91d53f7e911e962243afc4`)
and `/private/tmp/kryn-boundary-public-20261003-03/` (manifest
`9ef4d1b10e35214766c904290314cf52c9c19f80bc295030026fd4c85629d88e`).

**Boundary mechanics pass the current no-model and OpenCode shell probes; the
public model workflow has mixed results and no clean executable success on the
repaired runner.** No sealed holdout result exists. These selected alias
checks do not cover every macOS information channel. A frozen 30-task roster,
browser/source-gateway boundaries, broken-seed/reference/partial-patch
controls and exact hashes remain prerequisites before protected H1 analysis.
The three public turns measure neither a success rate nor frontier-agent parity.

A fourth fresh public turn on merged source `aad56ec` used the repaired parser.
It was stopped by the unchanged sustained-host-warning guard during the first
model request, before a tool call or patch. The sampled pressure rose from
normal to warning twice in succession; swap growth was zero, and the owned
session and runtime settled. The boundary/seed/reference checks passed and the
oracle image detached. This is an occupied-host fit failure, not a coding
outcome or a reason to weaken the guard. The raw receipt is
`/private/tmp/kryn-boundary-public-20261003-04/`; its 56-file manifest SHA-256
is `22ad1a7b739c7e1456ff3c46d5cc71db1499ccfe1ddbb74ea9eb00982ac9a810`.
No identical retry is scheduled.

## Candidate-volume alternative, no-model screen

The 30 new task drafts prompted a second isolation layout. The candidate Git
workspace and its OpenCode temporary directory can be siblings on a disposable
APFS volume, while private grader material stays on the host volume. This makes
same-volume hardlink aliases to the grader impossible without keeping a mounted
grader volume during the Agent turn. The research-only `private_parent` option
in `NativeServer` requires those siblings to be on a device different from
`/private/tmp`; ordinary product runs retain their original temporary layout.

`python3 -B research/check_holdout_boundary.py candidate-volume` passed a
no-model canary on this Mac. It verified different device IDs, direct/symlink/
copy/metadata/file-URL denials, impossible trusted-parent hardlink, denied
candidate hardlink, denied raw device and image reads, denied run-root listing,
visible workspace access, a working `python3` through OpenCode's real shell
API, hidden-oracle read denial through that API, active product plugin, and
successful image detachment. The same-volume control still exposes the alias.
This is a boundary mechanism test, **not** admission of the 30 draft tasks.
The eventual protected runner must compare each real grader's device ID to
the candidate workspace device, prove the grader is outside all readable
dependencies, and rerun the real path/alias canary. Supplying
`--private-parent` by itself does not establish that separation.

Independent draft review found that 12 of the second task author's graders
initially imported candidate code into the privileged grader process. The
revised offline draft runs those probes in pinned, networkless Docker containers
with bounded output and lifetime; its 15 seed/reference/partial controls pass.
Every task remains protected-ineligible: three browser tasks need a qualified
model-facing browser gateway, three long-workflow and three restart tasks need
real staged model turns, and three external-information tasks use synthetic
sources rather than current external information. The three error-recovery
drafts have not run through the real candidate-volume grader path. Offline
Playwright and Docker controls do not establish protected model results.
The local Chrome process aborted in macOS application registration under the
whole-process research profile, before navigation. No browser task is scored
as a protected model result on this basis.

An alternative no-model probe downloaded Playwright 1.55.0's dedicated
Chromium headless shell (build 1187) into a disposable `/private/tmp` cache.
Its first launch was correctly denied because Playwright tried to create
artifacts in the host temporary directory; after redirecting `TMPDIR`, `TMP`,
`TEMP`, and `HOME` to the candidate-private volume, the launch did not finish
within 20 seconds. No matching process remained after timeout. This does not
qualify a browser gateway, and a repeated prompt/flag tweak is not treated as
an acceptance path. A separately isolated browser service or a different
audited browser channel would need its own hidden-file and navigation checks.

## Private Python draft preflight

The separate Python draft has 15 synthetic tasks across repository bugs,
multi-file features, API compatibility, persistence and refactoring. Its
original `/private/tmp` manifest SHA-256 was
`b0c36b7fc82e67bbb5d132aa045f01bc3c18eb13c5607e109d0e2ccd2d7b50de`.
The original durable owner-only copy is under
`/Users/pranav/Documents/Codex/kryn-research-private/python-draft-20261003`;
its manifest SHA-256 is
`08aa7a5da0d4b56efe94136294fdf929e1e11696cdb0c43fe73d518f97bd4603`.
All seed/reference/partial, direct-import, omission, output-limit and isolation
controls passed offline. Four task-specific coverage limits remain flagged in
that original private manifest. The `linecfg-duplicate-key` task was exposed during
development calibration and is retired; the remaining Python tasks have not
been used in model turns.

A later owner-only v7 offline draft is frozen at
`/Users/pranav/Documents/Codex/kryn-research-private/python-draft-v7-20261003`
(manifest SHA-256 `0431ca91cc2dcab0448aec8107e3835bcd3cab3aa0eb924b322b100237d6d0a3`,
freeze receipt SHA-256 `b31097edd384f7b1ba4f98ea64c81e6ba859fb3f8e272fe21f1ab24060c036e2`).
All 15 seeds and partial patches fail; all 15 references and five valid
alternatives pass; 19 wrong-solution mutations and four omissions fail. An
independent read-only review verified that the tokenizer probe checks tuple
type and arity before JSON conversion and the amount parser compares invalid
errors to a trusted baseline under the same pinned sandboxed interpreter.
These are sampled controls, not exhaustive semantic proofs. Journal recovery
after physical power loss remains untested; the exposed duplicate-key task
remains retired. Every v7 task still has `protected_status=false`, and no v7
model or real Agent-to-grader turn has been scored.

At clean research commit `682f9b3268beca203cf35b81877cb86d764f3251`,
the current-source **no-model** `preflight_protected_python.py` was run once for
each of the 15 frozen v7 tasks. All 15 passed its seed/reference/partial and
real OpenCode candidate-volume boundary mechanics in both KRYN and native
arms, with matching input hashes, a pinned Python/rg/pytest/Git environment,
hidden oracle/reference/manifest and unlisted loopback denial, and proved
image detachment. No model request was made. Fourteen returned `passed=true`;
`ledger-journal` correctly returned `passed=false` despite passing mechanics
because its frozen scientific flag says physical power-loss recovery is
untested. This does **not** upgrade any manifest `protected_status`, seal the
combined 30-task roster, prove model-facing browser work, or count as an H1
trial. The third persistence slot still needs a fully qualified task or a
justified change to the preregistered roster before sealing.

The full receipts are retained in an owner-only archive outside the public
repository.
The summary SHA-256 is
`08898eca87c2daba919ad59f7bdb849e54e4c6dd4dad2a271d32e7a3f5e6f7f8`,
and its 15-report archive index SHA-256 is
`a2782563af202ce346aa8c7100f296870421a3c235e904b0d09cd0a1e381be50`.
The compact public entry is
[`history/protected_preflight.jsonl`](history/protected_preflight.jsonl).
To repeat one task with a fresh receipt name on this Mac, use the v7 draft
directory, a manifest task ID, the existing pinned tool venv, and the command
shown below for `linecfg-leading-bom`:

```sh
/opt/homebrew/bin/python3.14 -B research/preflight_protected_python.py \
  /Users/pranav/Documents/Codex/kryn-research-private/python-draft-v7-20261003 \
  linecfg-leading-bom /private/tmp/a-new-v7-preflight-receipt \
  --tool-venv /private/tmp/kryn-python-tools-v2-20261003
```

`research/preflight_protected_python.py` verifies one real task with its
candidate checkout and private temp on a fresh disposable APFS volume. It
checks exact prompt/grader/reference/partial hashes, a clean seed, all private
files on another device, impossible answer hardlinks, direct Seatbelt probes,
the native OpenCode shell API, expected seed/reference/partial outcomes and
image detachment. A `passed=true` receipt requires a clean committed research
tree. It issues no model request. The copied Python/ripgrep/pytest and CLT Git
environment is an explicit dependency for both arms; its final no-model
preflight passed all 15 drafts from clean `2ce1309`. Example on this Mac:

```sh
/opt/homebrew/bin/python3.14 -B research/preflight_protected_python.py \
  /Users/pranav/Documents/Codex/kryn-research-private/python-draft-20261003 \
  linecfg-interpolation \
  /private/tmp/kryn-python-preflight-new-receipt \
  --tool-venv /private/tmp/kryn-python-tools-v2-20261003
```

The exposed `linecfg-duplicate-key` task is retired from sealed use. The
development-only model calibration and exact receipts are in
[PYTHON_CALIBRATION.md](PYTHON_CALIBRATION.md).

Even a passing task preflight is not a protected H1 trial: the 30-task roster,
all category-valid graders, paired model turns and independent scoring remain
separate gates. The private draft and raw receipts stay outside the public
repository and runtime package.

## Persistence-slot replacement draft

The frozen v7 journal task and its physical-recovery flag remain unchanged.
An owner-only **new** persistence draft was built for that category slot; its
manifest SHA-256 is
`1f61ee77dc6008ce469b52765ee97f636fccf455e2c3a87e004ffb4efce65e02`.
Its seed and incomplete patch fail, its reference and a structurally different
valid implementation pass, and five wrong-solution variants fail. The control
receipt SHA-256 is
`68ccc93665ecd077e5f35a47c3694257baae9e5a32a790df74f01c7534250b1e`.
At clean source `57a92beadcfc1481c2ce047a47158bef0c237010`, the same
current-source no-model task preflight passed its real OpenCode KRYN/native
boundary and grader controls, with normal volume detachment. Its report
SHA-256 is
`919bf34cd2d7bf1470486fa928f7771fa30937e9bc4b58459dbd747373db105e`;
the verified owner-only archive index SHA-256 is
`acf4dd1fe563156e407de692468f4e48669f3b40d1603507d733eace694b3bac`.
The compact [history entry](history/protected_preflight.jsonl) discloses no
prompt, oracle, reference or task ID before roster sealing.

This gives the Python side 14 v7 draft slots plus one mechanically passing
replacement slot without clearing the journal flag. **None** has been
admitted to a sealed combined roster or exposed to a candidate model as a
protected task; every private manifest still says `protected_status=false`.
An independent oracle review, the remaining non-Python categories and the
actual 30-task Agent-to-grader study are still required. The Python tasks
also share only three repository families, so they cannot stand in for 15
independent repositories.

## Persistence draft oracle correction

An independent read-only audit found that the v1 replacement reference failed
one of its own malformed-record error requirements, while its oracle omitted
that case. Its manifest and preflight receipt remain unchanged. A new owner-only
v2 draft makes the contract explicit, corrects the reference, adds the missing
oracle branch and an error-specific negative control. The v2 manifest SHA-256
is `8eb5fab22cf02158a19314272410068797a942858c4220e8ad450f098baf7bbf`.
Its seed and partial patch fail, the reference and a structurally different
valid alternative pass, and six targeted wrong variants fail. No candidate
model has seen either draft.

On clean merged `main` at `7728c8e380c58726fc74df238363a0c3e01cf18f`,
the corrected draft passed the current-source no-model KRYN/native preflight:
exact task hashes, separate-device grader, hidden-file and unlisted-loopback
denial, seed/reference/partial controls, and candidate-volume detachment. The
report SHA-256 is
`0c1d0d76931471d9a25d31baf9258ac229edda922d583996d91809d2d3e19d6e`;
the owner-only archive index SHA-256 is
`cdcb0e77b573ee8818df5954a48c9ae4184adf1087c401f75d20078b4b0b3149`.
The compact [history entry](history/protected_preflight.jsonl) omits the prompt,
oracle, reference and task ID. This corrects one independently identified
defect, not a broad oracle-completeness proof or protected admission. Every
private manifest still says `protected_status=false`; the combined roster,
non-Python categories and real paired Agent turns remain open gates.

## Error-recovery draft oracle corrections

An independent no-model audit of the owner-only `06-verified-restore` draft
found that its grader accepted a mutation selecting the **oldest** valid
snapshot: the original test supplied only one valid snapshot, so it did not
measure its newest-valid requirement. The old draft and its manifest remain
unchanged. A separate owner-only replacement clarifies that snapshot filenames
encode creation order, then tests two valid snapshots whose filesystem mtimes
point in the opposite order, followed by corrupt and malformed newer files.

The old-oracle wrong-oldest pass is reproduced by private receipt SHA-256
`c74061a7c9810f53ce500c2693e519b368e2ad78d2219dc0798f04f39a9394ef`.
With the corrected oracle, the seed and partial patch fail, a reference and
structurally different implementation pass, and four targeted mutants fail:
oldest-first, mtime-first, digest bypass and in-place write. The eight-control
receipt SHA-256 is
`11b1ed063f2bb80b79ae8408ce5c68de199d0363456a5a02589e16fd260d0f37`;
the 16-file owner-only archive index SHA-256 is
`3cb02fbf87d113c0f19705d3ce3153abd1c6e671530b677cab76a32d3eb2e7c6`.
Its compact [history entry](history/ui_gateway.jsonl) discloses no task prompt
or oracle. This is a stronger **draft**, not protected admission: no candidate
model request, real OpenCode boundary, 30-task roster seal or paired grading
was performed. Its manifest still says `protected_status=false`.

A second audit of the owner-only upload-retry draft found its grader accepted a
mutation that passed a **negative** retry delay to the injected sleep callback,
despite the prompt's nonnegative-delay requirement. The original oracle also
required exact error-message text absent from the task contract. A separate
replacement tests negative delay and rejection of 302 as a 2xx success, while
accepting a structurally different implementation with different error text.
The old-oracle mutant pass has private receipt SHA-256
`a4734531922e23c26d89b9d31500c14bf23d137555aea76aa32025b2a93736d7`.
The seed and partial patch fail, reference and alternative pass, and negative-
delay, redirect-as-success and two-try mutants fail in the new seven-control
receipt, SHA-256
`8b62d8013d37964c3800f4e34bf32e1565f5b1b5eefa0716638f576399c80c31`.
The 16-file owner-only archive index SHA-256 is
`74e26492df7f7b73271ea7f845032af27d8f6927fc3e4fbfa1ffe9aaf014a6dd`.
Its [history entry](history/ui_gateway.jsonl) contains no hidden prompt or
grader. This also remains an unsealed no-model draft with
`protected_status=false` and no real candidate-volume admission.

The third error-recovery slot had a similar gap: its mailbox grader accepted a
reference mutation that quarantined malformed line 1 only. A separate owner-
only replacement makes checkpoint and quarantine JSON shapes explicit and
tests two malformed positions, ordered delivery, callback-failure resume and
deduplication after checkpoint rewind. The original mutant pass has private
receipt SHA-256
`8eb77cf02ccb17db2f1455ecae1a107455cd6875d608ebd5cab8ad764d5442ba`.
The seed and partial patch fail, reference and structurally different
alternative pass, and index-one-only and duplicate-quarantine mutants fail in
the new six-control receipt, SHA-256
`4bc902d10790b14baac7e7ee3e36c39da0e6ea8e942b08c8d3e25d9b4d27fd54`.
The 16-file owner-only archive index SHA-256 is
`417ec569e52aa92136d1cc7a8de4f0ba58d04f56596adcbe767d4906ffaaf260`.
Its [history entry](history/ui_gateway.jsonl) also omits the hidden prompt and
grader. All three corrected recovery slots remain unsealed and unscored; these
targeted controls do not establish complete oracle coverage.

## Real OpenCode boundary preflight for the recovery drafts

At clean research source `7af7eac514cec1c6bedaac658d3da7aff1c88f0b`,
`preflight_recovery_draft.py` ran the three corrected owner-only drafts without
model requests. Each used a disposable APFS candidate checkout, the real native
OpenCode shell in both KRYN and minimal-control configurations, and the pinned
Python/ripgrep/Git tool environment. For each task, 14/14 direct boundary
checks and 18/18 OpenCode checks **per arm** passed: hidden oracle, manifest,
reference, partial and validation bytes were denied, while ordinary candidate
reads and tools worked. The candidate volume detached before trusted grading.
Fresh, separate Docker-visible checkouts then reproduced the frozen seed fail,
reference pass and partial fail, including the expected output hashes. The
three successful no-model receipt hashes are:

| Draft slot | Receipt SHA-256 |
| --- | --- |
| Restore | `ec0a5ec04489beb9cb248262e27231dc410b51272e70429b0a132e5fefe9a6da` |
| Upload | `5af2dae2d5cc92a76d537722d63ef85e625aae756b3cfdbb9bebf55fb9d5416d` |
| Mailbox | `aaaf327610f37747c0889bc700cc261b3f1861b03d75a4bb88d7003020284704` |

The first passing triplet at `0b0a554` is retained in the append-only
[history](history/ui_gateway.jsonl). The later input-alias check rejects
symlinked or escaping draft paths and seed symlinks; all three tasks passed
again at `7af7eac` without a model request.

The failed restore preflight receipts are preserved too:
`1c5e1f675f0223d4c674a31b132880fc116e478b5102a162bdaba0afe90f4eb3`
tried Docker grading directly on the nested APFS candidate mount; its reference
file was invisible to Docker and the image stayed busy until a separately
verified manual forced detach. Receipts
`3ca91a5e5bff2403ebe6529b728036d4567ff747ebd1ba856207ef6f531a1e9f`
and `97e6f2570d98bee4b651cacdf2255b209caaf2d755eefdc564fc055769aa2ab3`
used a reused grading path after the first Docker bind; Docker did not see the
subsequent Git patch. Both detached normally. A fresh checkout per control,
patched before Docker's first bind, resolved this file-sharing artifact. No
candidate volume or probe container remains mounted/running from these runs.

This advances **boundary and grader-control mechanics only**. The corrected
drafts retain `protected_status=false`. The production Agent-to-grader runner
still creates a separate APFS *grading* volume; Docker's visibility of that
actual handoff has not passed, so these receipts cannot admit the recovery
tasks or count toward H1. Independent category/oracle review, the sealed
30-task roster, paired model turns, and unseen task acceptance remain open.

## Replacement context/restart draft

The public staged-schema task in [PUBLIC_STAGED_SCHEMA.md](PUBLIC_STAGED_SCHEMA.md)
is retired after model exposure and a mismatched final oracle. A fresh owner-only
replacement draft was created for that category. Its first frozen oracle passed
a wrong-solution mutant; that draft and its no-model receipt are preserved, then
a versioned replacement corrected the criterion. The corrected draft's seed
fails all three staged checks, a partial implementation passes only stage one,
the reference and a structurally different valid implementation pass all
three, and two targeted mutants fail at the expected stages. This is sampled
oracle control, not a claim of complete semantic coverage.

At clean `main` commit `7b2e7c04800f1807969349d30e6ec09575707ef3`, a
separate **zero-model** preflight tested the corrected draft in the real
candidate-volume layout. Its first run passed all 14 direct boundary checks
and all 16 OpenCode checks in each arm, then failed before grading because
the host-copy parent directory was missing. The candidate volume detached.
The single path-creation repair was preregistered; the fresh second run passed
those same checks, copied only three bounded regular files to a Docker-visible
host workspace on another device, detached the candidate volume, and passed
the independent reference control. Neither run contacted the model. The
replacement remains `protected_status=false`: independent admission review,
the complete 30-task roster, real model-facing staged turns, and paired H1
grading remain open.

The owner-only source and receipts are archived outside the repository. The
rejected v1 freeze SHA-256 is
`c08a71768e17bee8c475e479ec009e0486b98fe351dd74c8a1166938c1fc50d5`;
the corrected v2 freeze is
`42071dd5a1d5e534ed706ca083aee4af5f31e6d13e69b1150520e8392cf20d04`.
The corrected six-variant, three-stage control receipt is
`b9fd1fd215400c3701180c5c7d68750b4586201506e31b5c989e536324a70e7f`.
The two verified preflight archives have an owner-only index SHA-256
`a89baff8da27c82f239645cc4ec8338ffe477cea925c421c95e8382229b531ef`;
the failed and passed result SHA-256 values are respectively
`a73d639940f1513297d375db9725e8675f1d3024657b6539090d5ccf0dcffbab`
and `6f011f668b9e3b19f8d624649299bd3e5fe08927e9c88dee1336efc2e965d71a`.

## Official-source external-information draft

An owner-only replacement for one fictional external-information slot now uses
a pinned current official documentation snapshot. No candidate model has seen
the task. The first oracle incorrectly accepted a wrong implementation that
placed a timing-safe comparison in dead code; its frozen draft and failed audit
remain archived. A runtime-call check then accepted a second wrong
implementation that made an irrelevant comparison before using ordinary
equality. The corrected draft adds a forced-false comparison probe. Its seed,
partial solution, and four targeted wrong variants fail; a reference and a
structurally different alternative pass the networkless, read-only Docker
grader. These controls test sampled behavior and do not prove exhaustive
timing security.

At clean `main` `90a3fa84a81022490919337d8702a9e1adba74bf`, a zero-model
preflight cloned the frozen seed onto a disposable candidate APFS volume. All
14 direct boundary checks and all 21 real OpenCode checks in **each** native
and KRYN arm passed. Both arms read the exact pinned source through their
shell API; source writes, private-sibling reads, hidden-grader reads and
unlisted loopback were denied. The source and provenance hashes were
unchanged. A bounded host copy of the reference passed independent Docker
grading after the candidate image detached. This is source-channel and oracle
mechanics only: it does not prove the native Agent selected and read that
source, admit a protected task, seal the combined roster, or measure H1.

The owner-only corrected draft freeze is
`a51edabc8a8b546199d6f322917f57c49f372995b6f3f042ce2053d1bdbdf953`;
its eight-variant validation receipt is
`c8392d520332b1825cf411ef923f7969f3456eca491014ae2f9e9f758bb876c4`.
The no-model preflight result SHA-256 is
`153a13bfd6c8dedaa5142a69e3b7e88752ea16ac90666e6cd6e8f5f692488b77`;
its verified archive index is
`43d94128ca70296ddcdcebb69f08626797d5bb772ef5d24a0e62330234a87eff`.
The draft remains `protected_status=false` pending independent admission
review and the remaining category gates.
