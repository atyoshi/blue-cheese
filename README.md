# Blue Cheese

Blue Cheese provides a local analyst GUI for Suricata network evidence: interactive
traffic views, exact log inspection, bounded investigations and saved reports.
Suricata performs packet capture and detection. Blue Cheese consumes its output.

## Start here

Already set up? From this repository, run:

```bash
./bluecheese
```

Open the **local URL printed in the terminal** (normally http://127.0.0.1:8501;
if that port is busy, the app tries the next available port). No activation
command, model key or long launch
flags are required. The launcher uses this checkout's `.venv` automatically and
opens the operational console with state in `./bluecheese-operations`. It does
not load synthetic scenarios or automatically start a sensor.

For a fresh checkout, install once using **Python 3.11 or newer**:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
./bluecheese
```

Check `python3 --version` first; if your OS's `python3` is older than 3.11, use
an installed newer interpreter for the first command, such as `python3.13`.
Suricata must be installed and configured separately on your sensor.

| Task | Command |
|---|---|
| Open the operational GUI | `./bluecheese` |
| Use another port | `./bluecheese gui --port 8502` |
| Check configuration with the GUI stopped | `./bluecheese doctor` |
| Check an EVE file before connecting | `./bluecheese doctor --eve /path/to/eve.json` |
| Choose another state directory | `./bluecheese --data-dir my-soc gui` |
| Show all CLI commands | `./bluecheese --help` |

To use `bluecheese` without the `./`, run `./install-command.sh` once and add
`~/.local/bin` to your PATH if prompted. This links to the checkout; it does not
copy the project. The preserved import/triage commands retain their legacy
`bluecheese-data` default; GUI, doctor and retention default to `bluecheese-operations`.
Stop the GUI with **Ctrl+C** in its terminal. One process may use a state directory
at a time, including diagnostic/export commands.

## Choose your telemetry input in the GUI

In the sidebar, choose **Telemetry input**:

### EVE file: live tail or completed capture

1. Select **EVE file**.
2. Enter the existing file's absolute path **on the machine running Blue Cheese**.
3. Click **Connect sensor**. Existing records load in bounded batches; new lines
   appear automatically. This option is live when Suricata keeps writing the file.

The path field starts empty unless `BLUECHEESE_EVE` is configured. Missing files,
directories and named pipes are rejected with an explanation. `/telemetry/eve.json`
is a Docker-mounted path, not a native macOS/Linux default.

Rename-and-create rotation recovery is enabled by default. It drains the retained
old descriptor for five seconds, then starts a new persisted generation. Matching
archives named `eve.json.*` can be recovered on restart in a bounded directory
search. Truncation, missing archives, partial rotated records and multiple rotations
during draining stop ingestion visibly. Late writes to retired generations and
undetectable copytruncate/regrowth are outside automatic recovery.

### Unix stream socket: live EVE without an input log file

1. Select **Unix stream**. Keep the suggested socket path or choose
   an unused path in an existing directory. Unix socket paths must be short.
2. Click **Connect sensor**. **Listening** means the receiver is ready; it does
   not yet mean Suricata is connected.
3. Open **Suricata stream configuration** in the sidebar. Copy its YAML into your
   sensor's existing EVE output configuration, preserving capture settings and rules.
4. Start/restart Suricata. **Streaming** means a producer has connected. The charts
   populate as alert and flow records arrive.

Blue Cheese is the listener; Suricata connects to it. This is EVE JSON transport,
not Suricata's command/control socket. Use `filetype: unix_stream`, not `unix_dgram`.
The GUI generates the exact `filename` socket path, avoiding manual path edits.
Suricata documents these [EVE output modes](https://docs.suricata.io/en/suricata-8.0.3/output/eve/eve-json-output.html).

Unix sockets work locally on Linux/macOS in the same filesystem namespace. The
socket is restricted to its OS owner; run Suricata as that user or root. Native
launch is the simplest option for this mode. The standard Docker telemetry mount
is read-only and does not expose the container's socket to a host sensor.

Received bytes are saved to a persistent receipt spool before parsing. They retain
the same immutable evidence, triage, visualization and investigation workflow as
file input. The current spool limit is **256 MiB per socket path**; reaching it stops
visibly without deleting received evidence. Archive the stopped state and select a
new state to continue. Producer disconnects stop ingestion and record a continuity
incident; reconnect explicitly. Partial records are retained and are never merged
with a new producer after restart: choose a new socket path/state when warned.
Existing socket paths are never replaced automatically, including stale paths left
by an abrupt process termination.

Socket delivery is not an end-to-end loss guarantee: Suricata can drop events while
the receiver is unavailable or congested. Monitor sensor output/drop statistics.
For persistent sensor-side buffering and easier restart recovery, use live file tail.

**Disconnect sensor** stops either input while preserving stored evidence. After
an app restart, reconnect explicitly. Saved investigations survive restart.

## Explore and learn

The **Overview** uses only accepted external telemetry:

- **Activity timeline:** compare alert and flow record counts over recorded event
  time in UTC. Hover for values; Shift + scroll to zoom time, drag to pan,
  double-click to reset. Normal scrolling leaves the chart scale unchanged.
- **Severity and protocol charts:** compare sensor rule priority and observed
  transport protocols. An alert is a lead, not proof of compromise.
- **Connection map:** see source → destination IP relationships. Orange edges
  contain alerts; blue edges contain only flow records in the displayed view.
- **Endpoint focus and connection inspection:** filter the visuals, then inspect
  the exact evidence behind a connection. Start an investigation from an alert.
- **Learning mode:** explanations of IPs, ports, TCP/UDP, flows, alerts and the
  investigation workflow. Switch it off for a compact analyst view. Record
  explanations also appear on the Alerts and Flows pages.

Visuals default to the latest 1,000 accepted records, with 250/5,000 options.
Use the **Activity**, **Connections** and **Evidence** tabs to move from patterns
to individual records. Endpoint and connection filters apply to all three tabs;
**Reset focus** clears both. The endpoint filter applies within that recent-record window. The connection map
shows up to 12 IP pairs; evidence detail shows up to 50 matching records. The
Alerts/Flows pages provide full pagination. All limits are labelled in the GUI.
Counts are log records, not unique sessions or packets. Old captures retain their
original event times. A zero in a chart does not establish uninterrupted coverage.

**Sensor connection** collapses when stored evidence is available. Expand it to
connect or disconnect an input. Switch **Auto refresh** off while reading or
editing; ingestion continues. Changing a filter or pressing **Refresh now** reloads
the view. Evidence labels show the rule or flow state, endpoint pair and short ID;
expand **Original evidence and normalized fields** for the exact stored record.

Use **Investigations** for saved reports, citations, JSON/Markdown downloads,
analyst notes and successor investigations. **Sensor health** shows source status,
cursors, stream spool paths, quarantine reasons and continuity incidents.
See the measured [UI/UX review](docs/UI_UX_REVIEW.md) for fixes and remaining checks.

## Connect a sensor or exercise it with tcpreplay

Suricata must run separately with detection rules and EVE `alert` and `flow`
outputs enabled. For example, on a Linux sensor (adjust paths/interface):

```bash
mkdir -p telemetry
sudo suricata -c /etc/suricata/suricata.yaml -i eth1 -l "$PWD/telemetry"
```

Point the console to that directory's `eve.json`. To exercise the sensor, run
`sudo tcpreplay --intf1=eth1 capture.pcap` on an isolated replay host whose traffic
the sensor sees. Blue Cheese consumes the sensor output; it does not capture packets,
generate scans or manage Suricata. A completed EVE file can also be connected.

This is a working **local, single-analyst console**, not a completed enterprise
platform. There is no authentication/RBAC or multi-sensor management; the native
launcher binds to localhost. Investigations use the bounded rule-based engine unless a model endpoint is explicitly configured.
Select **Investigate selected alert** to freeze a same-source endpoint neighborhood
within five minutes, or use the whole external scope. Table filters are independent
of case membership. The 10,000-record cap applies to each frozen case snapshot.
Automatic investigation is opt-in under Investigations and resets to off after
restart; durable queued work remains available. Failed/interrupted tasks require
explicit retry. Rule-based review does not infer benign intent from zero-byte flows.
Only alert/flow records are currently accepted; other event types are quarantined.
Use a separate state directory from the presentation, and one process per state.

The presentation below remains a separate developer/evaluation workflow.


## Operational checks, models and retention

With the GUI stopped:

```bash
./bluecheese doctor --eve /absolute/path/eve.json
./bluecheese retention --before-sequence 1000
```

`doctor` performs offline checks; it never contacts a model or launches capture.
Retention previews at most 1,000 eligible records per batch. Add `--apply` only to
execute that batch. All snapshot members and work references remain pinned, even
when an analyst closes a case. Tombstones prevent reimporting removed occurrences,
and the receipt sequence remains monotonic. Retention does not delete source logs,
quarantine, reports or backups, and does not promise immediate filesystem shrinkage.
The default policy deletes nothing.

To use an existing local server implementing Chat Completions with strict JSON
Schema responses, configure it before launch (no models are downloaded):

```bash
export BLUECHEESE_MODEL_ENDPOINT=http://127.0.0.1:8080/v1/chat/completions
export BLUECHEESE_MODEL=your-served-model-id
./bluecheese
```

If needed, set `BLUECHEESE_MODEL_API_KEY` through your environment/secret manager.
Remote endpoints require HTTPS and `BLUECHEESE_ALLOW_REMOTE_MODEL=true`; enabling
this transmits normalized observations, including IPs and detection signatures,
to that configured endpoint. Exact raw logs are omitted. No remote provider is
configured by default, and no real model endpoint was used for verification.
Provider calls have one attempt, bounded input/output, no redirects, and a timeout
limited by the remaining cooperative run deadline. Retrieval and countertests are
software-controlled; a model cannot issue SQL or shell commands. Claims receive
mechanical citation checks and remain semantically unassessed pending review.
The adapter follows the [Chat Completions structured output contract](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
Endpoint compatibility must be tested for the model/server you actually deploy.

Schema migrations 2–5 add analyst actions, source incidents, durable work,
retention metadata and file generations without rewriting existing evidence or
snapshots. Existing schema-1 stores upgrade automatically under the state lock.
Back up the stopped state before deploying an upgrade.

See [release gates](docs/RELEASE_GATES.md) for what is tested and what remains
necessary before any commercial deployment claim.

## Current status

The presentation implements deterministic logical roles, bounded file ingestion and
synthetic replay, immutable run snapshots, persisted case revisions and successor
history, background investigation/cancellation, auditable report bundles and offline
backup/restore. A single database worker owns DuckDB; an exclusive state-directory
lock prevents competing runtimes and exports. The legacy CLI/SQLite path remains
available.

The full master plan is **not complete**. The operational slices now include
bounded rename rotation recovery, retention, an optional structured model adapter
and a durable automatic investigation queue. Native macOS and local Suricata
integration have been tested. Docker execution, live model compatibility and
multi-analyst access controls remain release gates. See
[release gates](docs/RELEASE_GATES.md) and [verification details](docs/TESTING.md).

The specification is [Blue Cheese Master Implementation Plan](Blue_Cheese_Master_Implementation_Plan.md).
[ROADMAP.md](ROADMAP.md) tracks implemented slices and remaining gates;
[ARCHITECTURE.md](ARCHITECTURE.md) describes current boundaries.

## Native launch (presentation fallback)

From the repository root, use Python **3.11 or newer**. Linux with Python 3.14.7 was tested; macOS portability is intended, not verified. Installing dependencies needs package-registry access.

Use an up-to-date checkout before installing: `git pull --ff-only`. The commands
below use the lockfiles included in the current repository. If
`requirements-dev.lock` is missing, check that you are in the repository root
and that your checkout is current.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

For an editable development install using dependencies from `pyproject.toml`,
you can instead run the following in your activated environment:

```bash
python -m pip install -e ".[dev]"
python -m pytest -v
```

This installs pytest and Ruff alongside the application. Use the lockfile
installation above for the packaged presentation environment and its coverage
checks.

Open **http://127.0.0.1:8501**. The last command runs the application; Ctrl-C stops it. Launch only one application process per state directory. The four tabs are Evidence, Investigation, Comparison and Live. A rerender retains saved investigations; only investigation buttons run the provider. The Falsifier toggle and budgets apply to the next run. Replay starts only when requested.

State defaults to `./bluecheese-data/evidence.duckdb`; replay appends to `./bluecheese-data/replay/eve.jsonl`. Set `BLUECHEESE_STATE=/absolute/writable/path` and optionally `BLUECHEESE_REPLAY=/another/writable/path` before launch. Existing CLI state remains SQLite and is independent.

To create the bundled presentation exports **while the app is stopped**, using the same state:

```bash
python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports
```

This writes `suspicious-clean`, `suspicious-poisoned`, `benign-clean`, and `insufficient-clean` JSON/Markdown files. UI download buttons export saved offline/comparison/live reports. Reports state provider, snapshot, budget, warnings, unresolved evidence and validated citations.

## Docker Compose

With Docker Engine and Compose available to your user:

```bash
mkdir -p telemetry
docker compose up --build -d
docker compose logs -f bluecheese
docker compose down
```

`up` builds and starts the real-telemetry console in the non-root app at **http://127.0.0.1:8501**; `logs` follows output; `down` stops it and retains volumes. Native and Docker use `requirements.lock`. Persistent evidence is in `evidence-state`. `./telemetry` mounts read-only at `/telemetry`; to follow an external growing EVE file, place it there and enter path `/telemetry/eve.json`, in the sensor connection sidebar. Set `BLUECHEESE_TELEMETRY=/absolute/source/directory` to mount another directory. No privileged mode or host networking is needed.

Compose configuration was validated. Build/launch is **unverified**: the Docker daemon is unavailable in this environment. Use native launch for the operational console. The container intentionally excludes the legacy PCAP sensor path; it does not install Suricata.

## Verify

```bash
python -m ruff check src tests
python -m pytest -q --cov=bluecheese --cov-report=term-missing
```

Tests use temporary stores and files, offline fixtures, deterministic polling and no models/API keys. Existing PCAP integration uses local Suricata if installed and otherwise skips. AppTest exercises scenario selection, evidence, findings, saved runs and worker reuse. See [session status](docs/SESSION_STATUS.md) for measured results and [five-minute walkthrough](docs/DEMO.md).

## Implementation choices and limits

The presentation extends `NormalizedAlert` and the Suricata adapter with flow counters/state. Each event stores exact raw UTF-8 text including its newline, parsed JSON, canonical fields, source locator and an ID hashing scope, source identity, byte position and content. Identical lines at different positions remain distinct; retries at the same position do not duplicate acceptance. Malformed records are quarantined.

Typed tools are parameterized, scoped by scenario/variant and materialized snapshot membership, and capped at 100 records and 64 KiB of delivered evidence per call. Triage groups up to 20 visible alerts into five-minute buckets and assigns review priority separately from sensor severity. The Orchestrator selects one seed group by priority and stable occurrence ID. Correlation links same-source/sensor observations within a five-minute window using flow IDs/endpoints or exact endpoint tuples; links record their rule basis and ambiguity. The demo investigates the selected alert and correlated flows matching its non-null flow ID and endpoints. Established flows with at least 10,000 outbound bytes support `SUSPICIOUS`. The Falsifier independently queries the source IP for matching closed zero-byte flows: those produce `BENIGN_CONFOUNDER` when there is no active-flow support, or `UNCERTAIN` with conflicting support. An alert alone stays `UNCERTAIN`. These are inspectable demonstration rules, not universal security classifications. Enrichment text never drives this policy. The replaceable provider protocol preserves a small extension point; the repository had no existing real model provider.

Default budgets are six tool attempts and five seconds, shared across all logical roles. Dispatched tool failures consume the call budget; records withheld by the byte cap cannot be cited. Time limits are cooperative checks around queries/provider execution, not hard process preemption. Citation validation rejects invented, cross-scope and unseen IDs. Snapshot-bound reports remain unchanged while replay adds evidence.

One cached runtime submits database operations to a bounded 64-command queue on one owning worker thread. Its RLock protects lifecycle/follower state; provider execution runs outside database locks, allowing ingestion to continue. Only one provider investigation may be active. Each run freezes up to 10,000 scoped evidence interpretations; later records or normalization changes cannot alter that run. Replay appends one record every 0.5 seconds, cycling the synthetic fixture. Live refreshes every second. Reads are capped at 256 KiB/poll and lines at 64 KiB. Unterminated lines remain pending; oversized complete lines are quarantined with a bounded raw prefix explicitly marked as truncated. Accepted-event raw input is exact. Evidence/quarantine and committed source identity/offset commit in one transaction. Partial bytes are reread after restart. Append-only sources must preserve their existing bytes: device/inode, size and a committed 4 KiB prefix detect common replacement/truncation; undetected in-place edits or truncate/regrow between polls are outside this milestone. A detected gap stops with a clear message; select a new file/state to reset. Full rotation recovery is deferred.

Other deferred scope includes automatic case scheduling/editing, retention, real model providers, historical parser archives, vector retrieval, authentic dataset evaluation, training, packet capture, sustained load testing and multi-platform CI. Current correlation proposals do not automatically narrow case membership or schedule new investigations.

## Preserved Suricata CLI

The existing PCAP/EVE import, SQLite evidence, triage and simple web UI remain available. For PCAP import, install Suricata separately on PATH:

```bash
bluecheese --data-dir demo-data import-pcap tests/fixtures/bluecheese-demo.pcap --config tests/fixtures/suricata-demo.yaml --rules tests/fixtures/bluecheese-demo.rules
bluecheese --data-dir demo-data alerts
bluecheese --data-dir eve-data import-eve tests/fixtures/sample_eve.json
```

Use `bluecheese --help` for `evidence`, `triage`, `report` and the legacy `serve` command (localhost:8765). The bundled PCAP produces a synthetic payload alert and a related flow; its rule match alone does not prove compromise.

## Auditable offline bundles

With the app stopped, export to a new directory:

```bash
python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports-v2 --bundles
python -m bluecheese.application.report_bundle demo-exports-v2/suspicious-poisoned.bundle
```

Bundles include reports, scoped run manifest, tool trace, referenced exact raw,
parsed and normalized evidence, and SHA-256 checksums. Offline verification checks
retrieval visibility, occurrence identity, normalization and snapshot bounds.
Checksums detect corruption; they are not signatures or semantic support checks.
Existing bundles are never overwritten. Schema version 1 uses the current demo
parser; archived parser versions remain pending.

Presentation stores acquire an exclusive OS lock on the resolved state directory
before schema initialization. Competing runtimes/exports fail with instructions
to stop the first runtime or select another state directory. The lock file stays
on disk; OS ownership releases on process exit. Linux is tested; macOS execution
remains unverified. See ROADMAP.md for master-plan gaps.

## Case history, background work and backups

The Investigation tab now shows triage groups and correlation links. Saved case
runs survive restarts: load a report without rerunning it, or explicitly create a
successor revision linked to a selected run. The case question identifies the case;
the current deterministic policy investigates alert/flow observations and is not
a general question-answering model. It selects one bounded seed group per run.

“Start background investigation” keeps the UI responsive; “Cancel active
investigation” requests cooperative cancellation. The current provider call must
return before cancellation takes effect. Incomplete, cancelled and failed runs
remain distinct from completed reports with an uncertain verdict. Restart marks
unfinished work interrupted and retains its tool trace for a controlled successor.

Stop the app before backing up. Use a new backup directory and an empty restore
state directory:

```bash
python -m bluecheese.application.backup backup --state bluecheese-data --out backups/demo-001
python -m bluecheese.application.backup verify backups/demo-001
python -m bluecheese.application.backup restore --source backups/demo-001 --state restored-state
BLUECHEESE_STATE=restored-state python -m streamlit run src/bluecheese/interfaces/demo.py --server.address 127.0.0.1
```

Backups checkpoint and close the database while retaining the exclusive state
lock, copy it, and verify its hashes/schema/counts before publishing. Restore
preserves saved reports, snapshot interpretations and tool traces. External
telemetry and replay spools are not included; original source locators/cursors are
preserved and are not rewritten to imply continuity at a new location. Export
report bundles from the restored database for independent inspection.

Schema migration 1 adds case/snapshot/run/tool tables without changing existing
evidence or cursors. Migration metadata has a checksum; unsupported future or
modified migrations fail closed. No state reset is required for the previous
evidence-only schema. Database access now runs on one owning worker thread with
a bounded command queue, while lifecycle/follower state remains under the RLock.
See ARCHITECTURE.md and ROADMAP.md for the supported slice and remaining gates.

## Next steps

Follow the master plan's dependency order:

1. **Complete rotation recovery:** explicit source generations, draining archived
   files, restart-safe cursors and durable telemetry-gap records.
2. **Add recoverable case scheduling:** bounded triage/correlation case proposals,
   durable work items, cooldowns and controlled retries after restart.
3. **Finish local-operation release gates:** retention that protects evidence used
   by saved reports, Docker execution and native macOS verification.
4. **Integrate a real provider:** explicit capability/configuration profiles,
   structured-output validation, timeout/error handling and shared budgets, tested
   with fake providers before using a real model.
5. **Build the research harness:** matched baselines and poisoning experiments,
   with evaluator labels isolated from agent inputs and results limited to the
   tested scenarios.

Review and commit the tested implementation as a checkpoint before the next code
slice. See [ROADMAP.md](ROADMAP.md) for package-level boundaries and
[session status](docs/SESSION_STATUS.md) for the current handoff. Dataset/model
downloads and training remain excluded by the repository instructions.
