# Blue Cheese: alert to decision

The first product milestone is a useful local investigation assistant for a small
security team. Its workflow is **notice → understand → investigate → verify → decide**.
Enterprise SIEM case organization is the reference; commercial value must be
measured through analyst task completion, time saved and finding quality.

## Walkthrough

1. Connect an EVE file or local Unix stream. The status strip distinguishes current
   receipt from saved evidence. Expand **Sensor status and stored evidence totals**
   for cumulative counts, last successful sensor check and last bytes received.
2. **Needs attention** shows priority-ranked pages of stored alerts. Group counts
   and first/last timestamps describe the visible 20-alert page, not every related
   alert in the database. Open older pages without a latest-N cutoff.
3. Click **Investigate**. A named case opens automatically. It freezes the selected
   alert and same-source, directed endpoint-pair records within ±5 minutes.
   Sensor priority is a review order, not a probability of compromise.
4. While analysis runs, **Agent activity** shows its actual operations, elapsed
   time, model waits, evidence queries and returned records. Triage and correlation
   use rules; Investigator and model review in Falsifier use the configured model.
   Activity persists incrementally, including failed runs. The view retains the
   latest 128 recorded events and never schedules work on refresh.
5. **Ask Blue Cheese** is beside the case. With a model configured, ask why a finding
   matters, what the agents did, or whether an alternative explanation fits. The
   assistant receives current health, the selected case, recorded activity and
   bounded normalized evidence from its snapshot. Raw logs and credentials are
   omitted; returned citation IDs must belong to evidence actually retrieved for
   that chat answer. This mechanical check does not establish semantic accuracy.
6. New analysis is a proposal with a **Run proposed action** button. It creates a
   linked revision with a new snapshot. Source import/follow/stop and synthetic
   model probes also require this explicit confirmation. Read-only status and
   evidence commands execute directly. Model calls are asynchronous; cancellation
   is cooperative and cannot interrupt an in-flight HTTP request.
7. **Findings** separates analysis status, assessment and unconfirmed host compromise.
   Review observations, citations, the alternative explanation checked, unresolved
   questions and recommended next checks. Endpoint processes, identities, asset
   inventory and approved scanning schedules are not connected.
8. Under **Analyst decision**, enter analyst attribution, assignment, disposition
   and notes. These persist separately from the machine report. Names are local
   attribution, not authenticated users. History preserves reports and revisions.
9. New alert occurrences in a visible group are flagged against its saved snapshot.
   **Analyze new activity** creates a successor; older reports and evidence stay fixed.

Without a model, chat supports local tasks such as `/status`, `/alerts`, `/triage`,
`/network`, `/history`, `/report` and `/help`. It does not simulate conversational
model analysis. Settings and analyst decisions remain available through their forms.

**Network** ranks endpoints by alerts, then record count, and limits visuals to the
latest 250/1,000/5,000 received accepted records. Endpoint filters affect the visual
view; they do not change investigation membership. Case visuals use up to 1,000
frozen records and 12 directed IP pairs. Evidence detail retains original logs.

**Refresh now** reloads the view and shows completion. It does not generate traffic
or restart the sensor. Automatic investigations remain off after restart; configure
them under **Settings → Automatic investigation and retry queue**.

## Acceptance and limits

Synthetic workflow tests cover alert selection, scoped analysis, actual retrieval,
chat grounding and fabricated-citation rejection, cancellation, local assignment,
restart persistence, older alert pages, unchanged refresh and new activity without
snapshot mutation. Regression checks retain CLI, legacy UI, ingestion and reports.

The current release uses one local trusted-operator runtime. Authentication, shared
SOC deployment, additional telemetry sources, automatic containment, full semantic
claim verification and detection-quality evaluation remain separate master-plan work.
A successful synthetic walkthrough does not establish enterprise readiness or accuracy.

Restart the application process once after upgrading runtime code/schema. A browser
refresh alone cannot upgrade cached Python objects. Schema migration 6 is additive;
existing checksums, raw evidence and saved reports are retained. Stop the application
before using backup/export/maintenance tools; never open a second process on its DB.
