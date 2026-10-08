"""Local presentation: no investigation side effects on rerender."""

import os
from pathlib import Path

import streamlit as st

from bluecheese.agents.investigator import PROVIDER_LABEL
from bluecheese.agents.reporting import json_report, markdown_report
from bluecheese.application.demo_runtime import SCENARIOS, DemoRuntime


@st.cache_resource
def get_runtime(state_dir):
    return DemoRuntime(state_dir)


def inspect_event(runtime, scenario, variant, snapshot, event_id, snapshot_id=None):
    event = runtime.command(
        "get_event", scenario, variant, snapshot, event_id, snapshot_id=snapshot_id
    )
    if event:
        st.caption(
            f"Evidence ID: {event['id']} | Source: {event['source']} | Byte offset: {event['position']}"
        )
        left, right = st.columns(2)
        with left:
            st.write("Exact raw input (untrusted text)")
            st.code(event["raw"], language="json")
            st.write("Parsed JSON")
            st.json(event["parsed"])
        with right:
            st.write("Canonical normalized fields")
            st.json(event["normalized"])
    else:
        st.warning("Record not available in this fixed snapshot.")


def show_report(runtime, report, key):
    st.subheader(report["verdict"])
    if "run_id" in report:
        st.caption(
            f"Run {report['run_id']} • revision {report['case_revision']} • {report['run_status']}"
        )
    st.write(report["hypothesis"])
    st.write("Observable disconfirmation test:", report["disconfirmation_test"])
    st.write("Supporting IDs", report["supporting_ids"])
    st.write("Contradicting IDs", report["contradicting_ids"])
    if report.get("triage"):
        st.write("Triage priorities and candidate groups")
        st.json(report["triage"])
    if report.get("correlation"):
        st.write("Correlation links and rule basis")
        st.json(report["correlation"])
    st.write("Falsifier check")
    st.json(report["falsifier"])
    st.write("Tool activity / consumed budget")
    st.json({"activity": report["tool_activity"], "budget": report["budget"]})
    st.write("Unresolved evidence", report["unresolved"])
    st.caption(" | ".join(report["warnings"]))
    citations = list(
        dict.fromkeys(report["supporting_ids"] + report["contradicting_ids"])
    )
    if citations:
        chosen = st.selectbox("Inspect citation", citations, key=key + "-citation")
        inspect_event(
            runtime,
            report["scenario"],
            report["variant"],
            report["snapshot"],
            chosen,
            report.get("snapshot_id"),
        )
    left, right = st.columns(2)
    left.download_button(
        "Export JSON",
        json_report(report),
        file_name=key + ".json",
        mime="application/json",
        key=key + "-json",
    )
    right.download_button(
        "Export Markdown",
        markdown_report(report),
        file_name=key + ".md",
        mime="text/markdown",
        key=key + "-md",
    )


@st.fragment(run_every=1.0)
def live_panel(runtime, settings):
    st.caption(
        "Paced replay of synthetic EVE records; not packet capture. New lines keep distinct source positions. Reports use a fixed snapshot."
    )
    mode = st.radio(
        "Live source",
        ["Synthetic replay", "External append-only EVE file"],
        horizontal=True,
    )
    path = st.text_input("External EVE path", value="/telemetry/eve.jsonl")
    if st.button("Start / resume ingestion"):
        try:
            runtime.start(path=path, replay=mode == "Synthetic replay")
        except (OSError, ValueError) as error:
            st.error(str(error))
    if st.button("Stop ingestion"):
        runtime.stop()
    status = runtime.status()
    st.json(status)
    variant = "replay" if runtime.replay else "external"
    snapshot = runtime.command("snapshot")
    events = runtime.command("query", "live", variant, snapshot, newest_first=True)
    if events:
        selected = st.selectbox("Live evidence ID", [r["id"] for r in events], index=0)
        inspect_event(runtime, "live", variant, snapshot, selected)
    if st.button("Investigate live snapshot"):
        st.session_state["live_report"] = runtime.run("live", variant, **settings)
    if st.session_state.get("live_report"):
        show_report(runtime, st.session_state["live_report"], "live-report")


@st.fragment(run_every=1.0)
def background_controls(runtime, scenario, variant, settings):
    if st.button("Start background investigation"):
        try:
            st.session_state["background_run"] = runtime.begin_run(
                scenario, variant, **settings
            )
        except (RuntimeError, ValueError) as error:
            st.error(str(error))
    if st.button("Cancel active investigation"):
        if runtime.cancel():
            st.info(
                "Cancellation requested; the current provider call must return first."
            )
        else:
            st.caption("No active investigation.")
    pending = st.session_state.get("background_run")
    if pending is not None:
        if pending.done():
            del st.session_state["background_run"]
            try:
                st.session_state["report"] = pending.result()
                st.rerun()
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
        else:
            st.info("Investigation in progress. Ingestion remains active.")


