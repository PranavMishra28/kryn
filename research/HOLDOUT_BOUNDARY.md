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
private manifest SHA-256 is
`b0c36b7fc82e67bbb5d132aa045f01bc3c18eb13c5607e109d0e2ccd2d7b50de`.
All seed/reference/partial, direct-import, omission, output-limit and isolation
controls passed offline. Four task-specific coverage limits remain flagged in
the private manifest. No candidate model has seen these tasks.

`research/preflight_protected_python.py` verifies one real task with its
candidate checkout and private temp on a fresh disposable APFS volume. It
checks exact prompt/grader/reference/partial hashes, a clean seed, all private
files on another device, impossible answer hardlinks, direct Seatbelt probes,
the native OpenCode shell API, expected seed/reference/partial outcomes and
image detachment. A `passed=true` receipt requires a clean committed research
tree. It issues no model request. For this code-only trial scope, the external
runner uses no benchmark-tool venv or MCP gateway; adding either changes the
dependency boundary and requires a new preflight. Example on this Mac:

```sh
python3 -B research/preflight_protected_python.py \
  /private/tmp/kryn-protected-python-draft-20261003 \
  linecfg-duplicate-key \
  /private/tmp/kryn-python-preflight-new-receipt
```

Even a passing task preflight is not a protected H1 trial: the 30-task roster,
all category-valid graders, paired model turns and independent scoring remain
separate gates. The private draft and raw receipts stay outside the public
repository and runtime package.
