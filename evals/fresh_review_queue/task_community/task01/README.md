# Community Task 01: Simple Bug Repair

## Category
Repository comprehension / Bug repair

## Task Description
Fix a simple date boundary defect in the TaskboardLite project. The `summarize` function must use start-inclusive/end-exclusive ranges and preserve existing behavior.

## Requirements
- Fix the date-range boundary defect in `taskboard_lite/report.py`
- `summarize(rows,start=None,end=None,project=None)` must use start-inclusive/end-exclusive ranges
- Preserve zero-minute rows
- Return count/minutes as before
- Reject invalid canonical ISO dates
- Preserve all existing behavior and tests
- Check empty ranges and start=end cases
- Do not alter source fixture CSV or existing tests

## Verification
The task includes a frozen grader that verifies the fix works correctly. The task must pass `suite.py verify` and fail on the original seed repository.

## Files
- `seed_repo/`: The initial repository state with the defect
- `grader.py`: The verification script
- `reference_solution/`: A correct implementation
- `frozen.sha256.json`: Task manifest