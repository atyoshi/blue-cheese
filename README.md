# Blue Cheese local presentation

A local evidence-centered prototype: **raw Suricata EVE → normalization → DuckDB snapshots → triage/correlation → Investigator/Falsifier → cited JSON/Markdown**. All bundled scenarios are **synthetic**, not CTU-13, ATLAS or a real capture. The default **Deterministic demo provider** uses rules, needs no model/API key/network at runtime, and does not establish malicious intent or measure LLM superiority.

## Current status

The presentation implements deterministic logical roles, bounded file ingestion and
synthetic replay, immutable run snapshots, persisted case revisions and successor
history, background investigation/cancellation, auditable report bundles and offline
backup/restore. A single database worker owns DuckDB; an exclusive state-directory
lock prevents competing runtimes and exports. The legacy CLI/SQLite path remains
available.

The full master plan is **not complete**. Dependable local operation (M3) still
needs rotation recovery, retention and platform verification; M4 has deterministic
roles but no real model provider or automatic case scheduling. The latest recorded
Linux checks are **45 passing tests**, Ruff and dependency checks, plus an
export → backup → restore → export verification round trip. Docker execution and
macOS remain unverified. See [verification details](docs/TESTING.md) and
[measured handoff](docs/SESSION_STATUS.md).

The specification is [Blue Cheese Master Implementation Plan](Blue_Cheese_Master_Implementation_Plan.md).
[ROADMAP.md](ROADMAP.md) tracks implemented slices and remaining gates;
[ARCHITECTURE.md](ARCHITECTURE.md) describes current boundaries.

## Native launch (presentation fallback)

From the repository root, use Python **3.11 or newer**. Linux with Python 3.14.7 was tested; macOS portability is intended, not verified. Installing dependencies needs package-registry access.

Use an up-to-date checkout before installing: `git pull --ff-only`. The commands
below use the lockfiles included in the current repository. If
`requirements-dev.lock` is missing, check that you are in the repository root
and that your checkout is current.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

For an editable development install using dependencies from `pyproject.toml`,
you can instead run the following in your activated environment:

```bash
python -m pip install -e ".[dev]"
python -m pytest -v
```

This installs pytest and Ruff alongside the application. Use the lockfile
installation above for the packaged presentation environment and its coverage
checks.

Open **http://127.0.0.1:8501**. The last command runs the application; Ctrl-C stops it. Launch only one application process per state directory. The four tabs are Evidence, Investigation, Comparison and Live. A rerender retains saved investigations; only investigation buttons run the provider. The Falsifier toggle and budgets apply to the next run. Replay starts only when requested.

State defaults to `./bluecheese-data/evidence.duckdb`; replay appends to `./bluecheese-data/replay/eve.jsonl`. Set `BLUECHEESE_STATE=/absolute/writable/path` and optionally `BLUECHEESE_REPLAY=/another/writable/path` before launch. Existing CLI state remains SQLite and is independent.

To create the bundled presentation exports **while the app is stopped**, using the same state:

```bash
python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports
```

This writes `suspicious-clean`, `suspicious-poisoned`, `benign-clean`, and `insufficient-clean` JSON/Markdown files. UI download buttons export saved offline/comparison/live reports. Reports state provider, snapshot, budget, warnings, unresolved evidence and validated citations.

## Docker Compose

With Docker Engine and Compose available to your user:

```bash
mkdir -p telemetry
docker compose up --build -d
docker compose logs -f bluecheese
docker compose down
```

`up` builds and starts the non-root app at **http://127.0.0.1:8501**; `logs` follows output; `down` stops it and retains volumes. Native and Docker use `requirements.lock`. Persistent evidence is in `evidence-state`, and the separate writable replay spool is in `replay-spool`. `./telemetry` mounts read-only at `/telemetry`; to follow an external growing EVE file, place it there and choose **External append-only EVE file**, path `/telemetry/eve.jsonl`, in Live. Set `BLUECHEESE_TELEMETRY=/absolute/source/directory` to mount another directory. No privileged mode or host networking is needed.

