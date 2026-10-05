# Blue Cheese implementation prompt

You are working in the existing Blue Cheese repository. Build a small, complete, demonstrable system for tomorrow and preserve a clear path to the planned finished product. Develop for Linux and macOS, with a reproducible Docker option, and implement continuous ingestion of growing security logs as well as offline scenarios.

Inspect repository instructions, code, tests, configuration and docs first. Reuse working NormalizedAlert models, Suricata normalizers, agents and any existing ingestion loop. The owner has worked on this in another chat: verify the repository instead of assuming that conversation context is available or that a feature is implemented. Preserve existing functionality. Do not reorganize files for aesthetics. Make routine decisions yourself and document assumptions. Finish the workflow, tests and docs; do not stop at scaffolding.

## 1 Purpose and milestone

Blue Cheese is a lightweight, modular cybersecurity investigation framework. Its planned five roles are Orchestrator, Triage, Correlation, Investigator and Reporter. For this milestone implement an Investigator and Reporter with deterministic orchestration; document the other roles as future capabilities.

Implement this actual data path:

Security telemetry → source adapter → deterministic normalization → DuckDB evidence store → evidence tools → Investigator → validated findings → Reporter → Streamlit.

The audience must be able to inspect the raw input, its normalized representation, the queries made, the actual supporting records, the resulting report, and clean versus poisoned results. Add a live view that visibly updates when new records arrive.

Deliver three input modes:

1. Offline scenario import using bundled data.
2. Continuous ingestion from a growing Suricata EVE JSONL file.
3. Paced replay of bundled data into a new demo file, exercising the same continuous reader. Label this explicitly as replay of synthetic data rather than a live capture.

Live ingestion is included now. Packet capture is a separate sensor concern. Do not implement packet sniffing inside the app. PCAP may later be processed by external Suricata/Zeek adapters; do not present unsupported PCAP upload as working.

## 2 Architecture and interfaces

Use small protocols and concrete implementations for SourceReader, SensorPlugin, EvidenceStore, EvidenceTools, Investigator, Reporter and LLMProvider. Keep SQL inside the DuckDB implementation and telemetry parsing outside agents. Prefer standard-library mechanisms to a new framework.

Adapt the repository to conceptual components such as core/models, plugins/sensors/suricata, plugins/stores/duckdb_store, plugins/llms/mock, tools/evidence, ingestion/tailer, ingestion/replay, scenarios/loader, scenarios/poisoning, workflows/investigate, runtime/manager, ui/app and cli. Equivalent existing locations are acceptable.

Future sensors, models, retrieval methods and stores should be replaceable without rewriting the workflow. Do not create a large plugin discovery system: explicit registration is enough. Preserve existing providers if present.

## 3 Evidence and provenance

Preserve/extend the existing normalized model. Expose event_id, timestamp, sensor, event_type, src_ip, src_port, dest_ip, dest_port, protocol, alert_signature, severity, raw_event and source_file. Permit absent optional fields and additional DNS/HTTP/flow fields. Preserve raw bytes or an immutable raw archive alongside parsed JSON: parsed JSON alone does not preserve the exact original formatting.

Store source_id, source generation, byte offset or line locator, ingestion timestamp, raw content hash and parser version. Separate ingestion time from event time. Use UTC-aware timestamps and preserve the original timestamp string. Evidence IDs must remain stable across retries and restart, including repeated identical records at different locations. Do not use row order, wall-clock time, randomized hash() or the content hash alone. Use a documented deterministic source identity + generation + offset + content-hash scheme. IDs remain unchanged when replaying already committed source positions.

Namespace scenarios and evidence variants to prevent clean/poisoned runs or independent cases from mixing. Preserve original event IDs across a paired experiment for unchanged records; give injected records separate IDs and changed copies explicit parent references. Version the schema and reject incompatible input with useful errors.

Provide deterministic tools: get_event, list_alerts, find_events_by_ip, find_connections, search_events and get_case_summary. Return structured bounded results containing evidence IDs. Use parameterized SQL. Record tool names, inputs, result counts and returned IDs; do not expose hidden reasoning. Queries must stay within the case, variant and snapshot.

## 4 Bundled scenarios and corruption

Include approximately 20–100 synthetic Suricata-style events with benign background traffic, multiple related suspicious records and a scenario manifest. Also include a benign control and an insufficient-evidence case. Clearly identify all fixtures as synthetic. External datasets are optional future inputs, not an installation prerequisite; never mislabel fixtures as CTU-13 or CICIDS captures.

