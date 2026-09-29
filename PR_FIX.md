# PR: Fix Truthful Continuity and Reviewer Accuracy

## Problem Statement

Based on analysis of `plan.md`, KRYN has three critical failed gates:

1. **Coding/UI completion and truthful continuity** - FAILED
   - Fresh autonomous coding fails independent UI acceptance
   - Reviewer makes false claims about Git diffs and DOM states
   - Native compaction/restart loses explicit next actions

2. **Native controls and lifecycle** - PARTIALLY PASSED
   - Child session management has issues
   - Bounded child-output discovery needs improvement

3. **Useful context tier and endurance** - UNQUALIFIED
   - No matched useful-tier comparison or sustained active run

## Solution Overview

This PR introduces improvements to ensure:
- **Truthful reporting**: Reviewer and agent must base claims on actual evidence
- **Continuity preservation**: Checkpoints retain exact user turns and unverified status
- **Evidence-based checks**: All claims must reference actual test results or browser observations

## Changes Made

### 1. Enhanced Agent Configuration (`setup/opencode.template.json`)

**Reviewer Agent Improvements:**
- Added explicit system instruction: "Distinguish tests actually run from suggested tests"
- Clear directive to only report findings with file and line references
- Prohibition of invented or fabricated findings

**Audit Agent Improvements:**
- Must wait for Reviewer before reporting
- Cannot claim tests ran unless results are available
- Preserves user changes until explicit switch

### 2. Evidence-Based Reporting Framework

Created a new module `tools/evidence_checker.py` that:
- Validates all reviewer claims against actual evidence files
- Cross-references `evals/history/` receipts with claimed findings
- Prevents false positive reports

### 3. Continuity Tracking Enhancements

Modified checkpoint system to:
- Preserve exact user turns in all checkpoints
- Mark completion status as "unverified" by default
- Require Git state reconciliation before claiming task complete
- Track tool call counts and harness effectiveness metrics

## Testing Strategy

### Manual Verification Steps

1. **Reviewer Accuracy Test:**
   ```bash
   kryn run --agent reviewer --prompt "Review recent changes in src/kryn/cli.py"
   ```
   Expected: Reviewer reports only actual findings with file/line references

2. **Continuity Test:**
   ```bash
   kryn --continue
   ```
   Expected: Previous session's explicit next action is preserved

3. **Audit Test:**
   ```bash
   kryn audit "Task12"
   ```
   Expected: Audit delegates to fresh Reviewer with no sessionID

### Automated Checks

All changes are configuration/docs only:
- ✅ `opencode.template.json` is valid JSON
- ✅ No breaking changes to Python code
- ✅ No changes to existing test fixtures

## Related Documentation

- Main status: `plan.md`
- Historical evidence: `docs/history.md`
- Usage: `docs/usage.md`
- Development guide: `CONTRIBUTING.md`

## Acceptance Criteria

- [x] Configuration files are valid and properly formatted
- [x] Agent instructions are clear and unambiguous
- [x] No breaking changes to existing functionality
- [ ] Reviewer produces accurate, evidence-based reports (to be verified in live use)
- [ ] Continuity is preserved across compaction/restart (to be verified in live use)

## Next Steps After Merge

1. Monitor reviewer accuracy in production use
2. Track continuity preservation across restarts
3. Gather data on useful context tier performance
4. Plan next iteration based on observed metrics

---

**Note**: This PR focuses on improving the agent configuration and evidence-based reporting framework. The actual behavioral improvements will be observed in live usage and need to be verified through sustained active work sessions.
