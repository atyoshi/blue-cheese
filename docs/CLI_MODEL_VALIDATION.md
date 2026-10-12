# CLI model validation — 2026-10-12

Live tests use the user's configured OpenAI-compatible llama.cpp endpoint and
`unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`. This is one deployment's compatibility check,
not a detection-quality evaluation. Automated regression tests remain offline.
Live runs use isolated temporary databases, synthetic fixtures or an offline
backup/restore copy of operational evidence. Test runs do not enter operational
investigation history. API keys and private reasoning are not logged.

## Findings and changes

- The original config allowed 20 seconds per call. A synthetic structured-report
  capability probe took 27.42 seconds; forced tool calling took 7.73 seconds.
  Both passed with a longer allowance. The server understands these API formats.
- A full synthetic investigation's first two evidence-tool requests took 105.26
  and 28.57 seconds. Its report request still timed out at 120 seconds.
- Disabling thinking through the server's compatible chat template produced
  valid tool calls on copied operational evidence in 22.73 and 5.03 seconds,
  but report generation still timed out at 120 seconds. Disabling thinking alone
  is therefore not a demonstrated complete fix.
- Transport errors now distinguish timeout, HTTP status and connection failure,
  without exposing server response bodies or credentials. Cancellation requested
  during a failing transport is preserved as CANCELLED rather than FAILED.
- CLI investigation time allowance scales with configured call timeout and
  maximum attempts, with a 60-second minimum. Approval displays both limits.
  Per-call timeout remains finite and is configurable up to 600 seconds.
- Optional `enable_thinking` config/environment setting controls the llama.cpp
  chat-template extension; omission preserves server behavior. It does not change
  scope, tool permissions or citation validation. Other servers may not support it.
- Model report instructions now ask for at most four short claims, directly
  relevant citations, explicit unreviewed scope and preserved counterevidence.
- With a 300-second allowance and thinking disabled, an operational-copy
  Investigator report completed in 121.79 seconds and passed citation/schema
  validation. The subsequent LLM Falsifier requested a seventh evidence retrieval
  against the shared six-call cap, correctly producing an INCOMPLETE run.
  The provider now switches to a structured final assessment as soon as the
  retrieval budget is exhausted, while preserving the same cap. An endpoint that
  still requests tools on that turn cannot execute them.
- After that change, the live copied-evidence investigation completed in 334.5
  seconds: five model requests, six evidence-tool calls, Investigator and LLM
  Falsifier schema/citation validation passed, final verdict UNCERTAIN. The
  Investigator report took 149.03 seconds and Falsifier report 146.24 seconds.
  A completed workflow does not establish detection accuracy or exhaustive review.
- The user's config was updated to `timeout: 300`, `enable_thinking: false`, with
  other fields retained and an owner-only original backup under the diagnostic
  temporary directory. The successful report is also exported there as JSON/MD.

## Prompt checks

With a 120-second call timeout, the live planner correctly selected:

| Prompt | Selected task / measured result |
| --- | --- |
| Hello. What can you help me do? | General answer, no evidence task |
| List the current alerts. | Alerts; actual scoped records displayed |
| What do you think about these alerts? | Investigation; original question preserved; full run hit report timeout |
| Show my saved investigations. | History; actual saved test runs displayed |
| Show the latest saved report. | Report; retrieved the saved failed run and its trace |
| Where are the current alerts coming from? Is ingestion running? | Status; actual current-session status displayed |

Additional planner-only checks selected investigation for an IP-focused question,
benign-explanation/counterevidence question and compromise/missing-evidence
question, and network for connection statistics. A repeated source/ingestion
question after these exchanges selected alerts instead of status; the planner
instructions were clarified to explicitly distinguish this intent. Planner-only
checks do not execute additional investigations or establish answer quality.
The first retest corrected source/status routing but selected investigation for
a descriptive connection summary. Instructions were further clarified to send
connection/statistics summaries to network and risk/significance questions to
investigation. Retests use the updated config through the actual transport
extension, rather than a diagnostic payload override.
The final five-prompt live retest selected investigate, investigate, investigate,
network and status respectively, matching each expected task type. Together with
the six executed session prompts above, this covers all ten distinct suggested
natural-language prompts; the three specialized security questions were tested
for routing rather than running three additional investigations.

Final regression suite: `.venv/bin/pytest -q` — 118 passed in 10.26 seconds
outside the sandbox for existing Unix socket tests. Ruff and diff whitespace
checks passed. Changes remain in the working tree.

Declined requests, invalid proposals, terminal escaping, cancellation and
retrieval/citation enforcement also have deterministic offline regression tests.

## Remaining limits

The planner receives bounded chat history, not previous evidence results. An
investigation starts with up to 20 alerts and one prioritized seed group; it is
not an exhaustive analysis of every alert in the database. Mechanical citation
validation checks retrieval authority, not semantic truth. Triage, correlation
and orchestration remain deterministic; Investigator and the model-review stage
of Falsifier use LLM tool loops. Source management and decision-model evaluation
are recorded as deferred work in ROADMAP.md.