Keep ground truth in evaluation-only metadata. It may appear in a clearly labelled audience/evaluation panel, but never in model prompts, agent-visible summaries or retrieval responses. The mock must also infer its deterministic result from the available input rather than read the answer label.

Create a seeded corruption generator operating on copies. Include misleading enrichment/context and, if feasible, one altered-log variant. Keep originals immutable and save a manifest of injected/modified IDs, strategy, seed, parent hashes and parameters. Distinguish log corruption from retrieved-document poisoning: a log-only experiment does not establish RAG robustness.

Mark experimental artifacts synthetic/injected in an evaluator-only manifest and audience view. Do not automatically expose oracle labels to the investigator. Any trust signals visible to the agent must also be available in the intended real deployment, such as source identity, integrity checks or document provenance. Hashes support integrity checking, not proof that a source tells the truth.

Run clean and poisoned variants using the same model/provider, prompt, retrieval policy and budget. Never hard-code a poisoned run to fail or a provenance-aware run to win. Present actual results. A deterministic mock demonstrates plumbing and regression behavior, not LLM performance or research superiority.

## 5 Continuous ingestion

Implement a testable incremental JSONL reader with poll_once() and an interruptible worker wrapper. Use portable file polling and pathlib; avoid tail -F, Linux-only inotify and macOS-only filesystem APIs. Default polling may be around one second, configurable. Never rescan the whole file on every poll.

Required behavior:

- Read complete newline-terminated records; retain incomplete trailing bytes until completed. Handle UTF-8 characters split across reads.
- Handle valid alerts, DNS, HTTP and flow records according to supported schemas. Report unsupported or invalid records explicitly.
- Quarantine malformed complete records with original bytes, source locator and parse error, then continue with later valid lines. Bound line size and memory; an oversized line must not consume unbounded RAM.
- Support start-from-beginning and start-from-current-end as explicit settings. Resume from a saved checkpoint by default.
- Commit accepted events or quarantine records and the corresponding consumed checkpoint transactionally. On failure, do not advance past uncommitted records. Make retries idempotent.
- Maintain durable source identity/generation and cursor state. Handle rename-and-create rotation and detectable truncation; test both. Drain an accessible old file before switching. If continuity cannot be established, report a gap rather than claim lossless ingestion. Rapid copytruncate or disappearance before polling can lose data; document that boundary.
- Display source path, status, last observed record, last ingest time, ingested/invalid/duplicate counts, lag/backlog when measurable and gap warnings. No file, bad permissions or temporary read error should crash the entire application.
- Use bounded queues or bounded batch reads and interruptible backoff. Preserve unread input during overload; do not silently drop events.
- Provide start, stop and restart with clean worker shutdown. Streamlit reruns or multiple browser sessions must not spawn duplicate tailers.

Source readers produce records; normalization is shared by import, tail and replay. Default investigations remain manual. If automatic investigation is added, use explicit opt-in, debounce, fixed case windows, one in-flight investigation per case and strict call/time budgets. Do not call an LLM for every event.

## 6 DuckDB ownership and snapshots

Do not run independent ingestion and UI processes against the same native DuckDB file in read-write mode. For this milestone choose one process-wide runtime per data directory: a dedicated store worker owns the DuckDB connection and serializes writes, queries and checkpoint transactions through a bounded command queue. Streamlit accesses it through tools and a cached runtime facade. Other workers never use that connection directly. Background workers never call Streamlit APIs.

Use a maintained portable file-lock mechanism to reject a second process opening the same runtime directory for writing. CLI commands use their own data directory or exclusive ownership when the GUI is stopped. A separate replay producer may append telemetry without opening DuckDB. Do not add an API service solely to fix ownership.

Capture a stable evidence snapshot ID/watermark before investigation. Investigation and reporting use that same bounded snapshot while ingestion continues. New events become available to the next run. Persist run IDs, settings and snapshot identity so exports remain auditable.

## 7 Investigator and reporting

Define an LLMProvider interface and a deterministic MockLLMProvider for offline operation. Display a persistent “Deterministic demo provider” label when active. Preserve an existing real provider; an optional OpenAI-compatible adapter is useful only if it does not delay the functioning offline slice. Use configurable timeouts, bounded retries and call limits; store no secrets in the repository.

Produce structured results: verdict MALICIOUS/BENIGN/UNCERTAIN, summary, evidence_ids, concise explanation, claim-level evidence references and warnings. Confidence is optional and must be labelled heuristic or model-reported unless calibrated; never display an invented 0.91 as a measured probability.

