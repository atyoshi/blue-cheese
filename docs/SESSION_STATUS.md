# Matched live campaign running in the background — 2026-10-15 UTC

The user authorized the 14-hour / 24-investigation / maximum-144-provider-request
campaign, then explicitly requested independent background continuation through
Codex usage interruptions, with review later. Existing Qwen model/settings and
frozen baseline/candidate are unchanged. No new captures or models were downloaded.

Durable campaign: `/Users/yoshi/bluecheese-evaluations/20261015-matched-0543/`.
First provider request: **2026-10-15 05:44:54.744780 UTC**.
Original deadline: **2026-10-15 19:44:54.744780 UTC**. Pauses and restarts do not
reset it. A detached supervisor (initial PID 19623) owns the serial schedule.
`status.json` and `ledger.jsonl` record actual progress/request starts; results and
trial logs persist outside Git. Do not infer completion from this handoff.

Preflight verified 189 immutable recovered-archive checksum entries (mutable
`ui-server.log` excluded), prepared source/check artifacts, matching requirements
locks, frozen source imports and unchanged safe provider settings. Six offline
supervisor tests passed, including deadline/call caps, incomplete-ledger rejection,
interrupted-trial recovery and duplicate-supervisor exclusion. VPN connectivity
was restored before the first model request; non-model checks consumed zero model
requests. The 278 Python / 18 Chromium checks below apply to frozen platform code.

The supervisor checks connectivity before each trial, persists request starts
before sending, caps request timeout by the original campaign deadline, and
rechecks source hashes. If connectivity drops it waits without model probes;
clock time continues. A supervisor/child ownership lock prevents duplicate runs.
After process loss, only unstarted schedule entries resume; interrupted/ambiguous
requests stay consumed and interrupted trials are not replayed. Reports generated
by the supervisor contain mechanical results only; semantic acceptance and release
gates remain pending source review. No mid-campaign platform changes are permitted.

To inspect progress, read the campaign's `status.json`, `ledger.jsonl`,
`supervisor.log`, per-trial logs, and eventual `REPORT.md` / `scorecard.json`.
If the supervisor has stopped, resume its original bounds with:

```bash
/Users/yoshi/blue-cheese/.venv/bin/python \
  /Users/yoshi/bluecheese-evaluations/20261015-matched-0543/tools/supervisor.py \
  --campaign /Users/yoshi/bluecheese-evaluations/20261015-matched-0543
```

A second supervisor is rejected while any existing supervisor/trial owns the
lock. Expired allowance is not renewed by resuming. If a process or machine stops,
review the saved ledger and current phase before any further action. After live
work finishes, source-review all completed reports, verify bundles and matching,
apply the [semantic gates](LIVE_LLM_MATCHED_EVALUATION.md), review normal GUI cases,
and write the actual final report. Do not claim human time savings or accuracy.

---

# Investigation reliability increment — offline verified

Implemented schema-derived final/correction guides, a bounded typed fact catalog,
role-delivered model citation checks, flexible Investigator/Falsifier allocation,
one shared correction per role, explicit local-processing deadline checks and
opt-in rejected-output retention separate from state/APIs/bundles. At six calls,
Investigator may use four and preserves two for independent review; unused calls
transfer. No model budgets, schema limits, HTTP retries or response modes changed.

**278 Python tests passed**, **18 Chromium tests passed**, Ruff and whitespace
checks passed. One existing Starlette test-client deprecation warning remains.
The final Python run followed the delivery-boundary correction; browser checks
cover the unchanged normal interface. Initial sandbox socket restrictions were
resolved by rerunning the affected suites with local-socket permission.
Five matched offline allocation scripts yielded four baseline completions and
five candidate completions, with no allocation regression in those scripts.
This does not measure real-model quality, latency or detection accuracy.

Pre-change baseline sources/hash metadata, candidate freeze, allocation results,
final test logs and a fixed 24-trial live schedule are in ignored
`build/verification/reliability/`. All four archived seed/EVE hashes were checked.
The baseline includes the prior uncommitted correction-guidance fix. Existing
user changes are preserved; this increment remains uncommitted.

