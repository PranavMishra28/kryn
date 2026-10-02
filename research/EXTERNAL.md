# External benchmark calibration (frozen before model generation)

This is a one-instance **calibration**, not the predeclared representative
SWE-bench subset or a benchmark score. It tests whether KRYN's real OpenCode
loop can emit a patch accepted by the official evaluator on this Apple-Silicon
host. The same task will be run KRYN then minimal OpenCode, with the same local
model, timeout, candidate tools, permissions and sandbox. One pair cannot
establish an uplift or generalization.

| Input | Frozen value |
| --- | --- |
| Official evaluator | `SWE-bench/SWE-bench@02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` (`swebench` 5.0.2) |
| Dataset | `SWE-bench/SWE-bench_Lite@b0dde1093fe417d83b7184254edf8199c1f0dff5` |
| Local test parquet SHA-256 | `438e281d80587aa7be470896ce410557002fde02d2ceee3e099331d308f62dd3` |
| Instance | `sympy__sympy-20590` |
| Repository base commit | `cffd4e0f86fefd4802349a9f9b19ed70934ea354` |
| Official Docker image | `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590@sha256:3a282752833ce34730ee0621e22033501c993f45742775ca57f04c9ff27178a0` |
| Agent prompt SHA-256 | `767b87738cc2de709220547740b66623bec8630f8bd5f5dfe8978bede8462f8b` |
| Agent budget | 900 s, one local generation at a time, unchanged 22-GiB process guard and two-warning host guard |

The prompt is a fixed generic work instruction followed by the dataset's
`problem_statement`; it excludes `hints_text`, reference patch and test patch.
The candidate checkout was copied from the official image and reset to the exact
base commit. The evaluator log and gold patch remain outside the whole-process
macOS sandbox; only a one-model inference relay and the candidate's own OpenCode
server port are reachable. The research adapter emits a Git patch, and the
official evaluator alone grades that patch. An agent claim or a local test does
not decide acceptance.

The first official gold-patch preflight errored because the registry has no ARM
manifest for this image. An explicit `linux/amd64` pull under Docker Desktop
emulation fixed the environment; the second gold preflight resolved 1/1 with no
grader errors. Its run ID is `kryn-gold-lite-amd64-20261002`; this is an oracle
check, **not** model performance. The image occupies about 4.0 GB and was
retained for the candidate trials. No unrelated Docker data was deleted.

The first KRYN candidate generation failed the unchanged host-memory guard
after 255.887 s and 33 local inference requests, before any tracked edit. Its
sampled host pressure reached warning twice; sampled swap growth was zero.
Power switched between AC and battery during the run, so it cannot form a
matched performance pair with a later single-power control. The trace also
showed the isolated candidate had no usable ripgrep for OpenCode's `glob` and
`grep` tools, and the host's Python 3.14 could not import this old SymPy tree
(`distutils` was removed). These are calibration-environment faults, not an
accepted patch or a reason to weaken the resource guard. Earlier startup
preflights made no inference call and are retained separately.

A fresh disposable research tool venv now supplies Python 3.9.18, mpmath 1.3.0
and ripgrep 15.1.0 to **both** arms through the whole-process sandbox's
explicit dependency list. The isolated canary successfully imported SymPy
1.7.1 and ran ripgrep on the candidate tree. Its Python executable, ripgrep
binary and mpmath initializer SHA-256 values are respectively
`7787e81ff11ff35703620e6af5e0cd395bea30e9ed099e318940153004c2580f`,
`b8836cfabdf1e40f68431cab9b58d7add60c237b858c62a34cd3b2046fbadf8e`,
and `b241584d2c1fc0304b0a1015ea923749d7b0800411dd406dcab7c82bf25d9fe8`.
This environment correction is development calibration; any task observed here
is ineligible for protected holdout selection.

## Candidate result

