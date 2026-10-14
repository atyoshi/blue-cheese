"""Interactive, evidence-backed network overview for the operational console."""

import streamlit as st

from bluecheese.application.telemetry_visuals import (
    connection_graph,
    rank_endpoints,
    summarize,
)
from bluecheese.interfaces.console_design import (
    investigation_link,
    record_label,
    start_investigation,
    table_columns,
)
from bluecheese.interfaces.demo import inspect_event

SCOPE = ("live", "external")
COLORS = {"domain": ["alert", "flow"], "range": ["#d15b38", "#367eb3"]}


def explain_record(row):
    st.markdown("**Reading this record**")
    left, middle, right = st.columns([2, 1, 2])
    left.info(
        f"Source\n\n{row.get('src_ip') or 'Unknown'}\n\nPort {row.get('src_port') if row.get('src_port') is not None else 'unknown'}"
    )
    middle.markdown(f"### →\n{row.get('protocol') or 'Unknown protocol'}")
    right.info(
        f"Destination\n\n{row.get('dest_ip') or 'Unknown'}\n\nPort {row.get('dest_port') if row.get('dest_port') is not None else 'unknown'}"
    )
    st.caption(
        "An IP identifies a network endpoint. A port identifies a transport endpoint, often associated with a service. The arrow follows Suricata's source/destination fields; it does not prove who initiated the session or whether traffic is malicious."
    )
    if row["event_type"] == "alert":
        st.caption("Suricata matched this detection rule")
        st.code(row["alert_signature"], language="text")
        st.caption(
            "An alert is a lead to investigate. Severity 1 is higher priority than 2 or 3, but severity does not establish compromise. Read the rule, related flows and original evidence before deciding."
        )
    else:
        sent, received = row.get("bytes_toserver"), row.get("bytes_toclient")
        st.text("Flow state: " + (row.get("flow_state") or "Not reported"))
        st.caption(
            f"Bytes to server: {sent if sent is not None else 'not reported'} · Bytes to client: {received if received is not None else 'not reported'}. These are sensor-reported counters for this flow record; repeated flow updates must not be summed as unique traffic volume."
        )


def reset_focus():
    st.session_state["visual-endpoint"] = "All endpoints"
    st.session_state["visual-pair"] = "All connections"


def overview(runtime, snapshot, learning):
    controls = st.columns([1, 2, 1])
    limit = controls[0].selectbox(
        "Recent records to visualize",
        [1000, 5000, 250],
        format_func=lambda n: f"{n:,} records",
        key="visual-limit",
    )
    rows = runtime.command("visual_telemetry", *SCOPE, snapshot, limit=limit)
    if not rows:
        st.info(
            "Your workspace is ready. Connect a file or Unix stream under Sensor connection to populate these views."
        )
        if learning:
            fundamentals()
        return
    ranked = rank_endpoints(rows)
    by_ip = {item["ip"]: item for item in ranked}
    endpoints = list(by_ip)
    if st.session_state.get("visual-endpoint") not in ["All endpoints", *endpoints]:
        reset_focus()
    endpoint = controls[1].selectbox(
        "Focus on an endpoint",
        ["All endpoints", *endpoints],
        key="visual-endpoint",
        format_func=lambda ip: (
            ip
            if ip == "All endpoints"
            else f"{ip} · {by_ip[ip]['alerts']} alerts · {by_ip[ip]['records']} records"
        ),
        help="Ranked by alert count, then record count. Type an IP to search. This filters the overview; it does not start an investigation.",
    )
    controls[2].button(
        "Reset focus",
        on_click=reset_focus,
        icon=":material/filter_alt_off:",
        width="stretch",
    )
    filtered = [
        r
        for r in rows
        if endpoint == "All endpoints"
        or endpoint in (r.get("src_ip"), r.get("dest_ip"))
    ]
    endpoint_summary = summarize(filtered)
    connections = endpoint_summary["connections"]
    pair_options = [
        "All connections",
        *[f"{p['source']} → {p['destination']}" for p in connections],
    ]
    pair = st.selectbox(
        "Inspect a connection",
        pair_options,
        key="visual-pair",
        help="Narrows every visual and the evidence list to this directed IP pair.",
    )
    if pair != "All connections":
        selected_pair = connections[pair_options.index(pair) - 1]
        filtered = [
            r
            for r in filtered
            if (r.get("src_ip") or "Unknown") == selected_pair["source"]
            and (r.get("dest_ip") or "Unknown") == selected_pair["destination"]
        ]
    st.caption(
        "Viewing "
        + ("all recent endpoints" if endpoint == "All endpoints" else endpoint)
        + " · Choose an alert in Evidence to start an investigation."
    )
    summary = summarize(filtered)
    st.caption(
        f"Visual scope: {len(filtered):,} of the latest {len(rows):,} accepted records · limit {limit:,} · receipt sequence {snapshot:,}. All views below share this focus; header counters cover the stored external scope."
    )
    if not filtered:
        st.info(
            "No records in this focus. Reset the filters to return to the recent-record window."
        )
        return
    a, b, c = st.columns(3)
    a.metric("Alerts in view", sum(r["event_type"] == "alert" for r in filtered))
    b.metric("Flow records in view", sum(r["event_type"] == "flow" for r in filtered))
    c.metric("Directed IP pairs in view", len(summary["connections"]))
    activity_tab, connection_tab, evidence_tab = st.tabs(
        ["Connections", "Activity", "Evidence"], key="network-tab", on_change="rerun"
    )
    with connection_tab:
        activity(summary, filtered, learning)
    with activity_tab:
        st.markdown("#### Most active endpoints")
        st.vega_lite_chart(
            {
                "data": {"values": ranked[:10]},
                "mark": "bar",
                "encoding": {
                    "y": {
                        "field": "ip",
                        "type": "nominal",
                        "sort": "-x",
                        "title": None,
                    },
                    "x": {
                        "field": "records",
                        "type": "quantitative",
                        "title": "Recent records",
                    },
                    "color": {
                        "field": "alerts",
                        "type": "quantitative",
                        "title": "Alerts",
                    },
                    "tooltip": [
                        {"field": "ip"},
                        {"field": "records"},
                        {"field": "alerts"},
                    ],
                },
            },
            width="stretch",
            height=220,
        )
        st.markdown("#### Connection map")
        st.caption(
            "Source → destination · orange: includes alerts · blue: flow records only"
        )
        with st.container(height=410, border=True):
            st.graphviz_chart(
                connection_graph(summary["connections"][:12]),
                width="content",
                height="content",
            )
        st.caption(
            f"Top {min(12, len(summary['connections']))} of {len(summary['connections'])} IP pairs, ranked by alerts then records. Scroll inside the map; use its fullscreen control for a larger view. Select a connection above, then open Evidence to inspect its records."
        )
        if learning:
            with st.expander("How to read this map"):
                st.write(
                    "This is a logical relationship map, not a physical network diagram. The same IP can appear on both sides. Edge width shows log record count, not unique sessions. An orange edge is an investigation lead, not proof of an attack."
                )
    with evidence_tab:
        visual_evidence(runtime, snapshot, filtered, learning)


