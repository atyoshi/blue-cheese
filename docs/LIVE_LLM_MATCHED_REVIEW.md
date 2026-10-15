# Matched live campaign: diagnosis and source review — 2026-10-15

The campaign finished its 24-entry schedule; the candidate reliability increment
did not improve completion and must not be promoted on these results. All eleven
incomplete runs stopped at local context limits, not elapsed-time exhaustion or a
VPN timeout. The six completed reports contain useful observations, but none is
accepted unchanged under the full source-support, coverage and countertest rubric
below. Two need limited wording/coverage corrections; four have material semantic
defects. This is an engineering and source-support review, not a detection-accuracy
evaluation or a human analyst task-time measurement.

## Evidence and verification

Campaign: `~/bluecheese-evaluations/20261015-matched-0543/`. First request:
05:44:54.744780 UTC; final trial finished 08:10:42 UTC, October 15 (02:10 Denver).
The fixed 14-hour allowance did not cause the stop: all scheduled entries finished.
The ledger reconciles **90 request starts and 90 finishes: 88 returned responses
and two provider parser HTTP 500 errors**. There are no recorded transport timeouts,
connectivity-wait events or ambiguous unfinished requests in this campaign.
This does not establish when the user's VPN disconnected; it establishes that the
saved failures have other causes.

| Revision | Completed | Incomplete | Failed | Total |
| --- | ---: | ---: | ---: | ---: |
| Frozen baseline | 5 | 4 | 3 | 12 |
| Frozen candidate | 1 | 7 | 4 | 12 |

Read-only offline verification checked 160 baseline and 164 candidate source-file
hashes, both source archives, four campaign-tool checksums and all four archived
EVE hashes. All **17 exported bundles** (six completed, eleven incomplete) verified.
Their snapshot membership/digests and selected seeds independently match the
frozen input manifest. Exported records were reconstructed from the original EVE
bytes, source identity and byte positions and matched raw/parsed/normalized data.
All **22 explicit fact bindings** in the six completed reports match their own
claim citations and source fields. This validates those bindings, not the other
words in a claim, the hypothesis, the verdict or a recommended action's rationale.

The reproducible audit and per-report cited raw-source extracts are ignored local
artifacts in `build/verification/matched-review/`: `audit.py`, `audit.json`, six
`*-source-review.json` files, `semantic-review.json` and `checksums.json`. The
semantic grades are Codex source review, not independent human acceptance.
Re-run the mechanical audit from the repository with
`.venv/bin/python build/verification/matched-review/audit.py`. The audit opens no
state database, loads no credentials and makes no model/network requests. Original
campaign artifacts and analyst dispositions were left unchanged. Baseline audit
records do not contain the candidate's per-role delivery diagnostics; bundle
verification proves retrieval, not retrospective proof of baseline role delivery.

## Every incomplete run

Seconds below are recorded trial elapsed time, including setup/export. Each run
had fewer than six model requests, fewer than twelve evidence calls, and less than
1,800 seconds of investigation time when it stopped.

| Trial | Seconds | Model requests | Actual stop |
| --- | ---: | ---: | --- |
| repeat-01-stage-01-baseline | 366.218 | 4 | Full input >64 KiB, after a Falsifier query |
| repeat-02-stage-01-baseline | 394.156 | 4 | Full input >64 KiB, after a Falsifier query |
| repeat-03-stage-01-baseline | 84.683 | 1 | Full input >64 KiB, after an Investigator query |
| repeat-03-stage-03-baseline | 107.688 | 2 | Full input >64 KiB, after an Investigator query |
| repeat-01-stage-01-candidate | 104.759 | 2 | Investigator tool-delivery metadata cannot fit |
| repeat-01-stage-02-candidate | 149.930 | 2 | Investigator tool-delivery metadata cannot fit |
| repeat-01-stage-03-candidate | 337.249 | 4 | Investigator completed; Falsifier tool-delivery metadata cannot fit |
| repeat-02-stage-01-candidate | 101.832 | 2 | Investigator tool-delivery metadata cannot fit |
| repeat-02-stage-02-candidate | 101.565 | 2 | Investigator tool-delivery metadata cannot fit |
| repeat-02-stage-03-candidate | 109.617 | 2 | Investigator tool-delivery metadata cannot fit |
| repeat-03-stage-02-candidate | 116.691 | 3 | Investigator tool-delivery metadata cannot fit |

### Baseline: bounded queries, growing transcript

Frozen `adapters/agent_provider.py::_tool_result` serializes the entire projected
broker response plus retrieval metadata. A broker response is bounded separately
at 64 KiB of raw/parsed/normalized rows; that does not bound the accumulated model
transcript. `_stage` appends each tool result, and `_request` rejects the next
message list above 65,536 bytes. There is no complete next-turn/final-turn fit
reservation. The recorded terminal queries succeeded at the broker; the following
request was stopped locally before transport. Baseline transcripts are not saved
in full, so the exact rejected message size is not reconstructed here. The saved
warning, source path and preceding successful query identify this boundary.