See [implementation and retention behavior](INVESTIGATION_RELIABILITY.md) and
[matched live evaluation](LIVE_LLM_MATCHED_EVALUATION.md). The planned 14-hour,
24-investigation / maximum-144-request campaign requires separate authorization;
no live requests or operator messages were sent. Semantic release gates remain
unmeasured. Failed trials will remain in denominators; latency has no invented
failure penalty. Earlier campaign history follows unchanged.

---

# Recovered-evidence live rerun completed — 2026-10-15 UTC

The fresh campaign started from clean main `14beb049` at 01:58:22 UTC with a
04:58:22 UTC deadline. Four ordered pilots and two stage 02 reruns completed
within the allowance, retaining all 31 model calls and failures durably at
`~/bluecheese-evaluations/20261015-live-rerun-0158/`.

Stage 01 completed mechanically in 607.8 seconds and its 67-record bundle
verified. Stages 02/03 failed schema boundaries; stage 04 failed provider parser
HTTP 500. The requested stage 02 repeat failed schema validation; a narrow
schema-correction guidance change and same-seed retest then reached the Falsifier
but failed a URL fact bound to a DNS record. Strict validation remains enabled.
All trial EVE hashes, seeds, snapshot digests and actual memberships match the
recovered rules-host cases. These are separate from the lost original snapshots.

Manual review supports stage 01's source fields but flags imprecise HTTP byte
wording and a flawed TLS disconfirmation proposal; full semantic acceptance is
not established. Native Firefox review confirmed normal completed/failed cases,
real operations, cited findings/limits, Open disposition and Markdown export;
reading/refresh started no work. No analyst decision or GUI chat was made.

47 focused tests passed; Ruff and whitespace checks passed. Implementation and
project-log updates remain uncommitted on main; campaign artifacts stay outside
Git. See [actual rerun results](LIVE_LLM_RERUN_RESULTS.md) and
[next steps and possible fixes](LIVE_LLM_NEXT_STEPS.md). Provider reliability,
semantic quality, detection accuracy and analyst time savings remain open.

---

# Main-branch fixes and next live campaign handoff — 2026-10-14

The progressive-evaluation fixes and their regression coverage are being landed
on main together with the prerequisite scoped-comparison support. See
[LIVE_LLM_RERUN_HANDOFF.md](LIVE_LLM_RERUN_HANDOFF.md) for the next agent's
step-by-step plan, durable input paths, exact command, budgets, acceptance checks
and user-ready authorization prompt. No new live requests were made for this
handoff. The prior allowance is expired; submitting that prompt authorizes a
fresh bounded campaign. Captures, provider secrets and operational state stay
outside Git. The recovered campaign is preserved as a historical experiment.

---

# Progressive real-traffic evaluation — 2026-10-14

Four authorized Malware Traffic Analysis captures passed offline processing,
raw preservation, idempotent reimport and record reconciliation. Three live Qwen
runs failed on citation/format boundaries; the fourth started but its final
outcome was lost when temporary artifacts/processes disappeared during an
environment interruption. The three-hour wall-clock allowance expired. No
accepted live investigation or detection-accuracy claim follows from this campaign.

Recovered captures have matching original ZIP/PCAP hashes and durable evidence
under `~/bluecheese-evaluations/20261014-cnm99sk6/`. Their regenerated EVE identities
and selected scopes differ from the original live runs. Eight recovered comparison
reports complete, and 13 comparison/GUI/revision bundles verify. The normal GUI/API
workflow preserves decisions, summaries, scope and revision history without work
on reading/refresh; one explicit large-host revision completes.

Two native DuckDB 1.5.0 crashes on a 5,405-record host scope led to a tested patch
update to 1.5.6 in both package metadata and requirements.lock. A 5,500-record
subprocess regression covers commit/retrieval/restart/export/raw preservation.
Comparison settings record the DuckDB version. The provider prompt clarifies
same-claim fact citations, with a regression preserving strict rejection.
Final checks: 230 Python tests, 18 Chromium tests, Ruff, pip consistency and
whitespace checks passed. See [the evaluation report](REAL_TRAFFIC_RESULTS.md)
for actual timings, artifact-loss limits, a capture/reference discrepancy, test
logs and remaining live retests. Earlier sections below are historical.

---

# Application host investigations and factual recovery — 2026-10-14

