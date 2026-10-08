# Implementation roadmap

Authority: `Blue_Cheese_Master_Implementation_Plan.md`, particularly Sections 9,
11–13, 17 and work packages in Section 24. Status describes implemented code,
not completion of the intended system.

| Milestone | Current status |
| --- | --- |
| M0 | Baseline inventoried; CLI, SQLite, PCAP and legacy web paths retained. |
| M1 | Offline rule-based Investigator/Falsifier, structured citation validation, deterministic reports and offline-verifiable bundles. Parser archives and full claim semantics pending. |
| M2 | Bounded append-only ingestion, replay, checkpoints, UI and exports retained. Background runs/cancellation and saved-report loading added. |
| M3 | Canonical directory lock, owning database worker, additive checksummed migration, materialized interpretations/snapshots, interrupted-run recovery and offline backup/restore implemented. Rotation recovery, retention and Docker/macOS verification pending. |
| M4 | Deterministic triage/correlation connected through Orchestrator with one shared budget; case revisions and successor history persisted. Real provider, automatic scheduling and full case editing pending. |
| M5–M6 | Research harness and experiments pending. Dataset/model downloads and training excluded by AGENTS.md. |
| M7–M8 | Additional presentation sensors, socket transport, curated retrieval and workload profiling pending. |

## Current work-package evidence

| Package | Implemented slice / remaining boundary |
| --- | --- |
| W05 | Atomic additive migration from prior evidence-only schema; checksums/future versions checked. No destructive migration introduced. |
| W08 | Scoped snapshot membership with copied raw/parsed/normalized interpretations, digest and revisions; maximum 10,000 members. Cases currently use scenario/variant/question scope, not manual membership editing. |
| W11–W12 | Candidate shape/citation checks, delivery byte cap, retrieved-ID registry, snapshot-aware bundles with checksums and offline verifier. Mechanical validity is separate from semantic support. |
| W17 | Exclusive state-directory lock, bounded database queue, one owning thread and single active provider run. |
| W18 | Durable run/tool records, restart interruption marking, controlled successor retries and cooperative cancellation. Automatic ingestion-to-task scheduling/leases pending. |
| W21 | Offline checkpoint/copy backup, checksum verification and restore to empty state with report/evidence round-trip tests. No deletion/retention policy yet. |
| W23 | Triage priority/grouping and correlation links with rule/time/source provenance; one seed group per run. Automatic grouping into independently scoped cases/cooldowns pending. |
| W24 | Saved reports, persisted history and explicit parent-linked successor revisions connected to UI. No automatic reinvestigation. |
| W25 | Completion status independent of verdict; intent/endpoint-impact qualifiers and uncalibrated confidence label. Full disposition policy/evaluation pending. |

Next dependencies:
1. Design explicit file generations, archived-file recovery and durable source gaps;
   preserve visible append-only stops until recovery tests pass.
2. Add bounded automatic case proposals/scheduling with recoverable work leases.
3. Add a real-provider capability/configuration profile and contract tests before
   requesting any model installation or making provider performance claims.

No packet capture, network model calls or authentic dataset downloads were added.