The corrected run used fresh copies of the official task checkout, with the
same prompt bytes, model profile, OpenCode binary, 900-second bound, sandbox
and first-wire tool schema in both arms. Their SHA-256 values were, respectively,
`767b87738cc2de709220547740b66623bec8630f8bd5f5dfe8978bede8462f8b`,
`05c4645f3b691ae09b239534c026a9da5fa929677e39cff3c0d867fe9e91fe52`,
`f2dfe9ad5851219a6bd97b2e3cd2081c0964b5f120530f578d3da3aefc5ccc5a`,
and `1b56b6b37c804f7fd30cd60d131476c6a619cda5269ac2ccf9d2fc8a5d34a81e`.
The unchanged guard was active throughout. These are one public-task observations:

| Arm | Native outcome | Patch | Official evaluator | Wall time | Resource result |
| --- | --- | --- | --- | ---: | --- |
| KRYN | completed | two-line `Printable.__slots__` edit | resolved 1/1; no grader error | 338.446 s | normal sampled pressure, zero swap growth |
| Native OpenCode | interrupted | empty | empty-patch 1/1; not run by grader | 529.983 s | sustained host-memory warning, zero swap growth |

The official run IDs are `kryn-sympy-r5-20261002` and
`native-sympy-r5-20261002`. The KRYN candidate patch SHA-256 is
`9581a6a5474aa324fc05e9e2f065c399c1f6ac2cd0ae7fb7b7554e50b0c1ecb6`.
KRYN used 33 model requests and native used 34. KRYN made its edit after
source inspection and finished; native remained in source investigation until
the guard stopped it. KRYN's first piped pytest command was refused because it
masked the check exit; its subsequent direct pytest attempt failed because
the disposable tool venv lacks pytest. It ran smaller Python checks, but only
the official evaluator establishes acceptance for this external task.

This is **not** a matched timing/uplift result: KRYN's samples include AC and
battery power, while native's are battery-only; cache warmth also differed.
One task previously inspected during environment repair cannot establish
generalization, a confidence interval, or H1. The first KRYN candidate attempt
also failed the memory guard before its patch, so reporting only the accepted
retry would hide a real failure. The official evaluator correctly records the
native empty patch as `empty_patch_instances: 1`, not as a resolved or executed
test. Full Lite/Verified subsets, Harbor, protected holdout and long-horizon
gates remain open.

Raw private traces, resource samples, exact prompt/prediction JSON and official
evaluator logs are retained in the ignored
`evals/runs/external-sympy-20261002/` directory on this Mac, with a SHA-256
manifest. The folder is not part of the public source package.

Neither this calibration nor the earlier public TaskboardLite pilot is sealed
holdout evidence. The frontier-adjacency gate remains open.

## Frozen cross-repository subset

[The machine-readable roster](subsets/swebench-20261002.json) freezes six new
instances from six repositories before agent generation: three Lite and three
Verified. It pins task IDs, dataset revisions and test-file hashes, base
commits, platform image digests, prompt hashes, a 900-second cap and alternating
KRYN/native order. The roster SHA-256 at freeze time was
`d4dda57b2de1a046b56a268da6b176e6050fbce2c6a1478b8b0d3dad57f71737`.

Selection used only `instance_id` and `repo` metadata: take the six most frequent
repositories across the pinned Lite and Verified test splits after excluding
`sympy/sympy`, which was already used for calibration. Assign them in frequency
order alternately to Lite and Verified, then choose the lowest SHA-256 of
`seed + "\\0" + dataset + "\\0" + instance_id` within each assigned repo,
using seed `kryn-external-20261002-v1`. The prompt is the roster's exact generic
prefix followed by that instance's `problem_statement` and one newline;
`hints_text`, reference `patch` and `test_patch` are excluded. Private prompt
files were generated and hashed before any selected-task run.