This increment changes the actual evidence store, investigation runtime, provider
loop, API, contextual chat and React alert workflow. **Investigate source host**
freezes a separate same-source/sensor, five-minute host snapshot across destinations.
Connection cases and revisions preserve their scope. The alert drawer, case target
and explicit chat proposals carry the scope; executing a host proposal requires
the normal confirmation and does not mutate the existing connection case.
Migration 9 records scope while preserving migrations 1–8 and historical reports.

A diverse bounded host-context tool surfaces distinct protocol/destination/path
observations before repeated requests. Context remains separate from strict-flow
correlation, uses frozen membership and reaches model inputs and evidence exports.
Host questions ask about combined behavior. Capture labels and evaluator reference
answers remain excluded; there is no capture-specific verdict or alternate runtime.

Field-specific numeric/text fact schemas fix an output-contract mismatch. Up to
six relevant citations support a combined finding. One retrieved-fact correction
per stage shares existing global attempt/time limits, reserves independent review,
records the original rejection and revalidates the entire replacement. Persistently
wrong facts and unseen citations still fail. Chat receives explicit report
completion truth so a selected record cannot imply the accepted report is absent.

Measured checks: **224 Python tests passed**, **18 Chromium tests passed**, Ruff,
TypeScript/build, Prettier, pip consistency and whitespace checks passed. Initial
JavaScript is **101.0 KiB gzip**. Existing 14 visual baselines remain unchanged.
One Starlette test-client deprecation warning remains.

Two live host investigations using the same Grain model completed and retained
**MALICIOUS_ACTIVITY** after independent review. The first used six model requests
and took 723.8 seconds, including schema correction. The final typed-schema run
used an explicit two-request limit and took 461.3 seconds; both roles passed on
the first request. Its cited findings distinguish GET download, POST credentials
and GET protocol switch with correct numeric facts. Endpoint execution and theft
are not established by these fields. The frozen host scope held 1,076 records,
72 pairs and 64 HTTP records; the provider received a bounded sample.

Manual review still found overstatement and reversed direction in the unverified
hypothesis, plus a completion-status error in the first run's record-scoped chat.
Prompts/context address these; arbitrary prose correctness and false-positive rates
remain unproven. Three strict-schema chat rechecks returned HTTP 500 with a native
provider output-parser mismatch. A JSON-object compatibility check passed (44.6
seconds), including accepted completion and the selected GET/status/response-byte
facts. GUI chat now uses JSON-object responses with full local validation; report
roles and CLI format settings retain their configured behavior. Known native-parser
errors have an allowlisted diagnostic without exposing arbitrary error bodies.
A final updated-application chat check passed in 60.9 seconds with accepted status
and correct selected-record facts. External parser reliability remains a provider
validation boundary; automatic HTTP/timeout retries were not added. These successful runs establish this measured behavior, not
enterprise readiness, commercial performance or general detection accuracy.
See [workflow verification](ANALYST_WORKFLOW_VERIFICATION.md) for exact scope,
remaining semantic limits and ignored local artifact locations. Earlier sections
below are historical. Docker, shared hosting/authentication, human completion/time
savings and sustained capacity remain separate validation/release work.

---

# Grounded investigations and readable analyst workflow — 2026-10-14

Implemented the system-wide analyst readability and reliability increment. Chat
uses the configured model for ordinary reading questions, short paragraphs/lists,
case context and retrieval-bound citations. Offline answers and historical fixed
templates have readable presentation blocks. Shared interpretation guidance is
collapsed once; case-specific questions and actual analysis limits stay with the
findings. Source coverage, UTC time windows, source incidents, advisory scores,
failed-case recovery and per-request diagnostics are readable throughout the UI
and Markdown exports.

Targeted source/connection/time retrieval now filters before applying limits and
feeds correlation and the independent countertest. Fact-binding regressions reject
incorrect observable fields even with a valid retrieved citation. Fixed aliased
schema constraints, UTC relabelling, overbroad source-incident attribution,
unrequested chat actions, missing-target proposals and failed-run accounting.
Migration 8 persists bounded request diagnostics independently of final reports.
Model context/output bounds and a single budgeted schema/truncation correction
preserve citation rejection and global call/time limits. Failed-case fallbacks
retrieve the target first; timeout messages distinguish a configured limit from
actual elapsed time.

