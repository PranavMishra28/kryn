# Research Rung 2: Verifier-Driven Repair

Preregistered on 2026-10-03 before any verifier-driven-model turn. This is a **public development** screen on an already exposed failed task, never protected H1 or validation evidence. The original rate-limit pair and immutable Docker grader are documented in [PUBLIC_SOURCE_RATE_LIMIT.md](PUBLIC_SOURCE_RATE_LIMIT.md).

**Hypothesis R2:** If the existing KRYN worker receives independent verification failures with specific expected vs observed traces, it can repair its already generated patch and pass the unchanged eight-case grader in one guarded turn. The baseline is its frozen 7/8 patch. The only new input is the observed failure with specific traces; model, tools, permissions, source, runtime, source guard, and grader remain unchanged. This measures repair ability with evidence, not autonomous discovery of missing checks.

## Mechanism

The verifier-driven repair mechanism consists of:

1. **Verification Controller**: Identifies specific failures in verification results and extracts expected vs observed traces
2. **Repair Controller**: Processes failure information and generates targeted repair instructions
3. **Feedback Loop**: Feeds repair instructions back into the agent session
4. **Validation**: Confirms the repair passes the original verification criteria

## Test Procedure

1. Copy the KRYN patch with SHA-256 `04c74f195db46923a469620cb6730c3ea604ee57b8c0539ad402b8ee3768827c` from the original pair
2. Commit it to a fresh seed and independently confirm 7/8 before generation
3. Run the verifier-driven repair controller to identify specific failures
4. Feed the failure traces back into the agent session
5. Validate the repaired patch passes all 8/8 criteria

## Success Criteria

- The original 7/8 baseline reproduces
- The repair turn completes under the unchanged guard
- The agent reads the pinned official source
- All eight original Docker cases pass
- APFS source and Docker-visible source match
- Every owned volume/container settles
- The repair is completed in fewer than 19 requests and 586 seconds
- The test file is preserved after repair

## Expected Outcome

This approach should reduce the repair time and request count compared to the previous repair attempt while maintaining or improving repair quality. The verifier-driven mechanism should provide more specific and actionable feedback to the agent, leading to more efficient repairs.
