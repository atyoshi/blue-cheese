# Blue Cheese local presentation

A small offline prototype: **raw Suricata EVE → shared normalization → DuckDB evidence → investigation → executable Falsifier → cited JSON/Markdown**. All bundled scenarios are **synthetic**, not CTU-13, ATLAS or a real capture. The default **Deterministic demo provider** uses rules, needs no model/API key/network at runtime, and does not establish malicious intent or measure LLM superiority.

## Native launch (presentation fallback)

From the repository root, use Python **3.11 or newer**. Linux with Python 3.14.7 was tested; macOS portability is intended, not verified. Installing dependencies needs package-registry access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

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

Typed tools are parameterized, scoped by scenario/variant and a fixed append-only snapshot, and capped at 100 records. The demo investigates the first alert and flows matching its non-null flow ID and endpoints. Established flows with at least 10,000 outbound bytes support `SUSPICIOUS`. The Falsifier independently queries the source IP for matching closed zero-byte flows: those produce `BENIGN_CONFOUNDER` when there is no active-flow support, or `UNCERTAIN` with conflicting support. An alert alone stays `UNCERTAIN`. These are inspectable demonstration rules, not universal security classifications. Enrichment text never drives this policy. The replaceable provider protocol preserves a small extension point; the repository had no existing real model provider.

Default budgets are six tool calls and five seconds. Time limits are cooperative checks around queries/provider execution, not hard process preemption. Citation validation rejects invented, cross-scope and unseen IDs. Snapshot-bound reports remain unchanged while replay adds evidence.

One cached runtime owns DuckDB access and serializes UI, investigation and one ingestion worker through its lock. Replay appends one record every 0.5 seconds, cycling the synthetic fixture. Live refreshes every second. Reads are capped at 256 KiB/poll and lines at 64 KiB. Unterminated lines remain pending; oversized complete lines are quarantined with a bounded raw prefix explicitly marked as truncated. Accepted-event raw input is exact. Evidence/quarantine and committed source identity/offset commit in one transaction. Partial bytes are reread after restart. Append-only sources must preserve their existing bytes: device/inode, size and a committed 4 KiB prefix detect common replacement/truncation; undetected in-place edits or truncate/regrow between polls are outside this milestone. A detected gap stops with a clear message; select a new file/state to reset. Full rotation recovery is deferred.

Other deferred scope: five-role orchestration, vector RAG, real datasets, training, capture, new model/backend integrations, load testing and multi-platform CI. See the existing [planned-product design](Blue_Cheese_Codex_Build_Prompt.md).

## Preserved Suricata CLI

The existing PCAP/EVE import, SQLite evidence, triage and simple web UI remain available. For PCAP import, install Suricata separately on PATH:

```bash
bluecheese --data-dir demo-data import-pcap tests/fixtures/bluecheese-demo.pcap --config tests/fixtures/suricata-demo.yaml --rules tests/fixtures/bluecheese-demo.rules
bluecheese --data-dir demo-data alerts
bluecheese --data-dir eve-data import-eve tests/fixtures/sample_eve.json
```

Use `bluecheese --help` for `evidence`, `triage`, `report` and the legacy `serve` command (localhost:8765). The bundled PCAP produces a synthetic payload alert and a related flow; its rule match alone does not prove compromise.
