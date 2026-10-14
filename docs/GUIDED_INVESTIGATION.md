# Guided investigation and conversation

Start `./bluecheese --data-dir my-soc gui` and open **Practice investigation**.
This uses `my-soc/practice/evidence.duckdb`, a separate, exclusively locked
synthetic workspace. It never imports practice records into operational history.
No source, model, or investigation starts just by opening the page.

## Offline journey

1. Click **Prepare practice input**. Thirty records from the existing synthetic
   fixture become saved evidence. **Input ready** should be checked.
2. Choose **Practice target**. Identify the selected alert's endpoints and rule.
   **Target selected** should be checked. Nothing has been investigated yet.
3. Click **Run practice investigation**. The case target, snapshot ID, engine and
   live/saved state appear above the tabs. **Current activity** observes recorded
   operations, query counts and returned records. Offline rules may finish too
   quickly to observe a wait; no artificial delay is added.
4. **Evidence retrieved** reflects successful recorded tool execution.
   **Analysis finished** requires COMPLETED; failed, cancelled, interrupted and
   incomplete runs do not pass this checkpoint. Click **Review findings**.
5. Open **Evidence and connections**, select a directed connection and inspect
   its highlighted map relationship. Select a record to open the evidence drawer.
   The displayed case sample is at most 1,000 frozen records; the graph shows up
   to twelve pairs. A connection outside those twelve may have evidence but no
   displayed edge. Direct node interaction remains deferred.
6. Explicitly click **Explain this view**, **What is happening now?**,
   **Show the evidence**, or **What should I check next?**. These use offline
   application state and bounded evidence. No response is generated before a
   question/click. Read the response's captured scope and inspect its citations.
7. Open **Agent activity**. Expand role details, the chronological trace, and
   actual queries. Filter the trace by role/type. Query IDs, arguments, record
   counts, truncation, durations and outcomes describe actual execution. Open a
   returned evidence reference beneath its query. Old missing fields say
   `unavailable`; prompts, credentials and private reasoning are excluded.
8. Open **Analyst decision**, enter attribution/assignment, a disposition and
   note, then **Save analyst action**. **Decision recorded** should be checked.
9. Refresh repeatedly and change tabs, filters and selections. Activity/chat
   fragments update independently; analytical views do not automatically rebuild
   their evidence or move to another tab on completion. **Refresh now** explicitly
   reloads them. Verify no additional run or ingestion worker started. Restart
   the process and reopen the saved practice case to check durable state.

At every checkpoint record whether you can identify the **target, action,
evidence and next step**, and note any missing/unclear item. Repeat in Firefox at
roughly 1,280px and 600px window widths. Check that controls wrap, labels remain
readable, the selected tab/record survives refresh and reading position stays
usable. Automated AppTest checks do not establish those visual properties.

## Conversation expectations

GUI and CLI share captured `ViewContext` and read-only `summarize`/`explain`
intents. Definitions are labelled general information. Evidence answers label
the selected run/snapshot, view and selection, report execution separately from
assessment, identify unknowns, state sample limits and include retrieved IDs.
Queries deliver at most 20 records and six queries per answer; byte caps still
apply. Filters operate within that bounded query sample, so an empty sample does
not establish absence. These answers are deterministic descriptions, not a new
model assessment of risk or a substitute for analyst review.

In the CLI try `/alerts`, **Summarize these alerts**, `/report RUN_ID`,
**Summarize that investigation**, `/summary RUN_ID`, `/explain flow`,
**What does this alert mean?**, **What am I looking at?**, and
**What are you doing?**. Summary scope is explicit run/evidence ID or IPv4 endpoint/pair, then last
actual displayed/investigated context, then a labelled bounded workspace overview.
Existing slash inspection commands retain structured output and approvals.
Natural status questions return prose. Read-only summary/explanation commands
require no second approval and never create investigations or alter scheduling.
Actual command output enters bounded session context; model proposals do not
establish execution. New analysis still requires an explicit scoped request and
its existing execution approval/control.

## Separate user-initiated llama.cpp walkthrough

No live model call was made for this milestone's automated verification. To
repeat with the existing server, expand **Practice engine (optional model)** and
apply the existing endpoint and Investigator/Falsifier model settings. Reuse the
user's existing llama.cpp configuration: 300s call timeout, thinking disabled,
and the configured served model; do not download another model. Remote HTTP
needs the existing explicit remote and insecure-HTTP opt-ins. Credentials stay
process-local. Model settings apply only to this practice runtime.

Explicitly test the connection if desired, then choose a target and click
**Run practice investigation**. Record actual model waits, durations, completed
queries, truncation, budget usage, final status and citation quality. Change tabs
and select evidence while waiting; ask a read-only status question, then cancel
if desired. Cancellation is cooperative and cannot preempt the active request.
A timeout/failure must be visible and must not check **Analysis finished**.

