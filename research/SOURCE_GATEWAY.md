# Read-only official-source gateway preflight

Preregistered from clean `main` `41b260eb4af89d84644807d4dcec08868970a8dc`.
This is a research-only, no-model channel test. It does not admit any task or
change released v1.0.0, its provider, permissions, model or resource guard.

The present external-information drafts use fictional sources and are invalid
for that category. We froze one **public** official GitHub Docs source as a
channel canary: `github/docs` commit
`2bd66de8cea336061c9ea060c9b37385136e6ab3`, file
`content/rest/using-the-rest-api/using-pagination-in-the-rest-api.md`, fetched
2026-10-03 10:58 UTC. Its owner-only snapshot has 10,088 bytes and SHA-256
`418bdf281d74a89c7dabedc4af53a6f7b286f2416e7670d9cc71453db08d8640`.
The live [official page](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
and [pinned source](https://github.com/github/docs/blob/2bd66de8cea336061c9ea060c9b37385136e6ab3/content/rest/using-the-rest-api/using-pagination-in-the-rest-api.md)
give its provenance. No answer or hidden grader is in that source file.

**Hypothesis S1:** adding exactly this canonical file as an explicit read-only
dependency in the research whole-process Seatbelt profile lets both minimal
OpenCode and KRYN read the same current official source through native shell,
while denying writes to it, reads/listing of its private sibling, unlisted
loopback access, and same-volume hardlink aliases to the candidate checkout.
The baseline is the current candidate-volume profile without this source
dependency, which must deny reading the file. The candidate changes only the
single file-read allowance; the OpenCode arms, binary, tool environment and
candidate workspace are otherwise identical.

Acceptance is fixed before implementation: the baseline source read fails;
both candidate arms start the real native OpenCode server, read exactly the
10,088 source bytes, fail to write the source or read/list its sibling, keep the
source SHA unchanged, retain equal tool/permission configuration, deny an
unlisted local service, detach the candidate APFS volume and issue zero model
requests. Record wall time and each denial. Any missing observation rejects
this gateway mechanics candidate. Do not classify fictional drafts as current
external-information tasks even if this canary passes. Real tasks need their
own frozen official sources, independent oracle/category review, a sealed
30-task roster and paired model trials.

## No-model result

The first clean-source run (`a304f6b21e0e792e3f59c316ca37277e87f89d1a`)
passed the boundary checks but its receipt omitted the preregistered wall time.
That receipt remains at `/private/tmp/kryn-source-gateway-20261003-01/result.json`
(SHA-256 `99c82424ca60974b3ce7083b3983fa8699d39dc1164d3cb21fdc10b54e48e9b2`).
Only wall-time recording changed before the second run, from clean source
`c92981946e5491ba5d4295e80a32eb2c10ffc05f`.

The second run passed in **7.850 seconds**. The baseline denied the source;
the candidate's direct and both real OpenCode shell reads returned the exact
10,088 bytes. Direct and shell writes, private sibling reads, parent listing,
unlisted loopback and tested oracle aliases were denied. Native and KRYN had
equal tool/permission configuration. The source and provenance hashes were
unchanged, the candidate Git checkout was clean, and the APFS image detached.
The receipt records 14/14 hidden-boundary checks and 13/13 real-server checks
per arm, with zero model requests. Its SHA-256 is
`e305fd86001f0695c60020331db354aa8b221d846cad80fcad311b1f5d790880`
at `/private/tmp/kryn-source-gateway-20261003-02/result.json`; the runner SHA-256
is `30aaa778d739e0712baaca56b32b866a69e508c4466c4ed737eef0caccdfab2d`.

Reproduce the channel check on macOS with the pinned owner-only snapshot and
prepared research tool environment:

```sh
/opt/homebrew/bin/python3.14 -B research/preflight_source_gateway.py \
  --source-dir /Users/pranav/Documents/Codex/kryn-research-private/external-sources-github-20261003 \
  --output /private/tmp/kryn-source-gateway-NEW \
  --tool-venv /private/tmp/kryn-python-tools-v2-20261003
```

**Decision:** advance this exact-file read-only gateway as research mechanics
only. It has not passed a real model-facing source-retrieval task, full
candidate-to-grader external-information workflow, independent oracle review,
or protected H1 admission. The three fictional external-information drafts
remain invalid. The source snapshot and full traces remain owner-only;
the compact [preflight history](history/protected_preflight.jsonl) contains no
task answer or hidden grader.
