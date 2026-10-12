# Verification scope

Run using the pinned development environment:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/python -m pip check
```

The suite covers legacy CLI/PCAP/SQLite/web behavior, presentation evidence,
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

The latest macOS/Python 3.13 verification passed 71 tests, including local
Suricata PCAP and actual Suricata Unix-stream output, fragmented records,
disconnect/partial-tail handling, spool limits/restart, socket ownership, GUI
input switching, visual filter/reset behavior and short launcher defaults.
The socket tests need permission to bind local Unix sockets; a restricted agent
sandbox may deny this even though a normal native launch supports it.

The suite does not establish semantic model accuracy, provider hard preemption,
sustained ingestion capacity, all rotation policies or Docker execution. SHA-256
checks are not signatures. Current snapshot/bundle interpretation checks use the
shipped canonical parser; historical parser version archives remain deferred.
