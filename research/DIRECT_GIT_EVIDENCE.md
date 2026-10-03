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