def main():
    st.set_page_config(page_title="Blue Cheese", layout="wide")
    st.title("Blue Cheese — evidence to cited investigation")
    st.info("Synthetic data • " + PROVIDER_LABEL)
    st.caption(
        "Raw telemetry → normalization → evidence store → investigation → Falsifier → cited report"
    )
    runtime = get_runtime(
        str(Path(os.environ.get("BLUECHEESE_STATE", "bluecheese-data")).resolve())
    )
    scenario = st.sidebar.selectbox("Scenario", list(SCENARIOS))
    variant = st.sidebar.selectbox("Variant", SCENARIOS[scenario])
    falsification = st.sidebar.checkbox("Enable Falsifier", value=True)
    max_calls = st.sidebar.number_input(
        "Tool-call limit", min_value=0, max_value=20, value=6
    )
    max_seconds = st.sidebar.number_input(
        "Elapsed-time limit (seconds)", min_value=0.0, value=5.0
    )
    question = st.sidebar.text_input(
        "Case question",
        value="What does the observed alert and related flow evidence support?",
    )
    settings = {
        "question": question,
        "falsification": falsification,
        "max_calls": max_calls,
        "max_seconds": max_seconds,
    }
    evidence, investigation, comparison, live = st.tabs(
        ["Evidence", "Investigation", "Comparison", "Live"]
    )
    with evidence:
        counts = runtime.command("counts", scenario, variant)
        st.write(
            "Accepted:", counts["accepted"], "Invalid / quarantined:", counts["invalid"]
        )
        snapshot = runtime.command("snapshot")
        events = runtime.command("query", scenario, variant, snapshot)
        if events:
            chosen = st.selectbox("Evidence ID", [r["id"] for r in events])
            inspect_event(runtime, scenario, variant, snapshot, chosen)
    with investigation:
        if st.button("Run Investigation", type="primary"):
            st.session_state["report"] = runtime.run(scenario, variant, **settings)
        report = st.session_state.get("report")
        if report:
            st.caption(
                f"Saved run: {report['scenario']} / {report['variant']} / snapshot {report['snapshot']}. Settings above apply to the next run."
            )
            show_report(runtime, report, "investigation")
        background_controls(runtime, scenario, variant, settings)
        with st.expander("Saved case runs"):
            history = runtime.command("list_runs", scenario, variant)
            if history:
                st.table(history)
                selected_run = st.selectbox(
                    "Saved run ID", [r["run_id"] for r in history]
                )
                if st.button("Load saved report"):
                    saved_run = runtime.command(
                        "get_run", scenario, variant, selected_run
                    )
                    if saved_run["report"]:
                        st.session_state["report"] = saved_run["report"]
                        st.rerun()
                    else:
                        st.warning(
                            f"{saved_run['status']}: {saved_run['error'] or 'No completed report'}"
                        )
                if st.button("Investigate successor revision"):
                    st.session_state["report"] = runtime.run(
                        scenario, variant, parent_run_id=selected_run, **settings
                    )
                    st.rerun()
    with comparison:
        st.write(
            "Matched settings on the synthetic suspicious scenario. Differences below are computed from saved results."
        )
        if st.button("Run clean / poisoned comparison"):
            st.session_state["comparison"] = [
                runtime.run("suspicious", v, **settings) for v in ("clean", "poisoned")
            ]
        pair = st.session_state.get("comparison")
        if pair:
            st.table(
                [
                    {
                        "variant": r["variant"],
                        "verdict": r["verdict"],
                        "supporting": len(r["supporting_ids"]),
                        "contradicting": len(r["contradicting_ids"]),
                        "falsifier": r["falsifier"]["status"],
                        "calls": r["budget"]["calls"],
                        "enabled": r["falsification_enabled"],
                    }
                    for r in pair
                ]
            )
            st.write(
                "Observed verdict difference:",
                f"{pair[0]['verdict']} → {pair[1]['verdict']}",
            )
            st.caption(
                "IDs differ by variant; compare raw/normalized records, not ID strings. No claim of measured LLM superiority."
            )
            for r in pair:
                with st.expander(r["variant"]):
                    show_report(runtime, r, "comparison-" + r["variant"])
    with live:
        live_panel(runtime, settings)


if __name__ == "__main__":
    main()