### Candidate: a reservation that permits no deliverable reply

The candidate adds a fact catalog, a schema-derived final guide, refreshed budget
metadata and bounded tool results. `_stage` computes result room as:

`65536 - serialized_messages - serialized_tool_calls - guide_bytes - 4096`.

The guide is 2,975 UTF-8 bytes. At six stops, recorded current input size alone
leaves **negative room even before counting the new tool-call envelope**. At the
seventh, at most 395 bytes remain; the empty-observation result's metadata alone
requires 455 bytes. The other minimum metadata sizes range from 454 to 599 bytes.
The audit reproduces all seven `_tool_result` failures using the frozen-equivalent
implementation and archived query results, even allowing the generous room upper
bound that ignores the envelope. This is a boundary reproduction, not a replay of
the original model responses or a proof that a repaired run would finish.

The request still advertises tools when no tool reply can fit. `_tool_result`
executes the broker query first, then attempts packaging; even `get_event` for one
record fails. The same record's typed fields occur in both observation and catalog,
prior deliveries remain in the transcript, and selected/strict-flow observations
precede diverse host context in `bounded_observations`. Candidate initial omissions
were 46/67 retrieved records for stage 01, 6/30 for stage 02, 27/49 for stage 03 and
10/33 for stage 04. These are retrieved-set omissions, not whole-snapshot coverage.
Removing limits or increasing calls would not repair the reservation error.

### Misleading fallback and lost intermediate work

`agents/investigator.py` catches these context exceptions as `BudgetExceeded` and
emits the generic "did not complete within its budget" / "Budget exhausted"
fallback. It erases the accepted Investigator findings when subsequent model
review cannot finish. Three incomplete runs had an Investigator response marked
VALID before Falsifier context exhaustion: baseline repetitions 1/2 stage 01 and
candidate repetition 1 stage 03. That VALID marker is not source-semantic approval;
any preserved candidate must remain visibly provisional and separate from the
accepted final report. A typed stop reason and completed-stage audit would explain
what happened without implying that 1,800 seconds or six model calls were spent.

## Adjacent failures affecting the recovery plan

The seven FAILED outcomes are separate from the eleven INCOMPLETE outcomes:

| Trials | Failure | Consequence |
| --- | --- | --- |
| Baseline repeat-01-stage-04 and repeat-03-stage-04 | Native provider parser HTTP 500 on Investigator request 3 | Provider/template or response-path compatibility remains unresolved; no timeout/retry inference |
| Candidate repeat-03-stage-01 | `limitations` is a string instead of an array | First assessment came on Investigator turn 4; no role correction remained |
| Candidate repeat-03-stage-03 | Invalid JSON; retained response fails JSON parsing at character 3618 | Same turn-4 exhaustion; finish_reason was `stop`, not token truncation |
| Candidate repeat-03-stage-04 | Limitation exceeds 128 characters | Same turn-4 exhaustion despite the schema guide |
| Candidate repeat-02-stage-04 | Fact observation absent from that same claim's citations | Strict rejection worked; first assessment was on turn 4 |
| Baseline repeat-03-stage-02 | Too many facts, then overlong unresolved text on correction | One correction did not yield valid output |

All five completed baseline reports needed one Investigator schema correction;
the completed candidate report needed none. All six used all six provider calls.
The candidate's four-request Investigator allowance admits three retrieval turns
before the first assessment, leaving no correction inside that role's allowance.
Two globally unused calls in these failures were reserved for independent review;
they are not evidence that it is safe to consume review capacity for retries.
Earlier scripted allocation tests did not exercise this live context/format pattern.
Rejected candidate outputs remain private diagnostic artifacts, not GUI findings.

## Source review of the six completed reports

Review covers both claims in every report, hypotheses, impact, limitations,
recommended checks, the stated disconfirmation test and actual tool activity.
It distinguishes source-supported observations, plausible qualified inferences,
unsupported extensions, and data unavailable to the model. No evaluator reference
answer or capture name was used to choose a verdict. "Needs correction" below is
an assessment of the archived report as written; no historical report was edited.

### repeat-01-stage-02-baseline — limited correction required

Claim 1 is supported: `0d0a44a9a44f5cb669fd8069` records a GET, status 200 and HTTP
length 10 at 12:55:07.922954 −0700, correctly rendered as 19:55:07 UTC. The cited
following GETs and flow `64cd44c413b81e610d10c0a9` support a closed flow with 1,809
bytes to server and 746 to client. Those are whole-flow directional counters, not
the amount of uploaded application data.

