"""Case-centered alert-to-decision views for the operational console."""

import json
from datetime import UTC, datetime
from importlib.resources import files

import streamlit as st

from bluecheese.adapters.model_provider import investigation_seconds
from bluecheese.application.telemetry_visuals import connection_graph, summarize
from bluecheese.application.view_context import ViewContext
from bluecheese.interfaces.console_design import record_label, start_investigation
from bluecheese.interfaces.console_report import show_report
from bluecheese.interfaces.demo import inspect_event

SCOPE = ("live", "external")
DISPOSITIONS = [
    "OPEN",
    "INVESTIGATING",
    "ESCALATED",
    "CLOSED_BENIGN",
    "CLOSED_INCIDENT",
]


def open_run(run_id):
    st.session_state["open-case-run"] = run_id
    st.session_state["navigate-case"] = True
    st.rerun(scope="app")


def attention(runtime, snapshot):
    st.subheader("What needs attention?")
    st.caption(
        "Sensor priority guides review. An alert alone does not establish compromise."
    )
    page = st.number_input(
        "Alert review page", min_value=1, step=1, key="attention-page"
    )
    result = runtime.command("attention", *SCOPE, snapshot, page=page)
    st.caption(
        f"{result['total']:,} stored alerts · priority-ranked page {result['page']} · groups contain occurrences from this 20-alert page"
    )
    if not result["groups"]:
        st.info(
            "No detection alerts yet. Connect a sensor in the sidebar. Saved flow evidence is available under Network."
        )
        return
    for group in result["groups"]:
        row = group["seed"]["normalized"]
        with st.container(border=True):
            st.markdown("#### " + group["priority"].title() + " priority")
            st.text(
                f"{row.get('src_ip') or 'Unknown endpoint'} → {row.get('dest_ip') or '?'}"
            )
            st.code(row.get("alert_signature") or "Detection alert", language="text")
            st.caption(
                f"{group['occurrence_count']} alert occurrence(s) · First {group['first_seen']} · Last {group['last_seen']}"
            )
            st.caption(
                f"Priority reason: Suricata severity {row.get('severity') or 'unknown'}; asset importance and authorization are unknown."
            )
            if group["run_id"]:
                st.caption("Analysis " + group["run_status"].replace("_", " ").lower())
                st.caption(
                    (group.get("disposition") or "OPEN").replace("_", " ").title()
                )
                if group.get("owner"):
                    st.caption("Owner: " + group["owner"])
                if group.get("new_alerts"):
                    st.info(
                        f"{group['new_alerts']} new alert(s) since the saved investigation snapshot"
                    )
                    if st.button(
                        "Analyze new activity",
                        key="new-" + group["seed_ids"][0],
                        disabled=runtime.status()["investigation_pending"],
                    ):
                        prior = runtime.command("get_run", *SCOPE, group["run_id"])
                        start_investigation(
                            runtime,
                            *SCOPE,
                            question=prior["question"],
                            seed_event_id=prior["seed_event_id"],
                            parent_run_id=prior["run_id"],
                            max_calls=8,
                            max_seconds=investigation_seconds(runtime.provider),
                        )
                if st.button(
                    "Open investigation",
                    key="open-" + group["seed_ids"][0],
                    width="stretch",
                ):
                    open_run(group["run_id"])
            elif st.button(
                "Investigate",
                key="review-" + group["seed_ids"][0],
                type="primary",
                disabled=runtime.status()["investigation_pending"],
                width="stretch",
            ):
                start_investigation(
                    runtime,
                    *SCOPE,
                    seed_event_id=group["seed_ids"][0],
                    max_calls=8,
                    max_seconds=investigation_seconds(runtime.provider),
                )
    with st.expander("What will be investigated?"):
        st.write(
            "Your selected alert and records from the same source for its directed endpoint pair within ±5 minutes. Each investigation freezes its own evidence snapshot."
        )