After reviewing the first saved report, ask **Why is this suspicious?** to test
model conversation against the captured selection. Change the selection before
its response returns and verify the response still labels the original scope.
Then explicitly request a new investigation. Confirm it is only a proposal until
**Run proposed action** is clicked; it creates a linked revision in practice.
Revisit the old snapshot and confirm it is unchanged. Save an analyst decision.
Do not run a terminal/export/maintenance process against either GUI-owned DB.

Success demonstrates a synthetic workflow, not detection accuracy, commercial
readiness or real-world authorization. Choosing shadow evaluation, grouping or
additional asset context remains a subsequent decision after this walkthrough.

## Review record — 2026-10-13

The initial attempt lost native Firefox window access (`cgWindowNotFound`). A
user-requested retry succeeded. Firefox reviewed the isolated synthetic journey
on localhost 8504, including responsive viewports committed at 1,280px and 600px,
actual tab switching, connection/evidence selection, an explicit explanation,
trace-type filtering, analyst attribution/assignment/note saving, explicit
refresh and process restart. No real model or operational evidence was used.

| Checkpoint | Operator-visible target, action, evidence and next step |
| --- | --- |
| Input ready | Synthetic workspace identified; preparing input stored thirty records; next action was target selection. |
| Target selected | Rule and directed endpoints identified; no analysis claimed; next action was the explicit Run button. |
| Evidence retrieved | Actual role/tool activity and counts appeared; each run retrieved five queries delivering nineteen records across queries from six frozen records. |
| Analysis finished | Completion banner and Review findings action appeared; assessment, execution and unknown host compromise were separate; evidence drawer and scoped explanation exposed the selected record. |
| Decision recorded | Attribution, On-call assignment and review note persisted with disposition Open; all five checkpoints checked. |

The review found and corrected three issues: case metrics/engine text stayed on
Running after the independent activity header completed; evidence/chat columns
were cramped at 600px; and the case timeline said UTC while using a local-time
scale. Metrics/engine state now refresh with activity, the saved-run chooser no
longer carries a stale status label, practice execution controls re-enable after
completion, narrow columns stack, and the timeline uses an explicit UTC scale.
The revised UI was re-inspected in Firefox; its UTC axis showed 12 PM for the
fixture's 12:00 UTC events. A deterministic regression checks that the live
header changes from Running to Failed without rebuilding the case workspace.

Tabs and the connection/evidence selection survived explicit refresh and
viewport changes within the same case. The short review found no blocker to
identifying target, action, evidence or next step after the corrections.
Horizontal tab scrolling and truncated dropdown labels remain on narrow views;
full target/evidence text is available below. This was a manual spot-check, not a
comprehensive accessibility or long-session reading-position evaluation.

Two investigations were explicitly started to verify the original journey and
completion fix. Offline inspection while the server was stopped confirmed two
COMPLETED runs, thirty practice records, five queries/nineteen delivered records
per run, retained analyst history, and zero records/runs in the parent operational
workspace. Reopening after restart showed the saved result and decision. The
preview was relaunched on localhost 8504 in its temporary state directory.
The real-model follow-up was subsequently initiated by the user with `~/bc.json`; see the record below.


## Live model record — user configuration — 2026-10-13

The user authorized `~/bc.json`. The existing loader applied its settings to a
separate temporary practice preview on http://127.0.0.1:8505, without changing the
file. One synthetic investigation completed: 212.85s, six model calls, eight
queries, six unique retrieved/cited records, verdict UNCERTAIN. All six cited IDs
were checked against actual retrieval. Live status and tab navigation worked
while the model waited. The machine report and fixed snapshot survived restart.

This found an integer timeout/float widget mismatch and duplicate chat dispatch
after an explicit app rerun. Both were fixed and regression-tested. Two malformed
JSON chat responses were rejected. Explicit system-level output schema guidance,
strict single-fence formatting support and preservation of validated model
explanations were then tested against the server. The final explanation took
31.21s, cited the selected flow, and clearly distinguished the initial suspicious
hypothesis from an established conclusion. It did not launch another run.

A synthetic local analyst action left the case Open for authorization/endpoint
review. CLI summary/definition reads with the user's provider loaded were also
checked without starting analysis. The final suite has 156 passing tests; those
tests use mocked providers and no external model calls.

Firefox again lost window access during the final post-fix check. The successful
final explanation was inspected through the same runtime chat path and saved for
the restarted preview, rather than visually rechecked while switching selection.
Live cancellation, timeout and execution of a proposed successor remain separate
branches to verify; their deterministic tests pass. These results establish one
server's bounded compatibility and a synthetic journey, not detection quality.
