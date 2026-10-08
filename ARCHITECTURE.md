# Implemented architecture

Specification: `Blue_Cheese_Master_Implementation_Plan.md`. Deferred work and
milestone gates are in `ROADMAP.md`; actual checks are in `docs/SESSION_STATUS.md`.

The legacy CLI/PCAP/EVE/SQLite/triage/web workflow remains independent. The
presentation entry point is `src/bluecheese/interfaces/demo.py`.

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

Cases currently identify scenario/variant/question scope. Each run creates an
atomic revision and fixed snapshot, preserving exact raw/parsed/normalized copies.
Report history and parent-linked successors persist across restarts. Run status
is separate from verdict; citation validation does not establish semantic support.
Tool results are capped at 100 rows and 64 KiB per call by default; only delivered
rows enter the citation ledger. Failed dispatched tool attempts consume the call
budget. Time limits/cancellation are cooperative, not provider preemption.

Offline report bundles and database backups preserve evidence linkage and hashes.
Backups require a stopped runtime and include the database, not external telemetry
or replay spools. Restore preserves source locators/cursors and does not rewrite
source identity. No deletion policy exists, so retained snapshots remain pinned.
No authenticated signatures, parser archives, real provider or automatic response
adapter is claimed. Docker/macOS execution and rotation recovery remain unverified.
