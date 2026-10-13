# Decision-model triage research — 2026-10-13

Research only. No decision-model adapter, model download, model-server update or
suppression policy was introduced by this note. Current GUI triage remains rules.

## Verified upstream capability

llama.cpp merged native `/v1/systemone` support on October 2, 2026. Its decision
models score specified choices instead of generating a text answer. The API
supports choice, ordinal score and yes/no questions. Native decision models are
distinct from prompting a general chat model to emit a classification label.
The current model-discovery metadata can advertise `output_modalities: decisions`.
Older servers/models may not support this endpoint; verify the actual build.

Sources: [merged implementation](https://github.com/ggml-org/llama.cpp/pull/29818),
[server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#post-v1systemone-typesafe-compatible-system-one-api),
[maintainer introduction](https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp).

The server documentation explicitly says probabilities are not guaranteed to be
calibrated for the application's data. A high option score does not establish
that an alert is malicious. Published latency examples use an RTX PRO 6000 and
cannot establish throughput on the owner's hardware.

## Proposed Blue Cheese placement

The socket is a transport. The same classifier stage should work with file input.
Persist exact evidence before asynchronous classification; never wait for a model
inside the socket-read/database transaction. Use bounded queues and show backlog.

Use deterministic grouping and urgent-review rules first, then evaluate a compact
alert group plus bounded related flow context. Inputs can include detection rule,
severity, endpoints/ports, protocol, timestamps, occurrence counts and flow state/
byte counters. Authorization, asset inventory and endpoint process context are
unknown unless later integrations actually supply them. EVE `flow_id` can relate
records where available; correlation must retain source/time/endpoint validation.
[Suricata EVE fields](https://docs.suricata.io/en/suricata-8.0.6/output/eve/eve-json-format.html).

Proposed routing options:
- **Investigate:** put into the full-investigation queue.
- **Lower priority:** retain searchable evidence and a visible deferred queue.
- **Needs review:** uncertainty, missing context, invalid output, overload or model
  unavailability; preserve deterministic priority and require review.

A routing label is not an incident verdict. Urgent deterministic policy must override
model deprioritization. Never delete records, equate low priority with benign, or
silently drop work when a classifier is unavailable. Do not invent a model rationale:
store the actual input record references, option scores, policy/model versions and
software rule overrides. Full Investigator/Falsifier work supplies cited analysis.

## Evaluation before routing authority

Start in shadow mode: record proposed labels alongside existing rule priorities
without hiding alerts or changing scheduling. Compare Julia-1 (144M), Laya (421M)
and Kev-4B as candidate sizes; suitability for Suricata security triage is unproven.
Use locally supplied, legally usable analyst-labelled cases and separate evaluation
splits. Measure missed investigation-worthy cases first, then queue reduction,
precision, abstention rate, p95 latency and sustained backlog. Audit a sample of
lower-priority decisions and include adversarial/missing-context inputs. Select
thresholds from measured error tradeoffs; no default probability is justified yet.

Model licenses are a selection constraint for a paid product. The current cards
list Apache 2.0 for [Julia-1](https://huggingface.co/ggml-org/Julia-1-GGUF),
[Laya](https://huggingface.co/ggml-org/Laya-GGUF) and
[Kev-4B](https://huggingface.co/ggml-org/Kev-4B-GGUF).
[OpenJev](https://huggingface.co/ggml-org/OpenJev-GGUF) currently lists CC BY-NC 4.0;
do not assume its published weights are suitable for the intended paid deployment.
Recheck the exact upstream model/artifact terms before selecting it.