def activity(summary, filtered, learning):
    st.markdown("#### Activity over recorded time")
    if summary["timeline"]:
        st.vega_lite_chart(
            spec={
                "data": {"values": summary["timeline"]},
                "mark": {"type": "line", "point": True},
                "params": [
                    {
                        "name": "zoom",
                        "select": {
                            "type": "interval",
                            "encodings": ["x"],
                            "zoom": "wheel![event.shiftKey]",
                        },
                        "bind": "scales",
                    }
                ],
                "encoding": {
                    "x": {
                        "field": "time",
                        "type": "temporal",
                        "title": "Event time (UTC)",
                        "scale": {"type": "utc"},
                    },
                    "y": {
                        "field": "records",
                        "type": "quantitative",
                        "title": "Records per time bucket",
                        "scale": {"zero": True},
                        "axis": {"tickMinStep": 1},
                    },
                    "color": {
                        "field": "type",
                        "type": "nominal",
                        "scale": COLORS,
                        "title": "Record type",
                    },
                    "tooltip": [
                        {
                            "field": "time",
                            "type": "nominal",
                            "title": "Bucket start (UTC)",
                        },
                        {"field": "type"},
                        {"field": "records", "type": "quantitative"},
                    ],
                },
            },
            width="stretch",
            height=240,
        )
        st.caption(
            f"{summary['bin_minutes']}-minute buckets · Shift + scroll to zoom time, drag to pan, double-click to reset. Event times are UTC."
        )
        if summary["untimed"]:
            st.warning(
                f"{summary['untimed']} records lack a usable timezone-aware timestamp; only this timeline excludes them."
            )
        if learning:
            with st.expander("How to read this timeline"):
                st.write(
                    "A spike means more records in that interval. A zero means no records in this sample, not proof of uninterrupted coverage or a safe network. Times come from the sensor, so old captures retain their original dates."
                )
    else:
        st.warning(
            "No usable timezone-aware timestamps in this view. Other charts still include these records."
        )
    left, right = st.columns(2)
    with left:
        st.markdown("#### Alert severity")
        if any(r["event_type"] == "alert" for r in filtered):
            st.vega_lite_chart(
                spec={
                    "data": {"values": summary["severities"]},
                    "mark": {"type": "bar", "cornerRadiusEnd": 4},
                    "encoding": {
                        "y": {
                            "field": "severity",
                            "type": "nominal",
                            "sort": ["1 · High", "2 · Medium", "3 · Low", "Unknown"],
                            "title": None,
                        },
                        "x": {
                            "field": "alerts",
                            "type": "quantitative",
                            "title": "Alert records",
                            "axis": {"tickMinStep": 1},
                        },
                        "color": {
                            "field": "severity",
                            "type": "nominal",
                            "scale": {
                                "domain": [
                                    "1 · High",
                                    "2 · Medium",
                                    "3 · Low",
                                    "Unknown",
                                ],
                                "range": ["#c34632", "#ca8421", "#367eb3", "#78838c"],
                            },
                            "legend": None,
                        },
                        "tooltip": [{"field": "severity"}, {"field": "alerts"}],
                    },
                },
                width="stretch",
                height=180,
            )
        else:
            st.info(
                "No alert records in this view. Flow records can still be explored."
            )
        if learning:
            st.caption(
                "Sensor rule priority: 1 is high, 2 medium, 3 low. These labels do not measure the probability of an attack."
            )
    with right:
        st.markdown("#### Transport protocols")
        st.vega_lite_chart(
            spec={
                "data": {"values": summary["protocols"]},
                "mark": {"type": "bar", "color": "#367eb3", "cornerRadiusEnd": 4},
                "encoding": {
                    "y": {
                        "field": "protocol",
                        "type": "nominal",
                        "sort": "-x",
                        "title": None,
                    },
                    "x": {
                        "field": "records",
                        "type": "quantitative",
                        "title": "Alert + flow records",
                        "axis": {"tickMinStep": 1},
                    },
                    "tooltip": [{"field": "protocol"}, {"field": "records"}],
                },
            },
            width="stretch",
            height=180,
        )
        if learning:
            st.caption(
                "TCP uses connections and delivery checks. UDP sends datagrams without TCP's delivery guarantees. A transport protocol alone does not identify an application or establish malicious intent."
            )