def render_activity(runtime, run_id):
    saved = runtime.command("get_run", *SCOPE, run_id)
    if not saved:
        st.info("Investigation unavailable.")
        return
    events = (
        saved.get("workflow_activity")
        or (saved.get("report") or {}).get("workflow_activity")
        or []
    )
    active = saved["status"] in ("RUNNING", "QUEUED")
    if active:
        activity = runtime.activity.snapshot()
        duration = activity["elapsed_seconds"] if activity["run_id"] == run_id else 0
        st.info(
            "Analysis running · "
            + (events[-1]["role"] if events else "Starting")
            + f" · {duration:.1f}s elapsed"
        )
        if st.button("Cancel investigation", key="cancel-" + run_id):
            runtime.cancel()
            st.info(
                "Cancellation requested; an active model request must return before stopping."
            )
    else:
        st.caption("Analysis " + saved["status"].replace("_", " ").lower())
    if not events:
        st.info("No recorded activity is available for this older run.")
    roles = (
        "Orchestrator",
        "Triage",
        "Correlation",
        "Investigator",
        "Falsifier",
        "Reporter",
    )
    for role in roles:
        role_events = [event for event in events if event["role"] == role]
        if not role_events:
            continue
        last = role_events[-1]
        label = last["status"].replace("_", " ")
        if not active and last["status"] in ("working", "queued", "cancel_requested"):
            label = "stopped · " + saved["status"].lower()
        with st.expander(
            f"{role} · {label}",
            expanded=active and role == events[-1]["role"],
        ):
            for event in role_events:
                st.caption(f"{event['elapsed_seconds']:.1f}s · {event['kind']}")
                st.text(event["message"])
            report = saved.get("report") or {}
            if role == "Triage" and report.get("triage"):
                for group in report["triage"].get("candidates", []):
                    st.text(
                        f"{group['priority'].title()} priority · {group['occurrence_count']} occurrences · {group['reason']}"
                    )
            elif role == "Correlation":
                for group in report.get("correlation", []):
                    st.text(
                        f"Linked {len(group['member_ids'])} records; excluded {group['excluded_count']} candidates."
                    )
                    with st.expander("Relationship checks"):
                        st.json(group)
            elif role == "Falsifier" and report.get("falsifier"):
                st.text("Test: " + report.get("disconfirmation_test", ""))
                st.json(report["falsifier"], expanded=False)
            elif role == "Reporter" and report:
                st.text(
                    f"Saved {len(report.get('claims', []))} claims with {len(set(report['supporting_ids'] + report['contradicting_ids']))} evidence references."
                )
    with st.expander("Chronological technical trace"):
        role_filter = st.multiselect(
            "Trace roles",
            sorted({e["role"] for e in events}),
            key="trace-role-" + run_id,
        )
        type_filter = st.multiselect(
            "Trace types",
            sorted({e["kind"] for e in events}),
            key="trace-type-" + run_id,
        )
        for event in events:
            if role_filter and event["role"] not in role_filter:
                continue
            if type_filter and event["kind"] not in type_filter:
                continue
            st.text(
                f"{event['elapsed_seconds']:.1f}s · {event['role']} · {event['kind']} · {event['message']}"
            )
            st.json(
                {
                    key: event.get(key, "unavailable")
                    for key in (
                        "operation_id",
                        "implementation",
                        "arguments",
                        "duration_seconds",
                        "returned_count",
                        "truncated",
                        "outcome",
                    )
                },
                expanded=False,
            )
    calls = saved.get("tool_activity", [])
    with st.expander(f"Actual evidence queries ({len(calls)})"):
        for index, call in enumerate(calls):
            st.text(
                f"{index + 1}. {call.get('role', 'Agent')} · {call['tool']} · {call['status']} · {call.get('returned_count', 0)} records"
            )
            st.json(call.get("arguments", {}), expanded=False)
            if call.get("truncated"):
                st.warning("Evidence delivery was truncated.")
            ids = call.get("returned_ids", [])
            if ids:
                chosen = st.selectbox(
                    "Retrieved record",
                    ids,
                    key=f"tool-{run_id}-{index}",
                    format_func=lambda value, records=ids: (
                        f"Record {records.index(value) + 1}"
                    ),
                )
                with st.expander("Open retrieved evidence"):
                    inspect_event(
                        runtime, *SCOPE, saved["snapshot"], chosen, saved["snapshot_id"]
                    )
    with st.expander("Execution limits and model calls"):
        report = saved.get("report") or {}
        st.json(
            {
                "budget": report.get("budget"),
                "provider": report.get("provider"),
                "requests": report.get("provider_activity"),
            }
        )
        st.caption(
            "Tool limits bound retrieval. The time limit is cooperative; an in-flight model call must return before cancellation takes effect."
        )


