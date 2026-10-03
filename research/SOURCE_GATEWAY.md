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
