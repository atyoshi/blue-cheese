# Blue Cheese architecture and invariants

Preserve the existing CLI (`cli.py`), PCAP/EVE import, SQLite evidence, triage and legacy web UI. The presentation entry point is `src/bluecheese/interfaces/demo.py`; exact launch/check commands are in README.md. Reference planned product: Blue_Cheese_Codex_Build_Prompt.md. Current handoff: docs/SESSION_STATUS.md; walkthrough: docs/DEMO.md.

Presentation components:
- `domain/models.py` / `adapters/suricata.py`: shared canonical alert/flow normalization.
- `adapters/duckdb_store.py`: immutable raw text, parsed/normalized evidence, scoped bounded parameterized tools, quarantine/cursors.
- `agents/investigator.py`: replaceable provider protocol, deterministic offline Investigator, executable Falsifier, retrieval ledger, budgets and citation validation.
- `agents/reporting.py`: cited JSON/Markdown.
- `application/demo_runtime.py`: cached single-process runtime; one polling worker; serialized database access through its RLock.
- `application/ingestion.py`: testable bounded `poll_once()`, append-only source detection and atomic event/quarantine/cursor commit.
- `application/export_demo.py`: offline export command, run while the app is stopped.
- `data/*.jsonl`: synthetic fixtures. Evaluator manifest stays in docs/evaluator and never enters provider inputs.

Invariants: accepted raw text is exact and immutable. Event IDs include source identity, byte position, content and scope; identical lines at distinct positions are distinct. Every tool query uses case/variant and the run snapshot. Validate citations against actual retrieval, not mere store membership. Do not infer results from scenario/variant names or injection labels. Display log text using code/JSON widgets. No investigations or duplicate workers on rerender. Replay is synthetic logging, not packet capture. On source gaps stop visibly; full rotation recovery is deferred. The time budget is cooperative, not hard preemption. One process per state DB, including exports.

Tests beside implementation behavior live in tests/test_demo_store.py, test_investigator.py, test_ingestion.py and test_demo_ui.py. Retain legacy tests. Use temporary paths/no network/no real models; deterministic polling replaces sleep-based tests. Package using the same requirements.lock for native and Docker. Do not add an agent framework, restructure the repository or download datasets/models.

Implemented tasks 1–6; container execution and macOS remain unverified. See session status for measured checks and deferred scope.