Compose configuration was validated. Build/launch is **unverified**: this session's user cannot access `/var/run/docker.sock`. Use native launch as the presentation fallback. The container intentionally excludes the legacy PCAP sensor path; it does not install Suricata.

## Verify

```bash
python -m ruff check src tests
python -m pytest -q --cov=bluecheese --cov-report=term-missing
```

Tests use temporary stores and files, offline fixtures, deterministic polling and no models/API keys. Existing PCAP integration uses local Suricata if installed and otherwise skips. AppTest exercises scenario selection, evidence, findings, saved runs and worker reuse. See [session status](docs/SESSION_STATUS.md) for measured results and [five-minute walkthrough](docs/DEMO.md).

## Implementation choices and limits

The presentation extends `NormalizedAlert` and the Suricata adapter with flow counters/state. Each event stores exact raw UTF-8 text including its newline, parsed JSON, canonical fields, source locator and an ID hashing scope, source identity, byte position and content. Identical lines at different positions remain distinct; retries at the same position do not duplicate acceptance. Malformed records are quarantined.

Typed tools are parameterized, scoped by scenario/variant and materialized snapshot membership, and capped at 100 records and 64 KiB of delivered evidence per call. Triage groups up to 20 visible alerts into five-minute buckets and assigns review priority separately from sensor severity. The Orchestrator selects one seed group by priority and stable occurrence ID. Correlation links same-source/sensor observations within a five-minute window using flow IDs/endpoints or exact endpoint tuples; links record their rule basis and ambiguity. The demo investigates the selected alert and correlated flows matching its non-null flow ID and endpoints. Established flows with at least 10,000 outbound bytes support `SUSPICIOUS`. The Falsifier independently queries the source IP for matching closed zero-byte flows: those produce `BENIGN_CONFOUNDER` when there is no active-flow support, or `UNCERTAIN` with conflicting support. An alert alone stays `UNCERTAIN`. These are inspectable demonstration rules, not universal security classifications. Enrichment text never drives this policy. The replaceable provider protocol preserves a small extension point; the repository had no existing real model provider.

Default budgets are six tool attempts and five seconds, shared across all logical roles. Dispatched tool failures consume the call budget; records withheld by the byte cap cannot be cited. Time limits are cooperative checks around queries/provider execution, not hard process preemption. Citation validation rejects invented, cross-scope and unseen IDs. Snapshot-bound reports remain unchanged while replay adds evidence.

One cached runtime submits database operations to a bounded 64-command queue on one owning worker thread. Its RLock protects lifecycle/follower state; provider execution runs outside database locks, allowing ingestion to continue. Only one provider investigation may be active. Each run freezes up to 10,000 scoped evidence interpretations; later records or normalization changes cannot alter that run. Replay appends one record every 0.5 seconds, cycling the synthetic fixture. Live refreshes every second. Reads are capped at 256 KiB/poll and lines at 64 KiB. Unterminated lines remain pending; oversized complete lines are quarantined with a bounded raw prefix explicitly marked as truncated. Accepted-event raw input is exact. Evidence/quarantine and committed source identity/offset commit in one transaction. Partial bytes are reread after restart. Append-only sources must preserve their existing bytes: device/inode, size and a committed 4 KiB prefix detect common replacement/truncation; undetected in-place edits or truncate/regrow between polls are outside this milestone. A detected gap stops with a clear message; select a new file/state to reset. Full rotation recovery is deferred.

Other deferred scope includes automatic case scheduling/editing, retention, real model providers, historical parser archives, vector retrieval, authentic dataset evaluation, training, packet capture, sustained load testing and multi-platform CI. Current correlation proposals do not automatically narrow case membership or schedule new investigations.

## Preserved Suricata CLI

The existing PCAP/EVE import, SQLite evidence, triage and simple web UI remain available. For PCAP import, install Suricata separately on PATH:

```bash
bluecheese --data-dir demo-data import-pcap tests/fixtures/bluecheese-demo.pcap --config tests/fixtures/suricata-demo.yaml --rules tests/fixtures/bluecheese-demo.rules
bluecheese --data-dir demo-data alerts
bluecheese --data-dir eve-data import-eve tests/fixtures/sample_eve.json
```