def _execute_proposal(runtime, result, saved):
    action, argument = result["action"], result.get("argument", "")
    if runtime.practice and action in ("import", "follow", "stop"):
        raise ValueError(
            "Practice accepts synthetic fixture input. Open the operational workspace to manage sources."
        )
    if action == "investigate" and saved:
        runtime.begin_run(
            *SCOPE,
            question=argument or saved["question"],
            seed_event_id=saved["seed_event_id"],
            parent_run_id=saved["run_id"],
            max_calls=8,
            max_seconds=investigation_seconds(runtime.provider),
        )
        runtime.command(
            "append_chat",
            *SCOPE,
            saved["run_id"],
            "assistant",
            json.dumps(
                {
                    "reply": "Follow-up investigation started. Its new evidence snapshot and activity are available in the new revision.",
                    "action": "answer",
                    "citations": [],
                }
            ),
        )
        if runtime.practice:
            st.session_state["follow-next-run"] = True
        else:
            st.session_state["show-submitted-investigation"] = True
        st.rerun(scope="app")
    # Reuse the CLI's validated handlers for explicit source/test proposals.
    from bluecheese.interfaces.terminal import TerminalSession

    output = []
    session = TerminalSession(runtime, read=lambda _: "yes", write=output.append)
    if action in ("import", "follow", "stop", "test"):
        session.execute(action, argument)
        runtime.command(
            "append_chat",
            *SCOPE,
            result.get("run_id"),
            "assistant",
            json.dumps(
                {"reply": "\n".join(output), "action": "answer", "citations": []}
            ),
        )
        st.rerun(scope="app")


