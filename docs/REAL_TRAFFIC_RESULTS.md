# Progressive real-traffic evaluation — 2026-10-14

Four authentic Malware Traffic Analysis PCAPs were processed offline with
Suricata 8.0.7 and the existing 52,768-rule configuration. All four passed raw
evidence preservation, unchanged-file reimport, and ingestion reconciliation.
The campaign established useful storage and workflow results, but **did not
establish an accepted end-to-end live model investigation**.

## Live results and interruption

The existing Qwen Investigator/Falsifier profile retained six attempts,
300-second request timeouts, 2,048 output tokens, thinking disabled, and independent
review. A two-request synthetic capability check passed in 50.4 seconds.
Investigations used 12 evidence queries and a cooperative 1,800-second allowance.
Decision advice stayed disabled. Source pages, reference answers and scenario
titles were excluded from provider inputs.

| Stage | Capture | Observed live outcome | Seconds / attempts |
| --- | --- | --- | --- |
| 1 | [Easy as 123](https://www.malware-traffic-analysis.net/2026/02/28/index.html) | Rejected: a fact's observation was absent from its own claim citations | 306.848 / 3 |
| 2 | [Fake software download](https://www.malware-traffic-analysis.net/2025/01/22/index.html) | Investigator passed after schema correction; Falsifier invented a citation, so the run failed | 686.437 / 6 |
| 3 | [SmartApeSG / NetSupport / StealCv2](https://www.malware-traffic-analysis.net/2025/08/20/index.html) | Provider's generated-output parser failed with HTTP 500 | 224.939 / 3 |
| 4 | [Natureforce](https://www.malware-traffic-analysis.net/2026/10/01/index.html) | Started; final outcome unrecovered after environment interruption | Unknown |

The original campaign directory under `/private/tmp` and its processes were no
longer present when execution resumed. Historical timings/errors above survive
in conversation tool outputs and a clearly labelled reconstruction; original live
diagnostics, request transcripts and frozen databases are unavailable. Do not
count the fourth run as completed, failed, or semantically accepted.

The three-hour wall-clock live allowance expired during the interruption. No
further live requests were made. The same-seed prompt retest and live repetitions
remain uncompleted. This is an interrupted evaluation, not a successful four-case
autonomous detection benchmark.

## Recovered offline results

Recovery uses durable local storage at:

`~/bluecheese-evaluations/20261014-cnm99sk6/`

All four recovered ZIP and PCAP hashes match those recorded before interruption.
Regenerated EVE has different source identities, and priority ties can select
different alerts. These recovered runs are separate experiments, not replacements
for the lost live snapshots or matched rules/LLM comparisons.

| Stage | Accepted | Unsupported | Recovered host records | Rules assessment |
| --- | ---: | ---: | ---: | --- |
| 1 | 2,625 | 1,228 | 311 | SUSPICIOUS |
| 2 | 3,216 | 1,039 | 885 | UNCERTAIN |
| 3 | 5,597 | 5,563 | 5,405 | UNCERTAIN |
| 4 | 755 | 423 | 449 | UNCERTAIN |

Totals: **12,193 accepted and 8,253 unsupported records**. Unsupported records,
including SMB/Kerberos/DHCP, file metadata and sensor anomalies, were quarantined;
they are not evidence of malformed accepted inputs. Eight connection/host reports
completed, their ten source-observation claims matched cited fields, and all eight
bundles verified. Source support does not validate the uncalibrated policy's
activity classification.

Important investigation limits:

- The original first-stage seed's ±5-minute host window contained no HTTP
  transaction records although the full capture contained 264 NetSupport HTTP
  transactions. The recovered later seed included the final flow record and
  produced SUSPICIOUS. Scope and seed selection materially affect the result.
- The original third-stage window included early NetSupport traffic but excluded
  later StealC activity. A separate later case exposed the large-snapshot crash.
  The recovered queue selected that later activity naturally. A five-minute case
  cannot establish the whole infection sequence from this 77-minute capture.
- The deterministic policy mainly reviews alerts and matching flows; it does not
  turn a host protocol table into a comprehensive malware-chain assessment.
- MAC/user identity exists in unsupported source telemetry. Its absence from
  normalized provider input is a capability gap, not model failure to retrieve
  an available normalized field.
- Natureforce's published brief names `195.64.128.106` as C2. The hash-matched PCAP
  has zero packets matching that address under offline tcpdump inspection, and
  EVE has no corresponding traffic. Treat this as a reference/capture discrepancy,
  not a missed detection. The executable GET, status 200 and 1,046,284 response
  bytes are present; execution and successful compromise remain unconfirmed.

## Fixes and verification

A 5,405-record supplemental host case crashed twice in native DuckDB 1.5.0:
SIGSEGV after snapshot commit and SIGABRT during another snapshot commit. Reopening
the first state retained evidence and marked its unfinished run INTERRUPTED.
The same original input completed twice with DuckDB 1.5.6 and matching snapshot
digests. The recovered 5,405-record case and an explicit GUI revision also complete.
The exact upstream defect is not established; the [patch release notes](https://duckdb.org/2026/09/28/announcing-duckdb-156)
do not independently prove which fix addresses this workload.

Changes pin DuckDB 1.5.6 in both package metadata and the shared lock file, record
the actual DuckDB version in comparison settings, and explicitly require each
fact's evidence ID in the same claim's citations. A provider-pipeline regression
retains immediate rejection when that ID is cited elsewhere; no citation repair
or validation bypass was introduced. Live benefit from the prompt clarification
remains unverified.

The normal interface served four recovered cases. API checks verified scoped
evidence links, operation history, offline summaries, test-only decisions and
JSON/Markdown exports; reading started zero investigations. Native Firefox review
confirmed all four case views and one explicit 5,405-record host revision, with
preserved scope, decision and real operations. Subsequent navigation/refresh
started no extra work. Restart and stopped-state backup verification preserve
case history, decisions and chat. Including GUI reports and the revision, **13
bundles verify**. GUI runs use the normal eight-query limit, separately from the
12-query comparison runs. No operational workspace was modified.

Final checks: **230 Python tests and 18 Chromium tests passed**; Ruff, dependency
consistency and whitespace checks passed. One existing Starlette deprecation
warning remains. The new 5,500-record subprocess regression covers snapshot commit,
retrieval, bundle verification, restart, immutable raw text and idempotent reimport.
A recovery check first hit its 60-second watchdog during concurrent offline work;
that failure is retained, and the final passing run uses a 180-second watchdog.
This test does not assert ingestion throughput.

The durable directory contains `REPORT.md`, `historical-observations.json`,
`recovered-campaign.json`, `source-review.json`, `bundle-verification.json`,
`ui-api-verification.json`, `ui-native-observations.json`, restart/backup checks,
test logs, source references, sensor manifests and isolated state. Captures,
credentials and operational transcripts are not added to Git. Human completion
time, time saved, detection accuracy, calibration and commercial readiness remain
unmeasured.
