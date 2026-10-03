# Isolated Python task calibration (development only)

This screen uses one private `linecfg-duplicate-key` draft to debug the real
candidate-volume runner. The task was exposed to the research team and is
**retired from any sealed holdout**. No result below estimates H1 uplift.
Released KRYN v1.0.0, its 9B model, 22-GiB runtime ceiling and host guard were
unchanged.

| Turn | Source | Agent / independent result | Model requests | Wall time | Finding |
| --- | --- | --- | ---: | ---: | --- |
| KRYN, no benchmark tools | `6ea5846` | completed / pass | 11 | 65.1 s | OpenCode `glob` and `grep` failed because ripgrep was absent from the isolated path. |
| KRYN, symlinked Python venv | `6ea5846` | failed completion / pass | 26 | 201.6 s | Search worked, but Python resolved to Apple's unavailable `/usr/bin/python3` shim; repeated shell retries ended in an auto-denied web fetch. New files were also omitted by the old patch collector. |
| Native OpenCode, copied Python venv | `a1ec5a3` | completed / pass | 6 | 50.4 s | Python test exited 0; no tool errors. |
| KRYN, copied Python venv | `a1ec5a3` | completed / pass | 10 | 62.0 s | Python test exited 0; no tool errors. One new test file was included in the patch. |

The last two turns used the same task prompt/base, OpenCode binary, model
revision/profile, first wire tool schema (10 tools, SHA-256
`1b56b6b37c804f7fd30cd60d131476c6a619cda5269ac2ccf9d2fc8a5d34a81e`),
sampling settings and copied Python/ripgrep/pytest environment. Both saw only
normal sampled memory pressure, no swap growth, AC power and no guard
intervention. The native turn used five tool calls; KRYN used nine. One easy
task with both arms passing gives **no evidence of harness uplift**. It is
also not a fully qualified tool-parity comparison: the Mac's Git shim failed
inside that isolated environment, although this task did not require Git.

The repair is a research-only tool environment with copied Python, pinned
ripgrep and a Command Line Tools Git link. The candidate server sets
`GIT_CONFIG_NOSYSTEM=1` because its sandbox cannot stat the absent
`/etc/gitconfig`. The no-model preflight from clean `1704e93` now proves
Python, pytest, ripgrep and Git through both real OpenCode shell APIs, plus
active requested arm, hidden-oracle denial, seed failure, reference pass,
partial-patch failure and image detachment. Its passing receipt is
`/private/tmp/kryn-python-tools-git-preflight-20261003-01/report.json`
(SHA-256 `9f92a41b6e688d11769993432a46f147f9a1aac1960b73f0c6892e2faa95fb6e`).
This remains a **no-model admission check**, not a protected score.

The adapter now builds its patch through a temporary intent-to-add Git index,
so new files are included without changing the agent checkout's index. The
unit test checks tracked and new file content plus unchanged index bytes.
The private Python grader initially left `__pycache__` after grading because
its `-I` child ignored `PYTHONDONTWRITEBYTECODE`. The unsealed draft now invokes
that child with `-B`; it runs **after** patch capture, so this did not affect
the recorded grades. A subsequent all-task preflight using Python 3.13 passed
14/15 exact controls and failed `ledger-journal`: its traceback differed from
the frozen Python 3.14 validation. The preflight now requires the frozen grader
binary hash and version. An explicit 3.13 negative control fails before a
candidate starts; all **15/15** no-model preflights pass with Python 3.14.6,
including both OpenCode arms' Python/pytest/ripgrep/Git canaries, seed/reference/
partial controls and image detachment. The private manifest SHA-256 is
`08aa7a5da0d4b56efe94136294fdf929e1e11696cdb0c43fe73d518f97bd4603`;
that manifest is the owner-only durable copy at
`/Users/pranav/Documents/Codex/kryn-research-private/python-draft-20261003/manifest.json`,
not the older `/private/tmp/kryn-protected-python-draft-20261003` snapshot. The
15-receipt summary is
`/private/tmp/kryn-python-v3-preflight-20261003-summary.json` (SHA-256
`f5aaa3a7500c089d58e9432e1ddcb6dffacbd718a7d9933b4c776c8f70f75fd4`).
The failed 14/15 calibration remains at
`/private/tmp/kryn-python-v2-preflight-20261003-summary.json`.

