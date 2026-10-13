"""Readable operational reports with intact cited evidence and downloadable audit."""

import streamlit as st

from bluecheese.agents.reporting import json_report, markdown_report
from bluecheese.interfaces.demo import inspect_event


def show_report(runtime, report, key):
    st.markdown("#### Investigation result")
    a, b, c = st.columns(3)
    a.metric("Assessment", report["verdict"].replace("_", " ").title())
    b.metric(
        "Run status", report.get("run_status", "Unknown").replace("_", " ").title()
    )
    c.metric("Host compromise", "Unconfirmed")
    st.text(report["hypothesis"])
    st.caption(
        "Analysis completion and security conclusions are separate. Citations are mechanically checked; review whether the evidence supports each claim."
    )
    st.markdown("#### Observations and supporting evidence")
    for index, claim in enumerate(report.get("claims", []), 1):
        st.text(claim["text"])
        with st.expander(f"Evidence for observation {index}"):
            for event_id in claim["citations"]:
                inspect_event(
                    runtime,
                    report["scenario"],
                    report["variant"],
                    report["snapshot"],
                    event_id,
                    report.get("snapshot_id"),
                )
    if not report.get("claims"):
        st.info("No evidence-backed observations were recorded in this result.")
    check = report.get("falsifier", {})
    with st.expander("Alternative explanation checked", expanded=True):
        st.text(report["disconfirmation_test"])
        st.text("Outcome: " + check.get("status", "Not recorded"))
        if check.get("checked"):
            st.text(check["checked"])
    if report["unresolved"]:
        with st.expander(
            f"Unresolved questions ({len(report['unresolved'])})", expanded=True
        ):
            for item in report["unresolved"]:
                st.text("• " + item)
    if report["warnings"]:
        with st.expander(f"Limits and warnings ({len(report['warnings'])})"):
            for warning in report["warnings"]:
                st.text("• " + warning)
    st.markdown("#### Recommended next checks")
    st.write(
        "Confirm whether this activity was authorized. Review endpoint process and authentication logs for the selected machine. These sources are not connected to Blue Cheese; network evidence alone cannot establish process identity or host compromise."
    )
    left, right = st.columns(2)
    left.download_button(
        "Export JSON",
        json_report(report),
        file_name=key + ".json",
        mime="application/json",
        key=key + "-json",
        icon=":material/download:",
    )
    right.download_button(
        "Export Markdown",
        markdown_report(report),
        file_name=key + ".md",
        mime="text/markdown",
        key=key + "-md",
        icon=":material/download:",
    )
    citations = list(
        dict.fromkeys(report["supporting_ids"] + report["contradicting_ids"])
    )
    with st.expander(f"Verify cited evidence ({len(citations)})"):
        if citations:
            chosen = st.selectbox(
                "Inspect citation",
                citations,
                key=key + "-citation",
                format_func=lambda value: f"Evidence {citations.index(value) + 1}",
            )
            inspect_event(
                runtime,
                report["scenario"],
                report["variant"],
                report["snapshot"],
                chosen,
                report.get("snapshot_id"),
            )
        else:
            st.info(
                "This report has no supporting or contradicting citations. Inspect its unresolved questions and retrieval audit."
            )
    with st.expander("Reasoning and retrieval audit"):
        st.text("Observable disconfirmation test: " + report["disconfirmation_test"])
        st.write("Supporting IDs", report["supporting_ids"])
        st.write("Contradicting IDs", report["contradicting_ids"])
        st.json(
            {
                "triage": report.get("triage"),
                "correlation": report.get("correlation"),
                "falsifier": report["falsifier"],
                "tool_activity": report["tool_activity"],
                "budget": report["budget"],
                "provider": report["provider"],
                "provider_activity": report.get("provider_activity"),
                "workflow_activity": report.get("workflow_activity"),
            }
        )
