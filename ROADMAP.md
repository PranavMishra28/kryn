# Roadmap

## The goal

A coding agent that runs on your own Mac and does the everyday engineering work you would otherwise hand to a hosted frontier agent like Claude Code or Codex: fix the bug, add the feature, keep the tests green, survive a long session. No per-token bill, and the code never leaves the machine for inference.

KRYN 1.0.0 is not that yet. It is a supervised local workspace that is safe on a shared laptop and keeps an honest record. The distance to the goal is measured, not guessed: "frontier-adjacent" goes in the README only when every gate below passes.

## The gates

Collected from the [research protocol](research/PROTOCOL.md) and [evaluation guide](docs/evaluation.md). Each links to its evidence.

| Gate | Passing means | Today |
|---|---|---|
| 1. Supervised daily use | The [v1 qualification](docs/v1-qualification.md) on the final release wheel | **Passed** for v1.0.0 ([receipt](evals/history/2026-10-02-v1-final-qualification.json)). v1.0.1 re-runs it. |
| 2. Same-model uplift | At least 15 points more strictly accepted work than plain OpenCode on the same model, 95% lower bound above zero, no rise in false completions, at least 1.1x accepted work per hour | **Not shown.** No measurable uplift on the public subsets; eight single-mechanism candidates so far, all reverted. |
| 3. Sealed holdout | 30 fresh tasks across ten categories, graded outside the candidate's reach | **Not started.** The first 30 drafts were exposed before sealing and [demoted to development data](research/HOLDOUT_BOUNDARY.md). |
| 4. External transfer | Pinned SWE-bench Verified and Lite subsets and Terminal-Bench 2.0 tasks through their official evaluators | **First subsets run.** SWE-bench 0/6 vs native 1/6 ([EXTERNAL.md](research/EXTERNAL.md)); Terminal-Bench 1/2 each ([HARBOR_SUBSET.md](research/HARBOR_SUBSET.md)). |
| 5. Long horizon | Six sequences with two compactions, two restarts, changed repository state, an injected failure and UI/API checks | **Not run.** |
| 6. Accurate local review | Reviewer findings that hold up against the current source | **Failing.** On known-bad code the local Reviewer missed material regressions and invented findings; a lower-temperature variant never finished its review ([receipt](evals/history/2026-10-01-reviewer-temperature-rejection.json)). |
| 7. Model on the same guard | Any bigger or different model passes the occupied-machine guard and the browser, restart, install and rollback gates | **9B passes on 48 GiB.** 35B and 14B did not fit a normally occupied 48 GiB Mac ([model receipt](evals/history/2026-10-01-daily-envelope-model-decision.json)). |
| 8. Frontier comparator | A hosted frontier agent on the same tasks, tools and budget | **Not authorized yet.** Needs a chosen provider and budget; KRYN configures no paid inference. |

## Milestones

Each milestone is a [GitHub milestone](https://github.com/PranavMishra28/kryn/milestones) with its issues.

1. **[v1.0.1: launchable on today's Macs](https://github.com/PranavMishra28/kryn/milestone/1).** Ship the security fixes (#250) and the newer-Chrome fix (#256) with a full owner qualification. Owner-only.
2. **[More Macs](https://github.com/PranavMishra28/kryn/milestone/2).** A shareable results block (#257), a 32 to 36 GB profile (#258), 27B-class models on 64 GB+ (#259), a real demo (#260), the oMLX port (#248, #252).
3. **[Benchmarks anyone can rerun](https://github.com/PranavMishra28/kryn/milestone/3).** One-command Terminal-Bench reruns (#261), a results table that accepts PRs (#262), community development tasks (#263), docs checks (#253). The sealed holdout comes after these, written by people who have never seen the candidate.
4. **[Research ladder](https://github.com/PranavMishra28/kryn/milestone/4).** One mechanism at a time: context selection (#264, with #247 as the open candidate), verifier-driven repair (#265), continuity (#266), adaptive reasoning (#267), cross-project memory (#268, after #249), and test integrity (#269).
5. **[Frontier comparison](https://github.com/PranavMishra28/kryn/milestone/5).** Gate 8. Opens once gates 2 to 5 have results worth comparing.

## How to help

- **Without a 48 GB Mac:** #262 (results table), #253 (docs anchors), #263 (task format), #252 (port message). These need Python and `make check`, not a model.
- **With a supported Mac:** #257 and the [hardware thread](https://github.com/PranavMishra28/kryn/discussions/254); a rerun of #261; a recording for #260.
- **With 32 to 36 GB or 64 GB+:** #258 or #259. Results from machines that aren't the maintainer's are the scarcest thing this project has.
- **With an idea about agent behavior:** a [research candidate](https://github.com/PranavMishra28/kryn/issues/new?template=research_candidate.yml) under the rung it belongs to.

## What won't change

- No second orchestrator, extra prompt rules or speculative tools to rescue a failing trial. Fix the layer that owns the problem.
- No lowering the resource guard, editing a grader, or moving a threshold to get a pass.
- No relabeling a receipt after the fact. Failed runs stay in the record.
- No paid inference configured by default. Other providers stay an explicit user choice.