Validate verdict, schema, cited IDs, case/variant membership, snapshot membership and whether citations were actually returned to the investigator. Reject invented IDs, cross-case citations and references to unseen records. Citation existence alone does not prove a claim is supported: use deterministic claim checks where feasible and disclose that semantic support still requires evaluation. Treat log text and retrieved context as untrusted data, never as tool instructions. For insufficient/conflicting evidence return UNCERTAIN or clearly qualified findings.

The Reporter uses stored cited records, not fabricated details. Produce JSON and Markdown exports containing case and variant, run/provider/settings, snapshot, verdict, labelled confidence, summary, claims and citations, relevant timeline, raw/normalized supporting evidence, warnings and tool activity. Include input/source hashes and processing counts. Distinguish sensor alerts from conclusions about actual compromise.

## 8 Streamlit demonstration

Keep the UI simple and readable. Add scenario selection, Clean/Poisoned, Offline/Live/Replay, provider label and Run Investigation. Use tabs or sections for Overview, Raw Input, Normalized Events, Live Ingestion, Agent Activity, Findings and Comparison.

Select one record and display exact archived raw text/JSON alongside its normalized fields with the same ID and locator. Raw/normalized counts, filtering and skipped-record counts must reconcile. Selecting a finding citation must reveal that exact record. Escape untrusted content; do not render log-supplied HTML with unsafe HTML enabled.

Live controls show start/stop, configured path and ingestion counters. Refresh the display without a blocking infinite loop; rerenders only retrieve runtime state. Keep ingestion independent of a browser refresh. Separate replay status from actual sensor log following. Show clean/poisoned runs side by side only when paired settings and scenario snapshot make comparison valid; otherwise flag the mismatch. Export both results and the experiment manifest.

Provide a five-minute presentation script: inspect source data, select a raw/normalized record, investigate, inspect citations, compare variants, replay new records into the live reader, show increasing counts, stop and resume, export the report. Do not invent screenshot or benchmark results.

## 9 Linux and macOS with Docker

Support native Python development using uv on Linux and macOS. Use one mutually compatible stable dependency set and commit uv.lock. Keep paths configurable and use pathlib. Avoid GNU-specific shell assumptions, absolute developer paths and unnecessary root requirements. Document Intel/Apple Silicon macOS and Linux amd64/arm64 as intended targets; mark targets actually tested separately.

Add Dockerfile, compose.yaml, .dockerignore and .env.example. Use a suitable pinned Linux Python base and the same uv.lock as native development. Run as a non-root user with correct volume permissions. Bind the published UI to 127.0.0.1:8501 by default, persist runtime data in a named volume, and mount the external telemetry directory read-only. Mount the directory rather than just eve.json so rotation replacements remain visible. Keep demo replay output in a separate writable spool. No privileged mode, Docker socket mount or host-network requirement for the application. Handle SIGTERM cleanly and provide a health check that does not require an extra curl install.

Docker packages the application; it does not make macOS host packet capture identical to Linux. On Linux an external Suricata sensor may capture traffic and write EVE logs. On macOS use existing logs, replay or logs produced by a Linux sensor/VM. Both modes feed the same file adapter. Do not claim an application container sees all host network traffic. Document optional host LLM endpoint configuration separately from offline defaults.

README commands should work from a clean checkout, for example uv sync --locked, uv run pytest, uv run ruff check ., uv run streamlit run <actual-app-path>, and docker compose up --build. Explain each command and document prerequisites, input directory permissions, volume persistence, stop/resume and troubleshooting. Docker is optional for running tests.

## 10 Tests and verification

Use pytest, pytest-cov and ruff unless established equivalents exist. Default tests use no internet, API keys, real LLM, installed sensor, Docker or external database. Block outbound provider/network calls in tests. Use temporary files/DuckDB and fake clocks or poll_once() to avoid timing-flaky sleeps. Aim for at least 85% coverage of deterministic core modules with explicit coverage scope; meaningful behavior matters more than a inflated global percentage.

Unit tests: normalization and optional fields, timestamp/port handling, raw-byte preservation, stable IDs and legitimate identical records at different offsets; manifest validation; tool filters; seeded non-mutating corruption; result/citation validation; reporting and serializable exports. Include benign and insufficient-evidence controls.

Integration tests: actual scenario → normalizer → DuckDB → tools, tools → MockLLM investigator → validated reporter; transactional ingest/checkpoint success and rollback; source/variant isolation; snapshot consistency while more events arrive.

