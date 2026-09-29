# Fix: Truthful Continuity and Reviewer Accuracy

## Summary

This PR addresses critical failures in KRYN's agent system as documented in `plan.md`. The main issues are:

1. **Truthful continuity** - Reviewer agent makes false claims about Git diffs and DOM states
2. **Coding/UI completion** - Fresh autonomous coding fails independent UI acceptance  
3. **Native controls and lifecycle** - Child session management has issues

## Problem Details (from plan.md)

### Failed Gates

| Gate | Status | Issue |
|------|--------|-------|
| Coding/UI completion and truthful continuity | ❌ FAILED | Reviewer makes false claims, native compaction loses next actions |
| Native controls and lifecycle | ⚠️ PARTIAL | Child session management needs improvement |
| Useful context tier and endurance | ❌ UNQUALIFIED | No sustained active work demonstrated |

## Changes Made

### 1. Enhanced Reviewer Agent System Instruction

**File:** `setup/opencode.template.json`

Added critical accuracy requirements:
- Only report findings verified against actual evidence
- Never invent findings or claim tests ran without results
- All claims must reference observable evidence (Git diff, browser snapshots, test results)

**Before:**
```json
"system": "Review the supplied work for correctness, regressions and missing tests. Return actionable findings with file and line references. Do not edit files. Distinguish tests actually run from suggested tests."
```

**After:**
```json
"system": "Review the supplied work for correctness, regressions and missing tests. Return actionable findings with file and line references. Do not edit files. Distinguish tests actually run from suggested tests. CRITICAL: Only report findings that you have verified against actual evidence (Git diff, browser snapshots, test results). Never invent findings or claim tests ran unless their results are available. All claims must be supported by observable evidence in evals/history/ or current Git state."
```

### 2. Enhanced Audit Agent System Instruction

**File:** `setup/opencode.template.json`

Added verification step before reporting:
- Must verify Reviewer's findings against actual evidence
- Cannot propagate false claims from Reviewer

**Before:**
```json
"system": "Coordinate a read-only audit. Inspect relevant files and available diff/check evidence, then delegate exactly once to a fresh Reviewer with no sessionID, model override, or background execution. Supply acceptance criteria, changed paths and actual evidence. Wait for the Reviewer, then report findings without fixing them. Do not claim tests ran unless their results are available. You remain read-only until the user explicitly switches agents."
```

**After:**
```json
"system": "Coordinate a read-only audit. Inspect relevant files and available diff/check evidence, then delegate exactly once to a fresh Reviewer with no sessionID, model override, or background execution. Supply acceptance criteria, changed paths and actual evidence. Wait for the Reviewer, then report findings without fixing them. Do not claim tests ran unless their results are available. You remain read-only until the user explicitly switches agents. IMPORTANT: After Reviewer completes, verify their findings against actual evidence before reporting. Never propagate false claims from the Reviewer."
```

### 3. New Evidence Checker Module

**File:** `tools/evidence_checker.py` (NEW)

A validation module that:
- Validates reviewer claims against actual Git diff state
- Checks browser-related claims against snapshot evidence
- Provides automated validation of findings
- Generates evidence reports for audit trails

**Key Functions:**
- `validate_reviewer_claim(claim)` - Validates any reviewer claim
- `validate_git_diff_claim(claim, repo_path)` - Checks Git diff support
- `validate_browser_check_claim(claim, output_dir)` - Validates browser observations
- `generate_evidence_report()` - Creates audit trail of available evidence

## Testing

### Automated Checks ✅

- [x] Configuration files are valid JSON
- [x] No breaking changes to existing Python code
- [x] New module is importable and functional

### Manual Verification (To be done after merge)

1. **Reviewer Accuracy Test:**
   ```bash
   kryn run --agent reviewer --prompt "Review recent changes in src/kryn/cli.py"
   ```
   Expected: Reviewer reports only actual findings with file/line references

2. **Evidence Validation Test:**
   ```bash
   python tools/evidence_checker.py
   ```
   Expected: Reports available evidence and validates claims

3. **Continuity Test:**
   ```bash
   kryn --continue
   ```
   Expected: Previous session's explicit next action is preserved

## Acceptance Criteria

- [x] Configuration changes are minimal and focused
- [x] No breaking changes to existing functionality
- [x] New evidence checker module is functional
- [ ] Reviewer produces accurate, evidence-based reports (verified in live use)
- [ ] Continuity is preserved across compaction/restart (verified in live use)

## Files Changed

1. `setup/opencode.template.json` - Enhanced agent system instructions
2. `tools/evidence_checker.py` - NEW: Evidence validation module

## Related Documentation

- Main status and gates: [`plan.md`](plan.md)
- Historical evidence index: [`docs/history.md`](docs/history.md)
- Usage guide: [`docs/usage.md`](docs/usage.md)
- Development guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Next Steps

After this PR is merged, the following should be addressed in subsequent PRs:

1. **Continuity tracking improvements** - Enhance checkpoint system to preserve explicit next actions
2. **Browser check enhancements** - Improve evidence-based browser validation
3. **Useful context tier testing** - Run sustained active work sessions to qualify the 96K context tier

---

**Note:** This PR focuses on improving agent accuracy through better instructions and evidence validation. The actual behavioral improvements will be observed in live usage and need verification through sustained active work sessions.
