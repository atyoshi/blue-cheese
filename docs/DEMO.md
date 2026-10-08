# Five-minute walkthrough

Launch with README's native command; open localhost:8501. Keep the default six calls / five seconds and Enable Falsifier checked. No API keys or sensor needed.

1. **0:00–0:40 — Explain the path.** “Blue Cheese investigates telemetry through typed tools and seeks evidence against its own hypothesis. These records are synthetic; this is a deterministic offline demo provider, not an LLM benchmark.” Point at the visible path and labels.
2. **0:40–1:30 — Evidence.** Choose `suspicious / clean`. Accepted count is 30, invalid count zero. The first record alerts on `10.0.0.8 → 198.51.100.23`, flow ID 900. Show exact JSONL text, parsed JSON, normalized fields, source and byte offset. The hash-based ID resolves back to that record.
3. **1:30–2:40 — Investigation.** Click **Run Investigation**. Expected `SUSPICIOUS`: one alert and five established related flows, each reporting 16,000 outbound bytes, support the hypothesis. Show the actual `find_events_by_ip` Falsifier query and returned IDs. Its zero-byte alternative is **not observed**, which does not prove intent. Inspect a supporting citation. Endpoint activity remains unresolved. Try `insufficient / clean`: `UNCERTAIN`, flow evidence **not available**. `benign / clean` gives `BENIGN_CONFOUNDER` because its matching flow is closed with zero bytes.
4. **2:40–3:40 — Comparison.** Click **Run clean / poisoned comparison**. Clean is `SUSPICIOUS`; poisoned is `UNCERTAIN`, with four active-flow supports and one contradictory closed zero-byte flow. Expand poisoned and inspect its counterevidence citation. Its raw metadata also contains an instruction-like “approved backup” note, which this provider ignores. The changed counters cause the observed difference. Switch Falsifier off and rerun: both suspicious variants yield `SUSPICIOUS`; the poisoned conflicting record is no longer checked by the Falsifier. Describe these rule-policy observations without claiming LLM superiority or poison immunity.
5. **3:40–5:00 — Live and export.** Restore Falsifier on. Choose **Synthetic replay** in Live; click **Start / resume ingestion**. Counts and committed offset increase every 0.5 seconds; refresh occurs every second. Inspect the newest record. After roughly 15 seconds, active-flow records arrive; **Investigate live snapshot** yields the cited result while counts continue to grow. Stop; counts settle. Resume: new source positions are accepted, committed old positions are not duplicated. Stop again and download JSON/Markdown. The report's snapshot and saved citations stay fixed.

Saved presentation exports can be generated with `python -m bluecheese.application.export_demo --state bluecheese-data --out demo-exports` while the app is stopped. Exports from the UI are browser downloads. The evaluator-only manifest is `docs/evaluator/transformation.json`; it is not loaded into the evidence tools/provider.

On an already-used state directory, live counts start above zero and replay continues cycling. Offline import remains idempotent. To rehearse with empty live state, stop the app and set `BLUECHEESE_STATE` to a new writable directory. Do not delete or modify a followed file while expecting continuity. Replay is not packet capture.

## Master-plan additions

After Run Investigation, inspect the triage groups and correlation links. They
show separate sensor severity/review priority, grouped occurrence IDs, rule basis,
time window and correlation ambiguity. All logical roles share one bounded
retrieval budget; no additional models or framework are involved.

Use Saved case runs to load a persisted report without rerunning. Investigate
successor revision preserves the parent run and creates a new immutable snapshot.
A report's completed/incomplete/cancelled status is separate from its verdict.
Start background investigation lets ingestion continue. Cancellation is cooperative;
the current provider call must return. Restart retains prior reports and marks
unfinished work interrupted. README includes offline bundle and backup/restore
commands. Full rotation recovery and automatic case scheduling remain deferred.
