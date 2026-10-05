# Blue Cheese
Preserve the existing CLI PCAP/EVE import and SQLite triage path. The offline presentation uses Streamlit, a serialized local runtime and DuckDB. Extend the existing normalized model and Suricata adapter.

Invariants: raw input is immutable; IDs include source identity, byte position and content hash; case/variant and snapshot scope every evidence tool. Investigator sees telemetry only, never evaluator manifests. Validate citations against retrieved evidence. Replay is synthetic append-only logging, not packet capture. One runtime owns database access; UI reruns must reuse it and must not rerun investigations.

Current implementation/verification: docs/SESSION_STATUS.md. Planned product: Blue_Cheese_Codex_Build_Prompt.md. Keep changes small; no agent framework or model downloads.
