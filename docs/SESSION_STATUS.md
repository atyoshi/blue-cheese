# Current verification — user's LLM configuration — 2026-10-13

At the user's request, loaded `~/bc.json` through the existing validated provider
loader, without editing that file or printing credentials. The isolated model
preview uses the user's served `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`, 300-second
call timeout, six model attempts, thinking disabled and the file's endpoint/output
settings. A temporary cached bootstrap configures only the practice runtime once;
rerenders never reapply settings or call the model. Preview: http://127.0.0.1:8505.
The prior offline preview remains separate on 8504. No operational history or
real telemetry was used; no models/datasets/dependencies were downloaded.

The live, six-record frozen investigation completed in **212.85 seconds** with
verdict **UNCERTAIN**, **6 successful model calls** (3 Investigator, 3 Falsifier),
**8 evidence queries**, 33 delivered records across queries and 6 unique retrieved
records. All 6 unique cited records belonged to actual run retrieval. The report
recognizes the shared flow/tuple and non-zero counters, distinguishes repeated
updates from independently measured transfer volume, and preserves unavailable
payload, DNS/TLS/reputation, authorization and endpoint context. Mechanical
validation and this manual review do not establish detection accuracy.

Firefox showed live model waits, handoffs, completion, the cited report and a
read-only operational-status answer during the run. Navigation did not start a
second investigation. A summary returned existing findings. The live test exposed
an integer-timeout widget type error and a duplicate chat submission when a
fragment escalated to a full-app rerun. Run budgets now consistently return float
seconds, and chat dispatch occurs once in widget callbacks. Regressions cover
JSON integer timeout rendering and one submission per explicit repeated question.

Two conversational responses were rejected for invalid JSON, without executing
work. The planner now includes its actual output schema explicitly in system
instructions and accepts only a single exact JSON code fence as a formatting
wrapper; schema/citation checks remain mandatory. Three formatting/schema tests
retain rejection of surrounding prose and forbidden actions. A validated model
`explain` intent now preserves its cited model prose as an answer instead of
replacing it with a generic view description; a regression covers that behavior.

The final live follow-up succeeded in **31.21 seconds**, returned an explanation
of the selected established TCP/443 flow, cited its actually retrieved record
`e2b4fc9dbca25522c9b73c97`, and retained UNCERTAIN and missing context. Offline
verification while the preview was stopped confirmed the saved report was
unchanged, only one run existed, and the synthetic analyst action was retained.
CLI summary/definition reads with the same provider loaded created no run.
Synthetic artifacts are in the temporary `bluecheese-live-model-ftui7g5y`
directory: `live-report.json`, `live-report.md`, `validated-chat.json`, and
`cli-reading.txt`. Diagnostics retain only field/validation metadata, not prompts,
credentials, model response bodies or private reasoning.

Final verification: **156 passed in 16.20 seconds**; Ruff and diff whitespace
checks passed. All automated tests remain mocked/offline. Firefox lost native
window access (`cgWindowNotFound`) again during the final post-fix UI recheck.
The last successful model explanation was verified through the same runtime
response path with the preview stopped, then persisted for inspection in the
restarted preview. The successful final response was not visually rechecked
during a concurrent selection change. Live cancellation and live follow-up
revision execution were not exercised; deterministic coverage remains. The
operational runtime was unchanged. This is one server's compatibility check,
not commercial readiness or a completed broader roadmap.

# Previous verification — Firefox retry — 2026-10-13

The user-requested Firefox retry succeeded against isolated synthetic state on
localhost 8504. Reviewed input → selected alert → real retrieval → cited findings
→ saved analyst action, actual tab changes, scoped explanation, trace filtering,
refresh and restart. Responsive desktop (1,280px) and narrow (600px) views were
inspected. No real model calls or operational investigations were started.

Found and corrected stale case metrics/engine state after completion, cramped
narrow evidence/chat columns, and a local-time timeline labelled UTC. Case status
and engine now share the independent activity fragment; saved-run labels omit
transient status, practice controls refresh independently, narrow columns stack,
and the case timeline uses a UTC scale. Verified these changes in Firefox,
including automatic completion state and the 12:00 UTC timeline. A new regression
checks the header's persisted Running → Failed transition without rebuilding the
case workspace. Full regression verification: **151 passed in 15.75 seconds**;
Ruff and whitespace checks passed. The UTC display correction was also checked
in Firefox after a clean process restart.

