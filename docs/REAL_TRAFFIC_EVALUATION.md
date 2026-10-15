# Continue the real-traffic evaluation locally

Local execution results are now recorded in [REAL_TRAFFIC_RESULTS.md](REAL_TRAFFIC_RESULTS.md).
The campaign was interrupted after three rejected live runs and a fourth run whose
outcome could not be recovered. The live allowance expired; durable offline
recovery and focused fixes are documented there. The cloud handoff below is
historical, and its statement that the live allowance is unused no longer applies.

The authorized campaign plan is [the original request](evaluator/real_traffic_plan.md).
Read it and AGENTS.md before continuing. The user's explicit authorization to
download these four captures and run live models takes precedence over AGENTS.md's
default prohibition on dataset/model downloads. No model download is needed.
Use the existing local checkout, preserve user changes, and keep captures, model
configuration, operational state and evaluator answers out of Git and model inputs.

## Current handoff

The cloud checkout started at `8b1c7dff8653cab5ae9b4939193bca47208876db`
with no tracked or untracked changes. Its starting tracked diff SHA-256 was
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
No capture was downloaded, no real-traffic investigation ran, and no live model
request was made. The three-hour live allowance is unused.

The cloud has no `~/bc.json`, Suricata 8.0.7, or existing production sensor
configuration/rules. Its capture-site request returned a network-policy 403.
These cloud prerequisites do not transfer to the local machine. Inspect the local
configuration and test actual connectivity before declaring a local blocker.
The cloud environment draft added `www.malware-traffic-analysis.net`; it does not
change local networking. Cloud setup files, fixture state and credentials are
outside this repository and are not required by the changes here.

`compare_investigations` now supports `--scope connection|host`, preserving the
connection default. Host mode requires an explicit seed and exactly one EVE file.
Each result records scope, seed, effective limits and the commit/tracked-diff hash.
Successful reports export self-contained verified bundles. Failed runs retain
their saved error, provider diagnostics, activity and retrieval history in a JSON
artifact as well as their isolated state.

Cloud validation for these changes: 226 Python tests passed, two Suricata-dependent
checks skipped; Ruff and dependency consistency passed. A real CLI invocation on
the bundled synthetic EVE completed and its exported bundle verified. These are
development checks, not results for any of the four campaign captures.

This function's `baseline` and `advised` arms still mean decision advice disabled
and enabled. They are **not** a rules/LLM comparison. For this campaign, run it
once with no provider and once with `--provider ~/bc.json`, using the same EVE and
seed. Leave `--decision-profile` unset; `advised` is correctly `NOT_CONFIGURED`.

## Local setup and preflight

Run from the repository root. Python 3.11+ and a compatible Node installation are
required. Follow the README's pinned installation:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Choose a new campaign root **outside the checkout**, for example a newly created
directory under the local user's home. Record the actual starting commit, tracked
diff hash and user changes there before editing anything. Use neutral stage IDs
for inputs and state; scenario names/reference answers belong only in evaluator
notes. Freeze the application commit and diff before the held-out fourth stage.

Inspect `~/bc.json` without printing credentials or changing it. Verify it retains
six attempts, 300-second request timeout, 2,048 output tokens and thinking disabled.
`load_provider` reads that file directly. Its AgentModelProvider performs a separate
Falsifier review by default, using `falsifier_model` or the Investigator model.

Make one capability check using `load_provider(Path.home() / "bc.json")` and
`provider.test_connection()`. Record sanitized outcomes and actual elapsed time.
Capability checks count against the campaign's three-hour live allowance.
If unavailable, diagnose and make only one justified retry; then continue offline
and record live runs as blocked. Never print the config or provider profile.

Check `suricata -V` reports 8.0.7 and identify the existing config and full rules.
Verify payload/file extraction is disabled in the effective sensor configuration;
do not substitute the repository's tiny synthetic rules. Inspect downloaded
archives and extract only PCAP entries. Retain source pages/answers outside model
inputs. Use `prepare_case_study` for a fresh sensor output directory per capture:

```bash
.venv/bin/python -m bluecheese.application.prepare_case_study \
  --pcap "$CAPTURE" --out "$SENSOR_OUTPUT" \
  --config "$SENSOR_CONFIG" --rules "$SENSOR_RULES" --source-url "$SOURCE_URL"
```

