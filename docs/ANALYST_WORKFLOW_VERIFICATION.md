# Analyst workflow verification — 2026-10-14

This increment addresses investigation reliability, factual grounding and reading
quality throughout the local alert-to-decision workflow. Existing evidence,
snapshots, reports and chat transcripts are preserved.

## Problems established from operational history

The latest two operational investigations failed on the Investigator's final
assessment after earlier tool calls succeeded. Both used a 60-second request
limit against the configured Grain model. A saved request to “summarize with
natural language” took the deterministic reading path and repeated a fixed
status/evidence/reminder template.

Additional defects identified and corrected:

- Broad IP retrieval applied limits before relevance filtering; early large
  alerts crowded out matching flows in both correlation and countertests.
- A persisted evidence selection could narrow an explicit whole-case summary.
- Shared schema objects coupled unrelated output constraints. Schema expansion
  now breaks those aliases; claim citations require at least one reference while
  contradiction and unresolved arrays may be empty.
- Failed runs lost detailed provider accounting. Migration 8 adds independently
  persisted bounded request diagnostics, including validation outcomes.
- Natural reading requests could produce action proposals. Their model schema
  now permits only an answer, with compatible reading labels normalized safely.
- Model timestamps could be relabelled UTC without conversion. Provider inputs
  now include an explicit UTC projection alongside the unchanged source timestamp.
- Live model review exceeded its 2,048-token output limit. Assessment schemas now
  bound individual fields and require compact output; one correction for schema
  or truncation errors shares the existing global attempt/time budget. Invalid
  citations and conflicting source facts are rejected without repair. Subsequent
  model context is bounded to 32 KiB, prioritizing selected and cited records.
- Failed-case fallback summaries showed early workspace alerts before the target.
  They now retrieve the selected alert first and then related records; displayed
  evidence links are limited to the displayed records.
- Socket timeouts could occur before the configured request limit. Error messages
  now label that value as the configured limit rather than elapsed time.
- Every source incident in a workspace previously affected every new report.
  New reports select incidents associated with their own evidence sources.

During verification, the running operational profile was changed to a 300-second
request limit. Provider settings and credentials are process-local; configure
the profile again after restarting the server. Request limits remain cooperative; cancellation waits for an active
request to return. Timeout retries are not automatic.

## Presentation contract

Findings, chat and Markdown distinguish case gaps, actual run limitations and
shared interpretation guidance. Known legacy reminders are classified through
exact mappings in the presentation layer; saved reports are not rewritten and
unrecognized warnings remain visible.

Model chat asks for short paragraphs and lists. Deterministic answers produce the
same presentation blocks directly. Citations and proposed actions have separate
controls. Historical prose, line breaks and simple bold/list formatting render as
escaped React text; log evidence remains code/JSON. Standard guidance is collapsed
once at workspace level. Exported Markdown preserves guidance and diagnostics in
separate sections and presents protocol facts in a table.

The review also covers case time windows, failed-run recovery, source coverage,
readable source incidents, capability-check outcomes, advisory scores, both themes,
long labels, narrow drawers, keyboard focus and preserved reading/editing state.

## Factual accuracy checks

`tests/fixtures/analyst_accuracy.json` is reviewed synthetic evaluator material,
never a provider input. It deliberately separates POST `/api/credentials` with
status 200 from GET `/api/shell/agent` with status 101. Response bytes are not
request-upload bytes. Tests check record associations, endpoint fields, UTC
conversion, immutable source time, snapshot isolation, relevant counterevidence,
case-specific gaps and recommendations, and unsupported compromise/theft claims
in the deterministic policy.

Optional source fact bindings in model claims are checked against actual retrieved
fields. Incorrect method/status/path/time/endpoint/value assertions fail even when
the citation ID exists and was retrieved. A full provider-pipeline regression
verifies rejection without an automatic repair of conflicting evidence.

These checks do **not** prove arbitrary natural-language claims, intent, attack
classification or model accuracy. A model can omit a binding or attach accurate
bindings to misleading prose; semantic review remains required. No LLM judge or
expected-verdict shortcut substitutes for that review.

## Workflow benchmark

The comparison uses documented investigation patterns from
[Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/incident-investigation)
and [Elastic Security](https://www.elastic.co/docs/solutions/security/investigate).
It is a workflow comparison, not a feature-parity claim.

| Analyst expectation | Implemented behavior | Evidence or remaining limit |
| --- | --- | --- |
| Prioritize and open a target | Alert review queue, named case, owner/disposition | Browser journey; prioritization is uncalibrated |
| Understand scope | Target, frozen membership and labelled time window | Snapshot/API tests and rendered review |
| Inspect supporting evidence | Linked records, citations, connection/timeline views | Scope and citation regressions; bounded evidence |
| Distinguish facts from assessments | Source protocol table, claims, unverified hypothesis, separate impact | Reviewed fact fixtures; free prose still needs review |
| Understand work performed | Real operation history, request duration and failure diagnostics | Mock failure/cancellation/restart tests |
| Ask follow-up questions | Contextual natural language and explicit case/record selection | Model-routing tests and browser presentation checks |
| Record a decision | Attribution, assignment, disposition, notes and history | Save/restart tests; local attribution is not authentication |
| Recover from failure | Saved evidence/activity, readable fallback, explicit new revision | Error and browser scenarios |
| Share a durable result | JSON/Markdown and evidence bundles | Export/integrity tests; integrity is not semantic truth |
| Operate as a shared enterprise service | Not implemented by this increment | Authentication, RBAC, shared deployment, scale and integrations remain separate |

Automated journey time is test execution time, not human analyst completion time.
No time-saved or commercial-readiness claim is made. A professional team still
needs to measure task completion, review effort and finding quality on its own
workflow.

## Measured validation

The complete offline suite passed **210 Python tests** and **17 Chromium tests**.
TypeScript/build, Ruff, Prettier, dependency consistency and whitespace checks
passed. Initial JavaScript is **100.9 KiB gzip** against a 200 KiB budget.

Live Grain verification did not produce an accepted end-to-end investigation.
Earlier requests demonstrated successful Investigator assessment and conversational
chat, but the independent model review timed out or exhausted its output tokens.
A later attempt hit connection timeouts while the workstation was disconnected
from the required VPN; those failures do not measure inference latency.

After VPN reconnection, two evidence requests succeeded in 39.8 and 13.4 seconds.
The assessment returned in 201.9 seconds but failed schema validation. Its single
bounded correction returned in 111.9 seconds, then failed the source-fact check
for `src_port`. The application rejected the conflicting assessment; the Falsifier
model review did not run. Failed-run evidence, diagnostics and labelled saved-state
fallbacks remained available. No successful result was substituted for failures.
Schema corrections now identify the failed schema rule without including rejected
values; this improvement has offline regression coverage.

All three VPN-connected chat questions passed format and retrieval-citation
checks (84.4, 33.4 and 27.8 seconds). Manual source review confirmed the summary's
three supplied A-record DNS requests, converted UTC times, 116 client-bound flow
bytes and 483-record snapshot. The answers reported the failed Investigator and
distinguished completed flow countertesting from unexecuted model review.

Model reliability and semantic quality therefore remain open validation work.
Local logs are under ignored `build/verification/`; no credentials, operational
captures or live transcripts are added by this change.

Browser baselines are reviewed macOS/Chromium captures; other browser engines, screen-reader
certification, Docker execution and sustained production capacity are unverified.
