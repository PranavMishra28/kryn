# Read-only Reviewer screen on archived Harbor failures

Frozen 2026-10-03 before Reviewer model generation. This is public
**development** data selected after two failed Harbor outputs were inspected.
It is a mechanism screen, not a protected test, an independent Harbor score,
or a product change. Released v1.0.0 stays installed and unchanged.

## Hypothesis and fixed inputs

**R1:** a separate use of KRYN's existing read-only `reviewer` agent can
identify a concrete logic defect in a worker's output before another coding
turn. The changed variable relative to the completed one-pass trajectories is
one additional read-only model turn. No Reviewer system prompt or product hook
is changed. A positive screen would justify testing an automatic review-and-repair
workflow on fresh tasks; it would not qualify one for the product.

Two disposable Git workspaces contain only the public Harbor sample's
`instruction.md`, the final agent-generated `candidate.py` or `candidate.sh`,
the agent's own `summary.csv`, and a sorted list of the 164 task image log
filenames. They contain no official verifier output, expected counts, hidden
oracle, or reference solution. Source task image:
`ghcr.io/laude-institute/terminal-bench/log-summary-date-ranges@sha256:277e7926a960bd0c9db733f50ce9861635abad6f5281910a33759d89e52bf9ab`.
The archived worker outputs are from the two trials in
[HARBOR_CALIBRATION.md](HARBOR_CALIBRATION.md). The same read-only prompt is
used in both cases, SHA-256
`fecbb7a4ca8ea16f4c5ff6352bbfb7c6081605e66de76188ea916c3b263d908d`.
The source hashes are `d0c0aa582282e5413ca2f9f40a43be8af429de889ebb3c2e12af995e332125fc`
(KRYN Python) and `76b82bf1a095157e8004469b49b2b4d7424a679d2ea5879329585e507a22779c`
(native shell). The task instruction is
`c1d4516ad4ec2238209740eaf01291df9ab48b0028a3fc5df383c6f831453484`;
the shared filenames are
`75bbbcd7e4daf9068cff65fbece3c187fe84b5953b7f0a4af10433566a386330`.
The agent-output CSV hashes are
`86461431e7cf171bc4f217a3c3e3e30df049c08f645d0b4ce13bbc8083334318`
and `a1ccec7c44376e32ec2a71219037cc4ad5a704af6a0da2cbcb9c30e91f71816b`.
Raw disposable inputs remain in ignored
`/private/tmp/kryn-reviewer-screen-20261002/` and are not production payload.

## Frozen trial and decision

Run one Reviewer turn on each fresh workspace, KRYN artifact first and native
artifact second, with `tools/run_native_trial.py --agent reviewer --variant
default --daily-use-guard --candidate-product-source --without-browser
--timeout 300`. Use the exact prepared `prompt.txt` per case. The Reviewer is
read-only under the product role; no shell, edits or hidden grader. Record
native completion, source reads, final findings, guard state, latency and
tokens. Stop if the unchanged resource guard fires; do not retry an attempted
generation on the same case.

The fixed independent rubric is:

- For `candidate.py`, identify that `total` is incremented once explicitly
  and again through the loop over periods including `total`, cite the relevant
  current `candidate.py` line, and state the resulting aggregate invariant.
- For `candidate.sh`, identify that its hard-coded last-30-day file pattern
  starts on July 27 even though the required inclusive window starts July 14
  and the filename inventory includes dates in that gap; cite the relevant
  current `candidate.sh` line.
- In both, do not claim to have executed checks, seen the Harbor grader, or
  established acceptance from source inspection alone. Label unverifiable
  assertions as such.

R1 screens positive only if both one-shot reviews complete with clean guard
and report their respective defect with a valid source citation within the
300-second turn cap. One or zero correct findings rejects this Reviewer path
without extending its prompt. A positive result still requires a fresh,
predeclared coding task distribution, whole-workflow acceptance, resource cost
and a same-model ablation before any product integration. No result from these
already-seen failures can support H1 or frontier adjacency.