def chat_panel(runtime, run_id=None):
    saved = runtime.command("get_run", *SCOPE, run_id) if run_id else None
    st.subheader("Ask Blue Cheese")
    st.caption(
        "This conversation uses "
        + (
            "this investigation’s frozen evidence and recorded activity."
            if saved
            else "current sensor status and workspace evidence. Select an investigation for case-specific questions."
        )
    )
    if not runtime.provider:
        st.caption(
            "Local commands are available. Definitions, summaries and current-state explanations also work offline."
        )
    history = runtime.command("chat_history", *SCOPE, run_id)
    for index, item in enumerate(history):
        with st.chat_message(item["role"]):
            if item["role"] == "user":
                st.text(item["content"])
                continue
            try:
                result = json.loads(item["content"])
            except (ValueError, TypeError):
                result = {"reply": item["content"]}
            if result.get("scope"):
                st.caption("Response scope: " + result["scope"])
            st.text(result.get("reply", ""))
            for citation in result.get("citations", []):
                if saved or result.get("snapshot") is not None:
                    with st.expander(
                        "Evidence citation "
                        + str(result["citations"].index(citation) + 1)
                    ):
                        inspect_event(
                            runtime,
                            *SCOPE,
                            result.get(
                                "snapshot", saved["snapshot"] if saved else None
                            ),
                            citation,
                            (result.get("view_context") or {}).get("snapshot_id")
                            or (
                                saved["snapshot_id"]
                                if saved and result.get("run_id") == run_id
                                else None
                            ),
                        )
            if result.get("retrieval"):
                with st.expander("Evidence used for this answer"):
                    st.json(result["retrieval"])
            if index == len(history) - 1 and result.get("action") in (
                "investigate",
                "import",
                "follow",
                "stop",
                "test",
            ):
                st.caption("Proposed action · awaiting your confirmation")
                if st.button(
                    "Run proposed action", key="proposal-" + item["created_at"]
                ):
                    try:
                        _execute_proposal(runtime, result, saved)
                    except (OSError, ValueError, RuntimeError) as error:
                        st.error(str(error))
            if result.get("view") in ("Needs attention", "Network") and st.button(
                "Open " + result["view"], key="chat-view-" + item["created_at"]
            ):
                st.session_state["navigate-page"] = (
                    "Overview" if result["view"] == "Network" else "Needs attention"
                )
                st.rerun(scope="app")
    future = runtime.pending_chat
    busy = future is not None and not future.done()
    if busy:
        started = getattr(runtime, "chat_started", None)
        elapsed = (datetime.now(UTC) - started).total_seconds() if started else 0
        st.info(
            f"Chat request running · {elapsed:.1f}s elapsed · waiting for model or evidence query"
        )
        if st.button("Cancel chat request", key="cancel-chat-" + str(run_id)):
            runtime.cancel_chat()
            st.info("Cancellation requested. Waiting for the active request to return.")
    error_key = "chat-submit-error-" + str(run_id)
    chat_key = "case-chat-" + str(run_id)

    def submit(message=None):
        # Widget callbacks run once per submission, before rendering the fragment.
        # An app rerun after reading chat_input can replay its trigger value.
        message = message or st.session_state.get(chat_key)
        if not message:
            return
        try:
            current = runtime.command("get_run", *SCOPE, run_id) if run_id else None
            runtime.begin_chat(message, run_id, captured_view(runtime, current))
        except (ValueError, RuntimeError) as error:
            st.session_state[error_key] = str(error)

    for label in (
        "Explain this view",
        "What is happening now?",
        "Show the evidence",
        "What should I check next?",
    ):
        st.button(
            label,
            key=f"ask-{run_id}-{label}",
            disabled=busy,
            width="stretch",
            on_click=submit,
            args=(label,),
        )
    st.chat_input(
        "Ask what happened, what is running, or what to check next…",
        key=chat_key,
        disabled=busy,
        max_chars=4096,
        on_submit=submit,
    )
    error = st.session_state.pop(error_key, None)
    if error:
        st.error(error)