Claim 2's TeamViewer DNS-alert and Microsoft NCSI observations are supported, with
a citation defect: `f3904b4c07b0d9af18ff1019` is a separate bare-IP HTTP request,
not Microsoft/NCSI evidence. Remove that citation or describe it separately. The
report says the exact DNS name is unverified and recommends expanding it, although
raw alert `4b08470a0e1304452768a3fa` already has a DNS v3 query name. The alert
normalization deliberately omits embedded protocol details; `get_event` did not
deliver that raw field to the model. This is a projection limitation, not evidence
that the source lacks the name. Retrieve a typed DNS record before recommending an
external lookup. The qualified SUSPICIOUS assessment and missing-authorization /
missing-endpoint limits are reasonable for analyst triage.

Actual checks were the deterministic nonzero-flow test and model rereading of the
seed. The authorization/session check is a useful proposed endpoint/ITSM action,
not an executed test. No contrary authorization evidence was supplied.

### repeat-02-stage-02-baseline — limited correction required

Claim 1 correctly binds port 80, the GET with a `data` query parameter, and 1,809
whole-flow bytes to server. Claim 2's named DNS requests match
`17d710a08f594bbb124198a1`, `c1a541578afb8b955dfe2c42`,
`b0f5f59acf2d478ffa26f002` and `06451d63f3a6397dc62ba2ae`. Requests span about
21 seconds; they do not independently demonstrate a sustained remote session.
Replace "sustained DynGate connectivity" with "repeated DynGate DNS requests"
and retain the separately observed HTTP traffic. The report appropriately leaves
authorization, credentials, compromise and interactive access unconfirmed; its
endpoint and inventory checks are useful proposals. The identifier it recommends
correlating is present in the cited URL, not evidence of an authenticated session.

The model Falsifier reread the seed; the actual software test found nonzero flow
counters. Neither executed an authorization check. Core observations support
provisional analyst triage, after the wording correction.

### repeat-01-stage-03-baseline — material correction required

Claim 1's repeated POSTs, signature names and HTTP response length 29,875 are
supported by `3dd40db78ea7c3c3dbbf4762`, `53772daa7ddeae67cc104ddb`,
`7df42a58546c8a90493d7319` and `524e241bd15383844fb0ef8e`. Treat the two
signatures as sensor detections on the same flow, not independent corroboration.
The response length describes server response data, not stolen client data.

Claim 2 overstates `4f3ca21d5ecc718d2c03c184` and `0e67c94f4361b62aff7a210a` as a
"persistent interactive channel concurrent" with that activity. Its cited records
show a NetSupport-labeled POST and an NC_DATA observation about five minutes before
the selected alert. They do not prove interactive control or persistence across
that interval. The full snapshot contains later same-flow NC_DATA observations,
but those uncited observations cannot repair this claim retrospectively, and
network exchanges still do not establish interactive operator control. Retain
"separate NetSupport-labeled traffic" and qualify any duration inference using
actually delivered, cited timestamps.

The C2-consistent hypothesis is a qualified lead; the generic missing-flow test and
model rereading of the same HTTP/alert records do not independently establish it.
Endpoint/authorization checks are useful next steps. Later flow summaries exist
in the archive outside this snapshot; do not describe them as source-wide absence.

### repeat-02-stage-03-baseline — material correction required

Claim 1's POST path, endpoint, HTTP 200 and recorded StealC/StealC_V2 signatures are
supported. Claim 2 correctly cites the NetSupport user-agent and NC_DATA record
`38aeb9ad30fe6b54460d1bd2` with HTTP length 2,891, but labels an "interactive channel"
as an observation. Its impact description repeats that unsupported extension.
Replace it with the observed protocol traffic and an explicit, unconfirmed
remote-access hypothesis.

The disconfirmation test asks to verify that the already-cited POSTs and alerts
did not occur. That is contradicted by its own evidence and is not a useful
alternative explanation. Test whether an authorized tool or another process
explains the observations, and identify the external source needed. The suggested
18:45–18:52 UTC endpoint window is correctly converted from −0600 timestamps.
DNS/TLS and flow-end records are absent from this frozen snapshot, not necessarily
the archived source. No claims of confirmed theft or execution were accepted.

### repeat-01-stage-04-candidate — material correction required

Claim 1's GET, curl user-agent, status 200 and 1,046,284-byte HTTP length match
`1decd3355c5c13173bcb4a51`; cited alerts establish that those signatures fired.
Claim 2's two earlier curl GETs and status 301 match
`cd7c2e58892e469015a1c371` and `6674fbff83f922610f5a7b14`. "About 90s" is a loose
summary of roughly 96–98 seconds; use the actual timestamps when ordering matters.
The report correctly says the redirects' causal relationship is unproven.

