# Direct Git evidence candidate (research only)

Preregistered before editing the plugin. Released v1.0.0 stays unchanged.

The exposed rate-limit repair emitted a JavaScript syntax-coverage warning in a
Python-only repository. The hook did not find JavaScript; its Git snapshot was
unavailable. In the unchanged research Seatbelt profile, `/usr/bin/git` exits 1
because Apple's shim cannot read `/var/select/developer_dir`. The installed
Command Line Tools Git exits 0 with the same workspace, environment and profile.
Both observations were reproduced without a model request on 2026-10-03.

**G1:** choosing the root-owned Command Line Tools Git directly when present,
and retaining `/usr/bin/git` as a fallback, restores complete Git evidence in
the research sandbox without changing the model, prompts, tools, permissions,
grader or guard. The only implementation variable is the Git executable used
by the plugin's two read-only evidence commands.

The development screen is fixed now: a Python-only committed repository with
one changed tracked file must produce a non-null Git snapshot and no JavaScript
syntax-coverage warning after a completed shell call in the actual Seatbelt
profile. A deliberately malformed changed JavaScript file must still produce
syntax feedback. The same two checks must pass in ordinary unsandboxed plugin
tests. Capture the exact source/tool hashes and both pre/post results. Revert
this candidate if the sandbox result fails, if it widens the file/network
boundary, or if product tests fail. These no-model checks alone do not justify
product promotion or show accepted-work uplift; fresh model validation,
protected transfer and release checks remain prerequisites.

## No-model development result

The first smoke invocation selected a Homebrew Node build whose `libuv` dylib
was not in the sandbox's dependency list, so neither arm started. The second
started both arms but incorrectly looked for Git evidence in a first-turn
context hook, which intentionally does not emit a checkpoint. The corrected
smoke uses a compaction hook and a pinned standalone Node binary. These two
scaffolding failures are retained as the `-20261003.json` and
`-20261003-02.json` receipts under `/private/tmp/kryn-direct-git-evidence*`;
they do not count as candidate behavior.

The corrected screen (`-03.json`) reproduced the baseline failure: no current
Git snapshot, the irrelevant Python-task warning, and no changed-JavaScript
syntax feedback. The candidate reported a current Git snapshot, omitted the
Python-task warning, and reported the malformed JavaScript. Both arms exited
normally. The candidate also passed `make check` with 215 setup, 26 research,
87 Node and the frozen offline suite checks. This is a deterministic sandbox
compatibility result, not an accepted coding task or evidence of H1 uplift.
