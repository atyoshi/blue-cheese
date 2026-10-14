# README verification — 2026-10-14

Historical record preceding the frontend replacement. Current interface checks
are documented in [TESTING.md](TESTING.md).

The README was followed on macOS using Python 3.13.15 and installed Suricata
8.0.7. All checks used isolated temporary state; existing operational evidence
and provider configuration were left intact. Placeholder paths were replaced
with real local paths. No models or datasets were downloaded.

| Documented path | Observed result |
| --- | --- |
| Fresh installation | Created a separate virtual environment; installed `requirements.lock` and the editable package using the documented flags. `pip check` passed and the installed CLI's doctor succeeded. |
| Launcher and doctor | Compatibility launcher accepted `--cli`; doctor accepted the bundled EVE and reported `ok: true`. |
| Operational GUI | Started the actual server on an explicit unused port; its HTTP health endpoint returned 200. |
| First walkthrough | Streamlit AppTest connected the bundled EVE, opened Alerts, started an investigation, reviewed the saved Findings view, and saved an attributed, assigned `ESCALATED` analyst action. Reopening the state confirmed the saved action. |
| Refresh and settings | Rerender retained exactly one investigation. Settings rendered the optional decision controls without an endpoint configured. No AppTest exceptions occurred. |
| Interactive terminal | Followed `/help`, `/import`, `/triage`, `/network`, `/investigate`, `/report`, `/history`, `/summary`, `/explain` and `/quit`, approving evidence tasks. A cited report persisted and the process exited successfully. |
| Offline capture preparation | Processed both the synthetic fixture and existing `bad.pcap` with explicit configuration/rules. Both manifests reported `PROCESSED`. The real capture produced 194 alerts, 342 flows, 503 DNS, 93 HTTP and 57 TLS records, plus unsupported event types. |
| Offline comparison | Three baseline repetitions completed. All three advised arms were correctly `NOT_CONFIGURED`. JSON/Markdown reports and the comparison index were written. This did not evaluate decision-model effectiveness. |
| Backup and restore | Backed up stopped terminal state, verified it, and restored it into a new directory. Both evidence records and schema migration 7 were preserved. |
| Retention | Preview and apply succeeded on restored state. No records were eligible because the investigation pinned them. |
| Synthetic presentation | Launched using the newly installed environment; HTTP health returned 200. Exported all four synthetic scenario reports and bundles; the poisoned bundle verified with six citations. Presentation interaction checks also passed in the test suite. |
| Legacy interface | EVE and synthetic PCAP imports succeeded. Alert listing, evidence, triage and report commands succeeded. The legacy web page returned HTTP 200. |
| Finite-backlog benchmark | Accepted 1,000 synthetic records with zero invalid records and zero provider calls. This is not a sustained capacity measurement. |
| Development checks | 189 tests passed in 20.59 seconds with 79% aggregate coverage; Ruff, `pip check` and `git diff --check` passed. |

GUI interaction used Streamlit's testing interface, accompanied by actual server
startup/HTTP checks. This is not a visual review across browsers or platforms.
Temporary logs, manifests and smoke-check scripts are under
`/private/tmp/bluecheese-readme-check-20261014`; temporary artifacts may be removed
by the operating system. This document records the durable verification summary.

## Optional paths and limits

`docker compose config --quiet` passed, but Docker Engine was not running.
Container build and execution remain unverified. Linux package installation,
privileged live capture/replay, command installation into the user's PATH and
updating the checkout with `git pull` were not performed during this check.

No live model requests were made during this README verification. Existing
real-capture model results and their semantic errors are recorded in
[session status](SESSION_STATUS.md); they do not establish compatibility with
other models. Native decision-model execution remains pending a compatible
configured endpoint. Neither synthetic tests nor this walkthrough establish
detection accuracy, analyst time savings or readiness for shared team hosting.
