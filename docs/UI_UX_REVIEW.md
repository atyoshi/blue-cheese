# Operational console UI/UX review — 2026-10-12

Reviewed the working operational console, not the synthetic presentation app.
The goal was to reduce scrolling, make evidence exploration understandable, and
keep operational state and limitations visible. This is an implementation review,
not an enterprise readiness certification or a user study.

## Findings and changes

| Finding | Change |
|---|---|
| Setup controls and repeated headings competed with analyst work. | Compact workspace heading, sidebar brand, collapsible sensor setup and consistent dark/teal theme. The CLI applies the theme even when launched outside the repository. |
| The overview mixed charts, a large map and raw records into a long page. | Activity, Connections and Evidence tabs; bounded map viewport with fullscreen; collapsed raw details and beginner explanations. |
| Normal wheel scrolling zoomed the timeline, sometimes producing a blank chart and fractional count scales. | Shift + wheel zooms time only. Normal scrolling leaves scales unchanged; the count axis retains its zero baseline. Instructions appear beside the chart. |
| Connection selection narrowed evidence but left charts showing a different population. | Endpoint and directed-pair filters now apply to all overview tabs and view counters; Reset focus clears both. Stored-scope header counters remain explicitly distinguished. |
| New flow records could bury older alerts in the first 50 visual records. | Evidence type selector; alerts appear first, newest within each type. Matching count and display limit are labelled. Full pagination remains on Alerts/Flows. |
| Long evidence hashes and run IDs were difficult to recognize. | Rule/flow-state, endpoint-pair and short-ID labels; saved runs show status and short ID. Full identifiers remain in evidence and exports. |
| Investigation actions were buried below raw JSON. | Actions above raw detail, direct navigation to Investigations, prominent exports, concise assessment and expandable citation/retrieval audit. Unresolved questions stay expanded. |
| Sensor buttons could display stale enabled states after disconnect. | Immediate app refresh after connection changes; disable inappropriate actions and input edits while connected. |
| Continuous refresh lacked a reading/editing control. | Auto refresh toggle and Refresh now. Pausing refresh preserves ingestion; filters/manual refresh still reload current data. |
| Busy/empty queue actions could give insufficient feedback. | Pending investigations disable duplicate submission; queue actions explain when no eligible alert is available. |
| Technical quarantine JSON was difficult to scan. | Readable table with source, byte offset and reason; full continuity incidents remain available. |
| Detection text could be interpreted as Markdown in new summaries. | Rule text uses code widgets; report prose uses plain text. Original evidence remains in code/JSON widgets. |

## Verification

- Native Firefox rendered review on macOS, using the existing capture-derived
  operational evidence: 536 accepted records, 194 alerts and 342 flows. Confirmed
  the new theme, workspace controls, scope labels, readable charts and updated
  timeline interaction. Normal wheel input left both chart scales unchanged.
- Streamlit AppTest checks file input, missing-path recovery, endpoint and pair
  filtering, filter reset, evidence-type selection, learning mode, refresh pause,
  manual refresh, direct investigation navigation, exports/citation/audit controls,
  and socket connect/disconnect button state. These interactions retain one
  ingestion worker and do not trigger investigations on rerender.
- Temporary Unix-stream tests use isolated state; no synthetic test records were
  inserted into the operational evidence database.
- Full regression suite: **71 passed** on macOS/Python 3.13. Ruff passed.

## Remaining checks and release constraints

The desktop browser review was interrupted when the native Firefox window became
unavailable to the automation API. Narrow-screen rendering and a final rendered
pass through every tab remain unverified; automated widget checks do not replace
those checks. Responsive CSS is present, but mobile usability is not certified.

Keyboard focus styling, labelled controls, text legends and reduced-motion
support are implemented. Formal WCAG contrast, screen-reader, keyboard-only and
cross-browser testing remain necessary. Streamlit tables and charts require
particular attention during accessibility testing.

The map is a ranked logical view of up to 12 directed IP pairs, not a physical
network topology. It supports scrolling/fullscreen and selection through the
connection control; nodes are not clickable. The recent-record window is bounded
and the refresh toggle pauses the timer, not an immutable evidence snapshot.

For a multi-analyst on-prem SOC, authentication, authorization, reliable user
attribution and multi-session concurrency validation remain release gates. The
current Analyst field is explicitly local attribution, not an authenticated
identity. Also complete container execution, sustained sensor/load testing and
deployment validation before sale. See [release gates](RELEASE_GATES.md).
