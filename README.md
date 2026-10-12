# Blue Cheese

Blue Cheese is a local analyst workspace for Suricata network evidence. Connect
an EVE file or local Unix stream, explore traffic, inspect original logs, run a
bounded investigation, and save a cited report and your analyst decision.
Suricata performs capture and detection; Blue Cheese consumes its output.

The operational console runs locally without a model key. It uses a rule-based
investigator by default. This is a single-analyst development release: individual
authentication, roles and shared SOC deployment remain unfinished. Native macOS
and local Suricata integration have been tested; Docker execution and live model
compatibility remain unverified. See [current verification](docs/TESTING.md) and
[release gates](docs/RELEASE_GATES.md).

Quick links: [install](#install-and-open-the-console) ·
[connect telemetry](#connect-telemetry) ·
[investigate](#investigate-and-record-a-decision) ·
[backup and maintenance](#check-back-up-and-maintain-state) ·
[troubleshooting](#troubleshooting) ·
[synthetic presentation](#synthetic-presentation-and-offline-bundles).

## Install and open the console

Run these commands **from the repository root**, where this README and the
`bluecheese` launcher live. Use Python **3.11 or newer**; check with
`python3 --version`. If necessary, substitute an installed newer interpreter,
such as `python3.13`, in the first command. Installing dependencies needs
package-registry access.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
./bluecheese
```

For later launches, just run `./bluecheese`. The launcher uses this checkout's
`.venv` automatically; environment activation is unnecessary. Open the **local
URL printed in the terminal**, normally http://127.0.0.1:8501. If the default port
is busy, Streamlit tries the next available port. Leave the terminal running and
stop the app with **Ctrl+C**. Closing the browser tab does not stop the app.

The console initially has no telemetry. It does not load demonstration scenarios
or start Suricata automatically. Install/configure Suricata separately if you
want live sensor output; an existing EVE file needs no running sensor.

| Task | Command |
| --- | --- |
| Open the operational GUI | `./bluecheese` |
| Choose an explicit port | `./bluecheese gui --port 8502` |
| Choose a state directory | `./bluecheese --data-dir my-soc gui` |
| Check configuration with the GUI stopped | `./bluecheese doctor` |
| Check an EVE path with the GUI stopped | `./bluecheese doctor --eve /absolute/path/eve.json` |
| Show commands/options | `./bluecheese --help` or `./bluecheese gui --help` |

Put the global `--data-dir` option **before** the subcommand. Relative state paths
are relative to the terminal's working directory. The GUI, doctor and retention
commands default to `./bluecheese-operations`; legacy CLI commands default to
`./bluecheese-data`. Use the same explicit absolute state path across launches
and maintenance commands if you work from different directories. Only one process
may use a state directory at a time, including exports and maintenance.

Optional: run `./install-command.sh` to link this checkout's launcher into
`~/.local/bin`. If prompted, add that directory to your shell's PATH, for example
`export PATH="$HOME/.local/bin:$PATH"`, and persist it in your shell configuration.
You can then use `bluecheese` from other directories; state paths still follow the
working directory. The link depends on this checkout remaining in place.

## First walkthrough: connect, inspect, investigate

With an existing Suricata EVE file:

1. In the sidebar, expand **Sensor connection**, select **EVE file**, and enter
   the file's absolute path on the machine running Blue Cheese.
2. Click **Connect sensor**. Watch **Accepted records**, **Alerts** and
   **Quarantined records**. Existing lines load in bounded batches; new lines
   continue arriving if Suricata is writing the file.
3. Open **Overview** to inspect activity, then **Alerts**. Filter if needed and
   choose a record under **Inspect evidence**. Expand **Original evidence and
   normalized fields** to read the exact log, parsed JSON and canonical fields.
4. Click **Investigate selected alert**, then open **Investigations**. Select the
   completed run under **Saved investigation** and review its result and citations.
5. Use **Export JSON** or **Export Markdown** to download the report. Enter your
   name, disposition and note under **Analyst disposition**, then click
   **Save analyst action**.

To learn without a sensor, use a **separate synthetic practice state**:

```bash
./bluecheese --data-dir practice-state doctor --eve "$PWD/tests/fixtures/sample_eve.json"
./bluecheese --data-dir practice-state gui
```

Connect the absolute path printed by doctor as the EVE file. This small bundled
fixture is synthetic; its old timestamps are expected. It lets you exercise the
same controls without generating network traffic. For clean/poisoned comparisons
and paced synthetic replay, use the [separate presentation](#synthetic-presentation-and-offline-bundles).

## Connect telemetry

Only EVE `alert` and `flow` records are currently accepted as evidence. Other
record types, including DNS, and malformed records are quarantined. One input
source can be connected per runtime. Disconnect before changing inputs. Stored
evidence remains available while disconnected, and reconnecting after an app
restart is explicit.

### EVE file: growing log or completed capture

Select **EVE file**, enter **Suricata EVE file**, and click **Connect sensor**.
The file must already exist and be readable by the Blue Cheese process. The
field starts empty unless `BLUECHEESE_EVE` is configured before launch:

```bash
export BLUECHEESE_EVE=/absolute/path/to/eve.json
./bluecheese
```

Paths refer to the server running the app, not necessarily the browser's machine.
Missing files, directories and named pipes are rejected before ingestion starts.
A completed EVE capture works too; it remains connected waiting for more lines
after reaching the end. An unfinished last line waits for its terminating newline.

Keep **Recover rename rotation** enabled for bounded rename-and-create recovery.
The follower drains the old descriptor for five seconds before switching to a
persisted new generation. Matching archives named after the input, such as
`eve.json.*`, can be recovered on restart through a bounded directory search.
Truncation, missing archives, partial rotated records and multiple rotations
during draining stop ingestion visibly. Late writes to retired generations,
arbitrary edits to earlier bytes and undetectable copytruncate/regrowth are
outside automatic recovery. Inspect **Sensor health** when ingestion stops.

### Unix stream: local EVE without a sensor-side input log

1. Select **Unix stream** and keep the suggested **Unix socket path**, or choose
   an unused short path in an existing directory.
2. Click **Connect sensor**. **Listening** means Blue Cheese is ready; no producer
   is connected yet.
3. Expand **Suricata stream configuration** and merge the generated YAML into
   your sensor's existing EVE output configuration. Preserve its capture settings
   and rules. The generated `filename` matches your selected socket path.
4. Start/restart Suricata. **Streaming** means a producer has connected. Accepted
   alert/flow records populate the workspace.

Blue Cheese listens and Suricata connects. This is EVE JSON transport using
`filetype: unix_stream`, not Suricata's command/control socket or `unix_dgram`.
Use the same filesystem namespace on Linux/macOS; run Suricata as the socket's
OS owner or root. The socket is owner-only. Native launch is the simplest path:
the standard read-only Docker telemetry mount does not expose a container socket
to a host sensor.

Received bytes are persisted in a receipt spool before parsing. The limit is
**256 MiB per socket path**. Reaching it stops visibly without deleting evidence;
archive the stopped state and choose a new state to continue. A producer disconnect
stops ingestion and records a continuity incident; reconnect explicitly. Unfinished
prior records are retained and never merged with a new producer after restart;
choose a new socket path/state when warned. Existing socket paths, including stale
ones left by abrupt termination, are never replaced automatically.

Socket transport does not guarantee end-to-end delivery. Suricata can drop events
when the receiver is unavailable or congested; monitor the sensor's drop statistics.
Use file tail for persistent sensor-side buffering and easier restart recovery.

### Produce EVE with Suricata

Configure Suricata with detection rules and EVE `alert` and `flow` outputs. For
example, on a Linux sensor, adjust the configuration path and capture interface:

```bash
mkdir -p telemetry
sudo suricata -c /etc/suricata/suricata.yaml -i eth1 -l "$PWD/telemetry"
```

Connect the resulting `eve.json` in Blue Cheese. The application user needs read
access to that file and its parent directories. For an isolated replay exercise,
run `sudo tcpreplay --intf1=eth1 capture.pcap` on a replay host whose traffic the
sensor can see. Blue Cheese does not generate scans, replay packets or manage the
sensor process. Its presentation replay only appends synthetic log records.

## Explore the workspace

Use the sidebar's **Workspace** selector to move between these pages:

| Page | How to use it |
| --- | --- |
| **Overview** | Spot activity patterns, focus on endpoints/connections, and drill down to evidence. |
| **Alerts** | Filter by exact endpoint IP, signature substring and sensor severity; select an alert to inspect or investigate. |
| **Flows** | Filter by exact endpoint IP and inspect flow state, endpoints and byte counters. |
| **Investigations** | Start runs, review saved results, export reports, manage queued work and record analyst decisions. |
| **Sensor health** | Inspect source status, committed byte offset, spool path, rotation notices, quarantine reasons and continuity incidents. |

On **Overview**, use **Activity**, **Connections** and **Evidence** to move from
patterns to individual records. Endpoint and connection focus apply across all
three tabs; **Reset focus** clears both. The timeline uses event time in UTC:
hover for values, Shift + scroll to zoom, drag to pan, and double-click to reset.
Normal scrolling leaves its scale unchanged. Orange map edges contain alerts;
blue edges contain only flows in the displayed view.

Visuals default to the most recently received **1,000** accepted records, with
250/5,000 options. Endpoint focus applies within that window. The map shows up to
12 IP pairs and evidence detail up to 50 matching records. Use **Alerts** and
**Flows** for full pagination at 50 records per page, newest received first.
Visual limits and table filters do not define investigation membership.

Counts are log records, not unique sessions or packets. Sensor severity describes
rule priority; an alert alone does not establish compromise. A zero in a chart
cannot establish uninterrupted coverage, and an old capture retains its original
event times.

**Learning mode** adds explanations of IPs, ports, TCP/UDP, flows, alerts and
record fields. Switch it off for a compact view. **Auto refresh** refreshes the
operational workspace every two seconds. Turn it off while reading or editing;
ingestion continues. Changing a filter or pressing **Refresh now** reloads the
view. **Sensor connection** collapses once evidence is available; expand it to
connect or disconnect.

## Investigate and record a decision

### Choose scope and budget

**Investigate selected alert** on Alerts, or **Investigate this alert** in
Overview, freezes a same-source endpoint neighborhood within five minutes of
that alert. On **Investigations**,
set **Case question**, choose a **Scope alert**, and click **Start investigation**.
The scope selector lists the latest 50 alerts; select older alerts from **Alerts**.
You can also choose **Whole external scope**. Each snapshot has a **10,000-record
limit**; if the whole scope exceeds it, choose an alert neighborhood.

The case question labels the case. The rule-based investigator evaluates alert/flow
evidence rather than answering arbitrary natural-language questions. Triage assigns
review priority, correlation proposes links with provenance and ambiguity, and one
bounded seed group is investigated per run.

Expand **Investigation budget** to set **Tool calls**, **Seconds (cooperative
limit)** and **Check contradicting evidence**. The operational defaults are eight
tool calls and five seconds with rules, or 30 seconds with a configured model.
The selected-alert shortcut uses these fixed defaults; edit budgets through the
Investigations page for a custom run. The presentation defaults are six calls and
five seconds. Retrieval is capped at 100 records and 64 KiB per call. Failed tool
attempts consume budget; records withheld by delivery limits cannot be cited.

One investigation runs at a time, while ingestion continues. **Cancel
investigation** requests cooperative cancellation: an active provider call must
return before it takes effect. Time limits are cooperative too. Restart marks
unfinished runs interrupted; saved completed reports survive.

### Review the report before deciding

Select a run under **Saved investigation**; **Run history** shows saved statuses.
Review these parts in order:

1. **Assessment**, hypothesis and **Run status**. A completed run can still have
   an uncertain assessment; failed, interrupted, incomplete and cancelled runs
   are distinct from a completed uncertain report.
2. **Unresolved questions** and **Limits and warnings**, including source incidents
   and budget limits.
3. **Verify cited evidence** → **Inspect citation** to read the exact records
   behind supporting and contradicting IDs.
4. **Reasoning and retrieval audit** for the disconfirmation test, triage,
   correlation, Falsifier query results and consumed budget.

`SUSPICIOUS` is a lead supported by the current policy, and `UNCERTAIN` means the
available evidence does not resolve the question. The synthetic presentation can
also produce `BENIGN_CONFOUNDER` for matching closed zero-byte flows. Operational
rule-based review does not infer benign intent from those flows. Citations are
checked against actual retrieval and the frozen snapshot; that check does not
establish that every claim is semantically correct. Review the evidence yourself.

Use **Export JSON** for a structured report or **Export Markdown** for a readable
copy; these are browser downloads. Reports retain their snapshot and citations
as later telemetry arrives. Downloads contain the report, not a full database
backup. Use **Create successor investigation** to make a new run linked to the
selected report with a new snapshot; the prior report stays unchanged.

Under **Analyst disposition**, enter **Analyst**, choose `OPEN`, `INVESTIGATING`,
`ESCALATED`, `CLOSED_BENIGN` or `CLOSED_INCIDENT`, add a **Note**, and click
**Save analyst action**. Actions persist separately from the machine report and
appear below the form. Analyst names are local attribution, not authenticated
identities. Closing a case does not release its pinned evidence for retention.

### Use the automatic queue

Expand **Automatic investigation queue**, enable **Investigate incoming alerts
automatically**, then click **Apply scheduling policy**. Automatic processing is
opt-in, runs one bounded investigation at a time while ingestion is connected,
and resets to off after restart. Durable work remains available after restart.

Use **Investigate next queued alert** to process queued work manually. For failed,
interrupted, cancelled or incomplete work, choose **Retryable alert**, click
**Requeue selected alert**, then start the next queued alert or enable automatic
processing. Automatic grouping into independently scoped cases, cooldowns and
manual membership editing remain unfinished.

## Check, back up and maintain state

Stop the GUI with Ctrl+C before maintenance. The operational database is
`bluecheese-operations/evidence.duckdb` by default. A state-directory OS lock
prevents competing runtimes and maintenance; its file can remain after exit
without representing a held lock.

### Diagnose configuration

```bash
./bluecheese --data-dir bluecheese-operations doctor --eve /absolute/path/eve.json
```

Doctor prints JSON with `ok`, errors, resolved paths, Python support, database
schema/upgrade status, Suricata availability and provider configuration. It checks
paths and configuration offline; it does not validate EVE contents, contact a
model, start capture or guarantee sensor delivery. `database_initialized: false`
is expected before the first GUI launch, and Suricata need not be on this machine
when reading an existing file.

### Back up and restore the operational database

Use a **new backup destination** and an **empty restore state**. From the repository
root, with the application stopped:

```bash
.venv/bin/python -m bluecheese.application.backup backup --state bluecheese-operations --out backups/operations-001
.venv/bin/python -m bluecheese.application.backup verify backups/operations-001
.venv/bin/python -m bluecheese.application.backup restore --source backups/operations-001 --state restored-operations
./bluecheese --data-dir restored-operations gui
```

Backup checkpoints and closes DuckDB under the state lock, then verifies the
copied database's hashes, schema and evidence count. Restore preserves reports,
frozen interpretations, tool traces and stored evidence. **External telemetry and
receipt/replay spools are not included.** Preserve these separately while stopped
if you need them for continuity. Restore does not relocate recorded source paths
or cursors; review Sensor health and source availability before reconnecting.
Checksums detect corruption, not authenticity.

Back up before upgrading. With the app stopped, update the checkout and reinstall
its pinned dependencies and package:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
```

Additive checksummed migrations upgrade older stores automatically at open without
rewriting accepted evidence or existing snapshots. Unsupported or modified
migration histories fail closed. Keep the old backup for recovery.

### Preview or apply retention

The default policy deletes nothing. Choose a **receipt sequence cutoff**, not a
timestamp, and preview before applying. For example:

```bash
./bluecheese --data-dir bluecheese-operations retention --before-sequence 1000
./bluecheese --data-dir bluecheese-operations retention --before-sequence 1000 --apply
```

This considers records with receipt sequence below 1000, at most 1,000 eligible
records per batch. Inspect the preview; run additional batches explicitly if
needed. Snapshot members and work references stay pinned, including for closed
cases. Tombstones prevent removed occurrences from being reimported, and receipt
sequence remains monotonic. Retention does not delete source logs, quarantine,
reports or backups and does not promise immediate filesystem shrinkage.

## Optional model provider

No model is downloaded or required. To use an existing server implementing Chat
Completions with strict JSON Schema responses, configure it **before launch**:

```bash
export BLUECHEESE_MODEL_ENDPOINT=http://127.0.0.1:8080/v1/chat/completions
export BLUECHEESE_MODEL=your-served-model-id
./bluecheese
```

Set `BLUECHEESE_MODEL_API_KEY` through your environment/secret manager if needed.
The sidebar identifies the selected provider. Doctor validates configuration but
never calls the endpoint. Test a manual investigation and inspect its status,
errors and citations to check your actual server/model; live compatibility remains
unverified. Restart the app after changing provider configuration. To return to
rules, unset the provider variables before restarting:

```bash
unset BLUECHEESE_MODEL_ENDPOINT BLUECHEESE_MODEL BLUECHEESE_MODEL_API_KEY BLUECHEESE_ALLOW_REMOTE_MODEL
./bluecheese
```

Remote endpoints require HTTPS and `BLUECHEESE_ALLOW_REMOTE_MODEL=true`. Enabling
them sends normalized observations, including IPs and detection signatures, to
the configured endpoint; exact raw logs are omitted. Provider calls use one
attempt, bounded input/output, no redirects and a timeout bounded by the remaining
cooperative deadline. Software controls retrieval and countertests; the model
cannot issue SQL or shell commands. Mechanical citation checks leave semantic
claim validation to review.

## Troubleshooting

| Symptom | What to check or do |
| --- | --- |
| Python version or missing module error | Use Python 3.11+ to create `.venv`, then install `requirements.lock` and the editable package as above. |
| Browser cannot reach the app | Keep the launch terminal running and use its printed URL. For an occupied explicit port, stop the competing server or choose another `--port`. |
| Unexpected empty/new workspace | Check the working directory and `--data-dir`; a relative path can select a different state. |
| File connection fails | Use an existing readable regular file on the app's machine. Native paths differ from Docker's `/telemetry/eve.json`. Correct the path and reconnect. |
| Connected but no new records | Check Suricata output, file growth and enabled alert/flow output. A completed capture simply waits at EOF; old timestamps remain old. |
| Unix stream stays Listening | Start the producer after the receiver; verify the generated socket path, `unix_stream` mode, filesystem namespace and OS permissions. |
| Socket path already exists or is too long | Use a new short unused path in an existing directory; existing paths are never overwritten automatically. |
| Stream disconnect, partial prior record or spool quota | Inspect Sensor health. Reconnect explicitly after a clean disconnect; use a new socket path/state when warned about partial records, or a new archived state after quota. |
| Quarantined records increase | Inspect reasons in Sensor health. Unsupported event types and malformed/oversized records are quarantined rather than accepted. |
| Ingestion stops after rotation/truncation | Inspect rotation notices and persisted incidents. Restore required archives if available; unsupported gaps require an explicit new source/state. Saved evidence remains available. |
| State is locked | Stop the other app/export/maintenance process using that state, or choose another state directory. Deleting the lock file is not a recovery procedure. |
| Investigation cannot start | Wait for or cancel the active run. For whole scopes over 10,000 records, select an alert neighborhood. Inspect failed-run errors or budget warnings. |
| A report does not include newer telemetry | Its snapshot is intentionally frozen. Create a successor or start a new investigation. |
| Automatic work is not running | Connect ingestion, enable the policy and click Apply scheduling policy. After restart it is off; failed/interrupted work requires explicit requeue. |
| Model run fails | Check endpoint/model configuration and strict JSON Schema support; inspect the saved error. Use the default rules while compatibility is unresolved. |

## Docker Compose

Native and Docker use the same `requirements.lock`. Docker build/launch is
**unverified**; Compose configuration has been validated. The container runs as
UID/GID 10001, excludes legacy PCAP capture dependencies and does not install
Suricata. With Docker Engine and Compose available:

```bash
mkdir -p telemetry
docker compose up --build -d
docker compose logs -f bluecheese
```

Open http://127.0.0.1:8501. Place the sensor's EVE file in `./telemetry` and connect
`/telemetry/eve.json` in the sidebar. Files/directories must be readable/traversable
by the container user. To mount another host directory, set
`BLUECHEESE_TELEMETRY=/absolute/source/directory` before `docker compose up`.
The telemetry mount is read-only; no privileged mode or host networking is used.

Ctrl+C exits log following; stop the app separately:

```bash
docker compose down
```

Evidence persists in the `evidence-state` named volume. `down` retains it; adding
`--volumes` would delete it. Native state and the container volume are separate.
The standard Compose file does not pass model-provider environment variables into
the container. Use native launch for the verified operational workflow and local
Unix stream setup.

## Synthetic presentation and offline bundles

The developer/evaluation presentation is separate from the operational console.
It loads bundled synthetic scenarios and provides Evidence, Investigation,
Comparison and Live tabs. It uses the deterministic provider regardless of
operational model configuration. No sensor or model key is needed. Use a separate
state from operational evidence. After the install above:

```bash
BLUECHEESE_STATE=bluecheese-data .venv/bin/python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Open the printed URL. Select `suspicious / clean` in Evidence, run an investigation
in Investigation, then run the clean/poisoned comparison in Comparison. Keep the
default six-call/five-second budget and Falsifier enabled for the walkthrough.
In Live, choose **Synthetic replay**, then **Start / resume ingestion**; it appends
fixture records every 0.5 seconds and refreshes every second. **Stop ingestion**
stops replay. Investigations use fixed snapshots while later records arrive.
These are deterministic policy demonstrations, not model accuracy measurements.
See [the five-minute walkthrough](docs/DEMO.md) for expected synthetic outcomes.

Presentation state defaults to `bluecheese-data/evidence.duckdb` and replay to
`bluecheese-data/replay/eve.jsonl`. `BLUECHEESE_STATE` and `BLUECHEESE_REPLAY` can
select other writable paths. Presentation background/cancellation and saved
successor controls preserve prior reports; rerendering does not start new runs.

With the presentation **stopped**, export synthetic reports and bundles to a new
directory, then verify a bundle offline:

```bash
.venv/bin/python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports-v2 --bundles
.venv/bin/python -m bluecheese.application.report_bundle demo-exports-v2/suspicious-poisoned.bundle
```

This runs all four bundled scenario/variant combinations and writes JSON/Markdown
reports plus immutable `.bundle` directories. **This command generates synthetic
presentation reports; it does not export your operational cases.** Use the
operational GUI's report downloads and the database backup commands for those.
Existing bundle directories are never overwritten; choose a new output directory.

Bundles include a report, run/snapshot manifest, tool trace, referenced exact raw,
parsed and normalized evidence, and SHA-256 checksums. Verification checks retrieval
visibility, occurrence identity, normalization and snapshot bounds. Hashes are not
signatures or semantic support checks. Historical parser archives remain pending.
The evaluator manifest in `docs/evaluator` never enters provider inputs.

## Preserved CLI and legacy web UI

The original PCAP/EVE import, SQLite evidence, triage and web UI remain available.
They use `bluecheese.sqlite3`, independently of the GUI's DuckDB evidence. A legacy
import does **not** populate the operational console; connect EVE in the GUI for
that workflow. These examples use the checkout launcher:

```bash
./bluecheese --data-dir eve-data import-eve tests/fixtures/sample_eve.json
./bluecheese --data-dir eve-data alerts
```

Copy an alert's ID from the output and replace `EVENT_ID` below:

```bash
./bluecheese --data-dir eve-data evidence EVENT_ID
./bluecheese --data-dir eve-data triage EVENT_ID
./bluecheese --data-dir eve-data report EVENT_ID
./bluecheese --data-dir eve-data serve --port 8765
```

Open http://127.0.0.1:8765 for the legacy UI. For PCAP import, install Suricata on
PATH (or use `--suricata /path/to/suricata`):

```bash
./bluecheese --data-dir pcap-data import-pcap tests/fixtures/bluecheese-demo.pcap --config tests/fixtures/suricata-demo.yaml --rules tests/fixtures/bluecheese-demo.rules
./bluecheese --data-dir pcap-data alerts
```

The bundled PCAP is synthetic. A detection-rule match alone does not prove
compromise. Use subcommand `--help` for further options.

## Development checks and remaining work

Install the pinned development dependencies before running checks:

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest -q --cov=bluecheese --cov-report=term-missing
.venv/bin/python -m pip check
```

Tests use temporary state, offline fixtures and deterministic polling, with no
real models/API keys. Local Suricata integration runs when available; otherwise
it skips. Unix socket tests need permission to bind local sockets. The latest
recorded macOS/Python 3.13 verification passed 71 tests, including local Suricata
PCAP/stream integration and GUI interactions. Earlier native Linux/Python 3.14.7
checks are recorded in [session status](docs/SESSION_STATUS.md).

For an isolated synthetic finite-backlog ingestion measurement:

```bash
./bluecheese benchmark --records 1000
```

The benchmark uses temporary state and makes no provider calls. It does not
establish sustained capacity or detection quality.

Accepted raw text is exact and immutable. IDs distinguish source identity, scope,
byte position and content; identical lines at distinct positions remain distinct.
All investigation tools are scoped to the run's frozen snapshot and validated
against actual retrieval. One database worker owns the connection, and provider
calls execute outside database locks. See [architecture](ARCHITECTURE.md) for the
implementation boundaries.

The full master plan remains incomplete. Next dependencies are individual access
controls and verified shared deployment; live model compatibility and semantic
claim/detection-quality evaluation; and sustained ingestion/overload, sensor drop
monitoring, spool lifecycle, Docker execution and deployed rotation-policy checks.
Historical parser archives, richer case editing and research acceptance criteria
also remain pending. Dataset/model downloads and training are excluded by the
repository instructions.

Use [ROADMAP.md](ROADMAP.md) for implemented slices and remaining work,
[release gates](docs/RELEASE_GATES.md) for deployment requirements,
[session status](docs/SESSION_STATUS.md) for the current handoff, and the
[master implementation plan](Blue_Cheese_Master_Implementation_Plan.md) for the
planned product.