def investigation_workspace(runtime, counts):
    history = runtime.command("list_runs", *SCOPE)
    pending = runtime.activity.snapshot()
    if st.session_state.pop("follow-submitted-run", False):
        st.session_state["follow-next-run"] = True
    if (
        st.session_state.get("follow-next-run")
        and pending["run_id"]
        and any(row["run_id"] == pending["run_id"] for row in history)
    ):
        st.session_state["saved-investigation"] = pending["run_id"]
        st.session_state["follow-next-run"] = False
    requested = st.session_state.pop("open-case-run", None)
    if requested and any(row["run_id"] == requested for row in history):
        st.session_state["saved-investigation"] = requested
    if not history:
        st.info("Choose an alert under Needs attention to open an investigation.")
        if runtime.status()["investigation_pending"]:
            st.info("Preparing your investigation and freezing its evidence…")
        st.fragment(run_every=1.0)(chat_panel)(runtime)
        advanced_controls(runtime, counts)
        return
    by_id = {row["run_id"]: row for row in history}
    if st.session_state.get("saved-investigation") not in by_id:
        st.session_state["saved-investigation"] = next(iter(by_id))
    selected = st.selectbox(
        "Saved investigation",
        list(by_id),
        key="saved-investigation",
        format_func=lambda value: (
            f"{by_id[value].get('title') or by_id[value].get('question')} · {by_id[value]['created_at'][:19].replace('T', ' ')}"
        ),
    )
    saved = runtime.command("get_run", *SCOPE, selected)
    st.text(saved.get("title") or saved.get("question") or "Evidence investigation")
    st.caption(
        f"{saved.get('record_count', 0):,} frozen records · {saved.get('pair_count', 0)} directed IP pairs · Question: {saved.get('question', '')}"
    )
    if saved.get("seed_event_id"):
        st.caption(
            "Scope: selected alert + same-source directed endpoint pair within ±5 minutes. New arrivals do not change this snapshot."
        )
    st.fragment(run_every=1.0)(activity_header)(runtime, selected)
    evidence_column, chat_column = st.columns([3, 2])
    with evidence_column:
        if "case-tab-" + selected not in st.session_state:
            st.session_state["case-tab-" + selected] = (
                "Agent activity"
                if saved["status"] in ("RUNNING", "QUEUED")
                else "Findings"
            )
        tabs = st.tabs(
            [
                "Findings",
                "Evidence and connections",
                "Agent activity",
                "Analyst decision",
            ],
            default="Findings",
            key="case-tab-" + selected,
            on_change="rerun",
        )
        with tabs[0]:
            if saved.get("report"):
                show_report(runtime, saved["report"], "case-" + selected)
            elif saved["status"] in ("RUNNING", "QUEUED"):
                st.info(
                    "Investigation running. Actual operations are recorded under Agent activity; findings appear here when saved."
                )
            else:
                st.warning(
                    "Analysis "
                    + saved["status"].lower()
                    + ". Review recorded activity before retrying."
                )
                if saved.get("error"):
                    st.code(saved["error"], language="text")
            if st.button(
                "Create successor investigation",
                disabled=runtime.status()["investigation_pending"],
            ):
                start_investigation(
                    runtime,
                    *SCOPE,
                    question=saved["question"],
                    seed_event_id=saved.get("seed_event_id"),
                    parent_run_id=selected,
                    max_calls=8,
                    max_seconds=investigation_seconds(runtime.provider),
                )
        with tabs[1]:
            rows = runtime.command("case_evidence", *SCOPE, selected)
            summary = summarize(rows)
            st.caption(
                f"Showing the newest {len(rows):,} of {saved.get('record_count', 0):,} frozen records; graph shows up to 12 IP pairs."
            )
            if summary["connections"]:
                pairs = [
                    (pair["source"], pair["destination"])
                    for pair in summary["connections"]
                ]
                connection = st.selectbox(
                    "Selected connection",
                    [None, *pairs],
                    key="connection-" + selected,
                    format_func=lambda pair: (
                        "All connections" if pair is None else " → ".join(pair)
                    ),
                )
                st.graphviz_chart(
                    connection_graph(summary["connections"], connection),
                    width="stretch",
                )
                if connection:
                    rows = [
                        row
                        for row in rows
                        if (row.get("src_ip"), row.get("dest_ip")) == connection
                    ]
                endpoint = st.text_input("Endpoint filter", key="endpoint-" + selected)
                if endpoint:
                    rows = [
                        row
                        for row in rows
                        if endpoint in (row.get("src_ip"), row.get("dest_ip"))
                    ]
                kind = st.selectbox(
                    "Record type", ["All", "alert", "flow"], key="kind-" + selected
                )
                if kind != "All":
                    rows = [row for row in rows if row["event_type"] == kind]
            if summary["timeline"]:
                st.vega_lite_chart(
                    {
                        "data": {"values": summary["timeline"]},
                        "mark": {"type": "line", "point": True},
                        "encoding": {
                            "x": {
                                "field": "time",
                                "type": "temporal",
                                "title": "Event time (UTC)",
                                "scale": {"type": "utc"},
                            },
                            "y": {"field": "records", "type": "quantitative"},
                            "color": {"field": "type"},
                        },
                    },
                    width="stretch",
                    height=180,
                )
            if rows:
                if st.session_state.get("evidence-" + selected) not in {
                    row["id"] for row in rows
                }:
                    st.session_state["evidence-" + selected] = None
                chosen = st.selectbox(
                    "Inspect case evidence",
                    [None, *[row["id"] for row in rows]],
                    key="evidence-" + selected,
                    format_func=lambda value: (
                        "Select a record"
                        if value is None
                        else record_label(
                            next(row for row in rows if row["id"] == value)
                        )
                    ),
                )
                if chosen:
                    with st.expander("Evidence drawer", expanded=True):
                        inspect_event(
                            runtime,
                            *SCOPE,
                            saved["snapshot"],
                            chosen,
                            saved["snapshot_id"],
                        )
        with tabs[2]:
            st.fragment(run_every=1.0)(render_activity)(runtime, selected)
        with tabs[3]:
            with st.form("decision-" + selected):
                actor = st.text_input("Analyst", max_chars=128)
                owner = st.text_input(
                    "Assigned to", value=saved.get("owner", ""), max_chars=128
                )
                disposition = st.selectbox(
                    "Disposition",
                    DISPOSITIONS,
                    index=DISPOSITIONS.index(saved.get("disposition", "OPEN")),
                    format_func=lambda value: value.replace("_", " ").title(),
                )
                note = st.text_area("Note", max_chars=8192)
                st.caption(
                    "Local attribution only; analyst names are not authenticated accounts."
                )
                if st.form_submit_button("Save analyst action"):
                    try:
                        runtime.command(
                            "save_case_decision",
                            *SCOPE,
                            selected,
                            actor,
                            owner,
                            disposition,
                            note,
                        )
                        st.success(
                            "Assignment and decision saved. Evidence and machine report retained."
                        )
                    except ValueError as error:
                        st.error(str(error))
            actions = runtime.command("analyst_history", *SCOPE, selected)
            if actions:
                st.dataframe(actions, hide_index=True, width="stretch")
    with chat_column:
        st.fragment(run_every=1.0)(chat_panel)(runtime, selected)
    with st.expander("Run history and revisions"):
        st.dataframe(
            [
                {
                    "Investigation": row.get("title") or row.get("question"),
                    "Started": row["created_at"][:19],
                    "Analysis": row["status"],
                    "Decision": row.get("disposition"),
                    "Owner": row.get("owner"),
                    "Revision": row["case_revision"],
                }
                for row in history
            ],
            hide_index=True,
            width="stretch",
        )
    advanced_controls(runtime, counts)


