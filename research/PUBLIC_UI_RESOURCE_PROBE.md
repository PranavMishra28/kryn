# Public UI resource-feasibility probe

Frozen before any model request for this probe. This is a **public
development** diagnostic on the existing TaskboardLite 06 fixture, not a
protected UI result, H1 comparison, or product candidate. Earlier isolated
browser-gateway trials stopped on sustained host-memory warning before the
first browser call. Those trials used a different browser service and host
state, so their result does not identify the cause.

**U1:** on the current occupied Mac, KRYN's already-installed browser MCP can
complete model inference and invoke a browser tool under the unchanged strict
two-warning research guard. One fresh KRYN Agent turn will use the released
v1.0.0 plugin, Qwen3.5-9B-6bit/oMLX, installed 96K model profile, Default
variant, full native browser/search MCP, 900-second cap, and no operator repair.
The fixture is `evals/runs/public-ui-resource-20261003`; its frozen Task06
prompt SHA-256 is
`8e0e6cc35ea2d9e67faac7aab40e99606bbc1c6e0506f2eae4a0eacf48912489`.
The suite manifest, model profile, driver and product plugin SHA-256 values are
`186fd74343eff01992b48ac7d29b9a01ed7543968da6048745e6c42e1ec63ab6`,
`05c4645f3b691ae09b239534c026a9da5fa929677e39cff3c0d867fe9e91fe52`,
`96d48ecf461764adbdb5440917366711b6413e94949a7e3dfe310043331644f6`,
and `24c55c06a0b9ba6fe126034247479004885af1bf349d2d47dfb365dcf1aefc3f`.
No application will be closed and no guard, installed config, browser policy,
task, or grader will be changed. A setup-only, non-task model warmup is allowed
and recorded before the turn.

The resource gate passes only if the guarded native turn records at least one
completed model generation and one completed browser tool call before any
resource abort. The stricter **task acceptance** gate separately requires the
native turn to finish, frozen automatic checks, independent browser evidence
for every manual Task06 criterion, preserved tests/data, and a clean resource
verdict. The task requests evaluator-controlled 503 injection; this probe has
no automated injection service, so that manual criterion must remain
`NOT_TESTED` unless actual independent evidence exists. An agent's claim or
source code alone cannot pass it. Any guard stop, missing telemetry, browser
dispatch error, or timeout is retained as a failure/limitation. One attempt
only; do not retry an unchanged resource-gated condition.

Record model requests, browser tool calls/errors, pressure, swap, loaded state,
power, wall time, frozen grader, and any independent browser evidence. A pass
would show only that this different *public* browser path is feasible under
the observed host state; it would not prove that the isolated gateway is at
fault or that a protected grader boundary exists.

## Observed result

The one frozen Agent turn started with the model loaded and idle on AC power.
It completed 55 native step-finish events, made 74 tool calls, and invoked 35
browser tools (29 completed, 6 errored). Navigation, screenshots, form input,
clicks, snapshots, console and network inspection all ran through the existing
browser MCP. This demonstrates **initial model-facing browser dispatch** on
this public path. After 364.882 seconds the unchanged strict guard observed
sustained host-memory warning and interrupted the turn. Sampled swap growth
was zero and peak sampled oMLX physical footprint was 13.84 GB. The session
and runtime settled. The preregistered sustained resource gate therefore
**failed**; the earlier isolated-gateway prefill failures cannot be attributed
causally to that gateway from unmatched host and browser conditions.

The frozen automatic grader passed both API/original tests and found the
existing test and data files unchanged. Independent Chrome 154/Playwright
1.55.0 checks used a fresh browser context and disposable server/database.
They confirmed valid save and reload, evaluator-injected 503 followed by one
persisted retry, responsive Save-button bounds and saved screenshots, plus
console/network inspection. Invalid form input triggered native HTML validity
but produced **no persistent accessible error message**, so the frozen manual
review records five passes and that one failure. The resulting Task06 grade is
`FAIL`, independently of the resource abort. The Agent also created the
`.fail-next` marker itself during its own testing, contrary to the prompt's
evaluator-control instruction; the later independent evaluator injection
proves code behavior, not correct Agent procedure. Browser call errors included
startup connection refusals, stale element references and invalid fill
arguments; the Agent recovered from some but did not finish.

The compact development receipt is in
[history/development.jsonl](history/development.jsonl) as
`public-ui-resource-20261003`. Raw Agent/browser evidence, independent QA
script, screenshots, frozen grade and a private 82-run-file/7-QA-file manifest
remain outside the tracked repository; its SHA-256 is
`881d93b8e5718f9d53cd06c546bfb38b9c86f639a4f105a07a9c7a24bf1f1330`.
The result supports a narrower conclusion: model-facing browser operations
are possible for several minutes on the occupied host, but the strict guarded
turn and full UI task did not pass. No product or resource-guard change is
promoted, and the same resource-gated condition will not be retried.
