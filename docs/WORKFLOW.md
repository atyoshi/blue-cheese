# Alert to decision

The single analyst interface supports notice → understand → investigate → verify
→ decide. Demonstrations follow the [README walkthrough](../README.md#first-walkthrough-connect-inspect-investigate).

- **Alerts:** prioritized, paginated review queue. Select a detection to review
  its scope and investigate or open its case.
- **Cases:** named target, fixed snapshot, findings, linked evidence visuals,
  actual agent activity, contextual chat, and separate analyst decisions.
- **Network:** bounded telemetry windows with linked timeline, connection, and
  record selection. Visual filters do not change investigation scope.
- **Settings:** source connection, appearance, model endpoints, automatic queue,
  and source diagnostics.

New analyses and chat proposals require explicit actions. Reading and refresh
never initiate work. Polling updates activity and chat independently. Decisions,
reports, and evidence persist across restarts. Revision history retains prior
snapshots and reports.

Priorities guide review rather than estimate compromise probability. Mechanical
citation validation establishes retrieval provenance, not semantic correctness.
Analyst attribution is local. Cancellation cannot interrupt an active provider
request. One application process owns each state directory.

Verify usefulness through analyst completion, elapsed task time, and finding
quality. Synthetic tests do not establish detection accuracy or commercial
readiness. Authentication, shared deployment, and additional telemetry sources
remain separate product work.

## Broader host investigations

Use **Investigate source host** from the alert drawer when the initiating alert
does not capture the host's surrounding behavior. The new case freezes same-source
traffic to and from that source host across destinations within five minutes.
The case labels its host target; revisions preserve scope. Existing connection
reviews retain their boundaries. Cross-connection context does not establish
causality, and malicious activity is assessed separately from proven endpoint
execution or theft. This is part of the normal application workflow.
