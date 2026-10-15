# Investigation reliability increment

Implemented after the [six-trial live rerun](LIVE_LLM_RERUN_RESULTS.md), preserving
strict validation and the existing Investigator/Falsifier provider protocol.
These changes have offline coverage; live reliability and latency are unmeasured.

## Behavior

The final-turn and correction instructions include a field guide derived from the
actual report schema. Schema limits are unchanged. Each model receives a typed
fact catalog for its delivered observations. Catalog values and factual validation
share one projection; missing or unrepresentable fields are not suggested.
Observations and catalog share the existing 32 KiB initial/review context budget.
Tool deliveries are bounded by available transcript space, up to 16 KiB, and
disclose omissions. Selected evidence, candidate citations and known counterevidence
are required; an oversized required set fails visibly. Complete messages retain
the 64 KiB limit. This can reduce the number of delivered records: omission metrics
and live review must assess the thoroughness trade-off.

Citations must belong to the fixed snapshot, actual retrieval ledger, and the
current role's delivered evidence. Retrieving a record does not itself authorize
citing it if the model never received that record. Raw evidence is unchanged.

At the default six model calls, Investigator may use up to four, preserving two
for Falsifier. Unused calls transfer to Falsifier. For other caps, Investigator's
ceiling is one at caps two/three; otherwise `min(cap - 2, floor(cap / 2) + 1)`.
Each role's last turn is reserved for an assessment. Earlier turns may retrieve
one tool result or finish early. A role may use one correction, shared across
schema, truncation and source-fact rejection, only if calls/time remain.
Two dependent queries plus an assessment by each role can therefore fit six
calls, with no promised correction. A schema correction followed by a conflicting
fact now fails rather than receiving a second correction. Unseen citations remain
fatal. No global budget increase, HTTP retry or response-mode fallback was added.

Role context contains current call/time/retrieval allowance and prior query
summaries. Diagnostics record ceilings, calls used, omissions, forced-final and
correction reasons, denied exploration, local validation/retention timing, request
mode/hashes and actual completed role responses. Deadline checks surround local
processing and precede transport; cancellation remains cooperative. Role completion
and schema/fact validity do not establish semantic support.

Falsifier guidance distinguishes observed HTTP from authorization hypotheses,
HTTP response length from whole-flow directional bytes, and network activity from
endpoint execution, compromise and theft. Arbitrary prose still requires review.

## Optional rejected-output retention

The comparison CLI accepts `--retain-rejected-output`, disabled by default. It
requires a tool-using model provider. Files are written under each comparison's
`case-NNN/rejected-output/`, separate from the state directory and report bundles.
Use a private durable comparison directory outside the checkout for live runs.
The optional provider `candidate_sink` supports other local integrations; normal
GUI operation does not enable it.

Only rejected response text is retained, captured before report normalization.
Each exclusively created file identifies run, role and attempt, with rejection
reason, original-content SHA-256, request/schema hashes, redaction/truncation flags
and at most 16 KiB of UTF-8 candidate text. There is at most one candidate file per
attempt. Parent retention directories are created with mode 0700 and files with
0600. Known configured API secrets and common credential patterns are redacted
before truncation. Headers, configuration objects and arbitrary provider error
bodies are never passed to the sink. Telemetry and unrecognized secrets can still
remain: redaction is not a guarantee of anonymization.

Candidate prose never enters normal case APIs, GUI views, Markdown reports or
bundles. The directory name is Git-ignored. Retention write errors produce a
sanitized `WRITE_FAILED` diagnostic and do not alter validation. File ownership,
access and deletion are local operator responsibilities; there is no automatic
expiration. Delete the comparison's `rejected-output` directory when its diagnostic
purpose is complete. Metadata/hashes remain in ordinary run diagnostics.

## Verification and next gate

Offline coverage exercises both roles' bounds and bindings, supported call caps,
dependent queries, shared correction limits, role-delivery provenance, context
omissions, retention controls, and provider/validation/retention deadline crossings.
The preserved pre-change baseline and candidate allocation probes are under
`build/verification/reliability/`; that ignored directory contains test logs and
source snapshots, not live provider credentials. In five identical scripts the
baseline completed four and the candidate completed five, retaining independent
review. The additional completion required three Investigator queries plus one
Falsifier query. This measures control flow, not real-model reasoning or accuracy.

**278 Python tests and 18 Chromium tests passed**, along with Ruff and whitespace
checks. One existing Starlette test-client deprecation warning remains.

See [matched live evaluation](LIVE_LLM_MATCHED_EVALUATION.md) for the separately
authorized 24-run campaign and semantic release gates. No failure penalty is used
as a latency release gate. Human task timing and detection accuracy remain absent.
