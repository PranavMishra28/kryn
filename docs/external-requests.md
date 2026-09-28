# External Requests regression

[Development commands](../CONTRIBUTING.md) · [Current status](../plan.md)

Run the commands below from the repository root.

[The external evaluator](../evals/external_requests.py) reproduces one [SWE-bench Verified instance](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/tree/c104f840cc67f8b6eec6f759ebc8b2693d585d4a), `psf__requests-6028`, against [Requests commit 0192aac](https://github.com/psf/requests/tree/0192aac24123735b3eaf9b08df46429bb770c283). This optional evaluator is separate from the installed KRYN package. It calls no model and changes no inference settings. Prerequisites are Python 3.10+, Git and `uv`; initialization creates an isolated Python 3.10.16 environment with the exact dependency versions embedded in the adapter.

Run these from the repository root, choosing a new state directory outside the checkout:

```sh
kryn_eval_state="$HOME/kryn-evals/requests-6028"
python3 -B evals/external_requests.py --state "$kryn_eval_state" init
python3 -B evals/external_requests.py --state "$kryn_eval_state" selftest
python3 -B evals/external_requests.py --state "$kryn_eval_state" prepare trial-1
```

The last command prints a fresh Git workspace containing only upstream source and the exact issue as `TASK.md`. In a separate terminal, enter that workspace, put the evaluator's `venv/bin` first on `PATH`, start your normal harness, and submit `TASK.md` verbatim. Give the candidate access only to its workspace. Keep the state directory's `oracle/`, `grades/`, reference solutions and other attempts out of its context. These ordinary filesystem directories are **not a security sandbox**.

After the attempt ends, grade it from the repository root:

```sh
python3 -B evals/external_requests.py --state "$kryn_eval_state" grade "$kryn_eval_state/workspaces/trial-1"
```

Initialization verifies the source archive, exact problem/test/reference hashes and all 102 frozen fixture inputs. The Hugging Face rows API is not revision-addressable, so changed fields fail their fixed hashes instead of silently updating the task. `init --source-archive PATH --instance-json PATH` can use cached official inputs under the same checks. Existing nonempty state and workspace labels are never overwritten. A failed initialization remains for inspection; use a fresh state directory to retry.

Grading copies the candidate outside its workspace, checks preserved original tests/configuration, rejects added `conftest.py` files and symlinks, applies the unchanged official test patch, and runs the focused and adjacent test module. Case and skip identities must match the frozen reference. Only the grader workspace and owned virtual-environment prefixes in test names become `<workspace>` and `<venv>`; the latter removes one absolute `pytest.__file__` parameter path. No assertion or skip changes. `selftest` requires the original bug to fail both official regression cases, the reference to pass 5 focused cases and 203 adjacent cases with 11 upstream skips, and modified tests to be rejected before execution. Reports and raw pytest output remain under the chosen state directory. Exit 0 means PASS, 1 means a graded failure, and 2 means a setup/error condition.

This is a native macOS adaptation of one public 2022 task, not the official SWE-bench Docker score, a representative benchmark, or demonstrably uncontaminated training data. A passing fixture grade does not establish model completion, tool correctness or resource safety; retain those separate native-run checks.
