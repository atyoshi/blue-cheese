# Verification scope

Run using the pinned development environment:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/python -m pip check
```

The Linux suite covers legacy CLI/PCAP/SQLite/web behavior, presentation evidence,
normalization, ingestion transactions, checkpoints/gaps, Investigator/Falsifier,
retrieval budgets/citations, Streamlit interactions and the additional local
operation contracts. Tests use temporary paths, offline fixtures and deterministic
thread events rather than sleep-based polling or real model/network calls.

New coverage includes competing writers/symlink aliases, worker ownership and
queue saturation, provider-versus-ingestion progress, cooperative cancellation,
startup cleanup, old-schema upgrade/future-version rejection, fixed interpretation
snapshots, successor history, interrupted/failed/incomplete statuses, delivery
byte caps, role grouping/correlation exclusions, offline bundle tampering, saved
report/background UI interactions and backup/restore report/evidence round trips.

The suite does not establish semantic model accuracy, provider hard preemption,
rotation recovery, automatic case scheduling, sustained ingestion capacity,
macOS behavior or Docker execution. SHA-256 checks are not signatures. Current
snapshot/bundle interpretation checks use the shipped canonical parser; historical
parser version archives remain deferred.
