# Session status
1. Baseline: complete. Existing CLI/SQLite/Suricata pipeline retained; 10 tests passed.
2. Scenarios / shared normalization / DuckDB: complete. 30 synthetic records, seeded poisoned copy, benign/insufficient fixtures; 4 focused tests passed.
3. Investigator / executable Falsifier / cited exports: complete. Offline provider, scoped retrieval ledger, call/time budgets, ablation, JSON/Markdown. 7 investigation tests passed.
4. Streamlit presentation: pending.
5. Continuous append-only ingestion / replay: pending.
6. Verification / packaging / walkthrough: pending.

Presentation entry point: `src/bluecheese/interfaces/demo.py`.
Native command (after dependencies): `python -m streamlit run src/bluecheese/interfaces/demo.py`.
Reuse NormalizedAlert and Suricata normalization; retain legacy CLI. New local runtime serializes DuckDB access. Default provider is deterministic and offline. Planned product reference: `Blue_Cheese_Codex_Build_Prompt.md`.
