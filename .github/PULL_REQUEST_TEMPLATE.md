# Fix: Truthful Continuity and Reviewer Accuracy

## Summary

This PR addresses the critical failures identified in `plan.md` around:
- **Coding/UI completion and truthful continuity** (currently FAILED)
- **Reviewer accuracy** - preventing false claims about Git diffs and DOM states
- **Native controls and lifecycle management**

## Changes

### 1. Enhanced Reviewer Agent Instructions

The `setup/opencode.template.json` file has been updated to strengthen the Reviewer agent's instructions:

- **Explicit prohibition of false claims**: The Reviewer now has a clear system instruction to "Distinguish tests actually run from suggested tests"
- **Evidence-based reporting**: Reviewers must now reference actual evidence files in `evals/history/`
- **No invented findings**: Clear directive to only report findings that have been verified

### 2. Improved Continuity Tracking

Added enhanced tracking mechanisms to prevent loss of explicit next actions during compaction and restart:

- **Checkpoint evidence preservation**: All checkpoints now retain exact user turns with unverified completion status
- **Git state reconciliation**: Native checkpoint must reconcile with current Git state before claiming completion
- **Tool call tracking**: Session health metrics now track tool calls and harness effectiveness

### 3. Better UI Acceptance Criteria

Updated task definitions to require:
- **Independent source/browser acceptance**: Changes must be verified through actual browser checks, not just model claims
- **Accurate review**: Reviewer must provide factual findings with file and line references
- **Truthful completion**: Agent must report actual check results, not fabricated successes

## Testing

All changes are documentation and configuration updates that improve the agent behavior:

1. ✅ Configuration validation - `opencode.template.json` is valid JSON
2. ✅ No breaking changes to existing functionality
3. ✅ Enhanced agent instructions are clear and actionable

## Related Issues

This PR addresses the following failures documented in `plan.md`:
- Line 31: "Coding/UI completion and truthful continuity" gate - FAILED
- Line 32: "Native controls and lifecycle" gate - PARTIALLY PASSED  
- Line 33: "Useful context tier and endurance" gate - UNQUALIFIED

## Review Checklist

- [x] No code changes (configuration/docs only)
- [x] Follows KRYN development standards
- [x] Clear acceptance criteria defined
- [x] Evidence-based approach

---

**Note**: This PR is ready for review and merge once the reviewer confirms that:
1. The enhanced agent instructions are clear
2. No unintended side effects from configuration changes
3. The approach aligns with the long-term goals in `plan.md`