Verification: **210 Python tests passed**, **17 Chromium tests passed**, including
14 reviewed macOS screenshots. Ruff, TypeScript/build, Prettier, pip consistency
and whitespace checks passed. Initial JavaScript is **100.9 KiB gzip** (200 KiB
budget). One Starlette test-client deprecation warning remains.

Live Grain requests revealed failures beyond the original 60-second timeout:
missing claim citations, schema aliasing, long independent-review latency and
2,048-token output truncation. Earlier live chat responses passed format/citation
checks; manual review also found UTC conversion and unsupported role-retry advice,
now addressed in prompts/context and offline regressions. An attempt while disconnected from the required VPN
hit connection timeouts; those failures do not measure inference latency. After
VPN reconnection, evidence requests succeeded (39.8/13.4 seconds), followed by an
assessment (201.9 seconds) that needed schema correction. The correction returned
(111.9 seconds) but asserted `src_port` inconsistently with its retrieved source;
the factual validator rejected it before model Falsifier review. Schema corrections
now identify the failed schema rule without rejected values, with offline coverage.
All three VPN-connected chat questions passed format and retrieval-citation
checks (84.4, 33.4 and 27.8 seconds). Manual source review confirmed the summary's
three supplied A-record DNS requests, converted UTC times, 116 client-bound flow
bytes and 483-record snapshot. The answers reported the failed Investigator and
distinguished completed flow countertesting from unexecuted model review.

**No live end-to-end investigation completed successfully.** Provider reliability
and free-prose semantic quality remain open validation work; passing fixtures do
not establish detection accuracy or commercial readiness.

Local verification artifacts are under ignored `build/verification/` (Python,
browser and build logs plus isolated live state/request diagnostics). Live requests
used an existing local normalized capture; no datasets/models were downloaded and
no captures, credentials or operational transcripts are introduced by this commit.
Provider configuration is process-local and must be reactivated after a server
restart. Docker execution, other browser engines, screen-reader certification,
human completion/time savings and sustained production capacity remain unverified.
See [the workflow verification](ANALYST_WORKFLOW_VERIFICATION.md) for acceptance
scope and the comparison with documented professional investigation workflows.

Earlier entries below are historical; their counts and interface descriptions
refer to the corresponding earlier revision.

---

# Single analyst interface — 2026-10-14

Replaced the Streamlit console, presentation frontend, practice screens, and legacy
web frontend with the React/TypeScript interface served by
`bluecheese.interfaces.server`. `bluecheese gui` and default launch retain state
and port selection. The README walkthrough uses the normal source and case UI.
Existing CLI imports, SQLite evidence, investigation runtime, and report history
remain supported. Earlier entries below describe retired frontend behavior.

The interface includes light/dark themes, prioritized alerts, case findings,
source observations, linked timeline/connection/record selection, real activity,
contextual chat and explicit proposals, analyst decisions, exports, source settings,
and diagnostics. Shared tokens, portal overlays, keyboard tabs, reduced motion,
and bounded lazy-loaded assets replace the previous widget styling. Case IDs,
filter/pagination persistence, source counters, protocol timeline totals, and native
advice endpoint round trips have regression coverage.

Verification: **179 Python tests passed**; **14 Chromium browser tests passed**.
Ruff, TypeScript, Prettier, dependency consistency, and whitespace checks passed.
Twelve reviewed macOS screenshot baselines cover both themes and responsive queues,
case findings, and network views. Browser checks include rendered accessibility,
contrast calculations, long text/IPv6, literal HTML, narrow drawers, unsaved forms,
reduced motion, and a layout equivalent to 200% desktop zoom. Initial JavaScript
is **100.4 KiB gzip** against a 200 KiB budget. A fresh temporary wheel installation
served packaged assets, API, and health with empty initial state and no Streamlit.

Docker Compose configuration validates; Docker build/execution remains unverified
because the daemon is unavailable. No live model requests or operational evidence
changes were made. Other browsers, assistive technology, human task completion,
semantic accuracy, and detection quality remain unmeasured by these checks.

---

# README walkthrough verification — 2026-10-14

