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
See the [README verification record](docs/README_VERIFICATION.md),
[analyst workflow verification](docs/ANALYST_WORKFLOW_VERIFICATION.md),
[current verification scope](docs/TESTING.md) and
[release gates](docs/RELEASE_GATES.md).

Quick links: [install](#install-and-open-the-console) ·
[agent terminal](#interactive-agent-terminal) ·
[connect telemetry](#connect-telemetry) ·
[investigate](#investigate-and-record-a-decision) ·
[backup and maintenance](#check-back-up-and-maintain-state) ·
[troubleshooting](#troubleshooting) ·
[walkthrough](#first-walkthrough-connect-inspect-investigate).

## Install and open the console

Run these commands **from the repository root**, where this README and the
`bluecheese` launcher live. Use Python **3.11 or newer**; check with
`python3 --version`. If necessary, substitute an installed newer interpreter,
such as `python3.13`, in the first command. On this verified macOS installation,
`python3` is 3.9 while `python3.13` is supported. Installing dependencies needs
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
is busy, the launcher selects the next available port through 8600. Leave the terminal running and
stop the app with **Ctrl+C**. Closing the browser tab does not stop the app.

`./blue-cheese` is a compatibility wrapper for `./bluecheese`; both accept the
same arguments and launch the same application.

The console initially has no telemetry. Connect an existing EVE file or configure
Suricata separately for live output. The [walkthrough below](#first-walkthrough-connect-inspect-investigate)
uses the ordinary interface with an example file.

Light and dark themes follow your system preference initially. Change the theme
in **Settings → Appearance** or use the theme button in the header. The checkout
includes compiled frontend assets; Node is needed only when changing the frontend.

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
explanations remain read-only. With a configured model, GUI chat answers reading
questions conversationally; explicit CLI reading commands also work offline.
Neither starts an investigation. Existing slash inspection commands
retain structured output and approvals. See the [walkthrough](#first-walkthrough-connect-inspect-investigate).

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
| `/summary [RUN_ID]` / `/explain TERM` | Summarize the current context or explain a term without launching work |
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
  "endpoint": "http://model-server.example:8080/",
  "model": "your-served-model-id",
  "allow_remote": true,
  "allow_insecure_http": true
}
```

This base URL resolves to `/v1/chat/completions`; the server must implement the
OpenAI-compatible Chat Completions API. Reload with `/config /absolute/path/config.json` after
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

With a provider configured, ordinary terminal chat asks approval before sending
your message, up to three previous chat exchanges, and the last displayed command
result (bounded to 8 KiB) to the model's task planner. The model can answer from
that context or select an allowlisted task for separate approval; you do not need
to retype a slash command. Ask explicitly to “investigate whether this alert is
supported by the flows” to request new analysis. Summaries and explanations of
existing findings do not launch an investigation. The original investigation
question enters the bounded evidence workflow, which retrieves evidence,
validates citations and saves a report. GUI chat receives scoped workspace/case
context and presents actions for **Run proposed action**. Invalid task proposals
execute nothing. Slash commands bypass the planner and retain their existing
approvals. Without a provider, common task requests route locally to offline rules.

## First walkthrough: connect, inspect, investigate

Launch an isolated workspace using the same command used for normal operation:

```bash
# Print the absolute fixture path to paste into Settings.
.venv/bin/python -c "from pathlib import Path; print(Path('tests/fixtures/sample_eve.json').resolve())"
./bluecheese --data-dir walkthrough-state gui
```

1. Open **Settings → Evidence source**. Choose **EVE file**, enter the absolute
   path to `tests/fixtures/sample_eve.json`, and click **Import once**.
2. Open **Alerts**. Select the TeamViewer detection, review the endpoints and
   scope, and click **Investigate**.
3. In the case, review **Findings**. Open a citation to inspect **Raw**, **Parsed**,
   and **Normalized** evidence. Sensor detection does not establish compromise.
4. Open **Evidence**. Select a timeline bin or connection to filter the records.
   Open **Activity** to inspect the recorded agent operations.
5. Open **Ask Blue Cheese** and ask “Summarize this case”. Any proposed action
   requires **Run proposed action** before execution.
6. Under **Decision**, enter analyst attribution, assignment, disposition, and
   notes, then click **Save decision**.
7. Download **JSON** or **Markdown** from Findings. Use **New revision** to analyze
   again with a new frozen snapshot. Earlier reports remain available in history.
8. Stop with Ctrl+C, launch the same state directory, and reopen the case.

This example uses saved synthetic telemetry. It measures workflow behavior, not
model accuracy or detection quality. For another demonstration, substitute your
own EVE file and follow these same steps.

## Connect telemetry

Under **Settings → Evidence source**, select an EVE file or Unix stream. Paths
refer to the machine running Blue Cheese. **Import once** reads a completed EVE
file up to 16 MiB. **Connect** follows a file in bounded batches, including files
larger than that limit. **Disconnect** stops reception while retaining evidence.

For file sources, optionally enable **Recover matching rotated files**. Truncation
or an unresolved source gap stops ingestion and records a source incident. Inspect
**Settings → Source diagnostics** for quarantine and incidents. Unsupported event
types and malformed records are quarantined; accepted raw text remains exact.

For a Unix stream, choose an unused short socket path in an existing directory
and click **Connect**. Configure Suricata's EVE output using that path:

```yaml
outputs:
  - eve-log:
      enabled: yes
      filetype: unix_stream
      filename: /absolute/path/eve.sock
      types: [alert, flow, dns, http, tls]
```

Blue Cheese listens; Suricata connects. This is EVE transport, not a sensor control
socket. Keep the sensor's existing capture and rule configuration. The socket is
owner-only and requires the same filesystem namespace. Existing socket paths are
never overwritten. Received bytes are spooled before parsing, with a 256 MiB limit
per socket path. Disconnects and unfinished records require explicit recovery;
transport does not guarantee end-to-end delivery.

Suricata performs capture and detection separately. To convert an existing PCAP,
use the preserved CLI import or the [offline capture preparation commands](#prepare-a-capture-and-compare-investigations).
Connect the resulting EVE file in Settings.

## Explore the workspace

**Alerts** presents priority-ranked, paginated review groups. Counts describe the
visible 20-alert page. Filters apply to that page; older alerts remain accessible.
Selecting an alert opens details and its investigation or existing case.

**Cases** holds saved investigations and analyst decisions. Each case freezes a
named target and evidence snapshot. The selected alert's source and directed
endpoint pair within ±5 minutes define its scope. New arrivals do not change saved
findings. **New revision** creates a successor with a new snapshot.

**Network** links an activity timeline, directed connections, protocols, and a
record table. Choose a 250/1,000/5,000-record window and endpoint, then select a bin
or connection. Visual filters do not change investigation membership. Connection
diagrams show at most 12 directed pairs; case records are capped at 1,000.

**Refresh view** reloads displayed data without starting work. Activity and chat
update independently while the case's reading state remains stable.

## Investigate and record a decision

Click **Investigate** in an alert's details. Triage and correlation use rules;
Investigator and Falsifier use the configured engine. Activity shows actual
operations and elapsed time. Cancellation is cooperative: an active provider
request must return before the run can stop.

Review source observations, assessed findings, citations, alternative explanations,
unknowns, and next checks. Retrieval validation checks citation provenance; it
cannot establish whether a claim follows from its evidence. Host processes,
identities, asset inventory, and approved scanning schedules are not connected.

Analyst decisions persist separately from machine reports. Attribution is local,
not an authenticated identity. Assignment and disposition appear in the case
header and Cases list. Decision history and older run revisions remain readable.

Enable automatic investigations under **Settings → Automatic investigations**.
This setting resets to disabled on restart. Failed queue items can be retried
explicitly. Normal browsing, refreshes, and chat answers do not schedule analysis.

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
or cursors; review Settings → Source diagnostics and source availability before reconnecting.
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

## Investigation findings and optional decision advice

Version-2 findings separate activity assessment, observed impact, evidence limits
and case-specific next checks. Review **Observed protocol activity** before the
**Working hypothesis** (labelled **UNVERIFIED**) and assessed findings. HTTP methods, paths,
response statuses and response lengths come from retrieved source records;
response length does not establish upload size. Citations establish retrieval
provenance, so review whether each interpretation follows from its evidence.
Next checks are recommendations requiring analyst action.

Under **Settings → Decision advice**,
select **Model endpoint**, configure an existing native `/v1/systemone` endpoint
and model, then click **Apply**. Advice is disabled by default. **Test connection**
makes one synthetic request. Applying settings or
refreshing does not call the endpoint. Settings last for this process.

An enabled investigation makes at most one advice request using scoped retrieved
evidence. Scores are uncalibrated and do not change alert order, suppress alerts
or authorize actions. A chat endpoint alone does not establish native decision
support; live validation awaits a compatible decision model.

### Prepare a capture and compare investigations

Use installed Suricata, an explicit configuration and rules file, and **new output
directories**. This processes packets offline without transmitting them:

```bash
.venv/bin/python -m bluecheese.application.prepare_case_study \
  --pcap bad.pcap --config /path/to/suricata.yaml \
  --rules /path/to/suricata.rules --out capture-study
```

On Homebrew installations, the configuration is commonly
`/opt/homebrew/etc/suricata/suricata.yaml` and rules are commonly
`/opt/homebrew/var/lib/suricata/rules/suricata.rules`; check your installation.
The output includes `capture-manifest.json`, sensor diagnostics and
`capture-study/sensor/eve.json`. Connect that EVE file in the GUI.

For a quick offline check using the bundled synthetic EVE:

```bash
.venv/bin/python -m bluecheese.application.compare_investigations \
  --eve tests/fixtures/sample_eve.json --out offline-comparison \
  --repetitions 3 --max-calls 12
```

For actual model investigations, replace `--eve` with the prepared EVE path and
add `--provider /absolute/path/config.json`. Add `--decision-profile decision.json`
only for a configured native decision endpoint. Without it, advised arms are
recorded as `NOT_CONFIGURED`; the command does not establish an advice comparison.
Each case uses isolated state, matching snapshot digests and alternating arm order.
Reports and `comparison.json`/`comparison.md` record outcomes, calls and timings.
Human review fields remain unmeasured until completed by an analyst. Model runs
can take several minutes each; cancellation is cooperative. Failed or incomplete
runs write their index before returning a nonzero status. Existing output
directories are refused.

See [assessment configuration and comparison details](docs/INVESTIGATION_ASSESSMENTS.md)
for the decision-profile format, seed selection and validation boundaries. Three
recorded real-capture model runs completed, but generated prose contained
attribution errors and took 472–648 seconds per run. This is case-specific
validation, not detection accuracy or commercial readiness. Shared team hosting
remains separate release work.

## Reading findings and asking questions

Case details separate **Open questions** about the selected evidence from actual
**Analysis limits** such as truncated retrieval or a failed check. Shared definitions
and standard limitations are available under **How to interpret findings**, rather
than repeated in each case.

Chat presents answers as paragraphs and lists, with separate evidence citations.
“Summarize this case” uses the case snapshot even after inspecting an individual
record. Questions about a selected record retain that selection. Reading questions
cannot launch work; requested actions remain explicit proposals. If a model answer
fails validation or the provider is unavailable, the application labels the error
and can show a read-only saved-evidence fallback.

For slow inference, use a **300-second request timeout** in Settings. The setting
is process-local; preserve it in your terminal configuration when using the CLI.
An active request may take the full timeout to return after cancellation. Failed
runs retain request timing, usage when supplied, and validation diagnostics under
Activity/audit. A returned response still needs structure, citation and factual
review; successful execution does not establish accuracy.

## Optional model provider

No model is downloaded or required. In the operational GUI, open **Settings → Investigation engine**, select **Model endpoint**, and enter your existing
OpenAI-compatible API base URL (such as `http://127.0.0.1:8080/v1`), model name,
and optional API key. You may choose a separate Falsifier model on the same server.
Click **Apply**, then **Test connection**. The test sends
synthetic observations, exercises a tool-call round trip and structured report
output for each distinct model, and may incur endpoint usage. It sends no stored
telemetry. Choose **JSON object** if your server lacks strict JSON Schema support;
reports still undergo local schema and citation validation.

Settings apply to subsequent investigations without restarting and last for the
application process. Credentials entered in the GUI stay in memory; they are not
written to disk or reports. An API key environment variable is also supported.
Provider changes and connection tests are blocked during investigations. Select
**Rules** and apply to return to offline rules.

Alternatively, configure an existing server **before launch**:

```bash
export BLUECHEESE_MODEL_ENDPOINT=http://127.0.0.1:8080/v1/chat/completions
export BLUECHEESE_MODEL=your-served-model-id
./bluecheese
```

Set `BLUECHEESE_MODEL_API_KEY` through your environment/secret manager if needed.
Settings identifies the selected engine. Doctor validates configuration but
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
them sends normalized observations, including IPs, detection signatures, DNS
names, HTTP paths and TLS names, to the configured endpoint; exact raw logs are omitted. The Investigator can request
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
| Stream disconnect, partial prior record or spool quota | Inspect Settings → Source diagnostics. Reconnect explicitly after a clean disconnect; use a new socket path/state when warned about partial records, or a new archived state after quota. |
| Quarantined records increase | Inspect reasons in Settings → Source diagnostics. Unsupported event types and malformed/oversized records are quarantined rather than accepted. |
| Ingestion stops after rotation/truncation | Inspect rotation notices and persisted incidents. Restore required archives if available; unsupported gaps require an explicit new source/state. Saved evidence remains available. |
| State is locked | Stop the other app/export/maintenance process using that state, or choose another state directory. Deleting the lock file is not a recovery procedure. |
| Investigation cannot start | Wait for or cancel the active run. For whole scopes over 10,000 records, select an alert neighborhood. Inspect failed-run errors or budget warnings. |
| A report does not include newer telemetry | Its snapshot is intentionally frozen. Create a successor or start a new investigation. |
| Automatic work is not running | Connect ingestion, enable the automatic investigation switch in Settings. After restart it is off; failed/interrupted work requires explicit requeue. |
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
`/telemetry/eve.json` under Settings. Files/directories must be readable/traversable
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

## Offline evaluation bundles

The offline evaluator runs bundled fixtures separately from operational state.
With any application using the selected state directory stopped:

```bash
.venv/bin/python -m bluecheese.application.export_demo --state evaluation-state --out evaluation-bundles --bundles
.venv/bin/python -m bluecheese.application.report_bundle evaluation-bundles/suspicious-poisoned.bundle
```

This generates synthetic evaluation reports, not exports of operational cases.
Bundles contain reports, snapshots, tool traces, referenced evidence, and hashes.
Verification checks integrity and retrieval scope, not semantic correctness.
Use case downloads for operational reports and backups for the whole database.

## CLI imports and SQLite evidence

PCAP/EVE import, SQLite evidence, triage, and report commands remain available.
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
```

For PCAP import, install Suricata on
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
`telemetry/bad-capture/eve.json`. Enable EVE `alert`, `flow`, `dns`, `http` and
`tls` outputs in the sensor configuration. Offline `-r` processing reads packets from disk; it does
not transmit them. Use a fresh output directory for each conversion. The legacy
PCAP import stores evidence separately from the operational GUI database.

## Development checks and remaining work

See [verification scope](docs/TESTING.md) for current checks. Earlier execution
records remain in [session status](docs/SESSION_STATUS.md).

Install the pinned development dependencies before running checks:

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest -q --cov=bluecheese --cov-report=term-missing
.venv/bin/python -m pip check
cd frontend
npm ci
npm run build
npx playwright install chromium
npm test
cd ..
```

For frontend development, start the backend on its explicit development port:

```bash
.venv/bin/python -m bluecheese.interfaces.server --port 8501 --no-browser
```

In another terminal, run `npm run dev` from `frontend/`. Vite proxies `/api` to
that backend. Run `npm run build` after changes to update the packaged interface.

Allow at least 1 GB of free temporary space for tests; one fresh-user Linux run
used about 400 MB for DuckDB files. If `/tmp` is a small tmpfs and pytest reports
`No space left on device`, choose a temporary directory on a larger filesystem:

```bash
mkdir -p "$HOME/bluecheese-test-tmp"
TMPDIR="$HOME/bluecheese-test-tmp" .venv/bin/python -m pytest -q
```

Tests use temporary state, offline fixtures and deterministic polling, with no
real models/API keys. Local Suricata integration runs when available; otherwise
it skips. Unix socket tests need permission to bind local sockets. The current
macOS/Python 3.13 verification passed 210 Python tests
and 17 Chromium browser tests, including local Suricata PCAP/stream integration
and the alert-to-decision journey. See the
[analyst workflow verification](docs/ANALYST_WORKFLOW_VERIFICATION.md) for current checks and live-provider limits. The earlier [README verification record](docs/README_VERIFICATION.md) records the walkthrough scope. Earlier native Linux/Python 3.14.7
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
