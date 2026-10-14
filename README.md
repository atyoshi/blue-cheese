# Blue Cheese

Blue Cheese is a local analyst workspace for Suricata network evidence. Connect
an EVE file or local Unix stream, explore traffic, inspect original logs, run a
bounded investigation, and save a cited report and your analyst decision.
Suricata performs capture and detection; Blue Cheese consumes its output.

After installation, choose your workspace:

```bash
./blue-cheese --cli                       # Interactive agent terminal
./blue-cheese --cli --config config.json  # Terminal with your model server
./bluecheese                             # Browser-based analyst console
```

The operational console runs locally without a model key. It uses a rule-based
investigator by default. This is a single-analyst development release: individual
authentication, roles and shared SOC deployment remain unfinished. Native macOS
and local Suricata integration have been tested; Docker execution remains unverified.
One live llama.cpp model passed the [CLI compatibility checks](docs/CLI_MODEL_VALIDATION.md).
See [current verification](docs/TESTING.md) and
[release gates](docs/RELEASE_GATES.md).

Quick links: [install](#install-and-open-the-console) ·
[agent terminal](#interactive-agent-terminal) ·
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

`./blue-cheese` is a compatibility wrapper for `./bluecheese`; both accept the
same arguments and launch the same application.

The console initially has no telemetry. It does not load demonstration scenarios
or start Suricata automatically. **Practice investigation** offers a separate
synthetic workspace with five checkpoints; see [the guided walkthrough](docs/GUIDED_INVESTIGATION.md).
Install/configure Suricata separately if you
want live sensor output; an existing EVE file needs no running sensor.

| Task | Command |
| --- | --- |
| Open the operational GUI | `./bluecheese` |
| Open the interactive agent terminal | `./blue-cheese --cli` |
| Use a model configuration file | `./blue-cheese --cli --config config.json` |
| Show terminal startup options | `./blue-cheese --cli --help` |
| Choose an explicit port | `./bluecheese gui --port 8502` |
| Choose a state directory | `./bluecheese --data-dir my-soc gui` |
| Check configuration with the GUI stopped | `./bluecheese doctor` |
| Check an EVE path with the GUI stopped | `./bluecheese doctor --eve /absolute/path/eve.json` |
| Show commands/options | `./bluecheese --help` or `./bluecheese gui --help` |

Put the global `--data-dir` option **before** the subcommand. Relative state paths
are relative to the terminal's working directory. The GUI, agent terminal, doctor and retention
commands default to `./bluecheese-operations`; legacy CLI commands default to
`./bluecheese-data`. Use the same explicit absolute state path across launches
and maintenance commands if you work from different directories. Only one process
may use a state directory at a time, including exports and maintenance.

Optional: run `./install-command.sh` to link this checkout's launcher into
`~/.local/bin`. If prompted, add that directory to your shell's PATH, for example
`export PATH="$HOME/.local/bin:$PATH"`, and persist it in your shell configuration.
You can then use `bluecheese` from other directories; state paths still follow the
working directory. The link depends on this checkout remaining in place.

## Interactive agent terminal

`/summary [RUN_ID]` returns a concise summary of an explicit run, the last actual
displayed/investigated context, or a labelled bounded workspace overview.
`/explain TERM` explains a term or the selected evidence. Natural summaries and
explanations use the same read-only handling in the GUI and CLI, including without
a model. They never launch an investigation. Existing slash inspection commands
retain structured output and approvals. See [the practice and conversation walkthrough](docs/GUIDED_INVESTIGATION.md).

After installation, start the terminal with one command:

```bash
./blue-cheese --cli
```

`./bluecheese --cli` and `bluecheese chat` are equivalent. The GUI remains the
default without arguments. The terminal uses `bluecheese-operations` by default;
stop the GUI before opening the same state directory, or select a separate one:
`./blue-cheese --cli --data-dir terminal-state`.

Enter `/help` for commands. A typical session is:

```text
/import /absolute/path/eve.json
triage alerts
show network information
investigate whether the alert is supported by the flows
show the latest report
/quit
```

Lines without a leading `/` are natural-language requests: offline rules route
them locally, while a configured model proposes a task for approval. Slash
commands select tasks directly; the equivalents above are `/triage`, `/network`,
`/investigate whether the alert is supported by the flows`, and `/report`.

| Terminal command | What it does |
| --- | --- |
| `/import PATH` | Import a static EVE file with resumable cursors |
| `/follow PATH` / `/stop` | Start or stop following an EVE file |
| `/alerts` | Show alert evidence IDs and normalized records |
| `/triage` | Group and prioritize alerts using rules |
| `/network` | Summarize observed endpoints, protocols and connections |
| `/investigate QUESTION` | Run the agent workflow and save a cited report |
| `/report [RUN_ID]` / `/history` | Read the latest or selected report, or list runs |
| `/config [PATH]` / `/rules` | Select a model config file or offline rules |
| `/test` | Check the model endpoint's tool and report capabilities |
| `/status` | Show source and investigation state |
| `/help` / `/quit` | Show help or exit |

Each evidence task proposes its scope and waits for `y` or `yes`; Enter declines.
Investigations show actual role/action handoffs as they execute and save cited
reports in the same operational history as the GUI. Approval for an investigation
covers its bounded read-only evidence tools, model calls and saved report.
Ctrl-C during an investigation requests cooperative cancellation; the active model
call must return before it stops. Ctrl-D or `/quit` closes the runtime.

`/import` reads a static EVE JSONL file once (16 MiB maximum), using bounded
ingestion batches, quarantine and resumable cursors. An unfinished final line is
reported as pending bytes and remains uncommitted. `/follow /absolute/path/eve.json`
uses the existing bounded append-only ingestion worker with quarantine and cursor
recovery; `/stop` stops
following. Automatic investigations stay disabled. `/triage` reads at most 20
alerts; `/network` describes at most 1,000 recent records and performs no scan.
`/report RUN_ID` reads a historical report; `/history` lists run IDs. Reports
and telemetry are displayed as escaped JSON, including original evidence IDs.
`/status` shows the active ingestion source, not the last imported file; after
a one-time `/import`, `source: null` is expected unless a follower is running.

### Start a local model server (optional)

If you do not have a model server, start with the upstream
[llama.cpp build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)
or its [prebuilt releases](https://github.com/ggml-org/llama.cpp/releases).
Obtain a compatible instruction-tuned GGUF model from its publisher, choosing a
size that fits your machine's memory. With `llama-server` installed and the model
downloaded, a local-only starting command is:

```bash
llama-server -m /absolute/path/model.gguf --alias bluecheese-local --host 127.0.0.1 --port 8080 --jinja
```

Keep that server running. In another terminal, from this checkout:

```bash
./bluecheese --cli --endpoint http://127.0.0.1:8080/v1 --model bluecheese-local --timeout 300
```

Enter `/test` and approve the synthetic capability probes before investigating.
The model and chat template must support forced tool calls and structured JSON;
serving a GGUF alone does not guarantee compatibility. See the upstream
[server and tool-calling guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
for template and hardware options. This is setup guidance, not a newly tested
deployment; the one live deployment tested here is recorded in
[CLI model validation](docs/CLI_MODEL_VALIDATION.md).

For an OpenAI-compatible server, copy [config.example.json](config.example.json)
to `config.json`, set its endpoint and model, then launch:

```bash
cp config.example.json config.json
# Edit config.json to set your server's endpoint and model name.
./blue-cheese --cli --config config.json
```

The example config uses a local server at `http://127.0.0.1:8080/v1`. Replace
`your-model-name` with the model identifier served by your endpoint. If the
server requires a key, export `BLUECHEESE_MODEL_API_KEY` before launch, or set
`api_key_env` to the name of an environment variable that already holds your key.
To select a file after starting the terminal, enter `/config` and supply its path
at the prompt.

Or use flags:

```bash
./blue-cheese --cli --endpoint http://127.0.0.1:8080/v1 --model your-model
```

Inside the session, `/config` prompts for a config path, `/config PATH` loads it,
and `/rules` restores offline investigation. Settings do not send a request.
`/test` asks approval before synthetic tool/schema capability probes. With no
file or flags, the existing `BLUECHEESE_MODEL_*` environment configuration applies;
otherwise the selected file/flags define the provider, and flags override file
fields. `/help` and `--cli --help` list tasks and startup options.

Config fields are `endpoint`, `model`, `falsifier_model`, `api_key_env`, optional
`api_key`, `allow_remote`, `allow_insecure_http`, optional `enable_thinking`,
`timeout`, `max_output_tokens`, `max_attempts`, and
`json_mode`. Use `api_key_env` to reference an exported secret; `config.json` is
Git-ignored. Base URLs and full Chat Completions URLs are accepted. Remote
endpoints require `allow_remote: true` (or `--allow-remote`) and default to HTTPS.
For a server available only over HTTP, also set `allow_insecure_http: true`
(or `--allow-insecure-http`). Evidence and any API key travel unencrypted.
For example, retain your server's model identifier and set these fields in your config:

```json
{
  "endpoint": "http://grain.utep.edu:11434/",
  "model": "your-served-model-id",
  "allow_remote": true,
  "allow_insecure_http": true
}
```

This base URL resolves to `/v1/chat/completions`; the server must implement the
OpenAI-compatible Chat Completions API. Reload with `/config ~/bc.json` after
restarting an already-running terminal to pick up the updated code. Model
investigations send normalized evidence to that endpoint. Use `json_mode: true`
for servers without strict JSON Schema; local report/citation validation still
applies. See [measured live compatibility](docs/CLI_MODEL_VALIDATION.md) for the
tested server/model; other deployments remain unverified.

For slow model servers, increase `timeout` (maximum 600 seconds per call).
Operational model investigations use a cooperative run budget of at least 60 seconds,
or `timeout × max_attempts`, whichever is larger. The approval prompt shows
these limits. A timeout
does not establish that the server rejected the request format; `/test` checks
tool calling and structured report output using synthetic data.
On llama.cpp servers with a compatible chat template, optional config field
`enable_thinking: false` sends `chat_template_kwargs.enable_thinking=false` to
reduce generation latency. Omit it to preserve the server default; other servers
may not support this extension. Environment configuration can use
`BLUECHEESE_ENABLE_THINKING=false`. Citation and report validation still apply.

With a provider configured, ordinary chat asks approval before sending your
message and up to three previous chat exchanges to the model's task planner.
The model can answer general questions or select an allowlisted task for separate
approval; you do not need to retype a slash command. For example, “what do you
think about these alerts?” should propose an investigation, while “list alerts”
should propose an alert listing. The original investigation question enters the
bounded evidence workflow, which retrieves evidence, validates citations and
saves a report. The planner itself receives no telemetry or task results, so use
an investigation for evidence questions. Invalid task proposals execute nothing.
Slash commands bypass the planner and retain their existing approvals. Without
a provider, common task requests still route locally to offline rules.

## First walkthrough: connect, inspect, investigate

With an existing Suricata EVE file:

1. In the sidebar, expand **Sensor connection**, select **EVE file**, and enter
   the file's absolute path on the machine running Blue Cheese.
2. Click **Connect sensor**. Watch **Accepted records**, **Alerts** and
   **Quarantined records**. Existing lines load in bounded batches; new lines
   continue arriving if Suricata is writing the file.
3. Start on **Needs attention** and click **Investigate** on an alert. Use **Network** to inspect activity, or **Alerts** for detailed filtering. Filter if needed and
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
To explore the included `bad.pcap` capture instead, follow the
[PCAP conversion steps](#preserved-cli-and-legacy-web-ui); that path requires Suricata.

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

Suricata is required for PCAP conversion and live capture; importing an existing
EVE file needs no Suricata installation. On Debian/Ubuntu, install the distribution
package and check that the executable is on PATH:

```bash
sudo apt-get update
sudo apt-get install suricata
suricata --build-info
```

Package versions vary. For current stable packages and other operating systems,
follow the official [installation guide](https://docs.suricata.io/en/latest/install.html)
and [quickstart](https://docs.suricata.io/en/latest/quickstart.html), including
`suricata-update` for detection rules. The test fixture below supplies its own
rules; a real capture needs rules and network settings appropriate to your sensor.

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
| **Needs attention** | Review priority-ranked alert groups and open a named investigation. Ask about workspace state in chat. |
| **Network** | Spot activity patterns, focus on ranked endpoints/connections, and drill down to evidence. |
| **Alerts** | Filter by exact endpoint IP, signature substring and sensor severity; select an alert to inspect or investigate. |
| **Flows** | Filter by exact endpoint IP and inspect flow state, endpoints and byte counters. |
| **Investigations** | Follow a named target, ask contextual questions, inspect actual agent queries and cited findings, assign and record a decision. |
| **Settings** | Configure models, automatic investigation and queued retries. |
| **Sensor health** | Inspect source status, committed byte offset, spool path, rotation notices, quarantine reasons and continuity incidents. |

On **Network**, use **Connections**, **Activity** and **Evidence** to move from
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
record fields. It is off by default for a compact view. **Auto refresh** refreshes the
operational workspace every two seconds. Turn it off while reading or editing;
ingestion continues. Changing a filter or pressing **Refresh now** reloads the
view. **Sensor connection** collapses once evidence is available; expand it to
connect or disconnect.

## Investigate and record a decision

Start with the [alert-to-decision walkthrough](docs/WORKFLOW.md). Case chat,
connections, agent activity and decisions share an explicit investigation target.
Sensor totals are cumulative; they are available in the expandable status panel.
Refresh shows completion and whether new accepted records arrived.

### Choose scope and budget

**Investigate selected alert** on Alerts, or **Investigate this alert** in
Network, freezes a same-source endpoint neighborhood within five minutes of
that alert. On **Investigations**,
set **Case question**, choose a **Scope alert**, and click **Start investigation**.
The scope selector lists the latest 50 alerts; select older alerts from **Alerts**.
You can also choose **Whole external scope**. Each snapshot has a **10,000-record
limit**; if the whole scope exceeds it, choose an alert neighborhood.

The case question labels the case. The rule-based investigator evaluates alert/flow
evidence rather than answering arbitrary natural-language questions. Triage assigns
review priority, correlation proposes links with provenance and ambiguity, and one
bounded seed group is investigated per run.

Expand **Advanced: manual scope and investigation limits** to set **Tool calls**, **Seconds (cooperative
limit)** and **Check contradicting evidence**. The operational defaults are eight
tool calls and five seconds with rules, or a cooperative model budget derived from the configured call timeout and attempt limits.
The selected-alert shortcut uses these fixed defaults; edit budgets through the
Investigations page for a custom run. The presentation defaults are six calls and
five seconds. Retrieval is capped at 100 records and 64 KiB per call. Failed tool
attempts consume budget; records withheld by delivery limits cannot be cited.

One investigation runs at a time, while ingestion continues. **Cancel
investigation** requests cooperative cancellation: an active provider call must
return before it takes effect. Time limits are cooperative too. Restart marks
unfinished runs interrupted; saved completed reports survive.

The **Agent activity** tab follows the selected investigation. Actual query
arguments, returned records, rule outputs, model waits and errors remain tied to
its run. It refreshes every second independently of telemetry auto refresh.
Incremental activity persists for failed and interrupted runs as well as completed
reports; older runs with no recorded trace are labelled accordingly.

**Ask Blue Cheese** uses this case's frozen evidence and recorded activity. Model
explanations validate citations against bounded chat retrieval. New analysis or
source changes are explicit proposals; ordinary reading does not launch another
investigation. Without a configured model, local chat commands remain available.

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

Under **Analyst decision**, enter **Analyst**, set **Assigned to**, choose `OPEN`, `INVESTIGATING`,
`ESCALATED`, `CLOSED_BENIGN` or `CLOSED_INCIDENT`, add a **Note**, and click
**Save analyst action**. Actions persist separately from the machine report and
appear below the form. Analyst names are local attribution, not authenticated
identities. Closing a case does not release its pinned evidence for retention.

### Use the automatic queue

Open **Settings → Automatic investigation and retry queue**, enable **Investigate incoming alerts
automatically**, then click **Save automatic investigation setting**. Automatic processing is
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

Doctor reads provider settings from `BLUECHEESE_MODEL_*` and related environment
variables only. It does not load `config.json`, accept `--config`, or inspect the
GUI's selected provider. To validate a JSON provider file, launch
`./bluecheese --cli --config config.json` and use `/test` for approved live
capability checks. Doctor reporting `offline rules` does not invalidate that file.

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

No model is downloaded or required. In the operational GUI, open **Agents and
model endpoint** in the sidebar, select **Model agents**, and enter your existing
OpenAI-compatible API base URL (such as `http://127.0.0.1:8080/v1`), model name,
and optional API key. You may choose a separate Falsifier model on the same server.
Click **Apply agent settings**, then **Test agent connection**. The test sends
synthetic observations, exercises a tool-call round trip and structured report
output for each distinct model, and may incur endpoint usage. It sends no stored
telemetry. Choose **JSON object** if your server lacks strict JSON Schema support;
reports still undergo local schema and citation validation.

Settings apply to subsequent investigations without restarting and last for the
application process. Credentials entered in the GUI stay in memory; they are not
written to disk or reports. An API key environment variable is also supported.
Provider changes and connection tests are blocked during investigations. Select
**Rule-based** and apply to return to offline rules.

Alternatively, configure an existing server **before launch**:

```bash
export BLUECHEESE_MODEL_ENDPOINT=http://127.0.0.1:8080/v1/chat/completions
export BLUECHEESE_MODEL=your-served-model-id
./bluecheese
```

Set `BLUECHEESE_MODEL_API_KEY` through your environment/secret manager if needed.
The sidebar identifies the selected provider. Doctor validates configuration but
never calls the endpoint. Test a manual investigation and inspect its status,
errors and citations to check your actual server/model; the recorded CLI checks
cover one server/model. Environment changes require restarting. To return to rules on launch,
unset the provider variables before restarting:

```bash
unset BLUECHEESE_MODEL_ENDPOINT BLUECHEESE_MODEL BLUECHEESE_MODEL_API_KEY BLUECHEESE_ALLOW_REMOTE_MODEL
./bluecheese
```

Remote endpoints require `BLUECHEESE_ALLOW_REMOTE_MODEL=true` and default to HTTPS.
HTTP additionally requires `BLUECHEESE_ALLOW_INSECURE_HTTP=true`. Enabling
them sends normalized observations, including IPs and detection signatures, to
the configured endpoint; exact raw logs are omitted. The Investigator can request
bounded evidence queries; the Falsifier then challenges its candidate assessment,
can retrieve counterevidence, and returns a revised report. Both share the run's
tool/time budgets and a configurable provider-call cap (default six, split between
the two roles). The last turn of each role requires a report. Disabling
falsification disables the model critic and the fixed flow countertest.

The broker permits only `get_event`, `list_alerts`, `find_events_by_ip`, and
`search_events` within the fixed snapshot. Models cannot issue SQL, shell commands,
or change scope. Triage, correlation, scheduling and report assembly remain
deterministic. Input/output sizes, redirects and timeouts are bounded. Saved JSON
reports and the GUI audit include roles, model attempts and returned usage (unknown
usage stays unknown). Mechanical citation checks leave semantic claim validation
to review. Set `BLUECHEESE_MODEL_MODE=summary` to retain the original one-call
structured assessment adapter when launching from environment configuration.

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

The repository root also includes `bad.pcap` (about 49 MB). Its name is not a
verdict; inspect the resulting evidence. To import it into the legacy SQLite
workflow, using your installed sensor configuration and rules:

```bash
./bluecheese --data-dir capture-data import-pcap bad.pcap --config /etc/suricata/suricata.yaml
./bluecheese --data-dir capture-data alerts
```

For the operational GUI or agent terminal, first convert the capture to EVE in
a new output directory (adjust the configuration path for your installation):

```bash
mkdir -p telemetry/bad-capture
suricata -r "$PWD/bad.pcap" -c /etc/suricata/suricata.yaml -l "$PWD/telemetry/bad-capture"
./bluecheese
```

Select **EVE file** and connect the absolute path to
`telemetry/bad-capture/eve.json`. Enable EVE `alert` and `flow` outputs in the
sensor configuration. Offline `-r` processing reads packets from disk; it does
not transmit them. Use a fresh output directory for each conversion. The legacy
PCAP import stores evidence separately from the operational GUI database.

## Development checks and remaining work

Install the pinned development dependencies before running checks:

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest -q --cov=bluecheese --cov-report=term-missing
.venv/bin/python -m pip check
```

Allow at least 1 GB of free temporary space for tests; one fresh-user Linux run
used about 400 MB for DuckDB files. If `/tmp` is a small tmpfs and pytest reports
`No space left on device`, choose a temporary directory on a larger filesystem:

```bash
mkdir -p "$HOME/bluecheese-test-tmp"
TMPDIR="$HOME/bluecheese-test-tmp" .venv/bin/python -m pytest -q
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
