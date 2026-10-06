# Read the docs in this order

KRYN is a local coding workspace you supervise. OpenCode does the agent work;
oMLX runs the local model; KRYN installs the stack and adds resource guards,
session evidence and recovery. You still review the changes and the running app.

| I want to… | Read |
| --- | --- |
| Install and start coding | [README](../README.md) |
| Understand modes, tools, approvals and recovery | [User guide](usage.md) |
| Test it myself for 45–60 minutes | [Owner testing guide](testing.md) |
| See what passed and what is still open | [Current status](../plan.md) |
| Understand where a fix belongs | [Architecture](architecture.md) |
| Contribute a fix | [Contributing](../CONTRIBUTING.md) |
| Understand benchmark results | [Evaluation](evaluation.md) and [research index](../research/README.md) |
| Build, install or publish an artifact | [Release procedure](releasing.md) |
| Report a security problem | [Security policy](../SECURITY.md) |

## Words used in this repository

- **Release:** the published wheel and installer. There is one public version,
  [v1.0.0](https://github.com/PranavMishra28/kryn/releases/tag/v1.0.0).
- **Candidate:** source changes in a PR. The version string can still say 1.0.0;
  that does not make those bytes the published release.
- **Supervised:** you can review, correct and approve work. Corrections are
  recorded; they do not become autonomous successes.
- **Offline check:** code, packaging or fixture validation without a model run.
- **Live check:** an actual installed-model session, browser action or lifecycle
  operation. A simulated check cannot substitute for it.
- **Diagnostic:** a small observation used to investigate behavior. It is not a
  representative benchmark score.
- **Guard stop:** the run stopped to protect resources or ownership boundaries.
  Keep the partial work and investigate; do not lower the guard to get a pass.
- **Receipt:** a saved observation with enough identity information to tell which
  source, artifact and run it describes. A file hash proves identity, not quality.

You do not need to read the research archive to use KRYN. Start with the user
and testing guides. Research documents retain failed experiments and historical
instructions; their old launch commands are not an instruction to resume them.
