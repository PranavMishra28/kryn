# Local-only campaign checkpoint, 2026-10-04

This is an **incomplete research run**, separate from the released KRYN v1.0.0
supervised-product qualification. It does not support an autonomous or
frontier-adjacent claim.

The frozen comparison uses OpenCode 2.0.10, the same local
Qwen3.5-9B-6bit/oMLX 0.6.4 route, 96K configured context, tool schema,
effective Agent permissions, 900-second task limit and official SWE-bench
grader in both arms. KRYN adds its product plugin and guidance. The canary
is a separate mechanics diagnostic: both canary arms generated local patches,
reached their timeouts and received clean unresolved official grades. A
host-side handoff bug rejected those terminal timeouts; the failed receipt is
retained. The corrected 11-pair campaign uses a separately pinned source and
manifest, with stricter parity, evaluator and cleanup checks.

The corrected campaign was safely interrupted after **3 of 22 planned arms**
because the connected 65 W adapter could not sustain the Mac under inference;
battery reached the recorded 15% emergency cutoff. No grader, model worker or
benchmark-owned container remained afterward, and the local runtime was
healthy and idle. The second pair's native arm is interrupted, not scored as
a loss or retried. Its partial checkout and patch are archived privately with
hashes and full archive-member reads recorded in
`swebench-v3-checkpoint-evidence.json` before any future resume.

The one complete pair, `django__django-15863`, passed the frozen independent raw-arm
audit for matching model/tool wire, invocation controls, effective permissions,
power source, local-only generation and clean official grading; the same private
checkpoint receipt binds both arm files by SHA-256. Native
OpenCode completed and resolved the issue in about 9.5 worker minutes. KRYN's
patch also resolved in the official grader, but the Agent reached the 900-second
timeout; strict acceptance was **native 1, KRYN 0**. KRYN's patch included
four substitute `asgiref` files and six scratch tests, whereas the native
patch changed only the product file. The official resolved flag does not
certify artifact hygiene. Both arms spent time on missing local test
dependencies, so this austere candidate environment is a quality caveat.

This pair alone cannot estimate general success or prove a model ceiling.
The earlier matched Harbor baseline had only six scoreable pairs, with KRYN
2 versus native 3; its interval did not support uplift. Neither result
justifies promoting a new harness policy or changing the installed model.
The next experimental step is to resume the disjoint remaining tasks with
adequate power, without replaying the interrupted arm, then apply the frozen
independent adjudication and a separate power-intervention audit. Protected
holdout, long-horizon and autonomous-release gates remain unqualified.

Full task traces, interrupted checkout archive, source/evaluator hashes,
manifest, power log and frozen audit code are retained in the owner's private
`kryn-research-private` evidence store. Public counts here are a checkpoint,
not a SWE-bench full-suite score.

## Durable resumption amendment

The same frozen campaign resumed on a 140 W adapter and reached eight terminal
arms. A subsequent AC-to-battery transition stopped the one-shot wrapper during
the next task's image preparation, before its arm or gold grader started. The
eight completed receipts remain intact; this stop did not launch another arm.
The private `swebench-v3-resume-power-stop.json` retains the `power_drift` event.

The replacement research supervisor adds durable waiting and crash recovery
around the separately pinned controller. It does not change the frozen source,
task roster, model, prompts, worker timeout, grading or resource guard. Resume
requires three safe power observations, at least 120 W AC and 40% battery; active
work stops at 25% or on AC loss, with the existing disk/data limits retained.
macOS launchd restarts an unexpectedly exited supervisor; caffeinate is held only
while its controller is active. A future interruption retains its raw evidence
and candidate archive. A gold attempt interrupted before its receipt retires the
affected pair as unscored, allowing later tasks to run without replaying the
single-use oracle. Neither resumption nor a terminal report makes invalid work a
pass. Independent adjudication and the remaining quality gates are still open.

The supervisor's 15 recovery tests, full repository checks and clean package
smoke passed, as did an isolated native launchd crash/restart probe. The first
live launch is awaiting macOS's Python Documents-folder permission before script
execution; no ninth arm has started. The private startup receipt binds all eight
terminal arm files. These checks qualify lifecycle mechanisms, not completion of
the campaign or a successful end-to-end power interruption of this live run.
