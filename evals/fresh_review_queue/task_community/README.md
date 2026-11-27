# Community Development Tasks

This directory contains community development tasks that follow the established task format and verification system. These tasks are designed to be used for public development evaluation and can be extended by community members.

## Task Format
Each task must include:
- A seed repository with a specific defect or feature request
- A frozen grader that verifies the solution works correctly
- A reference solution that passes the grader
- A SHA-256 manifest for verification
- Clear documentation of the task requirements

## Task Verification
Tasks can be verified using the existing suite.py verification system:

```sh
python3 -B suite.py verify
python3 -B suite.py selftest
python3 -B suite.py prepare trial-1
# Run the installed KRYN agent in the workspace path printed by prepare.
python3 -B suite.py grade trial-1
```

## Adding New Tasks
To add a new community task:
1. Create a new directory under task_community/
2. Add the task files following the existing pattern
3. Update the task manifest
4. Test with the verification suite