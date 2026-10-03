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

The final canary code also requires the provenance sibling's frozen SHA at
entry and in the top-level verdict; a missing or changed source now fails that
verdict. A clean-source recheck at `a02e59176da928a699a379ab025b7b186cccd777`
passed both source arms again (16.600/16.782 seconds, AC, normal sampled
pressure, zero sampled swap growth). The receipt is
`/private/tmp/kryn-public-source-handoff-20261003-03/result.json`, SHA-256
`e411c170fc40eb4673050ef2f86096b14bdc33e779b8f148ec7a88ecb53140d9`,
with runner SHA-256
`8cba3d896cf3e12106c67efd195c0f0ac2729f6029064af17c2eec4a53edeac2`.
The original no-source Agent-to-Docker canary also passed both arms with the
final script; its regression receipt SHA-256 is
`21c967d13242d29f242e638f237dd6822fb3364b82c78091236d2e34cbf4a9e7`.

## S3 preregistration: native read permission

The first public coding pair found that OpenCode denied its native `read` on
the pinned external source, while the process sandbox allowed exact-file
shell reads. This is a research-adapter defect. Hypothesis: adding one narrow
OpenCode external-directory boundary and an exact-file `read` exception will
make the native tool usable without widening the actual process boundary.
The baseline is the current research configuration; the candidate changes
only source-file permissions when an owner-only `source_file` is supplied.
Neither the production configuration nor the Seatbelt policy changes.

Before another real-model trial, run a paired zero-model Agent canary in both
arms. Require the native `read` on the source to return the pinned bytes or an
explicit bounded, untruncated portion; native `read` on its provenance sibling
and native `write` on the source must be denied. The existing six exact shell
chunks, hidden-file denial, identical fixture patch, detached Docker grade,
equal effective permissions and tool schemas, complete telemetry, normal host
pressure, and clean APFS/container teardown must still pass. A native source
read that fails, truncates silently, or opens the sibling rejects the candidate.
Record wall time, synthetic request count, source hash, and resource samples.
Do not run a model or count this as protected task success until the canary
passes. A public model retry, if any, remains development data.

The first S3 canary at clean `9dcc73c` returned the exact requested first 20
numbered source lines in both arms, followed by OpenCode's explicit
`Continue reading with offset: 21` marker. OpenCode correctly marked the
*file* as truncated because more pages remain; the canary mistakenly required
`metadata.truncated: false` for a bounded page. All sibling/write denials,
six exact shell chunks, Docker grades and parity checks passed, but its raw
verdict stays failed at `/private/tmp/kryn-source-native-read-20261003-01/result.json`
(SHA-256 `d48772ccccfd9312eb8ef9eaf8ec908f3f524c070a6240dcc069d71bfe201db5`).
The measurement correction requires all 20 expected lines and the exact
continuation marker; it does not change the permission rules or trial inputs.

At clean `2ad0e74143ed7610c32ae555bc2666e47dd02e5b`, the corrected S3
canary passed in both arms. Each native `read` returned precisely lines 1–20
with the explicit next-offset marker; the native sibling `read` and source
`write` failed. The earlier six bounded shell reads reconstructed the full
10,088-byte source, its hash and provenance stayed unchanged, and the hidden
file remained inaccessible. Both arms produced the same patch and passed the
fresh networkless Docker grade. Permissions and tool catalogs matched; each
arm made 14 synthetic requests, zero real model requests, and took 16.562 s
(native) or 17.006 s (KRYN). AC power, normal sampled pressure, zero sampled
swap growth, complete telemetry, detached APFS images and removed containers
were observed. The raw pass receipt is
`/private/tmp/kryn-source-native-read-20261003-02/result.json`, SHA-256
`bfe8669cd917c5f23a9e323750bb89d7bca6ed540208aa75c7bfc2776c504b93`.
The no-source canned regression also passed both arms, receipt SHA-256
`a3fe23c43a345a52577403aa8f96dcf3adb571b91f81535a296f36d213da0d2d`.
`make check` passed. This admits the research source adapter for further
public development trials; it does not admit external-information tasks to
the protected holdout or establish a live-model capability gain.