Set those variables to real absolute local paths/URLs first. This command reads
packets offline; it does not replay them on a network. Supplement its provenance
manifest with archive/source-document hashes, sensor executable hash, effective
configuration/include hashes, download times and capture processing diagnostics.

## Matched comparisons

Before any investigation, import the complete static EVE into fresh selection
state using the same `runtime.command("import_file", eve, "live", "external")`
path as `run_comparison`. The import is synchronous and content-addressed.
Reimport unchanged bytes and verify counts, IDs and raw evidence remain unchanged.
Reconcile the original sensor event counts with accepted/unsupported/quarantined
counts; do not assume all sensor events are supported.

Select the first suitable internal-source alert in normal queue order through
`runtime.command("attention", "live", "external", runtime.command("snapshot"),
page=page)`. Save its ID, normalized fields and selection rationale. Browse later
pages when needed; absent suitable alerts are a coverage limitation. Importing
through the GUI's source API uses a different source identity, so its evidence IDs
must not be substituted for comparison-import IDs. Always close selection state
before opening another runtime on the same database.

Set `EVE`, `SEED_ID` and `STAGE_OUTPUT` to the chosen input and fresh output parent.
Each command creates its own new destination; never reuse an output directory:

```bash
.venv/bin/python -m bluecheese.application.compare_investigations \
  --eve "$EVE" --out "$STAGE_OUTPUT/rules-connection" \
  --scope connection --seed-id "$SEED_ID" \
  --repetitions 1 --max-calls 12 --max-seconds 1800

.venv/bin/python -m bluecheese.application.compare_investigations \
  --eve "$EVE" --out "$STAGE_OUTPUT/rules-host" \
  --scope host --seed-id "$SEED_ID" \
  --repetitions 1 --max-calls 12 --max-seconds 1800

.venv/bin/python -m bluecheese.application.compare_investigations \
  --eve "$EVE" --out "$STAGE_OUTPUT/model-host-pilot" \
  --scope host --seed-id "$SEED_ID" --provider "$HOME/bc.json" \
  --repetitions 1 --max-calls 12 --max-seconds 1800
```

Each live pilot needs its full 1,800-second cooperative allowance remaining in the
three-hour live campaign. Check config limits rather than silently overriding
them. Complete all four stage pilots before repetitions. Compare actual
`snapshot_digest` values between the rules-host and model-host baseline rows;
mismatch invalidates matching. Inspect host ±5-minute membership against full
capture times; use separate cases for longer sequences.

Bundles are verified during export and can be verified again independently:

```bash
.venv/bin/python -m bluecheese.application.report_bundle "$BUNDLE_DIRECTORY"
```

Verify all terminal reports and classify failed, cancelled and incomplete runs
separately. A verified bundle establishes integrity, not semantic acceptance.
Review every material claim against cited records and evaluator-only reference
observations; unsupported material claims prevent semantic acceptance.

## Normal GUI and deliverables

With the selected comparison state stopped, run the normal GUI against that
isolated state's absolute path, using `BLUECHEESE_STATE` and
`.venv/bin/python -m bluecheese.interfaces.server --no-browser --port 8502`.
Check findings/activity/evidence, summary, decisions, exports and restart
persistence. Selecting/refreshing/navigating must start no investigation. A new
GUI investigation is an additional run: record its actual default eight-call
budget separately from the 12-call comparison pilot and count live work against
the campaign allowance. Never launch two processes on the same state.

Create a campaign report and four-case scorecard outside tracked source, including
actual attempts/latencies, claims supported or rejected, missed-evidence layer,
contradictions, scope gaps and useful next checks. Preserve original failures
and separate retests. Add focused synthetic regressions for demonstrated defects,
then run the full Python suite; run frontend checks/browser tests when frontend
behavior changes. Keep evaluator indicators and expected verdicts out of code.

The cloud's six functional browser checks passed five and failed one existing
host-revision test: its poll accepts transient `#cases`, leading to a request for
`/cases/undefined`. The Python host-revision API check passed. This is a preserved
pre-campaign observation, not a tested real-capture result. Assess it locally
before any fix; macOS screenshot baselines need the normal local browser setup.

Suggested next Codex prompt: “Read docs/REAL_TRAFFIC_EVALUATION.md and the linked
original plan. Resume the four-stage campaign locally using ~/bc.json and the
existing Suricata 8.0.7 configuration/rules. Preserve local changes, inspect
prerequisites without exposing credentials, and complete the campaign within
the live allowance. The cloud performed no live requests or real-capture runs.”