These controls qualify only the draft mechanics. Four Python tasks still
carry explicit scientific-coverage limitations, one is retired, the UI draft
still lacks a qualified browser/source gateway, and the combined 30-task
roster remains unsealed.

Independent review also found that pre-turn Git status and post-turn patch
collection could execute candidate-controlled Git fsmonitor/filter commands on
the trusted host. The research adapter now runs both in a fresh, networkless
whole-process sandbox, streams bounded output, opens Git metadata without
following candidate links, pins the checkout's Git config across the turn, and
keeps the resource monitor active through capture. A real
no-tool capture and a pinned-tool capture both produced the expected patch. A
candidate-controlled clean filter fired in a no-model canary but could not read
a synthetic oracle outside the workspace; the regression test requires an empty
leak file. The exact policy-plugin/source check in both-arm canaries and a
bounded CLI event stream are part of this correction. These screens do **not**
qualify a protected model result or exhaustively prove descendant settlement.
Protected admission still requires fresh trusted checkout provenance; a reused
checkout may retain Git settings that distort patch construction even when the
hidden oracle remains inaccessible.
The two paired model turns above predate this capture correction.

A first clean-source post-correction preflight at `f3a451d` failed because the
stricter API-shell denial check required an empty combined output stream;
OpenCode included the expected `cat: …: Operation not permitted` diagnostic.
The exact-denial matcher at `f151eca` passed the candidate-volume boundary
canary and a fresh real-task preflight for `linecfg-interpolation` with both
arms. The failed and passing reports remain at
`/private/tmp/kryn-python-postcapture-preflight-20261003-01/report.json`
(SHA-256 `934eaf0709b5e002fd3da02fbbd533ced0168b141a00a160e3e35476976e77b1`)
and `/private/tmp/kryn-python-postcapture-preflight-20261003-02/report.json`
(SHA-256 `afe908569463a954f6b0e3b0ff14fc1c12593307ee350953081d4ba124f2ac86`).

One actual KRYN turn on the **retired** `linecfg-duplicate-key` draft at
`f151eca` stopped under the unchanged host-memory warning after one inference
request; its `result.json` SHA-256 is
`a98b4c62d2da346e4e9dd6300ed6624418ae0bbd5cb9c785ca6c69f1a04cff0a`.
With pressure back to normal, one fresh retry completed and independently
passed in 106.1 seconds with 18 requests, normal sampled pressure and no swap
growth. It captured a 1,192-byte patch (SHA-256
`769d83272418880f1eba957ec5450b887fb393dcede1bdc6f30ec2b8d348a464`)
and unchanged Git-config hash; the retry `result.json` SHA-256 is
`47d305a4c189db748828233c0554129343a4901517dea8485516204b12fefbbd`.
Both run directories are under `/private/tmp/kryn-python-postcapture-development-kryn-20261003-0{1,2}`.
This is adapter compatibility and a resource-guard observation, **not** an H1
estimate or a protected model result.

The next research-only admission correction requires the pinned Python/rg/Git
tool environment, treats ignored checkout residue as dirty, and checks that the
grader interpreter paths do not overlap the hidden draft. Each arm's no-model
OpenCode shell canary must also deny the reference and manifest files and a
live unlisted localhost service. The offline preflight now separates mechanics
from task eligibility: a retired task or one with declared scientific coverage
flags cannot report `passed=true`. This does not repair the still-unflagged
oracle coverage gaps or qualify the combined 30-task roster.

Raw local receipts: `/private/tmp/kryn-python-development-kryn-20261003-01/`,
`/private/tmp/kryn-python-development-tools-kryn-20261003-01/`,
`/private/tmp/kryn-python-development-tools-native-20261003-01/`, and
`/private/tmp/kryn-python-development-tools-kryn-20261003-02/`. Their respective
`result.json` SHA-256 values are
`9b7f6c1dc90d18d4f5762d72bb6916d0b83620693846f2ce7f7be59d15727c91`,
`1dc5c094e126cb96fbcb68484635891c4ded9c076197b380cd9239306b1cba65`,
`dfec7245e3349d833ededc71064c1e94e34d923febb55bc087f9e2632a2fa15b`,
and `1b98009ca3fe513d751f915d83b52fc3f777f967c82a4c4b78eb9ac476bfe9d7`.
The private draft and oracle are intentionally outside the public repository.
