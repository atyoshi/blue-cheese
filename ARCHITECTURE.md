# Implemented architecture

Specification: `Blue_Cheese_Master_Implementation_Plan.md`. Deferred work and
milestone gates are in `ROADMAP.md`; actual checks are in `docs/SESSION_STATUS.md`.

The legacy CLI/PCAP/EVE/SQLite/triage/web workflow remains independent. The
operational entry point is `src/bluecheese/interfaces/console.py` (`bluecheese gui`);
the preserved presentation remains `src/bluecheese/interfaces/demo.py`.

Presentation runtime ownership follows `docs/adr/001-local-runtime-and-snapshots.md`.
One database worker owns DuckDB behind a bounded queue; the runtime RLock protects
lifecycle and follower state. The ingestion worker submits whole bounded polling
transactions. Provider execution happens outside those locks, with one active run.

`agents/orchestrator.py` coordinates deterministic triage and correlation followed
by the replaceable Investigator/Falsifier and validated report assembly. All
retrieval uses one scoped broker ledger and one resource budget. Triage groups up
to 20 visible alerts into five-minute source/sensor/signature/endpoint buckets;
priority remains distinct from sensor severity and maliciousness. One seed group
is selected per run. Correlation proposes up to 100 members using same-source,
same-sensor flow IDs/endpoints or exact endpoint tuples in a five-minute window.
Links record basis, policy version, time tolerance and ambiguity; IP-only and
transitive merges are excluded. This is not a full streaming scheduler or SIEM.

Cases identify scenario/variant/question scope and, for selected-alert runs, the seed occurrence.
Selected-alert membership is bounded by source generation, directional endpoints
and a five-minute event-time window. Each run creates an
atomic revision and fixed snapshot, preserving exact raw/parsed/normalized copies.
Report history and parent-linked successors persist across restarts. Run status
is separate from verdict; citation validation does not establish semantic support.
Tool results are capped at 100 rows and 64 KiB per call by default; only delivered
rows enter the citation ledger. Failed dispatched tool attempts consume the call
budget. Time limits/cancellation are cooperative, not provider preemption.

Offline report bundles and database backups preserve evidence linkage and hashes.
Backups require a stopped runtime and include the database, not external telemetry
or replay spools. Restore preserves source locators/cursors and does not rewrite
source identity. Explicit bounded retention previews/deletes unpinned evidence only; all snapshots
and work references remain pinned. Tombstones prevent resurrection and a persisted
watermark prevents receipt-sequence reuse after deletion.
Analyst notes/dispositions are append-only records separate from machine reports.
Ingestion atomically enqueues external alerts; the opt-in scheduler processes one
seed at a time and retains terminal failures/interrupted tasks for explicit retry.
Rename recovery retains/drains descriptors, persists generation namespaces and
can reopen matching retained archives; truncation/ambiguous continuity still stop.

An optional strict-JSON Chat Completions provider receives bounded normalized
observations after deterministic retrieval/countertests. No model controls query
authority. One request attempt, bounded output and cooperative timeout; fake
transport tests verify scope/citation/error behavior. Real endpoint compatibility
and semantic model quality remain unverified.

No authenticated signatures, parser archives, distributed service or automatic
response adapter is claimed. Native macOS tests/browser launch were exercised;
Docker execution remains blocked by the unavailable daemon.

## Operational visual and stream paths

`interfaces/network_overview.py` renders bounded, scoped normalized observations
from `visual_telemetry`; `application/telemetry_visuals.py` derives record counts,
UTC bins (including zero-count gaps), protocol/severity breakdowns and directed
IP pairs. This analyst path does not expand provider retrieval or grant citations.
Endpoint focus intersects the recent receipt window; raw inspection resolves the
same evidence IDs.

`application/unix_stream.py` implements a nonblocking AF_UNIX/SOCK_STREAM listener
polled by the existing runtime/database worker. Each bounded receive is fsynced
to a persistent spool before the existing transactional EveFollower parses it.
The spool is capped at 256 MiB per socket path; no automatic deletion or rotation.
EOF/transport failure stops visibly; partial prior streams cannot merge with new
producer bytes. This does not acknowledge delivery back to Suricata or establish
producer-side completeness. The listener accepts one producer and uses mode 0600.
