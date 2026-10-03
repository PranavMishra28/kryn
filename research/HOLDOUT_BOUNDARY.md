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
(expected exit 0).

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

**B1 passes this public compatibility screen.** No sealed holdout result
exists. The canary checks selected alias paths, not every possible macOS
information channel. A full 30-task roster, independently isolated hidden
graders, browser/source-gateway boundary tests, broken-seed/reference/partial-
patch controls and frozen hashes remain prerequisites before H1 can use a
protected set. This screen measures boundary mechanics, not local-model
engineering quality or frontier-agent parity.

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
