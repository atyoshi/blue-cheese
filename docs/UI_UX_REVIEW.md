# Analyst interface review — 2026-10-14

The application uses one React interface served by the Python runtime. Alerts,
Cases, Network, and Settings form its navigation. The README walkthrough uses the
same interface and source controls as operational work.

## Design

Light and dark themes share typography, spacing, control dimensions, and semantic
colors. Graphite or white surfaces, blue actions, crisp dividers, and aligned SVG
icons establish hierarchy. Source diagnostics and retrieval details are secondary.
Findings distinguish observed facts, assessments, unknowns, and analyst decisions.

Drawers use focus-managed portals. Tabs support arrow keys, Home, and End. Motion
uses short control transitions, drawer movement, and linked chart highlighting;
reduced-motion preferences disable animations. Background updates retain reading
and editing state and never schedule investigations.

Text colors use relative-luminance contrast, not hex-channel distance. Primary
text exceeds 15:1; secondary text exceeds 7:1 on its tested surfaces. Functional
text pairs meet 4.5:1 and essential graphical indicators meet 3:1. Browser checks
also examine rendered contrast in overlays and interactive states.

## Rendered review and checks

Reviewed Chromium/macOS screenshots of both queues and case findings, including
390px layouts. Corrected narrow priority badges, offscreen table-label overflow,
control theme transitions, textarea labeling, case-history identity, and background
pagination resets discovered during browser testing.

The browser suite exercises actual investigations, citations, raw/normalized
views, activity, decisions, contextual chat, downloads, successors, source changes,
light/dark persistence, tooltips, reduced motion, long labels, IPv6, and unsaved
form state. See [verification scope](TESTING.md) for commands and coverage limits.

Visual summaries retain explicit windows and snapshot scope. They depict directed
IP relationships, not physical topology or established device ownership. Activity
indicates recorded execution rather than simulated progress. Human usability,
finding quality, other browsers, and assistive technology require further review.


## System-wide reading review — 2026-10-14

Reviewed alerts, cases/findings, evidence drawers, network, actual activity,
contextual chat, decisions, settings/source diagnostics, and Markdown exports.
Corrections include a labelled case time window, one shared interpretation-help
area, separate case gaps and material analysis limits, conditional next checks,
shorter action labels, semantic paragraph/list rendering, readable source incidents,
capability-check outcomes and advisory scores. Diagnostic JSON remains secondary.

Rendered desktop and 390px chat screenshots show readable paragraphs and lists;
literal markup remains text. Both themes retain contrast, keyboard, zoom and
unsaved-decision checks. Failure views retain access to saved evidence and actual
operations. See [workflow benchmark and evidence](ANALYST_WORKFLOW_VERIFICATION.md).
Human task completion, time saved and enterprise deployment capabilities have not
been established by this review.
