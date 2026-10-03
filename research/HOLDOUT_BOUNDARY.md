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
