# Investigation assessments and decision-model advice

Blue Cheese supports a local analyst workflow: review an alert, investigate a
frozen evidence snapshot, inspect cited findings, and record a separate analyst
decision. One runtime owns each state directory. Shared team hosting and
authenticated analyst identities remain separate release work.

## Findings

Version-2 reports distinguish the assessment of activity from observed impact,
evidence completeness and execution status. Malicious activity may be supported
while successful endpoint compromise remains unknown. Each model finding records
whether it is an observation or inference, its citations, contradictory evidence
and limitations. These are model assessments requiring review; citation checks
establish retrieval provenance, not semantic truth.

The model supplies one activity decision; software derives the legacy verdict
from that field. Compact model outputs allow up to two findings and two next
checks. This avoids contradictory duplicate assessments and bounds report size.

A table of protocol fields from retrieved source records precedes the unverified
working hypothesis and assessed findings. Its HTTP method, path, response status
and response length are assembled by software, independently of model prose. New
reports persist up to 20 rows; historical views read matching retrieved records
from the saved snapshot without rewriting the report. Source facts and generated
interpretations remain distinct in the interface.

Recommended checks describe a case-specific action, its purpose and the required
source. They are text for analyst review and do not execute commands. Saved
version-1 reports remain readable; missing structured fields are explicitly
unavailable. The legacy one-call provider retains its version-1 report contract.

Alert/flow interpretations retain their original shape. New DNS, HTTP and TLS
records carry bounded protocol context, including query names, HTTP paths/methods
and TLS names. Bodies and arbitrary protocol fields are omitted from model input;
exact accepted raw records remain available in evidence inspection. Truncated
protocol strings are labelled. Unsupported EVE types remain quarantined.

