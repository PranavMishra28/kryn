# Candidate C1: stable check guidance within a user turn

Preregistered 2026-10-02 before editing the product plugin. This is a
**development candidate**, not a production change or an H1 result. Released
v1.0.0 stays pinned. The six completed SWE-bench pairs and older TaskboardLite
pilots are diagnostic/training data; none may be relabeled as fresh validation.

## Observation and hypothesis

In the public Task02 pilot, native OpenCode held one system-prompt fingerprint
across 15 requests, while KRYN used eight across 22. KRYN spent 395,905 new
input tokens versus 182,109 native across the four public pilot runs. The
scikit-learn external pair likewise spent 161,396 KRYN versus 45,127 native new
input tokens, but its different trajectories and host pressure prevent causal
attribution. The plugin currently recomputes the observed-check counts and
references on every context/generate hook after tool outcomes change.

**C1 hypothesis:** keeping the *text* of the observed-check guidance fixed
between a user prompt and the next prompt or compaction will reduce prompt-prefix
changes and new-input token cost without reducing independently accepted work.
This is one variable: the timing of model-visible ledger text. The ledger's
actual observations, persisted provenance, stale-check logic, hard tool guards,
resource guard, model, tool catalog, permissions and native execution loop stay
unchanged. Tool results still show the result of a check in the live turn; a new
user prompt, compaction, or restart must refresh the ledger snapshot. Model text
must label a snapshot as historical, never as a current pass claim.

## Test and decision rule

1. In a deterministic plugin fixture, force a failed check between generation
   hooks. The C1 system text must remain byte-identical inside the turn, while
   the persisted ledger records failure and the hard guard responds exactly as
   v1. A compaction and new user prompt must each refresh model-visible state.
2. On public TaskboardLite 02 and 03, run two matched AB/BA repetitions per task
   with the same Qwen3.5-9B-6bit/oMLX/96K configuration, source bases, tools,
   permissions, frozen graders, timeout and unchanged resource guard. Record
   complete and failed runs. Candidate mechanism succeeds only if it reduces
   system-prompt fingerprint changes to at most one per uninterrupted user turn
   and lowers median new-input tokens per generation by at least 25% over the
   matched v1 arm, without losing a strict accepted trial, increasing false
   completion, worsening guard incidents, or lowering accepted work/hour.
   Trajectory and cache warmth differences must be disclosed; a shorter run is
   not automatically a cache win.

   Frozen invocation for these public development pairs: user-facing `agent`,
   default local variant, `--timeout 900 --daily-use-guard --ready-tools
   --without-browser --candidate-product-source`, with TaskboardLite's exact
   prepared prompt and no `--managed-acceptance` intervention. The browser MCP
   is omitted in both arms because these two tasks have no UI criterion; the
   remaining tool catalog must match. V1 runs use the clean `main` product
   plugin, C1 runs use the committed candidate plugin. Planned pair order:
   Task02 V1/C1, Task03 C1/V1, Task02 C1/V1, Task03 V1/C1. Run IDs encode task,
   arm and repetition. Each arm gets a fresh prepared workspace and session.
3. If development is promising, freeze **new** validation tasks and oracle hashes
   before reading any C1 result on them. Do not promote C1 until fresh validation
   has no strict-acceptance or accepted-work/hour regression and external/protected
   transfer is demonstrated under the existing protocol. If the first two
   attempts at this mechanism fail, stop adding prompt rules and change approach.

The current external subset scored KRYN 0/6 versus native 1/6, with 11/12 turns
resource-guarded. C1 cannot retroactively improve that result. No
frontier-adjacent, autonomous-production, or general harness-uplift claim follows
from a prompt-cache improvement alone.