For each instance, the official gold patch must first pass the pinned evaluator
under its pinned image digest. Each agent gets a fresh base checkout, the same
preflighted candidate tools, installed model and guard, and one uninterrupted
bounded attempt. Any image, local dependency, guard or oracle failure is recorded
against that frozen task, never silently substituted. The six-case subset is
small and cannot stand in for a full-suite SWE-bench score or the protected
internal holdout.

### Task 1: Django 15996 (Lite)

The pinned gold-patch evaluator resolved the instance (1/1), so the task's
official grading path is functional. Both candidate arms used clean copies of
the pinned base tree, the exact frozen prompt, Python 3.9 and ripgrep inside
the same sandbox, and the unchanged guard. Both were interrupted by sustained
host-memory warning on an occupied Mac, with zero sampled swap growth:

| Arm | Generation | Patch | Official diagnostic grade | Wall time |
| --- | --- | --- | --- | ---: |
| KRYN | interrupted after 15 requests | empty | empty patch; unresolved | 157.836 s |
| Native OpenCode | interrupted after editing | 15 added lines | executed; unresolved 1/1 | 202.006 s |

The native partial patch is *not* a completed task. Under the preregistered
all-criteria endpoint, both arms score zero. The official run IDs are
`gold-django-15996-20261002`, `kryn-django-15996-20261002` and
`native-django-15996-20261002`. All raw receipts, candidate patches, official
logs and a SHA-256 manifest are retained in ignored
`evals/runs/external-django-15996-20261002/` on this Mac. This one failed pair
offers no evidence of same-model harness uplift; the resource failure is itself
relevant to the daily-use envelope.

### Task 2: Sphinx 7440 (Verified)

The pinned gold patch resolved 1/1 in official run
`gold-sphinx-7440-20261002`. The first native-arm startup refused to send the
prompt because the kernel memory-pressure signal was already at warning. It
made zero model requests and did not alter the clean checkout. This preflight
failure is retained separately from the frozen one-attempt generation protocol.

Both subsequent arms used clean copies of the same base and prompt. Their
candidate venv had Sphinx 3.0.1 and ripgrep but lacked pytest, despite a
successful import canary. Both agents spent tool calls trying to obtain or
replace the missing test runner. This is a research-environment fault; it is
not evidence that the installed product lacks pytest for normal projects.

| Arm | Native turn | Official diagnostic grade | Frozen acceptance | New input tokens |
| --- | --- | --- | --- | ---: |
| Native OpenCode | completed in 258.866 s; 44 requests | resolved 1/1 | **pass** | 65,084 |
| KRYN | memory-guard interruption in 368.514 s; 46 requests | partial patch resolved 1/1 | **fail** | 119,940 |

The KRYN partial patch also added 11 lines to an existing test file, violating
the frozen instruction not to edit existing tests. The official evaluator tests
functionality, but it does not waive that task constraint or turn an interrupted
agent into a completed one. Its result is diagnostic only. Both candidate patch
hashes match the exact patches that the official evaluator applied; run IDs are
`native-sphinx-7440-20261002` and `kryn-sphinx-7440-20261002`. Native sampled
normal pressure and zero swap growth; KRYN sampled sustained warning and zero
swap growth. Both ran on AC power. Native started with the model unloaded and
KRYN with it loaded, so their wall times and cache costs are not a matched
performance comparison. The raw receipts and SHA-256 manifest are retained in
ignored `evals/runs/external-sphinx-7440-20261002/` on this Mac.

Across the first two selected tasks, the strict endpoint is KRYN **0/2** and
native OpenCode **1/2**. This tiny, partly unmatched subset shows no harness
uplift; it is neither a full-suite score nor a statistical conclusion. Before
the remaining Python tasks, the research tool venv preflight will require a
usable pytest command and record its package manifest. After adding pytest
8.3.3 to the disposable Sphinx venv, the native patch passed the focused
`tests/test_domain_std.py::test_glossary` check (1/1); this retrospective
environment check does not change either recorded agent outcome. Prior results
remain unchanged.

### Task 3: Matplotlib 25498 (Lite)