def advanced_controls(runtime, counts):
    with st.expander("Advanced: manual scope and investigation limits"):
        latest = runtime.command(
            "browse_telemetry", *SCOPE, runtime.command("snapshot")
        )["rows"]
        by_id = {row["id"]: row for row in latest}
        seed = st.selectbox(
            "Scope alert",
            [*by_id, "Whole external scope"],
            format_func=lambda value: (
                record_label(by_id[value]) if value in by_id else value
            ),
        )
        question = st.text_input(
            "Case question",
            value="What does the observed alert and related flow evidence support?",
        )
        max_calls = st.number_input("Tool calls", min_value=0, max_value=20, value=8)
        seconds = st.number_input(
            "Seconds (cooperative limit)",
            min_value=0.0,
            value=investigation_seconds(runtime.provider),
        )
        falsification = st.checkbox("Check contradicting evidence", value=True)
        st.caption(
            "Time limits stop the next step; they cannot preempt an in-flight model request. Whole scope is limited to 10,000 records."
        )
        if st.button(
            "Start investigation",
            disabled=runtime.status()["investigation_pending"]
            or not counts["accepted"]
            or (seed == "Whole external scope" and counts["accepted"] > 10000),
            type="primary",
        ):
            try:
                start_investigation(
                    runtime,
                    *SCOPE,
                    question=question,
                    seed_event_id=None if seed == "Whole external scope" else seed,
                    max_calls=max_calls,
                    max_seconds=seconds,
                    falsification=falsification,
                )
            except (ValueError, RuntimeError) as error:
                st.error(str(error))