Updated README telemetry types, current GUI labels, decision advice, offline
capture/comparison instructions and test counts. Corrected stale quarantine help
in the console. Followed the local workflow in isolated temporary state,
including a fresh pinned installation, actual GUI/legacy HTTP startup, AppTest
connect/investigate/save decision, terminal tasks, fixture and real PCAP conversion,
offline comparison, bundle verification and stopped-state backup/restore/retention.
189 tests passed with 79% coverage; Ruff, pip and whitespace checks passed.
Docker configuration validates but the daemon is unavailable. No new live model
requests; native decision-model execution remains pending. See the durable
[README verification record](README_VERIFICATION.md) for exact scope and limits.

# Investigation assessments and optional decision advice — 2026-10-14

Implemented version-2 findings with separate activity assessment, impact, evidence
limits, typed observations/inferences, contradictory citations and case-specific
next checks. The model supplies one activity decision; software projects the
legacy verdict. Compact model reports permit three claims/two checks. Historical
version-1 reports and the one-call provider remain readable/compatible.

Optional native `/v1/systemone` advice is disabled by default. GUI configuration
and an explicit synthetic capability test are available; one bounded request per
run uses already retrieved evidence. Scores remain uncalibrated and cannot change
routing or analyst authority. Migration 7 persists scope, input references/hash,
model/policy, usage, timing and failure/interrupted states through the store owner.
Advice scope labels stay out of model context. DNS/HTTP/TLS context complements
unchanged alert/flow interpretations, with bounded strings and no bodies in model
inputs. GUI, contextual chat, Markdown and bundles include the new information.

Added offline capture preparation and isolated matched comparison commands. See
[assessment documentation](INVESTIGATION_ASSESSMENTS.md). Comparisons preserve
snapshot digests and equal settings, alternate order and record per-arm timing
variation. Human semantic reviews and analyst completion time remain unset until
actually reviewed/measured. Missing native configuration is NOT_CONFIGURED;
failed/incomplete/cancelled runs return a nonzero CLI status.

Measured verification: `.venv/bin/pytest -q` outside the socket-restricting sandbox
— **189 passed in 15.11 seconds**. Ruff and diff whitespace checks passed. Automated
tests use synthetic inputs/mocked models and include persistence/restart, invalid
scores, cancellation, unavailable endpoints, misleading advice, injected tools,
retrieval-bound citations, unchanged raw evidence and no calls on refresh.

Authentic capture processing: existing `bad.pcap`, SHA-256
`40743e4d6c0e3de4222b8a4e81ae54ed571ac6accb7bb19c0cd81a14caf7ef55`,
49,668,763 bytes. Installed Suricata 8.0.7 read 49,591 packets offline. EVE contains
194 alerts, 342 flows, 503 DNS, 93 HTTP and 57 TLS records (1,189 supported), plus
425 unsupported records. Capture/configuration/rule hashes and event timing are
recorded in `/private/tmp/bluecheese-case-study-20261013/capture-final/capture-manifest.json`.
Source/content corroboration matches the September 24 source page and incident
reference in `docs/evaluator/capture_case.json`; original archive checksum and
redistribution rights were not established. No capture/model/dataset downloads,
packet transmission or operational-state changes occurred.

Three initial live baseline attempts with the user's six-call/300-second/2,048-token
profile all failed: incomplete provider output, a timeout, and contradictory
activity/legacy-verdict fields. Artifacts:
`/private/tmp/bluecheese-case-study-20261013/live-verified-comparison`.
These failures led to the compact single-decision contract; they are not valid
malicious-traffic findings. The corrective four-call pilot completed in **452.94
seconds**, verdict **SUSPICIOUS**, with four successful model calls and six evidence
queries. It cites outbound HTTP POSTs and curl/Go user agents while preserving
unknown reputation, authorization and endpoint impact. The saved report rendered
in AppTest with no exceptions; refresh kept one run and the report unchanged.
Its offline bundle verified **22 referenced records** against the snapshot/retrieval
trace. Artifacts: `/private/tmp/bluecheese-case-study-20261013/compact-pilot`.

