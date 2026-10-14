# Progressive real-traffic evaluation for Blue Cheese

## Summary

Test four Malware Traffic Analysis captures using offline rules and the configured Investigator/Falsifier LLM. Evaluate evidence quality, execution reliability, and the normal alert-to-decision workflow. Fix demonstrated defects and retain separate before/after results.

Allow up to three hours of live testing, including capability checks, investigations, retests, and model chat. Preparation, source review, and offline regression checks are outside that allowance.

## Scenarios and progression

Difficulty reflects the investigation task and available telemetry; confirm it after inspecting each capture.

| Stage | Capture | Main challenge |
|---|---|---|
| 1 — Compact baseline | Easy as 123, February 2026 (https://www.malware-traffic-analysis.net/2026/02/28/index.html) — 5.2 MB archive | Investigate NetSupport RAT alerts; identify the affected host and distinguish signature evidence from confirmed impact. |
| 2 — Multiple destinations | Download from Fake Software Site, January 2025 (https://www.malware-traffic-analysis.net/2025/01/22/index.html) — 20.5 MB | Connect delivery and subsequent communications across destinations; compare connection and host scope. |
| 3 — Multiple stages | SmartApeSG → NetSupport RAT → StealCv2, August 2025 (https://www.malware-traffic-analysis.net/2025/08/20/index.html) — 63.1 MB | Recover a multi-stage behavioral sequence amid unrelated traffic and bounded retrieval. |
| 4 — Held-out check | Natureforce, October 2026 (https://www.malware-traffic-analysis.net/2026/10/01/index.html) — 33.1 MB | Test whether improvements transfer to executable-delivery and CNCmachineRMS RAT traffic without scenario-specific tuning. |

Complete one live pilot per stage before spending remaining time on repetitions. Hold Natureforce out of fix development: freeze the application revision before its first run and report any later fixes separately.

## Preparation and execution

- Preserve the existing working-tree changes. Record the starting commit and diff hash, then use fresh campaign directories and isolated state for every capture.
- Download the four PCAP archives and evaluator reference material. Inspect archive contents and extract captures only. Process packets offline with installed Suricata 8.0.7, the existing configuration, and existing rules; keep payload/file extraction disabled.
- Record source URLs, archive and PCAP hashes, sensor/configuration/rule hashes, EVE hashes, timestamps, event counts, and processing diagnostics. Keep captures, transcripts, and state outside tracked source files.
- Build evaluator-only reference observations from published answers/IOCs, original EVE, and packet inspection where needed. Distinguish published attribution from facts independently verified in the capture. Reference answers, scenario titles, and expected verdicts never enter model inputs.
- Reconcile accepted, unsupported, and quarantined records. Check exact raw preservation, stable reimport behavior, and completed backlog ingestion before freezing investigations.
- Choose a source-host alert using observed telemetry and normal queue ordering. Save its ID and selection rationale before comparing engines. Require an internal source IP for host scope; report missing suitable alerts as a coverage limitation.
- Run connection and host scopes with offline rules. Use the host scope for each live pilot, with the same seed and frozen membership as its offline counterpart. Explicitly assess the ±5-minute boundary; longer sequences require separate cases.
- Load ~/bc.json without exposing credentials or editing it. Retain its current six model attempts, 300-second request timeout, 2,048-token output limit, and disabled thinking. Enable independent Falsifier review; leave optional decision advice disabled. Use 12 retrieval calls and a cooperative 1,800-second live-run budget.
- Start with one capability check. If provider connectivity remains unavailable after one diagnosed retry, stop live requests and complete offline evaluation, marking live outcomes blocked.
- After the four pilots, prioritize a retest of the most consequential fix, then a repetition of the hardest completed case. Start a run only when its full configured allowance fits within the remaining campaign time. Cancellation remains cooperative.

## Implementation and review

- Extend compare_investigations with investigation_scope="connection" and CLI --scope connection|host. Preserve the default; require an explicit seed for host mode. Record scope, seed, snapshot digest, application revision, and effective settings in results.
- Use the existing runtime and bundle APIs for matched rules/LLM runs. Export and verify completed reports; retain failed-run activity, diagnostics, timing, and retrieval history.
- Review each material claim against its cited records: endpoints, direction, UTC times, DNS names, HTTP methods/paths/statuses, and byte semantics. Assess behavioral conclusions separately from observable facts and endpoint impact.
- Classify missed evidence by where it disappeared: capture, sensor output, normalization, snapshot scope, retrieval, or assessment. Treat unsupported hostname/user/file-hash questions as capability gaps when those fields are unavailable.
- Exercise the normal React GUI for each case: alert selection, explicit host investigation, actual activity, evidence links, case summary, analyst disposition, export, and restart persistence. Verify that navigation and refresh start no work.
- Fix reproducible defects with focused changes and synthetic regressions. Preserve original failures and create new retest runs. Keep evaluator-specific indicators and expected classifications out of application logic.

## Acceptance and deliverables

- Integrity: accepted raw evidence remains unchanged; citations resolve to actual retrieval within the frozen snapshot; exported bundles verify; operational state is untouched.
- Quality: record supported and unsupported material claims, relevant evidence missed, retained contradictions, and useful next checks. Report execution success separately from semantic acceptance. Any unsupported material claim prevents semantic acceptance of that report.
- Workflow: findings, failures, scope limits, and saved decisions remain inspectable through the normal interface. Automated timings are not human time savings.
- Run targeted regressions after each fix, then the full Python suite. Run frontend checks and browser tests when frontend behavior changes. Automated tests remain offline with mocked models.
- Deliver a concise campaign report, per-case scorecard, provenance manifests, verified bundles, preserved failure diagnostics, and before/after fix results. Record actual run counts, latency, attempts, and budget limits.
- This is a four-case evaluation. Detection accuracy, commercial readiness, and analyst time savings remain unestablished.
