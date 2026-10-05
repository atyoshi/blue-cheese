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
