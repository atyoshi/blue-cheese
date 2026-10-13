"""Case-centered alert-to-decision views for the operational console."""

import json
from datetime import UTC, datetime

import streamlit as st

from bluecheese.adapters.model_provider import investigation_seconds
from bluecheese.application.telemetry_visuals import connection_graph, summarize
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
            "Local commands are available. Configure a model in Settings for conversational explanations."
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
                            saved["snapshot"] if saved else result["snapshot"],
                            citation,
                            saved["snapshot_id"] if saved else None,
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
    prompt = st.chat_input(
        "Ask what happened, what is running, or what to check next…",
        key="case-chat-" + str(run_id),
        disabled=busy,
        max_chars=4096,
    )
    if prompt:
        try:
            runtime.begin_chat(prompt, run_id)
            st.rerun(scope="fragment")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))


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
    selected = st.selectbox(
        "Saved investigation",
        list(by_id),
        key="saved-investigation",
        format_func=lambda value: (
            f"{by_id[value].get('title') or by_id[value].get('question')} · {by_id[value]['created_at'][:19].replace('T', ' ')} · {by_id[value]['status'].lower()}"
        ),
    )
    saved = runtime.command("get_run", *SCOPE, selected)
    st.text(saved.get("title") or saved.get("question") or "Evidence investigation")
    a, b, c = st.columns(3)
    a.metric("Analysis", saved["status"].replace("_", " ").title())
    b.metric("Decision", saved.get("disposition", "OPEN").replace("_", " ").title())
    c.metric("Assigned to", saved.get("owner") or "Unassigned")
    st.caption(
        f"{saved.get('record_count', 0):,} frozen records · {saved.get('pair_count', 0)} directed IP pairs · Question: {saved.get('question', '')}"
    )
    if saved.get("seed_event_id"):
        st.caption(
            "Scope: selected alert + same-source directed endpoint pair within ±5 minutes. New arrivals do not change this snapshot."
        )
    evidence_column, chat_column = st.columns([3, 2])
    with evidence_column:
        tabs = st.tabs(
            [
                "Findings",
                "Evidence and connections",
                "Agent activity",
                "Analyst decision",
            ],
            default="Agent activity"
            if saved["status"] in ("RUNNING", "QUEUED")
            else "Findings",
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
                st.graphviz_chart(
                    connection_graph(summary["connections"]), width="stretch"
                )
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
                            },
                            "y": {"field": "records", "type": "quantitative"},
                            "color": {"field": "type"},
                        },
                    },
                    width="stretch",
                    height=180,
                )
            if rows:
                chosen = st.selectbox(
                    "Inspect case evidence",
                    [row["id"] for row in rows],
                    format_func=lambda value: record_label(
                        next(row for row in rows if row["id"] == value)
                    ),
                )
                inspect_event(
                    runtime, *SCOPE, saved["snapshot"], chosen, saved["snapshot_id"]
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
