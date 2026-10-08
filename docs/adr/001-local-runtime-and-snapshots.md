# ADR 001: Owning database worker and materialized demo interpretations

Date: 2026-10-08. Status: implemented for presentation runtime.

The master plan (Sections 4 and 9; ADR03/ADR05) requires single runtime ownership
and fixed interpretation membership. The former RLock serialized connection
use but also held ingestion behind provider execution; watermark-only reports
could observe later changes to normalized interpretations.

Keep existing repository paths and legacy SQLite workflow. The presentation
runtime uses a bounded 64-command queue and one thread that creates, accesses and
closes DuckDB. Providers execute outside database locks; one provider run may be
active. Atomic snapshots copy scoped evidence interpretations (10,000-member
limit), retaining original occurrence IDs and a sorted membership/interpretation
digest. All run tools, citation inspection and bundles use those copies.

A high-watermark-only design was simpler but did not freeze derivatives. Full
versioned interpretation/link/context tables remain the longer-term design; copying
small bounded snapshots gives inspectable behavior without restructuring the repo.
It duplicates raw data and is not a measured scalable storage strategy.

Schema migration 1 is additive and checksummed. Existing evidence/cursors remain;
future or changed migration metadata is rejected. Restarts mark RUNNING records
INTERRUPTED, preserve traces and allow explicit successor attempts. Automatic
scheduler leases and intermediate persisted workflow states remain pending.

Verification: upgrade, rollback/member cap, frozen interpretations, restart/history,
provider-versus-ingestion concurrency, cancellation, worker queue saturation and
backup/restore tests use temporary state and deterministic coordination.
