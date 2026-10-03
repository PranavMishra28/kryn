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
   --candidate-product-source`, with TaskboardLite's exact prepared prompt and
   no `--managed-acceptance` intervention. The full tool catalog must match.
   V1 runs use the clean `main` product
   plugin, C1 runs use the committed candidate plugin. Planned pair order:
   Task02 V1/C1, Task03 C1/V1, Task02 C1/V1, Task03 V1/C1. Run IDs encode task,
   arm and repetition. Each arm gets a fresh prepared workspace and session.

   The first V1 command included both `--ready-tools` and `--without-browser`.
   Runner argument validation rejected that combination before starting a native
   server or model request. It is a recorded invocation preflight, not a trial;
   the command above was corrected before either arm generated.
3. If development is promising, freeze **new** validation tasks and oracle hashes
   before reading any C1 result on them. Do not promote C1 until fresh validation
   has no strict-acceptance or accepted-work/hour regression and external/protected
   transfer is demonstrated under the existing protocol. If the first two
   attempts at this mechanism fail, stop adding prompt rules and change approach.

The current external subset scored KRYN 0/6 versus native 1/6, with 11/12 turns
resource-guarded. C1 cannot retroactively improve that result. No
frontier-adjacent, autonomous-production, or general harness-uplift claim follows
from a prompt-cache improvement alone.

## Completed public development result

All eight preregistered generation turns were run serially and graded with the
frozen TaskboardLite grader plus the independent Task02 date-boundary or Task03
report/CLI/API probe. The same model revision, OpenCode binary, suite, runner,
tool catalog, effective permissions, timeout, requested controls and daily-use
guard hashes match across arms. The candidate bundle hash differs as intended
and is constant within each arm. Exact compact receipts are in
`history/cache_ablation.jsonl`; `python3 -B research/summarize_cache_ablation.py`
reproduces the totals.

| Pair | V1 strict acceptance / seconds | C1 strict acceptance / seconds |
| --- | --- | --- |
| Task02, V1 first | pass / 141.162 | pass / 225.234 |
| Task03, C1 first | fail (timeout) / 909.086 | pass / 433.513 |
| Task02, C1 first | pass / 397.927 | **fail** (wrong equal-range behavior) / 252.130 |
| Task03, V1 first | pass / 685.867 | fail (timeout) / 908.646 |

The strict total is **V1 3/4, C1 2/4** on only two previously seen tasks.
Paired acceptance deltas in run order are `[0, +1, -1, -1]`. V1 delivered
5.061 accepted trials per generation-hour versus C1's 3.957, a 21.8% C1
throughput loss. C1's Task02 failure was also a **false completion**: the final
answer claimed the defect fixed and all existing tests passed, but both
independent checks rejected its equal start/end behavior. Its trace shows the
agent rewriting and then deleting its own added test around that case. V1 had
no observed false-completion claim in these four turns. The two timed-out
Task03 turns produced partial source that passed both graders, but failed the
frozen native-completion endpoint.

The intended cache mechanism worked: V1 changed system-prompt fingerprint 31
times across 162 primary requests; C1 changed it zero times across 167.
New input tokens fell from 753,332 to 300,076 (60.2%), and the median of each
run's new-input tokens per primary request fell from 4,349.4 to 1,732.6.
Cache-read tokens were 3,831,808 versus 4,763,648. Those token counts reflect
different model trajectories, so they do not alone estimate a causal quality or
latency effect. Both arms had 16 tool errors in total. No turn tripped the
unchanged daily-use guard and sampled swap growth was zero; some observed
pressure reached warning. The first Task02 pair ran on battery, the first C1
Task03 arm crossed battery/AC, and the remaining turns ran on AC. That
power-state mismatch limits latency attribution.

**Decision: reject C1.** It missed the preregistered strict-acceptance,
false-completion, and accepted-work/hour gates. The one false completion cannot
be causally attributed to the snapshot change from this small stochastic sample,
but it cannot be ignored to promote the candidate. No protected holdout or
external-transfer trial was run on C1. The experimental plugin change is
reverted before merging this research record; released v1.0.0 and the owner
installation were never changed. Raw traces, source snapshots, grader outputs,
wire audits and a SHA-256 manifest remain in ignored
`evals/runs/cache-ablation-c1-20261002/` on this Mac. Its manifest SHA-256 is
`db3a7807619636b2b73981dd8f4106de2cc3f14050616eb1ed7a9c5999e03a57`.
The next candidate should address independent verification feedback and false
completion rather than add more prompt rules to C1.