Live-reader tests: append after EOF, split JSON/UTF-8, no premature partial-line parsing, malformed and oversized lines, empty/missing files, permissions/read errors, rename rotation, detectable truncation, restart/resume, retry/dedup, source gap warnings, bounded backlog, stop/restart, duplicate-worker prevention and rejection of a second writer process. Assert no loss/duplication for the documented append-only and tested rotation cases, not impossible guarantees for arbitrary file replacement.

Regression/golden tests: checked-in expected semantic results for clean, poisoned, benign and uncertain fixtures, event counts, normalized field values, exact cited IDs, tool results, warnings and export schema. Exclude volatile timestamps/latencies; compare meaningful structure. Never automatically update goldens to hide failures.

Smoke tests: import, DB initialization, fixture loading, complete workflow, CLI help, and actual Streamlit startup when feasible. An import is not a launch test.

Pipeline E2E tests: clean and poisoned load → normalize → store → investigate → report → JSON export, with all citations resolving to the correct snapshot. Add live E2E: replay/append → ingestion → investigation → evidence view data → export → restart/resume. Use Streamlit AppTest for selection, raw/normalized display, investigation, comparison and live controls where supported. Call this a simulated UI integration test rather than a real-browser test. If browser tooling is available perform one manual user journey and report it accurately; otherwise provide a manual checklist and mark it unverified.

Add small security/integrity checks for SQL parameters, case isolation, injected prompt-like log text, escaped display, no secrets in exports and no ground-truth leakage. No extensive penetration, stress or browser-matrix suite now.

CI should run locked install, lint and offline tests on Linux and macOS when the repository supports CI. Add a Docker build/smoke job on Linux; other architecture/platform claims remain unverified until run. A successful Docker amd64 build is not evidence of arm64 compatibility. Run all feasible checks now, fix failures and report unavailable tools honestly.

## 11 Durable context and documentation

Create/update README.md, AGENTS.md, ARCHITECTURE.md, RESEARCH.md, ROADMAP.md, docs/TESTING.md, docs/DEMO.md and docs/PRODUCT_DESIGN.md. Copy the supplied planned-product design into docs/PRODUCT_DESIGN.md if available; otherwise write a design consistent with this prompt. Keep design intent separate from implemented status. Reference any existing Blue Cheese report rather than pretending to have read an unavailable one. Include a compact Mermaid architecture diagram.

AGENTS.md must contain purpose, interfaces, DuckDB ownership, live-reader invariants, no ground-truth leakage, immutable evidence, claim citations, tests/commands, current milestone and next work. Keep a short current-status record with completed behavior, limitations and next three priorities so later Codex sessions can continue without the owner repeating context. Record decisions on source identity, snapshots and deployment.

RESEARCH.md must distinguish log corruption, misleading enrichment and RAG document poisoning; specify paired settings, model/prompt hashes, seeded manifests, ground-truth separation, controls and evaluation. Measure classification, claim support/citation precision, evidence recall only where annotated, abstention, warnings, tool calls, tokens when available, elapsed time and cost when known. Do not claim superiority from one synthetic mock run.

## 12 Acceptance and scope

Complete the following: clean install; bundled labelled fixtures; raw/normalized inspection; DuckDB storage and tools; investigator/reporter; valid evidence and claim citations; benign/uncertain controls; immutable paired poisoning; GUI launch and comparison; JSON/Markdown export; working continuous reader and replay; checkpoint/resume and tested rotation; clean shutdown; one database owner; native run instructions for both platforms; Docker/Compose packaging and persistent volumes; offline unit/integration/regression/smoke/pipeline E2E tests; meaningful UI tests; lint; coverage report; durable project docs and presentation walkthrough.

Do not add Kubernetes, Elasticsearch/OpenSearch, React, authentication, distributed queues, custom vector infrastructure, model training, RL, sensor installation, live packet capture, Malcolm/Security Onion integration or five fully implemented agents. Live log ingestion, Docker and replay ARE in scope. RAG and the full role architecture belong in the finished-product design with explicit later milestones. Do not introduce distributed services to solve a local demo.

Implement in dependency order: inspect/reuse → models/fixtures → normalization/store/tools → investigator/report → offline GUI → live reader/checkpoints/runtime/replay → Docker → verification/docs. Write tests with behavior, run the suite and lint, launch the UI and fix failures. Preserve the working offline path as live support is added. If the environment prevents a check, complete the remaining work and identify precisely what could not be verified.

Final response: concise built/changed summary, architecture, actual test counts and scoped coverage, platform/container checks actually run, exact run commands, presentation steps, limitations, next three priorities and an acceptance checklist marked PASS/FAIL/NOT VERIFIED. This task authorizes implementing the code and documentation, not claiming a finished production system or measured research advantage.
