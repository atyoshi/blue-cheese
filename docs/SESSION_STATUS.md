# Session status — 2026-10-05

All six implementation tasks completed and committed/pushed separately to `origin/main`.

| Task | Status / evidence |
|---|---|
| 1 Baseline | Passed. Existing CLI/SQLite/Suricata retained; initial 10 tests passed. No applicable AGENTS existed; added architecture invariants. |
| 2 Scenarios / normalization / DuckDB | Passed. 30-record synthetic suspicious fixture; seed-73 poisoned copy; benign/insufficient fixtures. Exact accepted raw lines, parsed JSON, shared canonical alert/flow model, source/byte locators, stable IDs; scoped bounded parameterized tools; idempotent imports. Evaluator manifest excluded from telemetry and wheel. |
| 3 Investigation / Falsifier | Passed. Offline provider protocol; evidence-derived policy; real IP counterevidence query; contradicted/not observed/not available; six-call/five-second defaults; ablation; retrieved/scope/snapshot citation validation; JSON/Markdown. |
| 4 Presentation | Passed. Evidence, Investigation, Comparison, Live tabs; safe code/JSON log display; citation inspection and downloads; matched-settings comparison. Two AppTest interactions verify scenarios/findings/evidence and rerun/worker invariants. |
| 5 Continuous ingestion | Passed. One cached runtime, one worker, serialized DuckDB commands. Bounded reads/lines; pending partial records; malformed/oversized quarantine; atomic inserts/cursors; retry and restart/resume; distinct identical lines. Replay advances in background; live reports use fixed snapshots. Gap detection stops visibly. |
| 6 Verify / package / walkthrough | Passed for native presentation and packaging files. Locked fresh venv; 27 tests passed in 5.26s (no skips), Ruff passed, pip check passed. Coverage 74% (732/994 statements); AppTest executes the UI but this coverage run does not instrument its module. Wheel verified: four telemetry fixtures, no evaluator manifest. Compose config valid; Docker build/launch unverified (socket permission denied). |

## Run / exports

Entry point: `src/bluecheese/interfaces/demo.py`.