Two synthetic investigations were explicitly started for the journey/completion
checks. Offline inspection with the server stopped confirmed two COMPLETED runs,
thirty practice records, six snapshot records and five queries/nineteen delivered
records per run, retained analyst history, and an empty parent operational
workspace. The temporary review server was restarted at http://127.0.0.1:8504;
saved findings, decision and all checkpoints reappeared. The operational server
was not changed. See [the review record](GUIDED_INVESTIGATION.md#review-record--2026-10-13).

Firefox's initial `cgWindowNotFound` blocker is resolved. This short manual
review does not establish comprehensive accessibility, long-session reading
stability or detection accuracy. The separate real llama.cpp walkthrough remains
pending user initiation. Broader master-plan choices remain deferred.

# Implementation verification — guided investigation and conversation — 2026-10-13

Implemented the next milestone's software workflow. **Practice investigation**
uses the existing thirty-record synthetic fixture in a separate, exclusively
locked `STATE/practice/evidence.duckdb`. Loading, selecting and navigating do not
start work. Five read-only checkpoints reflect input, selection, recorded
retrieval, COMPLETED analysis and a saved analyst action. Optional model settings
apply only to practice; no operational evidence or history is imported there.
Practice follow-up proposals and successor runs remain in the practice workspace.

Cases show target, fixed snapshot identity, engine and live/saved state above
stateful tabs. An independent activity header reports real operations, elapsed
model waits, completed queries and delivered counts, with **Review findings**
after persistence. Role details and the chronological role/type-filtered trace
expose operation IDs, implementation, timing, arguments, counts, truncation and
outcomes; returned records are inspectable beneath their queries. Missing
historical details are labelled unavailable. Query audits and timeline events are
cross-checked in tests. Timeout, cancellation and budget outcomes remain distinct.
No prompts, credentials, private reasoning or invented progress were added.
Existing database migration SQL/checksums are unchanged; this extends JSON audits.

GUI and CLI share immutable captured `ViewContext` and read-only `summarize` and
`explain` handling. Definitions and operational state work offline; descriptive
answers use selected, snapshot-bound retrieval and inspectable IDs, with explicit
sample limits and unknowns. Case connection selection highlights a single graph
edge and filters an evidence drawer. Submitted questions retain their original
tab/selection even if navigation changes during a model response. New analysis
remains a proposal or explicitly approved task. Terminal `/summary [RUN_ID]` and
`/explain TERM` preserve existing structured slash inspections and terminal
escaping. Actual bounded command output enters terminal model context, with that
transmission stated in its approval. Proposals never establish execution.

Analytical pages preserve reading state by refreshing activity/chat separately
from evidence. **Refresh now** explicitly reloads evidence; keyed tabs, filters
and selections persist. Completion does not force another tab. Automated tests
found and corrected an invalid fragment-only chat rerun during a full-page run.
AppTest does not support user tab clicks in this installed version; captured-tab
logic has a separate test, while browser interaction/scroll stability still needs
visual verification.

Measured verification: `.venv/bin/pytest -q` — **150 passed in 13.57 seconds**;
`.venv/bin/ruff check src tests` and `git diff --check` passed. Twenty-four new
synthetic test cases cover read-only intents with an unavailable model, all plain
term definitions, actual CLI command context and explicit targets, bounded
connection summaries, captured model selections, actual trace/query agreement,
practice journey/decision/isolation/repeated refresh, timeout, source gap and
interrupted restart. Existing failure, slow-model, cancellation, citation,
ingestion, CLI and legacy regressions remain. Automated tests made no external
model calls or downloads.

Firefox was opened against an isolated synthetic review server on localhost
8504. The initial application header loaded, then native UI access failed with
`cgWindowNotFound`, including reconnection/reset attempts. No practice checkpoint
received a completed visual review. Desktop/narrow layouts and reading position
remain unverified. The isolated review server was stopped; the operational server
and database were not restarted or used for this review. No live model call was
made. The separate user-initiated walkthrough using existing llama.cpp settings
is documented in [GUIDED_INVESTIGATION.md](GUIDED_INVESTIGATION.md).

Restart the app process after upgrading cached runtime code, then open **Practice
investigation**. This establishes synthetic workflow behavior, not detection
accuracy or commercial readiness. Live walkthrough/visual acceptance and the
choice of shadow evaluation, case grouping or additional context remain pending;
no broader master-plan completion is claimed.

# Previous workflow verification — 2026-10-13

The operational GUI now follows the small-security-team alert-to-decision milestone
in [WORKFLOW.md](WORKFLOW.md): priority-ranked alert pages, named case targets,
frozen evidence, contextual asynchronous chat, real per-run operations, cited
findings, local assignment/disposition and retained history. Broader master-plan
work remains deferred until this basic journey is useful and dependable.

Schema migration 6 adds case workspace metadata, run seed context, incremental
activity and local chat transcripts. Previous migration SQL/checksums remain
unchanged. Accepted raw evidence and existing reports are retained. Runtime changes
require one controlled process restart; browser refresh cannot update cached objects.

Measured verification: **126 passed in 11.32 seconds**, outside the filesystem/network
sandbox because Unix-socket tests require binding local sockets. Ruff and diff
whitespace checks passed. Eight new workflow tests cover the synthetic analyst
journey, snapshot/parent revision integrity, assignment and chat persistence,
actual activity, fabricated-citation rejection, async duplicate/cancel behavior,
priority paging and new-source activity without mutating old snapshots. Existing
CLI, presentation, ingestion, operations and provider regressions remain included.

Firefox review used isolated synthetic state on localhost port 8503. Home and
named-case views were inspected at a narrower desktop window. It exposed squeezed
card controls and counters; controls now occupy the card width, columns wrap,
and cumulative counters are collapsed behind a status panel. The operational
DB was not used for preview or test investigations. No real model or live packet
capture was used in this verification. Detection quality, current real-model GUI
compatibility, Docker and authenticated shared deployment are not established.

Chat shares the CLI's schema-validated task planner. GUI context uses bounded
normalized observations retrieved from the selected snapshot, current health,
recorded operations and saved findings. Citation IDs are checked against actual
chat retrieval; semantic support still requires review. Source/test changes and
new investigations are concrete proposals with an explicit execution control.
Local read commands remain available without a model. Assignment names are local
attribution, not authenticated users. Activity and chat never dispatch work on
rerender. New analysis remains bounded, and cancellation is cooperative.

Operational restart: gracefully stopped the verified prior server and relaunched
`./bluecheese --data-dir bluecheese-operations gui --port 8501`. Firefox confirmed
the new Needs attention screen loaded the existing 194 stored alerts and showed
the recorded continuity warning. No operational investigation or model call was
started for this check. Model settings remain process-local and must be reapplied
after restart if previously entered only in the GUI. The synthetic preview on
port 8503 uses a separate state directory.

## Previous verification — 2026-10-12

Live CLI investigation follow-up: verified the user's llama.cpp endpoint/model
using synthetic probes and an offline backup/restore copy of operational evidence.
The 20-second call timeout was insufficient; a report took 121.79 seconds even
with thinking disabled. At a tested 300-second call timeout, the Investigator
completed, then the LLM Falsifier exhausted the remaining shared retrieval budget.
The provider now requests a structured final assessment when no tool calls remain,
without increasing the retrieval cap. A subsequent live run completed both model
roles and citation validation in 334.5 seconds (5 model requests, 6 tool calls),
with verdict UNCERTAIN. Test runs are isolated from operational history.

Operational run budgets now scale with bounded model-call settings in CLI, GUI
and scheduled runtime paths. Call timeout is configurable up to 600 seconds;
optional `enable_thinking` sends the llama.cpp chat-template extension. Timeout
and connection failures are distinguished, and cancellation survives a transport
error. The user's JSON config now uses timeout 300 and thinking disabled, with
an owner-only original backup. Concise report instructions preserve missing
evidence and bounded coverage. Source/ingestion routing was clarified after a
live misroute; remaining live planner checks selected the expected task types.
Measured regressions: **118 passed in 10.26 seconds** outside the sandbox; Ruff
and diff whitespace passed. Live GUI behavior and detection accuracy remain
unverified. Evidence-source management and decision-model evaluation are deferred
notes in ROADMAP.md. Details: [CLI model validation](CLI_MODEL_VALIDATION.md).

CLI model planning follow-up: ordinary chat with a configured provider bypasses
keyword routing. A schema-validated model proposal selects an allowlisted task,
then enters its existing approval handler. Evidence interpretation is directed
to investigation; slash commands remain direct and offline routing is retained.
No shell dispatch, provider selection or recursive chat action is exposed to the
planner. Declined tasks, invalid proposals, original question preservation,
terminal escaping and approved real scoped retrieval are covered by tests.
Measured targeted checks: **45 passed in 4.02 seconds** outside the sandbox
(existing GUI socket test requires socket binding); Ruff and diff whitespace
passed. Live planner behavior against the user's server remains unverified.

Remote HTTP follow-up: provider JSON accepts `allow_insecure_http: true` together
with `allow_remote: true`. Equivalent terminal flag, GUI checkbox and
`BLUECHEESE_ALLOW_INSECURE_HTTP=true` environment opt-in are available. HTTPS
remains the remote default; HTTP opt-in alone does not authorize remote access.
Base URLs still resolve to OpenAI-compatible `/v1/chat/completions`, independent
of the chosen port. Evidence and credentials on HTTP are unencrypted.
Measured checks: **37 passed** across provider, terminal, demo UI, console and
agent-provider tests; Ruff and diff whitespace passed. No live server requests.

Interactive terminal follow-up: `./blue-cheese --cli`, `./bluecheese --cli` and
`bluecheese chat` open the operational terminal. Existing GUI defaults and legacy
subcommands remain. Slash commands and common task requests cover EVE import/follow,
triage, network summaries, investigations and saved reports. Tasks default to
declined approval; an approved investigation covers bounded agent reads/model
requests and report persistence. Actual activity events stream during the run;
Ctrl-C requests cooperative cancellation. With a provider, ordinary chat uses
separately approved structured model task planning, with up to three prior chat
exchanges and no telemetry/task results. Valid allowlisted proposals enter the
existing task approval handlers without requiring slash-command reentry. Evidence
interpretation is directed to the cited investigation workflow with the original
question; explicit slash commands bypass planning. Offline keyword routing remains.
Terminal control characters in data/model output are escaped.

Provider settings accept a selected JSON file (`config.example.json` documents
the fields), flags overriding that file, or existing environment configuration
when no settings are supplied. `/config` prompts for a path, `/rules` restores
offline rules and `/test` approves synthetic capability probes. Local/remote URL
policy and schema/citation validation reuse the existing provider. One-shot EVE
imports are capped at 16 MiB and use bounded ingestion/quarantine/cursors with
source identity; unfinished lines remain uncommitted. Automatic investigations
remain disabled. The same state lock excludes simultaneous GUI/terminal use.

Measured checks: **95 passed in 8.01 seconds**, Ruff and diff whitespace passed.
Nine new tests include an actual launcher/config/flag session, declined tasks,
offline investigation/report persistence, source identity/duplicate positions,
quarantine/cursor resume, secret-safe config errors and untrusted terminal output.
The full suite requires execution outside the sandbox for existing Unix socket
tests. Live OpenAI-compatible server behavior remains unverified; no dependencies,
real model calls or downloads were added. README includes launch/workflow details.

Live activity follow-up: every operational workspace now shows the current agent
role/action, elapsed time and a handoff timeline. Rule policies, model-response
waits and evidence tools are labelled separately. Actual execution emits bounded
events under the runtime lock; a read-only one-second UI fragment observes them
independently of telemetry refresh. The latest run retains at most 128 events.
Saved reports include activity through report preparation. No extra workers,
artificial delays, model calls on rerender or private reasoning display were added.
Completion, cancellation, failed steps and budget exhaustion stop the active view.

Latest checks: `.venv/bin/pytest -q` — **86 passed in 6.95 seconds**;
`.venv/bin/ruff check src tests` and `git diff --check` passed. New deterministic
tests pause a scripted model transport to inspect live waits/handoffs and GUI
rerenders, then cancel it; they also verify saved traces, reset isolation, failed
and incomplete terminal states, bounded history and stopped elapsed time.

Agent/provider follow-up: the operational sidebar now exposes **Agents and model
endpoint** with an OpenAI-compatible base/full URL, Investigator and optional
separate Falsifier model, in-memory API key or environment reference, remote HTTPS
opt-in, output mode and call/token/timeout limits. Settings last for the runtime
process and cannot change during active/pending work. Explicit connection testing
uses synthetic data to check tool calling and structured output for each model.
GUI rerenders never call models or start investigations.

The model Investigator and Falsifier can request allowlisted typed evidence queries
through the existing snapshot-bound broker. They share tool/time budgets and a
six-attempt default provider cap; argument, output-schema and retrieval-citation
validation remain software-enforced. The case question now enters model context.
Role/model attempts and available token usage appear in completed/cancelled/incomplete
reports and their GUI/Markdown audits. Triage/correlation/report assembly remain
deterministic; the presentation demo remains offline. The original one-call adapter
is retained through `BLUECHEESE_MODEL_MODE=summary`.

Measured follow-up checks: `.venv/bin/pytest -q` — **82 passed in 6.45 seconds**;
`.venv/bin/ruff check src tests` and `git diff --check` passed. New scripted tests
cover model acquisition, critic revision, persisted successful attempts, invented
citations, forbidden tools/scope arguments, shared budgets, cancellation,
capability probing and GUI apply/test/rerender/rule fallback. No network calls,
models, datasets or dependencies were added. Live server compatibility, prompt-file
versioning, schema repair, cost reservation and configurable redaction profiles
remain unverified or pending; this is not full master-plan completion.

Target: one customer's on-prem SOC with multiple analysts. Access controls are
still pending; see [commercial release gates](RELEASE_GATES.md).

Operational entry point: `./bluecheese --data-dir bluecheese-operations gui`.
The current verification instance runs at http://127.0.0.1:8502. Native GUI EVE
paths now start empty unless configured; Docker's `/telemetry` is not a host
default. Source preflight rejects missing files, directories and FIFOs before
starting workers or recording coverage incidents. The presentation external-file
control uses the same preflight. Doctor expands home paths and rejects incomplete
schema histories. A file that disappears after validation still stops visibly.

Measured checks: 71 tests passed on macOS/Python 3.13, including local Suricata
integration and missing-path correction/reconnect; Ruff, dependency consistency
and diff whitespace checks passed. Offline doctor confirmed the existing
capture-derived EVE artifact is readable. Docker execution and live model endpoint
compatibility remain unverified. Existing capture and SQLite evidence are preserved.

The default `./bluecheese` command now launches the operational GUI. The sidebar
selects file tail or a Unix stream receiver. A real local Suricata process sent
fixture-derived alert/flow EVE records through the receiver in integration tests.
Spooling precedes parsing; EOF, incomplete prior records and the 256 MiB quota
stop visibly. Socket permissions are owner-only and only owned paths are unlinked.
The Overview includes a zoomable UTC timeline, severity/protocol charts, a directed
IP map, endpoint/connection drill-down and optional record explanations. Aggregates
use a labelled bounded recent-record window, not fabricated telemetry.

The operational UI now uses a compact dark/teal workspace, collapsible sensor
setup, Activity/Connections/Evidence tabs, shared visual filters with reset,
readable record labels, refresh controls and concise reports with intact exports,
citations and retrieval audit. Native Firefox review identified accidental wheel
zoom; time zoom now requires Shift. Expanded AppTest checks passed, including
filter/navigation behavior and immediate socket button state. See
[UI/UX review](UI_UX_REVIEW.md) for findings, measured checks and the unverified
narrow-screen/accessibility/cross-browser work. This does not close SOC access
control or commercial release gates.

The following entries are historical and describe earlier revisions.

# Session status — 2026-10-05

All six implementation tasks completed and committed/pushed separately to `origin/main`.

| Task | Status / evidence |
|---|---|
| 1 Baseline | Passed. Existing CLI/SQLite/Suricata retained; initial 10 tests passed. No applicable AGENTS existed; added architecture invariants. |
| 2 Scenarios / normalization / DuckDB | Passed. 30-record synthetic suspicious fixture; seed-73 poisoned copy; benign/insufficient fixtures. Exact accepted raw lines, parsed JSON, shared canonical alert/flow model, source/byte locators, stable IDs; scoped bounded parameterized tools; idempotent imports. Evaluator manifest excluded from telemetry and wheel. |
| 3 Investigation / Falsifier | Passed. Offline provider protocol; evidence-derived policy; real IP counterevidence query; contradicted/not observed/not available; six-call/five-second defaults; ablation; retrieved/scope/snapshot citation validation; JSON/Markdown. |
| 4 Presentation | Passed. Evidence, Investigation, Comparison, Live tabs; safe code/JSON log display; citation inspection and downloads; matched-settings comparison. Two AppTest interactions verify scenarios/findings/evidence and rerun/worker invariants. |
| 5 Continuous ingestion | Passed. One cached runtime, one worker, serialized DuckDB commands. Bounded reads/lines; pending partial records; malformed/oversized quarantine; atomic inserts/cursors; retry and restart/resume; distinct identical lines. Replay advances in background; live reports use fixed snapshots. Gap detection stops visibly. |
| 6 Verify / package / walkthrough | Passed for native presentation and packaging files. Locked fresh venv; 27 tests passed in 5.26s (no skips), Ruff passed, pip check passed. Coverage 74% (732/994 statements); AppTest executes the UI but this coverage run does not instrument its module. Wheel verified: four telemetry fixtures, no evaluator manifest. Compose config valid; Docker build/launch unverified (socket permission denied). |

## Run / exports

Entry point: `src/bluecheese/interfaces/demo.py`.

```bash
source .venv/bin/activate
python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501. Native server launched separately with locked dependencies; `/` and `/_stcore/health` returned successfully. Browser automation was unavailable; AppTest exercised the UI. Linux/Python 3.14.7 tested; macOS intended, unverified. README has fresh-install commands.

Docker: `mkdir -p telemetry` then `docker compose up --build -d`; `docker compose down` stops and preserves state. Localhost port only, UID 10001, persistent evidence volume, read-only external telemetry, separate writable replay spool. Build attempt blocked by `/var/run/docker.sock` permissions; no container execution claim.

Generated files in `demo-exports/`: `suspicious-clean.{json,md}`, `suspicious-poisoned.{json,md}`, `benign-clean.{json,md}`, `insufficient-clean.{json,md}`. They are local generated artifacts, ignored by Git. Recreate while app is stopped: `python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports`. Associated evidence persists in `bluecheese-data/evidence.duckdb`; do not run two processes on that DB.

Expected on/default results: suspicious clean SUSPICIOUS (alert + five active flows), poisoned UNCERTAIN (alert + four active flows, one zero-byte closed contradiction), benign BENIGN_CONFOUNDER, insufficient UNCERTAIN. Falsifier off: both suspicious variants SUSPICIOUS. These describe this rule policy, not LLM performance. Full five-minute script: docs/DEMO.md. Planned product: Blue_Cheese_Master_Implementation_Plan.md.

## Limits / deferred

Only alert/flow presentation normalization; first-alert investigation; 100-row query cap with report warning. Cooperative elapsed-time budget, not hard preemption. Replay cycles its fixture (new byte positions, intentionally repeated telemetry). Accepted raw text is exact; oversized quarantine retains only a labelled bounded prefix. Append-only contract: device/inode, size and committed 4 KiB prefix catch common gaps; arbitrary in-place edits or truncate/regrow between polls are not guaranteed detected. Full rotation recovery deferred. Stop/reset by selecting a new source/state after a detected gap.

Deferred as requested: five-role orchestration, vector RAG, real dataset downloads, model training, packet capture, new model/backend integrations, exhaustive rotation recovery, load testing, multi-platform CI and extra documentation. No existing real model provider was present. Docker execution/macOS remain unverified. Existing local `bad.pcap` and `real-data/` were left untouched and uncommitted.

Next three tasks:
1. Build/launch Compose under a user with Docker socket access; verify volumes and external telemetry permissions.
2. Run the locked native walkthrough on macOS; record actual portability issues/results.
3. Design explicit source-generation/reset and full rotation recovery, with gap/restart tests, before relaxing append-only limits.

## Master-plan implementation update — 2026-10-08

Working-tree changes, not committed: implemented canonical state-directory OS
locking before presentation store connection/schema initialization (W17 writer
exclusion), and atomic self-contained report bundles with offline verification
(W12 export integrity slice). No schema migration. Existing exports remain
compatible; `--bundles` adds version-1 historical directories without overwriting.
README documents commands; ROADMAP inventories unfinished milestones.

Measured Linux checks:
- `.venv/bin/python -m pytest -q`: 30 passed in 7.62 seconds.
- `.venv/bin/ruff check src tests`: passed.
- Export command with temporary state/output and `--bundles`: four reports and
  bundles generated with existing expected verdicts.
- Offline verifier on poisoned bundle: valid, six cited records, snapshot 63.

Lock tests include another process, a symlinked state directory, competing opens,
and reopen after close. Bundle tests include tampering, recomputed-checksum identity
failure, unseen citations, immutable destination and temporary cleanup.

This does not complete the master roadmap. Dedicated DB worker, rotation recovery,
materialized cases/snapshots, backup/retention, real provider, richer claim schema,
research harness and additional adapters remain pending. Bundle hashes are integrity
checks, not authentication; normalized evidence verification currently uses the
shipped parser, not archived interpretation versions. macOS/Docker unverified.
User's deleted build prompt, untracked master plan, bad.pcap and real-data untouched.
Next three work packages are recorded in ROADMAP.md.

## Continued master implementation — 2026-10-08

Specification used: `Blue_Cheese_Master_Implementation_Plan.md`, Sections 4, 9,
11–13, 17, 24; work packages W05/W08/W11/W12/W17/W18/W21/W23/W24/W25.
Base revision `ef6dc4f`; changes remain uncommitted. This supersedes the preceding
update's pending database-worker/case-history statements; full milestones are
still incomplete. ROADMAP.md records package boundaries and next dependencies.

Changed responsibilities:
- One bounded database worker now creates/uses/closes the runtime connection;
  providers run outside lifecycle/database locks. Queue capacity 64, one active
  provider run, startup failure cleanup and stopped-runtime rejection.
- Additive checksummed schema migration 1 preserves evidence/cursors and adds
  cases, frozen snapshots/interpretations, runs and persisted tool activity.
  Unknown/modified versions fail closed. No reset required for old schema.
- Atomic case revisions use fixed membership (10,000-record cap) and interpretation
  digests. Saved runs, parent-linked successors, interrupted recovery and
  completed/incomplete/cancelled/failed statuses are durable.
- Candidate structure/citation validation and 64 KiB per-call delivery cap added;
  only delivered records enter citation visibility. Failed tool dispatches consume
  the call budget. Cancellation and elapsed-time limits remain cooperative.
- Triage's legacy API retained; presentation triage groups/prioritizes visible
  alerts. Correlation and Orchestrator are now implemented, not placeholders.
  Conservative source/sensor/time/flow/tuple links show provenance and ambiguity.
  One seed group per run; all logical roles share the same broker/budget.
- UI shows triage/correlation, saved history, successor revisions and background
  work/cancellation. Bundles use frozen interpretations and snapshot manifests.
- Offline backup/verify/restore commands keep the state lock through checkpoint,
  close and copy. Restore requires empty state; raw evidence, reports and traces
  round-trip. External telemetry/spools are excluded; locators are not rewritten.

Measured Linux checks:
- `.venv/bin/python -m pytest -q`: 45 passed in 11.44 seconds, no skips.
- `.venv/bin/ruff check src tests`: passed.
- `.venv/bin/python -m pip check`: no broken requirements.
- `git diff --check`: passed.
- Legacy CLI help and new backup command help execute successfully.
- Fresh CLI export → offline verification → backup → restore → export → offline
  verification passed using `/tmp/bluecheese-master-check-9voivcth`. All four
  scenario verdicts preserved; poisoned and restored-clean bundles each verify
  six referenced records, snapshot 63. No real network/model calls.

Remaining boundaries: no full rotation recovery, durable ingestion scheduler,
manual case editing/merge/split, intermediate persisted workflow transitions,
retention/deletion, archived parser versions, real provider, research harness,
additional presentation sensors or measured workload envelope. Snapshots currently
copy interpretations, increasing disk usage; they are scope-wide while correlation
proposes a narrower seed neighborhood. Case questions label scope; the demo rule
policy does not answer arbitrary questions. macOS/Docker execution unverified.
Legacy CLI/SQLite/PCAP/web paths retained. User's deleted build prompt and untracked
master plan, bad.pcap and real-data remain untouched. No dependencies added.

Next three dependencies: explicit source generations/rotation recovery; bounded
case scheduling/recoverable work leases; real-provider configuration/capability
contract. See ARCHITECTURE.md and docs/adr/001-local-runtime-and-snapshots.md.
