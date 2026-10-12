# Implementation roadmap

Authority: `Blue_Cheese_Master_Implementation_Plan.md`, particularly Sections 9,
11–13, 17 and work packages in Section 24. Status describes implemented code,
not completion of the intended system.

| Milestone | Current status |
| --- | --- |
| M0 | Baseline inventoried; CLI, SQLite, PCAP and legacy web paths retained. |
| M1 | Offline rule-based Investigator/Falsifier, structured citation validation, deterministic reports and offline-verifiable bundles. Parser archives and full claim semantics pending. |
| M2 | Bounded append-only ingestion, replay, checkpoints, UI and exports retained. Background runs/cancellation and saved-report loading added. |
| M3 | Canonical directory lock, owning database worker, additive checksummed migration, materialized interpretations/snapshots, interrupted-run recovery and offline backup/restore implemented. Bounded rename recovery, archive matching and pinned-evidence retention added; native macOS verified. Exhaustive source recovery and Docker execution pending. |
| M4 | Deterministic triage/correlation connected through Orchestrator with one shared budget; case revisions and successor history persisted. GUI-configurable OpenAI-compatible tool-using Investigator/Falsifier, capability probe and durable single-task queue added; live model validation and full case editing pending. |
| M5–M6 | Research harness and experiments pending. Dataset/model downloads and training excluded by AGENTS.md. |
| M7–M8 | Unix stream input, interactive operational visuals and isolated finite-backlog benchmark added. Additional sensors, curated retrieval and sustained workload profiling pending. |

## Current work-package evidence

| Package | Implemented slice / remaining boundary |
| --- | --- |
| W05 | Atomic additive migration from prior evidence-only schema; checksums/future versions checked. No destructive migration introduced. |
| W08 | Scoped snapshot membership with copied raw/parsed/normalized interpretations, digest and revisions; maximum 10,000 members. Cases support selected-alert same-source/time/endpoint neighborhoods or whole-scope snapshots; manual membership editing remains pending. |
| W11–W12 | Candidate shape/citation checks, delivery byte cap, retrieved-ID registry, snapshot-aware bundles with checksums and offline verifier. Mechanical validity is separate from semantic support. |
| W17 | Exclusive state-directory lock, bounded database queue, one owning thread and single active provider run. |
| W18 | Durable run/tool records, restart interruption marking, controlled successor retries and cooperative cancellation. Atomic alert enqueue and explicit retry after interrupted work added; one runtime claims tasks. No distributed leases. |
| W21 | Offline checkpoint/copy backup, checksum verification and restore to empty state with report/evidence round-trip tests. Bounded retention preview/apply added; snapshots and work references remain pinned, with tombstones and a monotonic receipt watermark. |
| W23 | Triage priority/grouping and correlation links with rule/time/source provenance; one seed group per run. Automatic grouping into independently scoped cases/cooldowns pending. |
| W24 | Saved reports, persisted history and explicit parent-linked successor revisions connected to UI. No automatic reinvestigation. |
| W25 | Completion status independent of verdict; intent/endpoint-impact qualifiers and uncalibrated confidence label. Full disposition policy/evaluation pending. |

Next dependencies:
1. Individual authentication, role enforcement, session controls and verified shared
   deployment for the selected single-customer, multiple-analyst SOC target.
2. Live endpoint/model compatibility, semantic claim validation and legally usable
   labelled detection-quality evidence; no accuracy claim follows from synthetic tests.
3. Sustained ingestion/overload, sensor drop monitoring, spool lifecycle management,
   Docker execution and remaining master-plan acceptance criteria.

Current Unix stream input is local, single-producer and owner-only. It uses a
256 MiB persistent receipt spool and stops visibly on disconnect, quota or unresolved
partial prior records. It does not guarantee sensor-side delivery completeness.
Operational visual summaries use a labelled 250/1,000/5,000-record window and do not
change provider retrieval/citation authority. README documents short launches.

No packet capture, live network model calls or authentic dataset downloads were added.

The operational sidebar now configures endpoint, Investigator/Falsifier models,
in-memory credentials, strict-schema/JSON-object output and provider limits.
Model roles can request typed read-only queries; software validates arguments,
enforces scope/budgets and checks citations. A synthetic capability probe runs only
on explicit click. Profiles last for the runtime process. This implements another
slice of Sections 13/15; prompt-file versioning, schema repair, cost reservation,
redaction profiles and live server compatibility remain pending.

Live workflow visibility now covers rule-based roles and model roles, actual
handoffs, model-response waits and typed retrieval. A bounded process-local activity
snapshot drives an independent read-only GUI refresh; completion, cancellation,
failure and budget exhaustion stop the running indicator. Saved reports include
the activity through report preparation. No synthetic delays or extra workers
were introduced.
