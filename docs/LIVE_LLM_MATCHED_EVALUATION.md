# Matched reliability evaluation — authorized and running

The user authorized **14 hours wall time, 24 investigations and at most 144 model
requests**, then explicitly requested background continuation through Codex usage
interruptions, with source review later. The current durable campaign is
`/Users/yoshi/bluecheese-evaluations/20261015-matched-0543/`; its first request was
2026-10-15 05:44:54.744780 UTC and its fixed deadline is 19:44:54.744780 UTC.
Read its live `status.json` and ledger for actual progress; source review remains
pending. The older campaign allowance remains expired. Do not send this document, evaluator
notes, source answers or scenario labels to either model.

## Freeze and preflight

Use the pre-change source snapshot and hash metadata in
`build/verification/reliability/baseline.tar.gz` and `baseline.json` as baseline;
it includes the previously uncommitted correction-guidance fix. Freeze candidate
sources only after final checks, preserving all new runtime files, SHA/diff and
untracked-source hashes. Copy both source archives, manifest and offline checks
to a new durable campaign directory under `~/bluecheese-evaluations/` after
authorization. Do not overwrite earlier campaigns. Run each revision from an
isolated source directory with the same installed requirements.lock dependencies.
Ensure imports resolve to that revision; record the source archive hash as well
as Git metadata (an extracted archive may have no .git directory).

Reuse recovered inputs from
`~/bluecheese-evaluations/20261014-cnm99sk6/stages/NN/`: `prepared/sensor/eve.json`
and `selection.json` → `selected_seed.id`. Verify the recovered immutable archive
checksums and each EVE hash. Compare every new seed, snapshot digest and actual
sorted membership with `rules-host/comparison.json`. These match recovered
snapshots, never the lost original campaign snapshots.

Read `~/bc.json` only with the existing loader. Confirm the existing model for
both roles is `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`, independent review is enabled,
300-second requests, 2,048 output tokens, thinking false and strict-schema mode.
Do not copy credentials into artifacts. Use non-model connectivity checks first.
A changed profile is a different experiment and must be resolved before requests.

A machine-readable 24-trial schedule with the verified EVE hashes, selected seeds
and expected snapshot memberships is prepared at
`build/verification/reliability/pending-live-campaign.json`. Its status is
`AUTHORIZATION_PENDING`; source revisions and deadline are frozen at execution.

## Fixed schedule and bounds

Execute three repetitions, each visiting stages 01, 02, 03, 04 in order. For each
stage/repetition run both revisions consecutively. Repetitions 1 and 3 order
baseline then candidate; repetition 2 orders candidate then baseline. This is
12 matched pairs / 24 investigations, each using a fresh output/state directory.
Do not change code, replace failed trials, select new seeds or add optional retests
mid-campaign. A subsequent fix starts a separately documented experiment.

Each invocation uses the existing comparison CLI with `--repetitions 1`,
`--scope host`, archived `--seed-id`, `--model-attempts 6`, `--max-calls 12`,
`--max-seconds 1800`, and the existing `--provider` profile. Do not configure
`--decision-profile`: the CLI's internal `baseline` arm means unadvised, regardless
of which source revision is running; its `advised` arm is NOT_CONFIGURED.
Label the outer revision separately to avoid confusing those names.
Candidate invocations also enable `--retain-rejected-output`; the frozen baseline
lacks that option. Record this diagnostic difference and retention overhead.

Before the first request, persist UTC start/deadline, complete schedule, safe
settings and revision/input hashes. Count every actual model request including
probes, errors and corrections toward 144. Run serially, one owner per state DB.
Before each new trial require at least 2,100 seconds until the campaign deadline
(1,800 cooperative allowance plus 300 margin). Stop starting trials if either
campaign allowance is exhausted; preserve all partial outcomes. An insufficient
allowance yields an incomplete campaign, not permission to exceed limits.

Save stdout/stderr, exit code, comparison artifacts, diagnostics and successful
verified bundles per trial. Failed trials remain in the denominator. Stop each
CLI before opening its state through the normal GUI. GUI chat/probes count toward
the same allowance; do not add them without remaining call capacity.

## Review and release gates

Review all completed reports against their cited source records. Record supported
observations, qualified inferences, retained contradictions, useful disconfirmation,
byte direction/coverage, UTC conversion, telemetry omissions, and unsupported
execution/compromise/theft claims. Missing or unreviewed values remain unknown.
Analyst review is separate from schema/citation/fact validation and desired verdict.

Report mechanical and semantic acceptance independently, plus schema/fact/citation/
parser failures, actual Falsifier execution/completion, calls, corrections, denied
exploration, context omissions, per-role request/local-processing time, and total
elapsed time. Compare individual complex cases for skipped checks or ceiling hits.
Keep raw timings for successes and failures separate. Compare paired latency only
where both revisions pass semantic review, publishing that subset's size. Do not
assign failed trials an invented 1,800-second elapsed time or optimize latency by
excluding their failure rates.

Promote only if at least 10/12 candidate investigations complete and pass semantic
review, at least two per seed, supported completions do not decline versus baseline,
and integrity checks pass. Call-allocation regressions or lost material
counterevidence block promotion. If fewer than 24 trials complete the schedule,
report results provisionally without claiming the gate was passed. Faster reports
are beneficial only with preserved support and thoroughness; investigate deadline
regressions individually. Do not infer statistical significance from this sample.

After quality review, inspect accepted/failed cases and exports in the normal GUI;
reading/refresh must start no new work. Preserve Open analyst disposition unless an
analyst explicitly decides otherwise. Save final scorecards, review notes and
checksums of immutable artifacts; update SESSION_STATUS with measured outcomes.

## Sanitized provider parser diagnostic

Prepare this packet for operator review; sending it is a separate explicit action.
In the previous stage-04 trial, Investigator's schema correction succeeded after
four calls. The Falsifier's sixth/global final request failed with the allowlisted
native output-parser HTTP 500 after approximately 211.987 seconds; the run failed
at 707.060 seconds. Model/settings are listed above. The allowlisted message is:
`The model produced output that does not match the expected peg-native format`.

Attach only safe role/attempt timings, response mode, schema hash, model/template
identifiers if available, and the exact allowlisted diagnostic. Never include
credentials, raw error bodies, evaluator answers or full telemetry by default.
Strict-schema/tool-to-final compatibility remains a provider boundary. No broad
HTTP retry, backend switch or automatic JSON-object fallback is part of this
campaign. Any response-mode A/B test needs its own matched schedule and allowance.