The hypothesis nevertheless adds "unauthorized ... staging/execution" and the
activity verdict is MALICIOUS without source evidence establishing authorization,
execution or malicious content. A curl GET, executable-looking path and signatures
support investigation of a suspicious download; they do not resolve that verdict.
The impact section is more cautious than the hypothesis. Its proposed purpose
"Confirm execution" from file creation/hash evidence is also too strong: those
records establish file presence/identity, not process execution or maliciousness.

The completeness statement "23/33 host events delivered" counts the initial
retrieved set; the fixed host snapshot actually has **449 records**. Say 23 of 33
retrieved observations were initially delivered, with 10 omitted, and disclose
the larger snapshot. The missing seed flow summary is outside the snapshot and
the raw truncated fileinfo is unsupported by the importer, as detailed below.
Actual Falsifier work reread an earlier redirect; endpoint/hash/authorization
checks were proposed only. Remove the unsupported extensions before acceptance.

### repeat-02-stage-04-baseline — material correction required

Both claims' HTTP fields and UTC times are supported: the large HTTP response and
two 178-byte HTTP 301 responses at 19:29:00–01 UTC. Alert
`0bb048e5ca241079a4891cf0` supports attribution that Suricata raised a Windows PE
download signature. It is not an independently verified file analysis.

The hypothesis "malicious staging/C2" and unqualified Windows PE description in
impact overreach this evidence. Use a suspicious executable-download hypothesis
with sensor-attributed PE identification pending file validation. Confirming that
a downloaded program ran would still not alone establish malicious compromise,
as the endpoint recommendation's purpose currently suggests. The proposed
authorized-distribution countercheck is useful; the flow record alone cannot
establish organizational approval.

The model Falsifier's broad host query returned 30 records. The cited two redirects
have flow-close records in the fixed snapshot (`fa49ed0e7c2a31b289df1d98` and
`b9e503dfa6cb217176ba68ef`); distinguish "not supplied to this assessment" from
"unavailable." The executable flow's summary is outside the snapshot. Missing
file-extraction/hash evidence must also acknowledge importer coverage, rather
than invite repeated queries against a type the broker cannot return.

## Shared coverage and countertest findings

Stage 03's selected flow closed at **18:52:00 UTC**, but its summary was logged at
**19:05:12 UTC**. Stage 04's selected flow closed at **19:30:38 UTC**, but its summary
was logged at **19:39:51 UTC**. Both are present in archived EVE and accepted by the
importer, but outside membership selected by ±300 seconds of the top-level logged
timestamp. This behavior follows the current contract; it demonstrates a product
limitation for session-completeness questions. The stage-03 summary reports
3,173,279 whole-flow bytes to server and 169,695 to client; those counters are not
proof of application payload contents or data theft. They were not available to
these reports and must not be backfilled into historical runs.

Stage 04 also has a raw same-flow `fileinfo` at 19:30:37 UTC, state TRUNCATED, size
102,400, `stored:false`, with no hash. The current normalizer accepts only alert,
flow, DNS, HTTP and TLS, so fileinfo is quarantined as unsupported along with other
types. This record would improve coverage disclosure, not prove full-file integrity,
execution or compromise. Raw HTTP redirects exist but their `redirect` field is
also omitted from the model projection; a supplied redirect target is distinct
from observing the subsequent connection.

All six completed reports have actual Investigator and Falsifier model turns
validated. All six retain the software zero-byte-flow test. That test finds a
nonzero seed flow in stage 02 and no seed flow in stages 03/04. It tests whether
bytes were observed, not authorization, interactive control or malicious staging.
Model review completion must not be presented as proof those alternatives were
tested successfully. No returned counterevidence IDs establish an authorization
alternative; that does not prove no alternative exists. A useful unavailable
result names the missing source and the next analyst action.

## Decision and coordinated next work

Mechanical completion is 5/12 baseline versus 1/12 candidate. Source review accepts
no completed report **unchanged across all rubric dimensions**; the two stage-02
reports are useful triage leads needing limited corrections, and the other four
require material changes. No matched pair completed mechanically in both arms,
and the accepted-pair latency subset is also empty;
do not compare failed/incomplete short runs as speed improvements. Completed trial
times range from 610.825 to 832.194 seconds; these are machine timings, not human
time savings. The original candidate promotion gate (at least 10/12 semantic
acceptances, at least two per seed, no decline from baseline and intact integrity)
is unmet independently of any judgment about prose.

The [master plan recovery track](../Blue_Cheese_Master_Implementation_Plan.md#matched-campaign-recovery-track--october-15-2026)
coordinates context/stop reporting, snapshot coverage, schema/call allocation,
claim/countertest quality, provider compatibility, and fresh matched evaluation.
It preserves strict validation and historical artifacts. This review implements
documentation and offline diagnostics only; application fixes, normal-GUI review,
human usefulness validation and any further live experiment remain future work.
