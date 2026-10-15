# Next-agent handoff: progressive live LLM reruns

Prepared 2026-10-14. This is a plan, not an executed rerun. Read AGENTS.md,
docs/SESSION_STATUS.md and docs/REAL_TRAFFIC_RESULTS.md first.

## Starting state

The platform fixes are ready for main: DuckDB 1.5.6 pinned in native/Docker
requirements; comparison metadata includes its version; provider instructions
require each fact's observation in that same claim's citations. Validation is
unchanged. Regressions cover large-host commit/retrieval/restart/export/raw
preservation and rejecting a fact cited only under another claim.

Recorded validation: 230 Python and 18 Chromium tests passed; final two focused
regressions passed after explicitly disabling inherited providers in the storage
test. Ruff, pip consistency and whitespace checks passed. No live retest has
validated the prompt change. The exact underlying DuckDB defect is unproven.

The original three-hour live allowance expired. Three original trials failed
(citation ownership, invented Falsifier citation, native provider parser HTTP 500);
the fourth outcome is unknown after temporary artifacts disappeared. Original
live databases/request diagnostics are unavailable. Do not relabel these outcomes.

Durable local archive (outside Git):
`/Users/yoshi/bluecheese-evaluations/20261014-cnm99sk6`

It contains matching recovered PCAPs, regenerated EVE, selection IDs, eight offline
comparisons, 13 verified bundles, saved GUI cases, backup, source reviews and logs.
These recovered snapshots differ from the lost live snapshots. New live trials
can match the recovered rules-host runs, never the lost original trials. Another
computer needs this archive transferred before proceeding; Git alone lacks it.
No new capture downloads, ingestion repair, Suricata processing or model downloads
are needed. New isolated comparison states still import the existing EVE.

## Authorization and bounds

Do not run live requests merely from reading this file. The user-facing prompt
below authorizes a fresh maximum three-hour wall-clock campaign when submitted.
Record UTC start/deadline durably before the first provider request. Count probes,
corrections, retests and interruptions against that allowance. No reset on resume.
Run serially, no subagents, one owning process per state database. Check deadline
before every new trial; reserve at least 1,800 seconds plus one 300-second request
margin. The runtime budget is cooperative, so do not describe it as hard preemption.
At deadline, interrupt/record unfinished work and retain partial diagnostics.
Complete four pilots before optional repetitions. Do not silently expand scope,
model budgets, time allowance or change model/backend to force success.

## Procedure

1. Start on clean main with the committed fixes. Record Git SHA/diff, dependency
   versions, safe provider settings and UTC budget in a new durable sibling
   campaign directory (never /tmp). Do not overwrite the recovered campaign or
   its checksums. Verify archived `artifact-checksums.json` entries against bytes;
   mutable preview-server log is deliberately excluded. Preserve credentials:
   load `~/bc.json` through the existing loader; never print/copy its secrets.
   Confirm configured Investigator/Falsifier remains
   `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`, timeout 300 seconds, 2,048 output tokens,
   thinking false, six total attempts and independent Falsifier enabled. If the
   profile changed, document that and resolve the intended comparison before calls.
   Check connectivity without an uncounted model probe; any actual probe counts.
2. Progress stages 01, 02, 03, 04 in order. Use each archived
   `stages/NN/prepared/sensor/eve.json` and
   `stages/NN/selection.json` → `selected_seed.id` verbatim. Use host scope,
   12 retrieval calls, 1,800 cooperative seconds and one repetition. No decision
   advice. No selection based on source answers, indicators or desired verdict.
   Selection IDs are comparison-import IDs; GUI IDs cannot substitute.
3. Run the existing CLI into a fresh per-stage destination. It persists run
   history/failure diagnostics and exports/verifies successful bundles. A failed
   CLI exit is an observed trial outcome, not a reason to discard artifacts or
   terminate the entire four-stage plan. Save stdout/stderr and exit code per
   trial, then inspect comparison.json and run history before continuing.
4. Compare each live baseline snapshot_digest, seed, EVE SHA and membership with
   archived `stages/NN/rules-host/comparison.json`. A mismatch invalidates matching;
   investigate before comparison or explicitly label a new experiment. The
   advised arm should be NOT_CONFIGURED and does not represent another live run.
