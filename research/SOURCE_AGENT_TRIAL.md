# Exact-source Agent handoff (preregistered 2026-10-03)

Start from clean `main` `c1865aefdefb24e8028f60409225880e99d85b9a`.
The released v1.0.0 product and its guard are unchanged. The official-source
gateway preflight in [SOURCE_GATEWAY.md](SOURCE_GATEWAY.md) proved native shell
access but did not run an Agent turn or grade work.

**Hypothesis S2:** passing one pinned, exact-file read-only source allowance
through the research Agent-to-grader barrier preserves the existing candidate
and grader isolation while allowing both matched OpenCode arms to use that
source during a coding turn. The changed variable is this source dependency;
model, runtime, context, tool catalog, permissions, guard and grader remain
matched across arms. The baseline for source access is the gateway's no-source
profile, which denied the file. This is a research channel test, not a harness
capability candidate.

Before any live model request, use a public, canned OpenCode Agent turn on a
one-file fixture. In both arms it must attempt a real native shell read of the
exact GitHub Docs pagination snapshot and a write to the same path. The read
must return the frozen bytes; the write and private-sibling read must fail.
The Agent must make the same small edit, pass the detached patch capture and
fresh Docker grader, leave the source SHA unchanged, settle the owned session,
detach every APFS image, and show identical tool/permission configurations.
Record wall time, request count (zero real model calls), resource and cache
state. Any missing observation rejects the channel candidate.

Only after that mechanics gate may one public development coding task ask each
arm to implement GitHub REST pagination from the pinned source. Freeze the
task, grader controls, prompt, seed, source hash, timeout and arm order before
generation. A guarded turn or independently rejected code is a recorded
failure, not a reason to relax the guard or change the oracle. The public pair
can validate the runner and diagnose behavior; it cannot count as protected
H1 uplift or admit the still-fictional external-information drafts. Three
fresh current-source tasks and an independently reviewed, sealed 30-task
roster remain prerequisites.

## First mechanics attempt: native shell truncation

The first clean-source canned run (`75fcd15`, zero real model requests) failed
the full-source-read criterion in **both** arms. OpenCode's native Agent shell
tool returned exit 0 but set `truncated: true`, exposing only its saved-output
tail: about 4.3K characters of the 10,088-byte file. Direct API shell access
in the earlier preflight had returned the full file, so that check did not
exercise the Agent-visible output limit. The sibling/write denials, edit,
detached patch capture and independent Docker grade did pass in both arms;
neither result is upgraded to a full handoff pass. The unchanged first receipt
is `/private/tmp/kryn-public-source-handoff-20261003-01/result.json`, SHA-256
`3a3635a857162673b280eda17123cf0c82fd450fec58e641b9ed444e98adba27`.

The minimal measurement correction is to request the same pinned file in
line-bounded chunks below the native output cap, require every chunk to be
untruncated and byte-exact, then reconstruct the full source. The source,
allowance, model, guard, grader and acceptance rule are unchanged.

## Corrected no-model handoff result

From clean source `f3ecfffab7b346f0a71faa24fd9f41bbb5bd5a17`, the same
source was retrieved through six `sed` reads, each at most 2,000 source bytes.
Every native shell result had exit 0, `truncated: false`, and exact expected
bytes; concatenation reconstructed the full pinned source. Both arms also
denied the `SOURCE.json` sibling and source write, made the same fixture edit,
captured identical patch SHA-256
`f4368f87b6286c90cd99aa4cee06a9fe5d9c3860e18fa6eda85977c00bba2f71`,
and passed the networkless, read-only, non-root Docker verifier on the fresh
host-visible clone after the APFS candidate detached. Candidate, capture and
grader images all detached; no canary container remains.

Each arm made 11 **synthetic** requests and zero real model requests. Native and
KRYN tool catalogs and effective permissions matched. Their wall times were
16.657 and 16.937 seconds; resource telemetry was complete, with AC power,
normal sampled pressure and zero sampled swap growth. The source hash stayed
unchanged. The retained receipt is
`/private/tmp/kryn-public-source-handoff-20261003-02/result.json`, SHA-256
`a6bb9052cc93fc0ce8e441bdc4288691c7a4719c037a06d7ec67652d5b2d59c9`;
the runner SHA-256 is
`4bbb7c3f633ade563442ce5d920bbed0bccaeb3b851f7e0a285fa986effaeb06`.

Run a fresh copy with:

```sh
/opt/homebrew/bin/python3.14 -B research/docker_grader_handoff_canned.py \
  --output /private/tmp/kryn-public-source-handoff-NEW \
  --tool-venv /private/tmp/kryn-python-tools-v2-20261003 \
  --grade-root /Users/pranav/Documents/Codex/kryn-research-private \
  --source-dir /Users/pranav/Documents/Codex/kryn-research-private/external-sources-github-20261003
```

**Decision:** the exact-file allowance may advance to a public development
model task. The real Agent's shell-output cap must be respected; a successful
`cat` exit alone is not evidence that the model saw the document. This result
is not a protected external-information task, accepted coding work, H1 uplift,
or a complete macOS information-boundary proof.