Before model delivery, HTTP `length` is exposed as `response_length_bytes`, based
on the [Suricata 8.0.7 response-length implementation](https://github.com/OISF/suricata/blob/suricata-8.0.7/src/output-json-http.c#L287-L288).
It does not establish request-upload size or payload contents. This model-input
projection preserves stored interpretations and existing bundle verification.

## Host context in the application

The normal alert drawer offers **Investigate source host**, alongside the existing
connection review. This freezes a separate, same-source/sensor, five-minute host
snapshot across destinations; existing cases and their revisions preserve their
original scope. The API accepts `investigation_scope: "host"` with a selected
alert. Migration 9 records scope, defaulting historical runs to `connection`.

The `find_host_context` tool filters by authorized snapshot membership, source,
sensor, host and time before applying its limit. A classification-independent
ranking balances protocol types and distinct endpoint/method/path/query contexts.
Host observations remain separate from exact-flow correlation and are prioritized
in bounded model context. They also reach reporting, evidence export and contextual
chat through the normal runtime. No sample-specific classification rule or demo
route is involved.

A retrieved fact conflict rejects the candidate and records `SOURCE_FACT_ERROR`.
At most one correction per model stage supplies the cited field's actual value as
untrusted evidence. It shares the existing global provider budget, reserves an
independent Falsifier attempt and revalidates the entire replacement assessment.
Schema/truncation correction retains its separate one-attempt cap. Numeric fact
fields use an integer branch of the schema; textual fields use a string branch,
so the output contract matches the source validator. Combined findings may cite
up to six directly relevant records without failing on an arbitrary three-ID cap. Unseen citation
errors remain terminal. This permits recovery from a transcription error without
accepting the conflicting candidate or treating a correction as verified prose.

## Optional advice

Under **Settings → Decision advice**,
configure a native decision endpoint and model. Settings last for this process;
advice is disabled by default. Applying settings and refreshing do not call the
model. **Test connection** sends one synthetic request
and checks the native choice-response contract.

An enabled investigation makes at most one advice request after scoped evidence
retrieval and before Investigator execution. When protocol evidence is already present, model
agents first acquire one bounded 20-record typed protocol slice so alert-heavy
queries do not crowd it out. Default advice timeout is 20 seconds,
bounded by the same cooperative investigation deadline. It uses already acquired
broker evidence, never a database transaction or ingestion callback. No model
downloads, automatic retries or background classifier queue are introduced.

Review importance and activity indicators are separate choice questions. Returned
option scores are **uncalibrated model scores**, not calibrated attack
probabilities, finding confidence or independent corroboration. No score threshold
changes routing, alert order, suppression or analyst decisions. The Investigator
and Falsifier can disagree and must ground findings in retrieved evidence.

Invalid responses and endpoint failures are visibly unavailable; cancellation and
deadline exhaustion retain their own run states. Advice status, input references
and hash, scope, model/policy version, usage and elapsed time persist through the
owning database worker. Interrupted requests are marked on restart. Credentials
and endpoint response bodies are not saved in advice records. Schema migration 7
adds the advice table without changing older migration checksums.

The adapter implements the native [llama.cpp System One contract](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#post-v1systemone-typesafe-compatible-system-one-api).
Chat-generated classifications are not substituted for native decision output.
Live capability remains pending until a compatible decision model is supplied.

## Reproducible capture processing and comparison

Process an existing capture using an explicit installed configuration and rule
file. Choose a new output directory:

```bash
PYTHONPATH=src .venv/bin/python -m bluecheese.application.prepare_case_study \
  --pcap bad.pcap --config /path/to/suricata.yaml \
  --rules /path/to/suricata.rules --out capture-study
```

This reads the capture offline without transmitting packets. The output includes
EVE, sensor diagnostics and a manifest with capture/configuration/rule hashes,
sensor version and event coverage. Generated flow identifiers and processing
statistics can vary between conversions; paired runs reuse the same frozen EVE
artifact. The capture is not modified or redistributed.
Source attribution and usage terms require separate verification.

Run three repetitions using the existing investigation profile:

```bash
PYTHONPATH=src .venv/bin/python -m bluecheese.application.compare_investigations \
  --eve capture-study/sensor/eve.json --provider ~/bc.json \
  --out investigation-comparison --repetitions 3 --max-calls 12
```

Add `--seed-id EVIDENCE_ID` to select a specific alert's existing five-minute,
same-source directed endpoint neighborhood. Without a seed, the snapshot covers
the imported scope, subject to the existing 10,000-member limit. Retrieval remains
bounded, so neither mode guarantees exhaustive investigation.

Optional `--decision-profile decision.json` accepts the existing `ModelProfile`
fields for a native endpoint, for example:

```json
{
  "endpoint": "http://127.0.0.1:8081/v1/systemone",
  "model": "configured-decision-model",
  "api_key_env": "BLUECHEESE_DECISION_API_KEY",
  "timeout": 20
}
```

No model is selected or provisioned automatically. Without this profile, advised
arms are recorded as `NOT_CONFIGURED`, not as successful comparisons. Omit
`--provider` only when deliberately comparing the offline rule policy. Repeat
`--eve` to include additional locally supplied cases; an explicit seed is limited
to a single input file.

Each case has an isolated state directory. Arms use matching snapshot digests,
investigation settings and budgets; execution order alternates across repetitions.
JSON/Markdown reports and a comparison index record outcomes, retrieval/model
calls, elapsed time, classifier overhead and available token usage. Unknown usage
remains unknown. Per-arm counts and minimum/median/maximum timings show repetition
variation without treating three runs as a throughput benchmark. Optional
`--model-attempts 4` applies the same investigation call cap to both arms without
editing the provider file. Failed/incomplete/cancelled runs produce a nonzero CLI
exit status after writing the comparison index. Ctrl-C preserves a partial index
and a cancelled run, then returns exit status 130. Existing output directories are refused.

Review the findings against independently established observations, then fill the
review fields in `comparison.json`: semantic support, contradictions, unsupported
conclusions, next-check usefulness, disposition and anchoring. Analyst completion
time is unknown unless measured. Keep reference answers and evaluator manifests
outside provider inputs. Synthetic/mocked results verify mechanics; authentic
capture results establish only the measured case behavior.

## Adversarial checks

Offline regressions cover injected telemetry requesting forbidden tools, advice
that attempts to smuggle actions or rationales, confidently wrong scores, missing
evidence, cancellation, invalid probabilities, unavailable endpoints and attempted
unretrieved citations. Snapshot boundaries, typed tools and deterministic output
validation constrain execution. They do not prove that adversarial text cannot
influence a model's conclusions; semantic manipulation requires separate review
of actual model outputs. Source records remain immutable throughout evaluation.