Pilot review exposed alert-heavy broad queries exhausting delivery bytes before
available `/api/credentials` HTTP records. Model agents now prefetch one 20-record
typed protocol slice when that protocol is already observed, within existing
scope and retrieval budgets. A regression verifies that this reaches later HTTP
records without sending oversized raw payloads. The first protocol-context
repetition completed in **643.13 seconds**, verdict
**SUSPICIOUS**, and surfaced `/api/credentials` and `/api/shell/agent`. Static review
found an unsupported claim that response lengths were request payload sizes;
that report is mechanically valid but not semantically accepted. The remaining
repetitions were interrupted rather than counted as valid results. Artifacts:
`/private/tmp/bluecheese-case-study-20261013/protocol-comparison`.

All model-input paths now project HTTP `length` to `response_length_bytes`, without
changing stored interpretations. Provider policy explicitly separates response
lengths and URL paths from request payload contents or successful theft. The
existing pilot bundle still verifies. Operator interruption now persists a
cancelled run and a partial comparison index, with exit status 130.

All three final live repetitions completed with **SUSPICIOUS** assessments,
**4 successful model calls and 7 evidence queries each**. Elapsed times were
**614.49 / 472.20 / 647.87 seconds** (median 614.49). They surfaced credential API
POSTs and the agent-channel endpoint while retaining unknown endpoint impact,
authorization and request contents. Their snapshot digests match. All three
offline bundles verify, with **22 / 22 / 24 referenced evidence records**.
Artifacts: `/private/tmp/bluecheese-case-study-20261013/semantics-comparison`;
`comparison.json`, `comparison.md`, per-run reports/bundles and `semantic-review.json`.

Static semantic review identified remaining method/status attribution errors in
the first report and timeline/timezone attribution errors in the second. The
third report's cited HTTP method/status/response-size observations align with the
inspected source records; its causal hypothesis remains unverified. These are
not consistently accurate autonomous malware findings. All three advised arms
are NOT_CONFIGURED, so no native-advice effect was measured. Human review fields
and analyst completion times remain unset.

A deterministic protocol-observation table now presents actual retrieved HTTP
methods, paths, response status and response length before the working hypothesis
and assessed findings. New reports persist these facts; historical views derive
only facts already retrieved for that run from its frozen snapshot. Narratives
are labelled as unverified/model-assessed rather than promoted to source facts.
The final case rendered in AppTest with GET /api/shell/agent → 101, 20 source rows,
no exceptions, unchanged saved report and three runs before/after refresh.
Source-table UI checks and the source-derived fact bundle regression passed.
The reused EVE artifact SHA-256 is
`d8a50fb4a442edbfc4062d3a65e3836040b73fe5c1bdcd4701fe65fbb5143460`;
generated EVE identities/statistics can differ between separate sensor conversions.

Native decision-model live validation and any genuine advice-effect comparison
remain pending a compatible configured model. The case study surfaces malicious indicators but does not establish an automatic
MALICIOUS classification or consistent narrative correctness. Analyst verification
and latency reduction remain professional release gates. No detection-accuracy,
calibration or analyst time-saving claim follows from these checks.

---

# Next session — advisory decision-model assessment — 2026-10-13

Documentation only: [decision-model research](DECISION_TRIAGE_RESEARCH.md) now
proposes advice for analysts and a bounded, labelled upstream model assessment
for the Investigator as the first application. Show suggested review importance,
uncalibrated option scores, scope, evidence references and important unknowns;
preserve insufficient evidence. The Investigator may disagree and must ground
findings in actual run retrieval. Two models reading the same records do not
provide independent corroboration. Analyst decisions and application controls
remain separate; scores alone cannot start work, reorder/suppress alerts, close
cases or authorize actions. Routing automation remains a separate future evaluation.

Next session should check native decision-model availability through the existing
`~/bc.json` configuration without printing credentials. Availability is not yet
verified. Compare investigations with and without advice for analyst usefulness,
finding quality, unsupported conclusions and anchoring, including confidently
wrong scores, missing telemetry, correlated records, disagreement and unavailable
classifiers. Verify retrieval-grounded citations and no work on navigation.
This follow-up adds no APIs, model downloads or runtime behavior; the roadmap
remains incomplete. Existing verification records below are unchanged.

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
was not changed. See the retired guided-investigation review record.

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
is documented in the retired guided-investigation document.

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
