# TaskboardLite

This disposable standard-library-only fixture records project time entries.
Run `python3 -B -m unittest -v` and `python3 -B -m taskboard_lite.cli summary data/entries.csv`.
Launch with `python3 -B -m taskboard_lite.server --db taskboard.db --seed data/entries.csv --port 8765`.
Use only the newly started loopback server and this repository. Do not install dependencies.

CSV fields are exactly `id,project,minutes,date`; IDs and projects are nonempty strings, minutes nonnegative integers, dates canonical YYYY-MM-DD. IDs are unique. Imports must validate the complete batch before any writes. Dates are compared using half-open ranges: start included, end excluded. Invalid requests return HTTP 400 JSON with an `error`; invalid CLI input exits 2. Successful creation/import returns 201; reads/edits return 200. The contract in TASK.md takes precedence over incomplete fixture behavior.
