# Decision-model triage research — 2026-10-13

Implementation update (2026-10-14): optional native advice, scoped persistence and comparison
tooling now implement the first advisory slice described below. See
[Investigation assessments](INVESTIGATION_ASSESSMENTS.md). Native live validation
awaits a compatible configured decision model. Current GUI triage remains rules;
no model downloads, server updates or suppression policy are introduced.

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

## Intended first application: advisory assessment

Show the analyst an additional assessment alongside existing rule priority and
cited findings. Distinguish **suggested review importance**, **model scores
(uncalibrated)** and **missing evidence**. Include the assessment, option scores,
case/variant and snapshot scope, actual input evidence references, important
unknowns and model/policy versions. Do not invent a model rationale. Preserve an
explicit **insufficient evidence** outcome. Invalid output, overload or classifier
unavailability must be visibly unavailable, never interpreted as a low-risk score.

Keep importance, maliciousness and confidence in a finding distinct. Urgency or
potential impact does not establish maliciousness, and an option score is not
calibrated finding confidence. Unknown authorization or endpoint context remains
unknown regardless of the score.

Supply the investigation model with a bounded, explicitly labelled **upstream
model assessment**, including its input references, option scores, scope and
unknowns within existing context and retrieval budgets. The Investigator must
assess the underlying evidence and may disagree; the Falsifier must remain able
to challenge claims. Two models assessing the same records do not provide
independent corroborating evidence. A classifier score cannot substitute for a
cited observation. Upstream references do not automatically authorize citations:
findings must cite evidence actually retrieved for that scoped run and snapshot.

Keep analyst decisions and application controls separate from advice. Scores
alone must not start investigations, reorder or suppress alerts, close cases, or
authorize actions. Navigation and rerenders must never launch work. Existing
rules, explicit execution controls, scope, budgets and citation validation remain
in force. The initial advisory interface is now implemented; native live validation remains pending.

## Evaluation before advisory adoption

Compare investigations **with and without the advisory assessment**, using matched
cases, frozen evidence, investigation settings and budgets. Use locally supplied,
legally usable analyst-labelled cases and separate evaluation splits. Measure
analyst usefulness and completion, time saved, finding quality, unsupported
conclusions and whether misleading scores anchor the investigation model. Review
semantic support as well as mechanical citation validity. Synthetic tests do not
establish detection accuracy or commercial readiness.

Include confidently wrong classifications, missing telemetry, correlated records,
model disagreement, adversarial inputs and unavailable classifiers. Verify that
correlated records do not become independent corroboration, insufficient evidence
survives high scores, and the Investigator can disagree based on retrieved evidence.
Check that cited findings remain grounded in actual scoped run retrieval and that
navigation never launches work. Unavailable assessments must leave the existing
analyst workflow usable.

Compare Julia-1 (144M), Laya (421M) and Kev-4B as candidate sizes; suitability for
Suricata security triage is unproven. Also measure abstention, p95 latency and
sustained backlog. Scores start explicitly uncalibrated; no default probability
threshold is justified without application-specific evaluation.

Routing automation is a separately evaluated future possibility, not the initial
application. Any future proposal needs measured missed investigation-worthy cases,
precision, queue effects and audits of lower-priority outcomes before requesting
routing authority. Retain visible evidence and deterministic urgent-review policy;
never equate low priority with benign or silently drop work on classifier failure.

Model licenses are a selection constraint for a paid product. The current cards
list Apache 2.0 for [Julia-1](https://huggingface.co/ggml-org/Julia-1-GGUF),
[Laya](https://huggingface.co/ggml-org/Laya-GGUF) and
[Kev-4B](https://huggingface.co/ggml-org/Kev-4B-GGUF).
[OpenJev](https://huggingface.co/ggml-org/OpenJev-GGUF) currently lists CC BY-NC 4.0;
do not assume its published weights are suitable for the intended paid deployment.
Recheck the exact upstream model/artifact terms before selecting it.
