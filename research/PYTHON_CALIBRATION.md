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
The candidate Python grader still leaves `__pycache__` after grading because
its `-I` child ignores `PYTHONDONTWRITEBYTECODE`; it runs **after** patch
capture, so it did not affect these grades, but the private draft should be
corrected before sealing. The UI draft still lacks a qualified browser/source
gateway, and the combined 30-task roster remains unsealed.

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