def captured_view(runtime, saved=None):
    """Capture widget values at submission; later navigation cannot retarget an answer."""
    run_id = saved["run_id"] if saved else None
    page = st.session_state.get("current-view-page", "Workspace")
    task = st.session_state.get("case-tab-" + run_id, "Findings") if run_id else page
    view = ViewContext(
        page=page,
        task=task,
        run_id=run_id,
        snapshot=saved["snapshot"] if saved else runtime.command("snapshot"),
        snapshot_id=saved["snapshot_id"] if saved else None,
        display_limit=1000
        if saved
        else st.session_state.get("visual-limit", 1000)
        if page == "Overview"
        else 20,
    )
    from dataclasses import replace

    if run_id and task == "Evidence and connections":
        return replace(
            view,
            connection=st.session_state.get("connection-" + run_id),
            endpoint=st.session_state.get("endpoint-" + run_id, ""),
            evidence_id=st.session_state.get("evidence-" + run_id) or "",
            event_type=st.session_state.get("kind-" + run_id, "").replace("All", ""),
        )
    if page in ("Alerts", "Flows"):
        kind = "alert" if page == "Alerts" else "flow"
        severity = st.session_state.get("alert-severity")
        return replace(
            view,
            endpoint=st.session_state.get(kind + "-ip", ""),
            signature=st.session_state.get(kind + "-signature", ""),
            severity=severity if isinstance(severity, int) else None,
            event_type=kind,
            evidence_id=st.session_state.get(kind + "-evidence") or "",
        )
    if page == "Overview":
        view = replace(view, task=st.session_state.get("network-tab", "Connections"))
        pair = st.session_state.get("visual-pair", "All connections")
        endpoint = st.session_state.get("visual-endpoint", "All endpoints")
        return replace(
            view,
            connection=tuple(pair.split(" → ")) if pair != "All connections" else None,
            endpoint=endpoint if endpoint != "All endpoints" else "",
            evidence_id=st.session_state.get("visual-evidence") or "",
        )
    if page == "Needs attention":
        return replace(view, event_type="alert")
    return view


def activity_header(runtime, run_id):
    saved = runtime.command("get_run", *SCOPE, run_id)
    events = saved.get("workflow_activity") or []
    active = saved["status"] in ("RUNNING", "QUEUED")
    snapshot = runtime.activity.snapshot()
    a, b, c = st.columns(3)
    a.metric("Analysis", saved["status"].replace("_", " ").title())
    b.metric("Decision", saved.get("disposition", "OPEN").replace("_", " ").title())
    c.metric("Assigned to", saved.get("owner") or "Unassigned")
    engine = (saved.get("report") or {}).get("provider")
    if (
        not engine
        and runtime.activity.snapshot()["run_id"] == run_id
        and saved["status"] in ("RUNNING", "QUEUED")
    ):
        engine = runtime.provider.label if runtime.provider else "Offline rules"
    st.caption(
        f"Target: {saved.get('title') or saved['question']} · Snapshot: {saved['snapshot_id'][:8]} (watermark {saved['snapshot']}) · Engine: {engine or 'historical details unavailable'} · {'Live execution' if saved['status'] in ('RUNNING', 'QUEUED') else 'Saved result'}"
    )
    st.markdown("**Current activity**")
    if active:
        elapsed = snapshot["elapsed_seconds"] if snapshot["run_id"] == run_id else 0
        latest = events[-1] if events else None
        st.info(
            f"{saved['status'].title()} · {elapsed:.1f}s elapsed · "
            + (latest["message"] if latest else "Preparing evidence snapshot")
        )
        if latest and latest.get("handoff_to"):
            st.caption("Next software-controlled stage: " + latest["handoff_to"])
        elif (
            latest and latest["kind"] == "model" and latest.get("outcome") == "STARTED"
        ):
            st.caption(
                f"Waiting for model · {max(0, elapsed - latest['elapsed_seconds']):.1f}s · next: validate the returned response"
            )
        else:
            st.caption("Next: finish the active operation and validate its result.")
    else:
        st.caption(
            "Execution "
            + saved["status"].lower()
            + " · "
            + (
                events[-1]["message"]
                if events
                else "Historical activity details unavailable"
            )
        )
        if saved.get("report"):
            st.success(
                "Findings saved. Next: review evidence and record your decision."
            )
            if st.button("Review findings", key="review-findings-" + run_id):
                st.session_state["case-tab-" + run_id] = "Findings"
                st.rerun(scope="app")
    completed = [e for e in events if e["kind"] == "tool" and e.get("outcome") == "OK"]
    st.caption(
        f"Recorded completed queries: {len(completed)} · delivered records across queries: {sum(e.get('returned_count', 0) for e in completed)} · latest 128 activity events retained"
    )