5. For every completed report, verify bundle integrity and manually compare
   factual/prose assertions against the actual cited retrieved records. Review
   direction, method/path/status, response bytes vs request contents, UTC times,
   observed activity vs endpoint execution/theft, counterevidence, retrieval and
   time-window limits. Mechanical validation alone is not semantic acceptance.
   Keep source titles/reference answers/evaluator manifests outside model inputs.
6. After pilots, use remaining authorized time for one demonstrated defect fix
   with an offline regression and a same-recovered-seed retest, or a repetition
   if no fix is warranted. Preserve first failure and record before/after code
   revisions/settings. Do not weaken citations, fabricate evidence, auto-repair
   unseen citations, or add broad retries to hide provider errors. Treat native
   HTTP 500 as a provider compatibility failure unless evidence shows otherwise.
7. Review accepted/failed cases in the normal `bluecheese gui` using new campaign
   state, never sharing a DB with a running CLI. Confirm real operations, cited
   findings, limits, analyst decision and export. Reading/refresh must start zero
   work. Any LLM chat request counts against campaign time; do not assume the
   existing preview server uses the live profile (it was configured for Rules).
8. Save a new results/scorecard JSON and Markdown report with per-stage status,
   model attempts/latency, schema/citation/parser failures, actual Falsifier
   execution, snapshot matching, bundle checks and manual review. Retain partial
   failures and unknowns; checksum completed immutable artifacts. Update
   SESSION_STATUS.md and REAL_TRAFFIC_RESULTS.md with links, revisions and next
   steps, preserving historical results. Report tests actually run for any new
   code. Human time saved/detection accuracy/commercial readiness remain unmeasured.

### Single-stage command template

Set `CAMPAIGN` to the new durable directory and `STAGE` to 01 through 04.
Create the campaign parent first; the command creates a NEW live-stage directory.
Run separately per stage with deadline/review checks between stages, not a blind loop.

```bash
ARCHIVE=/Users/yoshi/bluecheese-evaluations/20261014-cnm99sk6
EVE="$ARCHIVE/stages/$STAGE/prepared/sensor/eve.json"
SEED_ID=$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["selected_seed"]["id"])' "$ARCHIVE/stages/$STAGE/selection.json")
.venv/bin/python -m bluecheese.application.compare_investigations \
  --eve "$EVE" --out "$CAMPAIGN/live-$STAGE" \
  --scope host --seed-id "$SEED_ID" --provider "$HOME/bc.json" \
  --model-attempts 6 --repetitions 1 --max-calls 12 --max-seconds 1800 \
  > "$CAMPAIGN/live-$STAGE.log" 2>&1
```

Do not print the provider JSON. Capture the exit code immediately, including a
nonzero code, and inspect the durable artifacts. Do not rerun into the same output.

## Known interpretation limits

Stage 01 recovered host scope: 311 records; 02: 885; 03: 5,405; 04: 449.
Five-minute host windows cannot prove the entire infection chain. Unsupported
SMB/Kerberos/DHCP identity telemetry is absent from normalized provider inputs.
Stage 04's published C2 `195.64.128.106` has no matching packets in the verified
capture/EVE: reference discrepancy, not a missed detection. Its HTTP executable
GET/status/response bytes do not establish execution. Evaluator information in
this handoff must never be passed to the provider.

## Prompt to give the next agent

> Continue from main. Read AGENTS.md, docs/SESSION_STATUS.md,
> docs/REAL_TRAFFIC_RESULTS.md and docs/LIVE_LLM_RERUN_HANDOFF.md. Execute the
> handoff's four progressive live LLM host investigations using the durable
> recovered EVE/seeds and my existing ~/bc.json profile. I authorize a fresh
> maximum three-hour wall-clock live campaign, including probes and retests;
> record its start/deadline and stop when it expires. Use serial trials, six
> model attempts, 300-second requests, 2,048 output tokens, thinking off,
> independent Falsifier, 12 retrieval calls and 1,800 cooperative seconds per
> investigation, with decision advice disabled. Preserve strict validation.
> Reuse evidence, save all new artifacts outside /tmp in a fresh durable
> directory, and retain failures. Complete all four pilots before optional
> repetitions; fix demonstrated platform defects with offline regressions and
> retest within the remaining allowance. Verify matching against recovered
> rules-host snapshots, bundle integrity and semantic support, then review the
> normal GUI workflow. Keep reference answers out of model inputs. Update the
> project results/session logs with actual outcomes, limitations and artifact
> paths. Do not treat these as continuations of the lost original snapshots.