The pinned gold patch resolved 1/1 in official run
`gold-matplotlib-25498-20261002`. Both candidate checkouts were reset to the
frozen base and received the exact frozen prompt. The same pinned Python 3.11
dependencies and ripgrep were installed for each arm. Building this older
Matplotlib source on the Mac first failed while linking its bundled FreeType;
using the installed system FreeType fixed that candidate-tool environment
before either arm started. The focused `test_colorbar_renorm` canary passed in
both arms. The system FreeType version differs from the official Docker image,
so that Mac canary does not validate image-comparison tests; official grading
remains authoritative.

| Arm | Native turn | Official diagnostic grade | Frozen acceptance | New input tokens |
| --- | --- | --- | --- | ---: |
| KRYN | guard stop after 11 requests, 96.941 s | empty patch; unresolved | **fail** | 38,528 |
| Native OpenCode | guard stop after 12 requests, 107.571 s | empty patch; unresolved | **fail** | 43,943 |

Both saw sustained host-memory warning under the unchanged guard before any
tracked edit. Sampled swap growth was zero; peak sampled oMLX process physical
footprint was 13.93 GB for KRYN and 13.14 GB for native. Both ran on AC power.
The first KRYN grading CLI call omitted the required `model_name_or_path`
prediction field and produced no result; its run metadata is retained. The
corrected official runs are `kryn-matplotlib-25498-20261002-corrected` and
`native-matplotlib-25498-20261002`, each reporting one empty patch and zero
resolved instances. Raw traces, predictions, official results and a SHA-256
manifest are retained in ignored `evals/runs/external-matplotlib-25498-20261002/`
on this Mac. No same-task retry or guard change was made.

Across the first three frozen tasks, strict acceptance is KRYN **0/3** and
native OpenCode **1/3**. This is an occupied-host limitation and no evidence
of KRYN uplift. The small subset remains incomplete; even when complete it
cannot by itself qualify H1 or support a frontier-adjacent claim.

### Task 4: scikit-learn 25747 (Verified)

The pinned gold patch resolved 1/1 in official run
`gold-scikit-25747-20261002`. The copied source was reset to the frozen base in
two separate checkouts. A matched Python 3.11 environment built scikit-learn
1.3.dev0 from each checkout; both imported their own source and passed the
focused `test_make_union` canary. Its dependency versions differ from the old
official Linux image, so that local canary is only a tool-environment check.
The official Docker evaluator graded both resulting patches.

The first native startup correctly refused a world-writable Docker-copied
checkout before any model request. That preflight failure has its own receipt.
The two disposable checkouts were made owner-only, then the frozen native-first
generation pair ran with fresh evidence. Neither arm was retried after a model
request.

| Arm | Native turn | Official diagnostic grade | Frozen acceptance | New input tokens |
| --- | --- | --- | --- | ---: |
| Native OpenCode | guard stop after 20 requests, 144.708 s | partial patch unresolved | **fail** | 45,127 |
| KRYN | guard stop after 23 requests, 392.033 s | partial patch unresolved | **fail** | 161,396 |

Both saw sustained host-memory warning and zero sampled swap growth. The native
and KRYN sampled oMLX physical-footprint peaks were 12.66 GB and 13.22 GB,
respectively. The official runs `native-scikit-25747-20261002` and
`kryn-scikit-25747-20261002` executed their exact archived partial patches and
each returned zero resolved instances without grader errors. KRYN's much larger
new-input count is an observation, not yet an attributed cache or policy effect;
the arms ran at different times and neither completed. Raw traces, patches,
predictions, grader reports, the preflight failure and a SHA-256 manifest are
retained in ignored `evals/runs/external-scikit-25747-20261002/` on this Mac.

Across four frozen tasks, strict acceptance is KRYN **0/4** versus native
OpenCode **1/4**. The observed resource aborts and unresolved patches do not
support H1. Two selected tasks remain; the subset remains too small for a
generalization or frontier comparison.