def practice_checkpoints(runtime, run_id=None):
    saved = runtime.command("get_run", *SCOPE, run_id) if run_id else None
    return {
        "Input ready": runtime.command("counts", *SCOPE)["accepted"] > 0,
        "Target selected": bool(saved and saved.get("seed_event_id")),
        "Evidence retrieved": bool(
            saved
            and any(
                call.get("status") == "OK" for call in saved.get("tool_activity", [])
            )
        ),
        "Analysis finished": bool(saved and saved["status"] == "COMPLETED"),
        "Decision recorded": bool(
            saved and runtime.command("analyst_history", *SCOPE, run_id)
        ),
    }


def practice_workspace(runtime):
    st.info(
        "Practice investigation · synthetic saved input · separate state database · offline rules by default. No packet capture or live sensor."
    )
    counts = runtime.command("counts", *SCOPE)
    if not counts["accepted"]:
        st.write(
            "Next: load the synthetic input. Loading evidence does not start analysis."
        )
        if st.button("Prepare practice input", type="primary"):
            runtime.command(
                "import_file",
                files("bluecheese.data").joinpath("suspicious-clean.jsonl"),
                *SCOPE,
            )
            st.rerun(scope="app")
    else:
        alerts = runtime.command(
            "list_alerts", *SCOPE, runtime.command("snapshot"), limit=20
        )
        by_id = {row["id"]: row for row in alerts}
        seed = st.selectbox(
            "Practice target",
            [None, *by_id],
            key="practice-target",
            format_func=lambda value: (
                "Choose an alert"
                if value is None
                else record_label(by_id[value]["normalized"])
            ),
        )
        st.caption(
            "Choose a target for a bounded investigation. Review its findings and save an analyst action."
        )
        st.fragment(run_every=1.0)(practice_run_button)(runtime, seed)
    st.fragment(run_every=1.0)(practice_progress)(runtime)
    history = runtime.command("list_runs", *SCOPE)
    if history or runtime.status()["investigation_pending"]:
        investigation_workspace(runtime, counts)


def practice_progress(runtime):
    history = runtime.command("list_runs", *SCOPE)
    selected = st.session_state.get("saved-investigation")
    if selected not in {row["run_id"] for row in history}:
        selected = history[0]["run_id"] if history else None
    checks = practice_checkpoints(runtime, selected)
    if not selected:
        checks["Target selected"] = bool(st.session_state.get("practice-target"))
    st.write(
        " · ".join(("✓ " if done else "○ ") + label for label, done in checks.items())
    )


def practice_run_button(runtime, seed):
    if st.button(
        "Run practice investigation",
        disabled=not seed or runtime.status()["investigation_pending"],
    ):
        runtime.begin_run(
            *SCOPE,
            seed_event_id=seed,
            max_calls=8,
            max_seconds=investigation_seconds(runtime.provider),
        )
        st.session_state["follow-next-run"] = True
        st.rerun(scope="app")