```bash
source .venv/bin/activate
python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501. Native server launched separately with locked dependencies; `/` and `/_stcore/health` returned successfully. Browser automation was unavailable; AppTest exercised the UI. Linux/Python 3.14.7 tested; macOS intended, unverified. README has fresh-install commands.

Docker: `mkdir -p telemetry` then `docker compose up --build -d`; `docker compose down` stops and preserves state. Localhost port only, UID 10001, persistent evidence volume, read-only external telemetry, separate writable replay spool. Build attempt blocked by `/var/run/docker.sock` permissions; no container execution claim.

Generated files in `demo-exports/`: `suspicious-clean.{json,md}`, `suspicious-poisoned.{json,md}`, `benign-clean.{json,md}`, `insufficient-clean.{json,md}`. They are local generated artifacts, ignored by Git. Recreate while app is stopped: `python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports`. Associated evidence persists in `bluecheese-data/evidence.duckdb`; do not run two processes on that DB.

Expected on/default results: suspicious clean SUSPICIOUS (alert + five active flows), poisoned UNCERTAIN (alert + four active flows, one zero-byte closed contradiction), benign BENIGN_CONFOUNDER, insufficient UNCERTAIN. Falsifier off: both suspicious variants SUSPICIOUS. These describe this rule policy, not LLM performance. Full five-minute script: docs/DEMO.md. Planned product: Blue_Cheese_Codex_Build_Prompt.md.

## Limits / deferred

Only alert/flow presentation normalization; first-alert investigation; 100-row query cap with report warning. Cooperative elapsed-time budget, not hard preemption. Replay cycles its fixture (new byte positions, intentionally repeated telemetry). Accepted raw text is exact; oversized quarantine retains only a labelled bounded prefix. Append-only contract: device/inode, size and committed 4 KiB prefix catch common gaps; arbitrary in-place edits or truncate/regrow between polls are not guaranteed detected. Full rotation recovery deferred. Stop/reset by selecting a new source/state after a detected gap.

Deferred as requested: five-role orchestration, vector RAG, real dataset downloads, model training, packet capture, new model/backend integrations, exhaustive rotation recovery, load testing, multi-platform CI and extra documentation. No existing real model provider was present. Docker execution/macOS remain unverified. Existing local `bad.pcap` and `real-data/` were left untouched and uncommitted.

Next three tasks:
1. Build/launch Compose under a user with Docker socket access; verify volumes and external telemetry permissions.
2. Run the locked native walkthrough on macOS; record actual portability issues/results.
3. Design explicit source-generation/reset and full rotation recovery, with gap/restart tests, before relaxing append-only limits.

## Master-plan implementation update — 2026-10-08

Working-tree changes, not committed: implemented canonical state-directory OS
locking before presentation store connection/schema initialization (W17 writer
exclusion), and atomic self-contained report bundles with offline verification
(W12 export integrity slice). No schema migration. Existing exports remain
compatible; `--bundles` adds version-1 historical directories without overwriting.
README documents commands; ROADMAP inventories unfinished milestones.

Measured Linux checks:
- `.venv/bin/python -m pytest -q`: 30 passed in 7.62 seconds.
- `.venv/bin/ruff check src tests`: passed.
- Export command with temporary state/output and `--bundles`: four reports and
  bundles generated with existing expected verdicts.
- Offline verifier on poisoned bundle: valid, six cited records, snapshot 63.

Lock tests include another process, a symlinked state directory, competing opens,
and reopen after close. Bundle tests include tampering, recomputed-checksum identity
failure, unseen citations, immutable destination and temporary cleanup.

This does not complete the master roadmap. Dedicated DB worker, rotation recovery,
materialized cases/snapshots, backup/retention, real provider, richer claim schema,
research harness and additional adapters remain pending. Bundle hashes are integrity
checks, not authentication; normalized evidence verification currently uses the
shipped parser, not archived interpretation versions. macOS/Docker unverified.
User's deleted build prompt, untracked master plan, bad.pcap and real-data untouched.
Next three work packages are recorded in ROADMAP.md.

## Continued master implementation — 2026-10-08

Specification used: `Blue_Cheese_Master_Implementation_Plan.md`, Sections 4, 9,
11–13, 17, 24; work packages W05/W08/W11/W12/W17/W18/W21/W23/W24/W25.
Base revision `ef6dc4f`; changes remain uncommitted. This supersedes the preceding
update's pending database-worker/case-history statements; full milestones are
still incomplete. ROADMAP.md records package boundaries and next dependencies.

Changed responsibilities:
- One bounded database worker now creates/uses/closes the runtime connection;
  providers run outside lifecycle/database locks. Queue capacity 64, one active
  provider run, startup failure cleanup and stopped-runtime rejection.
- Additive checksummed schema migration 1 preserves evidence/cursors and adds
  cases, frozen snapshots/interpretations, runs and persisted tool activity.
  Unknown/modified versions fail closed. No reset required for old schema.
- Atomic case revisions use fixed membership (10,000-record cap) and interpretation
  digests. Saved runs, parent-linked successors, interrupted recovery and
  completed/incomplete/cancelled/failed statuses are durable.
- Candidate structure/citation validation and 64 KiB per-call delivery cap added;
  only delivered records enter citation visibility. Failed tool dispatches consume
  the call budget. Cancellation and elapsed-time limits remain cooperative.
- Triage's legacy API retained; presentation triage groups/prioritizes visible
  alerts. Correlation and Orchestrator are now implemented, not placeholders.
  Conservative source/sensor/time/flow/tuple links show provenance and ambiguity.
  One seed group per run; all logical roles share the same broker/budget.
- UI shows triage/correlation, saved history, successor revisions and background
  work/cancellation. Bundles use frozen interpretations and snapshot manifests.
- Offline backup/verify/restore commands keep the state lock through checkpoint,
  close and copy. Restore requires empty state; raw evidence, reports and traces
  round-trip. External telemetry/spools are excluded; locators are not rewritten.

Measured Linux checks:
- `.venv/bin/python -m pytest -q`: 45 passed in 11.44 seconds, no skips.
- `.venv/bin/ruff check src tests`: passed.
- `.venv/bin/python -m pip check`: no broken requirements.
- `git diff --check`: passed.
- Legacy CLI help and new backup command help execute successfully.
- Fresh CLI export → offline verification → backup → restore → export → offline
  verification passed using `/tmp/bluecheese-master-check-9voivcth`. All four
  scenario verdicts preserved; poisoned and restored-clean bundles each verify
  six referenced records, snapshot 63. No real network/model calls.

Remaining boundaries: no full rotation recovery, durable ingestion scheduler,
manual case editing/merge/split, intermediate persisted workflow transitions,
retention/deletion, archived parser versions, real provider, research harness,
additional presentation sensors or measured workload envelope. Snapshots currently
copy interpretations, increasing disk usage; they are scope-wide while correlation
proposes a narrower seed neighborhood. Case questions label scope; the demo rule
policy does not answer arbitrary questions. macOS/Docker execution unverified.
Legacy CLI/SQLite/PCAP/web paths retained. User's deleted build prompt and untracked
master plan, bad.pcap and real-data remain untouched. No dependencies added.

Next three dependencies: explicit source generations/rotation recovery; bounded
case scheduling/recoverable work leases; real-provider configuration/capability
contract. See ARCHITECTURE.md and docs/adr/001-local-runtime-and-snapshots.md.
