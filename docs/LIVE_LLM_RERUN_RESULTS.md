# Recovered-evidence live rerun — 2026-10-15 UTC

The campaign started from clean main `14beb049d3322601fb520103ac10d12f8c598dba`
at **2026-10-15 01:58:22 UTC**, with an unchanged **04:58:22 UTC** deadline.
All six trials finished before that deadline. Four ordered pilots preceded a
user-requested stage 02 repeat and a same-seed retest after one narrow fix.

Durable artifacts are outside Git and `/tmp`:
`/Users/yoshi/bluecheese-evaluations/20261015-live-rerun-0158/`.
The directory contains `REPORT.md`, `scorecard.json`, `campaign.json`, per-trial
logs/exit codes, successful bundle, failed-run diagnostics and isolated states,
semantic/GUI review notes, test records, code patch and `artifact-checksums.json`.

The existing `~/bc.json` loader supplied Qwen Investigator and independent
Falsifier (`unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`), 300-second requests, 2,048 output
tokens and thinking off. Every trial used six attempts maximum, 12 retrieval
calls, host scope, 1,800 cooperative seconds and one repetition. Decision advice
was disabled; every advised arm was `NOT_CONFIGURED`. Credentials were not copied.
VPN connectivity was corrected before the first model call; the initial DNS
failure and successful non-model TCP check consumed campaign time.

| Trial | Outcome | Seconds | Model calls | Retrievals | Host records |
| --- | --- | ---: | ---: | ---: | ---: |
| 01 pilot | COMPLETED / MALICIOUS | 607.802 | 6 | 9 | 311 |
| 02 pilot | FAILED: Falsifier limitations length | 660.051 | 6 | 8 | 885 |
| 03 pilot | FAILED: Investigator report shape, then fact count | 496.914 | 3 | 6 | 5,405 |
| 04 pilot | FAILED: Falsifier provider parser HTTP 500 | 707.060 | 6 | 8 | 449 |
| 02 requested repeat | FAILED: Investigator fact count, then limitations type | 377.487 | 4 | 7 | 885 |
| 02 after guidance change | FAILED: Falsifier URL/source mismatch | 586.560 | 6 | 9 | 885 |

These **31 model calls** are retained, including all failures. The stage 03 model
Falsifier never ran because Investigator failed. The other trials invoked it;
only stage 01 completed its model review. Stage 02 and 04 Investigator schema
corrections passed before their later failures. No final failed report was
accepted, and no bundle is claimed for a failed trial.

All trials use the exact recovered EVE and selected seeds. EVE SHA, seed,
snapshot digest and actual sorted snapshot membership match the archived
rules-host counterparts. Preflight verified 189 archived immutable checksum
entries; the mutable preview log was excluded. The recovered snapshot identities
remain separate from the lost original campaign.

## Citations and semantic review

Stage 01's bundle verifies **67 referenced records**. Manual source review
supports its flow direction, ports, established state and byte counters; POST,
URL, NetSupport user agent and logged HTTP length; the associated remote-access
alert; and UTC conversion. The report leaves execution, compromise and theft
unconfirmed. Its malicious classification and unauthorized/C2 explanation remain
model assessments without authorization or endpoint corroboration.

Two semantic qualifications remain. “Zero response bytes” should specify the
logged HTTP response length; the cited flow has 17,020 client-bound bytes.
The proposed disconfirmation combines authorization with TLS evidence, although
separate TLS evidence cannot overturn observed plaintext HTTP. Flow byte counters
also cover the recorded flow lifetime, not only packets inside the case window.
Consequently mechanical completion does **not** establish full semantic acceptance.

The post-fix stage 02 Falsifier bound a `url` fact to retrieved record
`17d710a08f594bbb124198a1`, a DNS request for `master16.teamviewer.com` with no URL
field. Strict validation rejected it. The exact rejected value/prose is not
persisted, so it cannot be reconstructed for further semantic review.

## Narrow correction-guidance change

Schema correction previously reported a rule path without its expected type or
bound. `agent_provider.py` now derives those constraints from the trusted schema
and includes them in the existing bounded correction message. Rejected values
are excluded; schema, citation, source-fact and global budget checks remain strict.

The same-seed retest had no schema correction and then failed source-fact
validation. It therefore **does not validate a live benefit from the new guidance**.
Comparison metadata records the before/after tracked-diff hashes; the checkout
patch is preserved durably. Code is left uncommitted on main for review.

**47 focused tests passed in 6.04 seconds**, including correction completion and
continued rejection after a second invalid report. Ruff and whitespace checks
passed. An earlier 13-test run is also retained. No new full Python suite or
browser suite result is claimed.

## Normal GUI review

Native Firefox review used the completed stage 01 and post-fix failed stage 02
states after their CLIs stopped. The accepted case showed cited findings, limits,
311-record host scope, actual model operations and completed Falsifier review.
Markdown export downloaded successfully. The failed case showed its saved error,
885-record scope and six actual model operations. Browser reload and in-app
refresh preserved history and started no new investigation. Analyst disposition
remained `Open`, with no decision history; no analyst decision was entered.
No GUI chat/model requests were made. Both GUI servers were stopped.

## Remaining work

See [next steps and possible fixes](LIVE_LLM_NEXT_STEPS.md). Provider schema
compliance, parser compatibility, evidence binding and semantic quality remain
open. Five-minute scope, absent identity/endpoint telemetry, and the documented
stage 04 reference/capture discrepancy still apply. Detection accuracy,
calibration, human completion time, time saved and commercial readiness are
unmeasured. Historical failures remain unchanged in
[REAL_TRAFFIC_RESULTS.md](REAL_TRAFFIC_RESULTS.md).