def visual_evidence(runtime, snapshot, candidates, learning):
    st.markdown("#### Evidence behind this view")
    record_type = st.radio(
        "Evidence type",
        ["All records", "Alerts", "Flows"],
        horizontal=True,
        key="visual-record-type",
    )
    candidates = [
        r
        for r in candidates
        if record_type == "All records"
        or r["event_type"] == ("alert" if record_type == "Alerts" else "flow")
    ]
    st.caption(
        f"{len(candidates):,} records match this evidence type and focus. Up to 50 shown, alerts first and newest within each type. Use Alerts or Flows for full pagination."
    )
    if not candidates:
        st.info(
            "No records of this type in the current focus. Choose another type or reset the filters."
        )
        return
    candidates = sorted(
        candidates, key=lambda r: (r["event_type"] != "alert", -r["sequence"])
    )[:50]
    st.dataframe(
        [
            {
                k: r.get(k)
                for k in (
                    "timestamp",
                    "event_type",
                    "src_ip",
                    "dest_ip",
                    "protocol",
                    "alert_signature",
                    "id",
                )
            }
            for r in candidates
        ],
        hide_index=True,
        width="stretch",
        height=260,
        column_config=table_columns(),
    )
    indexed = {r["id"]: r for r in candidates}
    selected = st.selectbox(
        "Inspect visual evidence",
        list(indexed),
        index=next(
            (i for i, r in enumerate(candidates) if r["event_type"] == "alert"), 0
        ),
        format_func=lambda event_id: record_label(indexed[event_id]),
        key="visual-evidence",
    )
    record = indexed[selected]
    if record["event_type"] == "alert":
        st.caption("Selected detection rule")
        st.code(record["alert_signature"], language="text")
    with st.expander("Original evidence and normalized fields", expanded=False):
        inspect_event(runtime, *SCOPE, snapshot, selected)
    if record["event_type"] == "alert" and st.button(
        "Investigate this alert",
        type="primary",
        icon=":material/manage_search:",
        disabled=runtime.status()["investigation_pending"],
    ):
        try:
            start_investigation(
                runtime,
                *SCOPE,
                seed_event_id=selected,
                max_calls=8,
                max_seconds=30.0 if runtime.provider else 5.0,
            )
            st.success(
                "Investigation submitted. Open Investigations for its saved report and citations."
            )
        except (RuntimeError, ValueError) as error:
            st.error(str(error))
    investigation_link("visual-open-investigations")
    if learning:
        with st.expander("Reading this record", expanded=False):
            explain_record(record)
        fundamentals()


def fundamentals():
    with st.expander("Learn the workflow: packets → flows → alerts → investigation"):
        st.markdown("""
1. **Packets** are individual pieces of network traffic. Suricata observes packets on the monitored interface; Blue Cheese reads its EVE output.
2. **Flows** summarize traffic between endpoints. Addresses, ports, protocol, state and byte counters help describe a conversation.
3. **Alerts** record detection-rule matches. A rule can match legitimate activity, so an alert needs context.
4. **Investigation** freezes a bounded evidence snapshot, reviews related records and checks for contradicting evidence. Open citations to verify the reasoning.
5. **Analyst disposition** records your conclusion and next steps. A machine report is a lead, and missing evidence can leave the outcome uncertain.

**Try it:** focus on an IP, compare the timeline and protocols, select a connection, then read an alert's original evidence. Ask: what was observed, what might explain it, and what evidence would change my interpretation?
""")