Use `bluecheese --help` for `evidence`, `triage`, `report` and the legacy `serve` command (localhost:8765). The bundled PCAP produces a synthetic payload alert and a related flow; its rule match alone does not prove compromise.

## Auditable offline bundles

With the app stopped, export to a new directory:

```bash
python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports-v2 --bundles
python -m bluecheese.application.report_bundle demo-exports-v2/suspicious-poisoned.bundle
```

Bundles include reports, scoped run manifest, tool trace, referenced exact raw,
parsed and normalized evidence, and SHA-256 checksums. Offline verification checks
retrieval visibility, occurrence identity, normalization and snapshot bounds.
Checksums detect corruption; they are not signatures or semantic support checks.
Existing bundles are never overwritten. Schema version 1 uses the current demo
parser; archived parser versions remain pending.

Presentation stores acquire an exclusive OS lock on the resolved state directory
before schema initialization. Competing runtimes/exports fail with instructions
to stop the first runtime or select another state directory. The lock file stays
on disk; OS ownership releases on process exit. Linux is tested; macOS execution
remains unverified. See ROADMAP.md for master-plan gaps.

## Case history, background work and backups

The Investigation tab now shows triage groups and correlation links. Saved case
runs survive restarts: load a report without rerunning it, or explicitly create a
successor revision linked to a selected run. The case question identifies the case;
the current deterministic policy investigates alert/flow observations and is not
a general question-answering model. It selects one bounded seed group per run.

“Start background investigation” keeps the UI responsive; “Cancel active
investigation” requests cooperative cancellation. The current provider call must
return before cancellation takes effect. Incomplete, cancelled and failed runs
remain distinct from completed reports with an uncertain verdict. Restart marks
unfinished work interrupted and retains its tool trace for a controlled successor.

Stop the app before backing up. Use a new backup directory and an empty restore
state directory:

```bash
python -m bluecheese.application.backup backup --state bluecheese-data --out backups/demo-001
python -m bluecheese.application.backup verify backups/demo-001
python -m bluecheese.application.backup restore --source backups/demo-001 --state restored-state
BLUECHEESE_STATE=restored-state python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1
```

Backups checkpoint and close the database while retaining the exclusive state
lock, copy it, and verify its hashes/schema/counts before publishing. Restore
preserves saved reports, snapshot interpretations and tool traces. External
telemetry and replay spools are not included; original source locators/cursors are
preserved and are not rewritten to imply continuity at a new location. Export
report bundles from the restored database for independent inspection.

Schema migration 1 adds case/snapshot/run/tool tables without changing existing
evidence or cursors. Migration metadata has a checksum; unsupported future or
modified migrations fail closed. No state reset is required for the previous
evidence-only schema. Database access now runs on one owning worker thread with
a bounded command queue, while lifecycle/follower state remains under the RLock.
See ARCHITECTURE.md and ROADMAP.md for the supported slice and remaining gates.

## Next steps

Follow the master plan's dependency order:

1. **Complete rotation recovery:** explicit source generations, draining archived
   files, restart-safe cursors and durable telemetry-gap records.
2. **Add recoverable case scheduling:** bounded triage/correlation case proposals,
   durable work items, cooldowns and controlled retries after restart.
3. **Finish local-operation release gates:** retention that protects evidence used
   by saved reports, Docker execution and native macOS verification.
4. **Integrate a real provider:** explicit capability/configuration profiles,
   structured-output validation, timeout/error handling and shared budgets, tested
   with fake providers before using a real model.
5. **Build the research harness:** matched baselines and poisoning experiments,
   with evaluator labels isolated from agent inputs and results limited to the
   tested scenarios.

Review and commit the tested implementation as a checkpoint before the next code
slice. See [ROADMAP.md](ROADMAP.md) for package-level boundaries and
[session status](docs/SESSION_STATUS.md) for the current handoff. Dataset/model
downloads and training remain excluded by the repository instructions.
