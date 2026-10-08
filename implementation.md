# Blue Cheese: staged implementation plan

  ## Summary

  Build a single-machine Python application that turns PCAPs and completed sensor logs into traceable incident reports
  through five replaceable investigation roles.

  The repository currently implements Suricata alert parsing, two domain dataclasses, a mock triage agent, and a CLI. Both
  existing tests pass; the remaining components are empty placeholders.

  The first end-to-end milestone is:

  PCAP → Suricata and Zeek → stored evidence → deterministic triage and correlation → inspectable report, with restart
  recovery and resource measurements. Model-driven investigation and the analyst UI follow on that foundation.

  ## Architecture and interfaces

  - Keep the existing package boundaries: domain objects, application services, ports, adapters, and agents. Add workflow,
    interface, and evaluation packages as their milestones arrive.

  - Keep domain objects as typed Python dataclasses and enums. Validate external input at adapter boundaries. Database,
    web, and LangGraph types stay outside the domain.

  - Define small protocols for sensor execution, normalization, evidence queries, case/job persistence, model completion,
    role execution, and report rendering.

  - Register implementations explicitly at startup with interface versions and capability declarations. Configuration
    selects implementations; incompatible combinations fail clearly.

  - Use DuckDB for normalized evidence, SQLite for cases/jobs/audit records, and managed local files for original
    artifacts.

  - One backend process owns database access. Initially, CLI commands acquire an exclusive workspace lock; after server
    mode exists, clients use its API. This follows DuckDB’s embedded concurrency model. DuckDB documentation
    (https://duckdb.org/docs/current/connect/concurrency)

  - Use SQLite WAL with short transactions and versioned schema migrations. Keep databases on local storage. SQLite
    documentation (https://www.sqlite.org/wal.html)

  - Preserve the existing bluecheese <eve.json> [--triage] invocation as a compatibility path. Introduce explicit import,
    triage, investigate, case, report, resume, serve, and evaluation subcommands.

  - Use TOML configuration for sensor paths, rules, storage, strategies, model endpoint, and budgets. Read model
    credentials from environment variables.

  Core types will include:

   Type                                   Purpose
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Artifact, ImportRun                    Original file identity, processing configuration, source availability, and
                                          import status
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────
   Event, NormalizedAlert, EvidenceRef    Observations, detections, and references to exact source records
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────
   AlertGroup, TriageResult               Group membership, priority, rationale, and routing decision
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────
   EvidenceBundle, ToolResult             Scoped observations, relationships, query status, and truncation
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────
   Finding, Case, AgentRun                Claims, supporting/contradicting evidence, revisions, execution history, and
                                          limitations

  Extend NormalizedAlert with optional provenance and detection metadata while preserving its existing fields and parser
  entry points.

  ## Implementation stages

  ### 1. Deterministic triage

  - Implement RuleBasedTriageAgent; retain MockTriageAgent for compatibility and tests.
  - Default priorities: severity 1 → high; 2 → medium; 3 → low; missing or unsupported severity → medium with an explicit
    data-quality explanation.

  - Group alerts within an import by detection identity, directional source/destination IP pair, protocol, and destination
    port. Use signature text when rule ID is unavailable.

  - Sort by timestamp and form five-minute groups anchored to each group’s first alert. Exclude source port so repeated
    connections can group together. Alerts missing necessary grouping fields remain individual.

  - Set group priority to its highest member priority. Automatically queue high and medium groups; retain low groups for
    manual investigation.

  - Keep original severity separate from operational priority. No rule match alone establishes maliciousness.
  - Make severity mapping, grouping window, and automatic-investigation threshold configurable; record the policy version
    in every result.

  Acceptance: repeated runs produce identical grouping and decisions, with an explicit rationale for every alert.

  ### 2. Evidence ingestion and persistence

  - Add immutable managed copies of PCAPs and source logs, SHA-256 hashes, and manifests. Evidence references identify the
    artifact and original record location.

  - Normalize timestamps to UTC while preserving original values. Preserve complete source logs and protocol-specific
    fields.

  - Import Suricata alert, flow, DNS, HTTP, and TLS records; initially support Zeek JSON conn, dns, http, and ssl logs.
    Unsupported logs remain preserved artifacts.

  - Stream records into bounded database batches. Quarantine malformed records with source location and error details; mark
    imports containing rejected records as partial.

  - Identify processing runs by input artifacts plus relevant sensor, ruleset, configuration, and parser versions. Use
    stable event IDs and idempotent writes.

  - Implement native Linux sensor runners using argument arrays, dedicated output directories, timeouts, captured
    diagnostics, and explicit exit-status checks. Run sensors sequentially by default.

  - Enable compatible Community ID settings in both sensors, using seed 0. Correlation must also enforce capture scope and
    time compatibility. Suricata documentation (https://docs.suricata.io/en/latest/output/eve/eve-json-output.html), Zeek
    documentation (https://docs.zeek.org/en/current/scripts/policy/protocols/conn/community-id-logging.zeek.html)

  - Persist each import phase. Since DuckDB and SQLite do not share a transaction, reconcile committed evidence batches
    before marking an import complete or queueing investigations.

  - Distinguish sources that were disabled, failed, or completed with no records. Partial imports require an explicit
    option before automatic investigation.

  - Add configurable free-space checks; stop new work cleanly without deleting evidence.

  Acceptance: every stored event resolves to its original record; duplicate submissions and interrupted imports produce no
  duplicate evidence.

  ### 3. Deterministic case investigation and reporting

  - Implement scoped tools for alert lookup, related events, host timelines, DNS activity, flow summaries, rule details,
    packet excerpts, and optional asset context.

  - Use parameterized queries. Enforce capture/case scope, time bounds, row limits, output limits, and timeouts in code.
  - Return distinct outcomes for matches, no matches, unavailable sources, failures, and truncated results.
  - Correlate using capture-scoped Community ID and Zeek UID relationships. Where identifiers are absent, use compatible
    endpoints and overlapping time windows, recording these as inferred relationships.

  - Default evidence retrieval to five minutes before and after the alert group. Cap each result at 200 records and 64 KiB,
    with explicit truncation.

  - Create one case per selected group and workflow configuration. Keep hypotheses, observations, detections,
    interpretations, and analyst decisions distinct.

  - Produce versioned JSON and Markdown reports containing triggering alerts, timeline, evidence references, findings,
    alternative explanations, missing evidence, and suggested analyst checks.

  - With inference disabled, describe supported observations and unresolved questions without inferring compromise from
    signatures alone.

  Acceptance: a fixture case produces a report whose citations can all be resolved, including an ambiguous TeamViewer
  example that remains appropriately uncertain.

  ### 4. Five-role workflow and model investigation

  - Implement the Orchestrator as a deterministic controller and Correlation as deterministic evidence gathering. Keep all
    five roles independently replaceable through their protocols.

  - Add LangGraph behind the workflow port with persistent SQLite checkpoints. Case and audit records remain
    application-owned; graph checkpoints track execution state. LangGraph persistence
    (https://docs.langchain.com/oss/python/langgraph/persistence)

  - Add a configurable OpenAI-compatible endpoint adapter supporting structured tool calls. Verify required capabilities
    before enabling model runs; retain an explicit model-disabled mode.

  - Implement the Investigator’s bounded loop: propose hypotheses, request permitted evidence, examine contradictions, and
    return structured findings.

  - Default to one active model request, eight tool calls, one transient retry, five minutes, and a 16,000-token aggregate
    allowance per investigation. Retries consume the same budgets; endpoint-specific token accounting must reserve capacity
    before requests.

  - Validate structured outputs and evidence references. Reject nonexistent or out-of-scope citations; record invalid
    outputs and preserve partial results.

  - Treat network strings as untrusted evidence. The model receives no arbitrary SQL or shell capability.
  - On model outage, leave investigation jobs waiting for retry while ingestion remains available. Budget exhaustion
    produces an incomplete run with an inconclusive report.

  - Allow optional LLM triage assessment and report wording through separate strategies. Preserve deterministic decisions
    and validated findings in the audit trail.

  - Make role writes idempotent so checkpoint replay cannot duplicate cases, findings, or reports.

  Acceptance: fake-endpoint tests and a real-endpoint smoke test demonstrate tool use, enforced limits, unavailable-model
  behavior, and restart recovery.

  ### 5. Local analyst interface and operation

  - Add a FastAPI backend with server-rendered pages and lightweight polling; use the same application services as the CLI.
  - Provide alerts, case timeline, evidence, and report views, plus job/run status showing failures, missing sources, and
    exhausted budgets.

  - Support import submission, manual investigation, retry/resume, analyst disposition, notes, and report export.
  - Expose corresponding versioned API resources for imports, alerts, cases, evidence, jobs, and reports.
  - Bind to localhost for one analyst; document SSH tunneling. Escape sensor and model content before rendering.
  - Provide Linux setup instructions, sensor configuration, a service definition, backup/restore procedures, and database
    migration checks.

  Acceptance: an analyst can import a capture, inspect a report’s original evidence, record a decision, restart the
  backend, and continue the case.

  ### 6. Evaluation and release baseline

  - Add reproducible benign, malicious, ambiguous, incomplete-capture, and failed-sensor scenarios. Keep ground truth
    outside tool-accessible evidence.

  - Include a small synthetic PCAP and deterministic test rules so the integration suite does not depend on changing
    external rulesets.

  - Compare deterministic processing, one Investigator with fixed preprocessing, and the configurable five-role workflow.
  - Measure backend and sensor RAM/CPU, disk growth, import throughput, query latency, model calls/tokens, tool calls, and
    case completion time. Report model-server resource usage only when telemetry is available.

  - Evaluate correct findings, missed findings, unsupported claims, recovery, and analyst corrections. Citation existence
    and claim support receive separate checks.

  - Export versioned JSON benchmark results and provide a subprocess entry point suitable for ModelScope. The external
    ModelScope adapter remains a follow-up because its repository and contract are not present here.

  - Establish measured baselines before choosing hardware ceilings or claiming improvements over Security Onion.

  ## Validation and explicit defaults

  - Run unit and contract tests on macOS and Linux; run real sensor integration tests on Linux.
  - Cover missing fields, malformed JSON, timestamp offsets, IPv6, grouping boundaries, repeated imports, missing Community
    IDs, and cross-capture isolation.

  - Inject failures between database commits, during sensor execution, and between workflow checkpoints. Verify recovery
    without duplicate evidence or cases.

  - Test empty versus unavailable data, truncation, invalid citations, hostile network strings, model timeouts, and
    exhausted budgets.

  - Preserve existing parser tests and CLI compatibility; add meaningful end-to-end tests as each stage becomes usable.
  - Require a complete PCAP-to-report run with inference disabled, a bounded model-enabled run, and an interrupted-run
    recovery demonstration before MVP release.

  Defaults: offline imports, Linux runtime, macOS development support, one backend, one analyst, one configurable model
  endpoint, and measured resource baselines. Live capture, distributed deployment, automated containment, multiuser
  authentication, model hosting, and endpoint collection are deferred.
