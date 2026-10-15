# Multiagent investigation next steps after the live rerun

Evidence: [live rerun results](LIVE_LLM_RERUN_RESULTS.md), plus the retained
six-trial campaign at `~/bluecheese-evaluations/20261015-live-rerun-0158/`.
Only one pilot completed mechanically; its semantic review still has
qualifications. The proposals below have not been implemented or live validated
unless explicitly marked otherwise. Keep the replaceable provider protocol,
bounded deterministic roles, retrieval ledger and existing architecture.

## Implementation update

The first offline increment is implemented and verified: output guide, typed fact
catalog/delivery checks, flexible call allocation, Falsifier guidance, and opt-in
local rejection retention. See [behavior and verification](INVESTIGATION_RELIABILITY.md).
Live benefit is still unverified. A sanitized parser diagnostic packet and a
separately authorized [24-run matched evaluation](LIVE_LLM_MATCHED_EVALUATION.md)
are prepared. The sections below retain the original proposals and observations;
the implementation document specifies their actual delivered behavior.

## 1. Make the output contract easier for both model roles to follow

Observed: Investigator and Falsifier exceeded fact, claim or text limits, and
one correction changed a limitations array to the wrong type. The narrow change
already implemented adds trusted expected constraints to schema-error guidance;
its offline behavior tests pass, but the live retest did not exercise correction.

Possible next change: derive a short field guide from the actual schema and put
it near the final-turn instruction: at most two claims, two facts per claim,
limitations as an array of at most one string of 128 characters, and the other
existing bounds. Keep one schema source and avoid separate drifting constants.
Do not increase the schema limits to accept these failures.

Verify with deterministic invalid outputs in both roles, including a second
invalid correction, then a bounded same-seed live trial that actually exercises
correction. Record schema completion separately from factual acceptance.

## 2. Prevent confusion between evidence records and observable fields

Observed: the Falsifier attached a URL fact to a DNS record. Strict validation
correctly stopped the run. Citation existence alone cannot prevent this mistake.

Possible next change: supply a bounded catalog of available typed facts grouped
by the exact retrieved ID, event type and timestamp. Make HTTP method/path/status
and response length visibly belong to their HTTP record. Keep citations bound
to delivered evidence; a catalog must not silently widen retrieval or omit
contradictory observations. A provider may select facts, while software verifies
exact bindings and preserves the model's original rejected attempt.

Verify a DNS/HTTP ID swap, unseen ID, correct ID with incorrect value, and a
corrected binding with still-unsupported prose. Never substitute IDs or repair
unseen citations automatically.

## 3. Reserve useful independent review within the global budget

Observed: stage 02 and 04 consumed four Investigator calls and left two for the
Falsifier. Several calls retrieved already supplied or empty connection context.
The post-fix stage 02 used all six calls before a factual error, leaving no
correction opportunity.

Possible next change: expose the retrieved/delivered ledger and remaining calls
clearly to each role; evaluate role-aware allocation with a reserved final review
and one correction opportunity where feasible. Prefer diverse host observations
to repeated identical requests. Any suppression of duplicate retrieval must
preserve the audit trail and disclose reused results.

Verify total call/time caps, cancellation, explicit Falsifier execution, and
unchanged rejection paths. Compare usefulness and latency on fixed recovered
seeds before choosing an allocation. More calls are a separate experiment,
requiring explicit settings and allowance rather than a hidden retry policy.

## 4. Diagnose provider output-parser compatibility

Observed: stage 04's Falsifier request returned the allowlisted native parser
HTTP 500 after Investigator succeeded. Local schema validation cannot fix a
response the provider never returns successfully.

Give the provider operator the retained stage, timing, model/template identifiers
and sanitized parser diagnostic. Investigate strict-schema support and the
tool-to-final-response transition. A JSON-object mode comparison may be useful
as a separately authorized experiment with complete local validation, equal
seeds/settings and its own artifacts. Keep failures visible; avoid broad HTTP
retries, backend changes or model substitutions to force a success.

## 5. Improve the Falsifier's reasoning and semantic checks

Observed: stage 01 suggests TLS evidence could falsify observed plaintext HTTP,
and says “zero response bytes” where the source supports a logged HTTP response
length of zero alongside nonzero flow bytes.

Possible next change: have the Falsifier identify the exact proposition it is
testing, what result would weaken that proposition, and what remains unchanged.
Authorization evidence can weaken an unauthorized-tool hypothesis; it cannot
erase observed HTTP. Source-derived byte labels should identify HTTP response
length versus directional whole-flow totals and their time coverage.

Use reviewed offline examples for these distinctions and manually inspect live
prose. Mechanical constraints cannot certify arbitrary causal explanations or
classifications. Preserve the distinction between observed network activity and
endpoint execution, compromise or theft.

## 6. Retain enough rejected output for an auditable investigation

Observed: failed-run diagnostics retain validation paths, timings and retrieved
evidence, but the exact rejected URL value and prose cannot be reconstructed.

Possible next change: an explicit local retention option for bounded candidate
output, request/schema hashes and rejection reasons. Redact credentials and
provider internals, escape text in the GUI, document retention, and keep those
artifacts outside Git. Store originals rather than replacing them with repairs.
Review retention/privacy requirements before implementing this option.

## 7. Measure the whole analyst workflow after reliability improves

Run fixed-seed matched repetitions, preserving first failures, before changing
selection or scope. Track report completion, schema/citation/fact failures,
independent Falsifier execution, semantic support and per-role latency separately.
Have analysts adjudicate supported observations, contradictory evidence,
disposition and next-check usefulness. Measure task completion time against a
documented baseline before claiming time saved.

Keep full-chain coverage, identity protocols, endpoint data, deployment/auth,
Docker/macOS release checks and commercial readiness as separate scoped work.
An accepted synthetic test or one successful live report establishes neither
detection accuracy nor readiness for unattended incident decisions.
