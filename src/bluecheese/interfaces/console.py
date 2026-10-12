"""Local analyst console for externally supplied Suricata telemetry."""

import json
import os
from pathlib import Path

import streamlit as st

from bluecheese.adapters.agent_provider import AgentModelProvider, completion_endpoint
from bluecheese.adapters.model_provider import ModelProfile, investigation_seconds
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.source_path import readable_eve_path
from bluecheese.interfaces.console_activity import agent_activity
from bluecheese.interfaces.console_design import (
    apply_design,
    investigation_link,
    record_label,
    table_columns,
)
from bluecheese.interfaces.console_report import show_report
from bluecheese.interfaces.demo import inspect_event
from bluecheese.interfaces.network_overview import explain_record, overview

SCOPE = ("live", "external")


@st.cache_resource
def get_runtime(state_dir):
    return DemoRuntime(state_dir, load_fixtures=False)


def provider_controls(runtime):
    provider = runtime.provider
    profile = provider.profile if provider else None
    busy = runtime.status()["investigation_pending"] or runtime.run_lock.locked()
    st.caption(
        "Investigator and Falsifier can use an OpenAI-compatible server. "
        "Triage and correlation use rules. Settings last for this app process."
    )
    with st.form("agent-provider-settings", clear_on_submit=True):
        mode = st.selectbox(
            "Investigation engine",
            ["Rule-based", "Model agents"],
            index=1 if provider else 0,
        )
        endpoint = st.text_input(
            "API base URL or Chat Completions URL",
            value=profile.endpoint if profile else "http://127.0.0.1:8080/v1",
        )
        model = st.text_input(
            "Investigator model", value=profile.model if profile else ""
        )
        falsifier_model = st.text_input(
            "Falsifier model (blank uses Investigator)",
            value=getattr(provider, "falsifier_model", ""),
        )
        api_key = st.text_input(
            "API key (optional, kept in memory)",
            type="password",
            help="Leave blank to retain the applied key or use the environment variable below.",
        )
        key_env = st.text_input(
            "API key environment variable",
            value=profile.api_key_env if profile else "BLUECHEESE_MODEL_API_KEY",
        )
        remote = st.checkbox(
            "Allow sending normalized evidence to a remote endpoint",
            value=profile.allow_remote if profile else False,
        )
        insecure_http = st.checkbox(
            "Allow unencrypted remote HTTP",
            value=profile.allow_insecure_http if profile else False,
            help="Requires remote access above. Evidence and any API key travel without encryption.",
        )
        output = st.selectbox(
            "Report format",
            ["Strict JSON Schema", "JSON object"],
            index=1 if getattr(provider, "json_mode", False) else 0,
            help="Use JSON object for servers without strict schema support. Both modes validate reports and citations locally.",
        )
        attempts = st.number_input(
            "Maximum model calls per investigation",
            min_value=2,
            max_value=12,
            value=getattr(provider, "max_attempts", 6),
        )
        timeout = st.number_input(
            "Timeout per model call (seconds)",
            min_value=1.0,
            max_value=600.0,
            value=float(profile.timeout) if profile else 20.0,
        )
        tokens = st.number_input(
            "Maximum output tokens per call",
            min_value=128,
            max_value=8192,
            value=profile.max_output_tokens if profile else 2048,
        )
        apply = st.form_submit_button("Apply agent settings", disabled=busy)
    if apply:
        try:
            selected = None
            if mode == "Model agents":
                selected = AgentModelProvider(
                    ModelProfile(
                        endpoint=completion_endpoint(endpoint),
                        model=model.strip(),
                        api_key_env=key_env.strip(),
                        timeout=timeout,
                        max_output_tokens=tokens,
                        allow_remote=remote,
                        allow_insecure_http=insecure_http,
                        enable_thinking=profile.enable_thinking if profile else None,
                        api_key=api_key
                        or (
                            profile.api_key
                            if profile
                            and profile.endpoint == completion_endpoint(endpoint)
                            and profile.api_key_env == key_env.strip()
                            else ""
                        ),
                    ),
                    max_attempts=attempts,
                    json_mode=output == "JSON object",
                    falsifier_model=falsifier_model,
                )
            runtime.configure_provider(selected)
            st.session_state.pop("agent-provider-test", None)
            st.success(
                "Agent settings applied."
                if selected
                else "Rule-based investigation enabled."
            )
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
    st.caption(
        "Models receive normalized observations, including IPs and signatures; exact raw logs are omitted. "
        "Keys are never saved to reports or disk. Test sends synthetic data and may incur endpoint usage."
    )
    if st.button(
        "Test agent connection",
        disabled=busy or not isinstance(runtime.provider, AgentModelProvider),
    ):
        try:
            with st.spinner("Testing tool calling and structured reports…"):
                result = runtime.test_provider()
            st.session_state["agent-provider-test"] = result
        except (ValueError, RuntimeError) as error:
            st.session_state["agent-provider-test"] = {
                "status": "failed",
                "error": str(error),
            }
    if "agent-provider-test" in st.session_state:
        st.json(st.session_state["agent-provider-test"])


def source_controls(runtime):
    current = runtime.status()
    mode = st.selectbox(
        "Telemetry input",
        ["EVE file", "Unix stream"],
        disabled=current["running"],
        help="EVE file follows a growing log live or reads a completed capture. Unix stream receives EVE JSON over a local socket.",
    )
    streaming = mode == "Unix stream"
    recover_rotation = False
    if streaming:
        path = st.text_input(
            "Unix socket path",
            value=str(runtime.state_dir.resolve() / "ingest.sock"),
            key="socket-path",
            disabled=current["running"],
        )
        socket_path = Path(path).expanduser().absolute()
        socket_path = socket_path.parent.resolve() / socket_path.name
        st.caption(
            "Local listener · Start the receiver before Suricata. One producer, same OS user or root."
        )
        with st.expander("Suricata stream configuration"):
            st.code(
                "outputs:\n  - eve-log:\n      enabled: yes\n      filetype: unix_stream\n      filename: "
                + json.dumps(str(socket_path))
                + "\n      types:\n        - alert\n        - flow\n",
                language="yaml",
            )
            st.caption(
                "Merge into your sensor's existing configuration; do not replace its rules or capture settings. Stream input uses a persistent receipt spool capped at 256 MiB; interruptions stop visibly and require explicit reconnect."
            )
    else:
        path = st.text_input(
            "Suricata EVE file",
            value=(current["source"] if current["source_mode"] == "file" else None)
            or os.environ.get("BLUECHEESE_EVE", ""),
            placeholder="Absolute path to an existing EVE file",
            disabled=current["running"],
        )
        st.caption(
            "File path on this server. New lines are followed live; Docker paths refer to mounted files."
        )
        recover_rotation = st.checkbox(
            "Recover rename rotation",
            value=True,
            disabled=current["running"],
            help="Drain the old descriptor for five seconds, then switch to the new generation. Truncation and missing archives still stop ingestion.",
        )
    if st.button(
        "Connect sensor",
        type="primary",
        disabled=current["running"],
        width="stretch",
        icon=":material/link:",
    ):
        try:
            source = socket_path if streaming else readable_eve_path(path)
            current = runtime.status()
            if current["running"] and (
                current["source"] != str(source)
                or current["source_mode"] != ("unix_stream" if streaming else "file")
            ):
                st.error("Disconnect the current sensor before changing inputs.")
            elif not current["running"]:
                if runtime.start(
                    path=source,
                    replay=False,
                    recover_rotation=recover_rotation,
                    unix_stream=streaming,
                ):
                    st.rerun(scope="app")
                st.error(runtime.status()["status"])
        except (OSError, RuntimeError, ValueError) as error:
            st.error(str(error))
    if st.button(
        "Disconnect sensor",
        disabled=not current["running"],
        width="stretch",
        icon=":material/link_off:",
    ):
        runtime.stop()
        st.rerun(scope="app")
    if current["stream_state"]:
        st.caption("Stream: " + current["stream_state"])


def telemetry_table(runtime, snapshot, event_type, learning=False):
    st.caption(
        "Filter the stored evidence, select a record, then investigate or inspect its original log."
    )
    left, middle, right = st.columns(3)
    ip = left.text_input(
        "Endpoint IP", key=event_type + "-ip", help="Exact source or destination IP"
    )
    signature = (
        middle.text_input("Signature contains", key=event_type + "-signature")
        if event_type == "alert"
        else ""
    )
    severity = (
        right.selectbox("Sensor severity", ["All", 1, 2, 3])
        if event_type == "alert"
        else "All"
    )
    page = st.number_input("Page", min_value=1, step=1, key=event_type + "-page")
    result = runtime.command(
        "browse_telemetry",
        *SCOPE,
        snapshot,
        event_type=event_type,
        ip=ip.strip(),
        signature=signature,
        severity=None if severity == "All" else severity,
        page=page,
    )
    st.caption(
        f"{result['total']:,} matches · page {result['page']} · 50 records per page · newest received first"
    )
    rows = result["rows"]
    if not rows:
        st.info("No matching records. Check the sensor connection and filters.")
        return
    columns = (
        [
            "timestamp",
            "severity",
            "alert_signature",
            "src_ip",
            "src_port",
            "dest_ip",
            "dest_port",
            "protocol",
            "id",
        ]
        if event_type == "alert"
        else [
            "timestamp",
            "src_ip",
            "src_port",
            "dest_ip",
            "dest_port",
            "protocol",
            "flow_state",
            "bytes_toserver",
            "bytes_toclient",
            "id",
        ]
    )
    st.dataframe(
        [{k: row[k] for k in columns} for row in rows],
        hide_index=True,
        width="stretch",
        height=300,
        column_config=table_columns(),
    )
    selected = st.selectbox(
        "Inspect evidence",
        [row["id"] for row in rows],
        format_func=lambda event_id: record_label(
            next(row for row in rows if row["id"] == event_id)
        ),
        key=event_type + "-evidence",
    )
    if event_type == "alert" and st.button(
        "Investigate selected alert",
        type="primary",
        icon=":material/manage_search:",
        disabled=runtime.status()["investigation_pending"],
    ):
        try:
            runtime.begin_run(
                *SCOPE,
                seed_event_id=selected,
                max_calls=8,
                max_seconds=investigation_seconds(runtime.provider),
            )
            st.success(
                "Investigation submitted. Open Investigations for the saved result."
            )
        except (RuntimeError, ValueError) as error:
            st.error(str(error))
    if event_type == "alert":
        investigation_link("table-open-investigations")
    with st.expander("Original evidence and normalized fields", expanded=False):
        inspect_event(runtime, *SCOPE, snapshot, selected)
    if learning:
        with st.expander("Reading this record"):
            explain_record(next(row for row in rows if row["id"] == selected))


def investigations(runtime, counts):
    with st.expander("Automatic investigation queue"):
        automatic = st.checkbox(
            "Investigate incoming alerts automatically",
            value=runtime.status()["automatic_investigation"],
        )
        st.caption(
            "Off after restart. One bounded investigation at a time while ingestion is connected. Failed or interrupted work requires an explicit retry."
        )
        if st.button("Apply scheduling policy"):
            runtime.set_automatic(automatic)
        queue = runtime.command("work_queue")
        if queue:
            st.dataframe(queue, hide_index=True, width="stretch")
            if (
                st.button("Investigate next queued alert")
                and not runtime.schedule_once()
            ):
                st.info(
                    "No queued alert is available, or another investigation is active."
                )
            retryable = [
                row["event_id"]
                for row in queue
                if row["status"] in ("FAILED", "INTERRUPTED", "CANCELLED", "INCOMPLETE")
            ]
            if retryable:
                retry = st.selectbox("Retryable alert", retryable)
                if st.button("Requeue selected alert"):
                    runtime.command("retry_work", retry)
                    st.success(
                        "Alert requeued. Start the next queued alert or enable automatic investigation."
                    )
    st.caption(
        "Manual investigation of external telemetry. "
        "Choose an alert to freeze its same-source endpoint neighborhood within five minutes, or investigate the whole scope. "
        "Table filters do not restrict the investigation. Findings are analyst leads, not a compromise verdict."
    )
    question = st.text_input(
        "Case question",
        value="What does the observed alert and related flow evidence support?",
    )
    latest = runtime.command("browse_telemetry", *SCOPE, runtime.command("snapshot"))[
        "rows"
    ]
    seed = st.selectbox(
        "Scope alert (latest 50; select older alerts from Alerts)",
        ["Whole external scope"] + [row["id"] for row in latest],
        format_func=lambda event_id: (
            "Whole external scope"
            if event_id == "Whole external scope"
            else record_label(next(row for row in latest if row["id"] == event_id))
        ),
    )
    seed = None if seed == "Whole external scope" else seed
    with st.expander("Investigation budget"):
        max_calls = st.number_input("Tool calls", min_value=0, max_value=20, value=8)
        max_seconds = st.number_input(
            "Seconds (cooperative limit)",
            min_value=0.0,
            value=60.0 if runtime.provider else 5.0,
        )
        falsification = st.checkbox("Check contradicting evidence", value=True)
    active = runtime.status()["active_run_id"]
    if counts["accepted"] > 10000 and not seed:
        st.warning(
            "Whole-scope investigation exceeds the 10,000-record limit. Select an alert to investigate a bounded neighborhood."
        )
    if st.button(
        "Start investigation",
        type="primary",
        disabled=runtime.status()["investigation_pending"]
        or not counts["accepted"]
        or (counts["accepted"] > 10000 and not seed),
    ):
        try:
            runtime.begin_run(
                *SCOPE,
                question=question,
                seed_event_id=seed,
                max_calls=max_calls,
                max_seconds=max_seconds,
                falsification=falsification,
            )
        except (RuntimeError, ValueError) as error:
            st.error(str(error))
    if st.button("Cancel investigation", disabled=not active):
        runtime.cancel()
    if active:
        st.info(f"Investigation running: {active}. Ingestion continues.")
    history = runtime.command("list_runs", *SCOPE)
    if not history:
        st.info("No saved investigations yet.")
        return
    st.markdown("#### Saved investigations")
    with st.expander(f"Run history ({len(history)})"):
        st.dataframe(history, hide_index=True, width="stretch", height=220)
    selected = st.selectbox(
        "Saved investigation",
        [row["run_id"] for row in history],
        format_func=lambda run_id, runs=history: next(
            f"{row['status'].replace('_', ' ').title()} · {row['run_id'][:8]}"
            for row in runs
            if row["run_id"] == run_id
        ),
        key="saved-investigation",
    )
    saved = runtime.command("get_run", *SCOPE, selected)
    if saved["report"]:
        show_report(runtime, saved["report"], "case-" + selected)
        if st.button("Create successor investigation"):
            report = saved["report"]
            try:
                runtime.begin_run(
                    *SCOPE,
                    question=report["scope_question"],
                    seed_event_id=report.get("seed_event_id"),
                    parent_run_id=selected,
                    max_calls=max_calls,
                    max_seconds=max_seconds,
                    falsification=falsification,
                )
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
    else:
        st.write("Status:", saved["status"])
        if saved["error"]:
            st.code(saved["error"])
        with st.expander("Retrieval audit"):
            st.json(saved["tool_activity"])
    st.subheader("Analyst disposition")
    with st.form("analyst-action-" + selected):
        actor = st.text_input(
            "Analyst",
            max_chars=128,
            help="Local attribution name; this release does not authenticate accounts.",
        )
        disposition = st.selectbox(
            "Disposition",
            ["OPEN", "INVESTIGATING", "ESCALATED", "CLOSED_BENIGN", "CLOSED_INCIDENT"],
        )
        note = st.text_area("Note", max_chars=8192)
        if st.form_submit_button("Save analyst action"):
            try:
                runtime.command(
                    "add_analyst_action", *SCOPE, selected, actor, disposition, note
                )
                st.success("Analyst action saved; machine report retained unchanged.")
            except ValueError as error:
                st.error(str(error))
    history = runtime.command("analyst_history", *SCOPE, selected)
    if history:
        st.json(history)


def workspace(runtime, page, learning=True, auto_refresh=True):
    status = runtime.status()
    counts = runtime.command("counts", *SCOPE)
    snapshot = runtime.command("snapshot")
    alerts = runtime.command("browse_telemetry", *SCOPE, snapshot)
    metrics = st.columns(4)
    input_state = "Connected" if status["running"] else "Disconnected"
    if status["running"] and status["source_mode"] == "unix_stream":
        input_state = (
            "Streaming"
            if status["stream_state"] == "Producer connected"
            else "Listening"
        )
    metrics[0].metric("Sensor", input_state, border=True)
    metrics[1].metric(
        "Accepted records",
        f"{counts['accepted']:,}",
        help="Stored alert and flow records in the external telemetry scope, including earlier sessions. These are records, not individual packets or unique conversations.",
        border=True,
    )
    metrics[2].metric(
        "Alerts",
        f"{alerts['total']:,}",
        help="Stored Suricata detection-rule matches. An alert is not proof of compromise.",
        border=True,
    )
    metrics[3].metric(
        "Quarantined records",
        f"{counts['invalid']:,}",
        help="Records not accepted as alert/flow evidence. Includes unsupported event types such as DNS, as well as malformed records. Inspect Sensor health for the reasons.",
        border=True,
    )
    if not status["running"]:
        if not status["status"].startswith("Stopped"):
            st.error(status["status"])
        else:
            st.info(
                "Choose an EVE file or Unix stream socket in the sidebar and connect. Saved evidence remains available while disconnected."
            )
    if status["running"] and status["stream_state"]:
        st.caption("Unix stream: " + status["stream_state"])
    st.caption(
        f"Last read: {status['last_ingest'] or 'No telemetry read this session'} · "
        + (
            "Auto refresh every 2 seconds"
            if auto_refresh
            else "Auto refresh off · filters or Refresh now reload the view"
        )
    )
    if page == "Overview":
        overview(runtime, snapshot, learning)
    elif page == "Alerts":
        telemetry_table(runtime, snapshot, "alert", learning)
    elif page == "Flows":
        telemetry_table(runtime, snapshot, "flow", learning)
    elif page == "Investigations":
        investigations(runtime, counts)
    else:
        st.write("Source:", status["source"] or "Not connected")
        st.write(
            "Input:",
            "Unix stream socket"
            if status["source_mode"] == "unix_stream"
            else "EVE file",
        )
        if status["stream_state"]:
            st.write("Receiver:", status["stream_state"])
            st.write("Receipt spool:", status["stream_spool"])
            st.caption(
                "Bytes received from the socket are fsynced to the spool before parsing. No end-to-end delivery acknowledgement exists: Suricata may drop events during downtime or congestion. A producer disconnect stops ingestion and records a continuity incident."
            )
        st.write("Ingestion:", status["status"])
        st.write("Committed file offset:", status["committed_offset"])
        st.write("Rename rotation recovery:", status["rotation_recovery"])
        if status["rotation_notice"]:
            st.warning(status["rotation_notice"])
        st.caption(
            "One EVE source per runtime. Rename rotation can drain the old generation and recover matching archives on restart; truncation or an unresolved drain stops ingestion. Unsupported event types and malformed records are quarantined; accepted alert/flow raw text is retained exactly."
        )
        rejected = runtime.command("quarantine_records", *SCOPE)
        if rejected:
            st.write("Latest quarantine details (up to 50)")
            st.dataframe(
                rejected,
                hide_index=True,
                width="stretch",
                height=260,
                column_config={
                    "source": "Source",
                    "position": "Byte offset",
                    "error": "Reason",
                },
            )
        else:
            st.success("No quarantined records.")
        with st.expander("Persisted source incidents"):
            st.json(runtime.command("source_incidents"))
        st.caption(
            "Capture and detection run in Suricata. This console does not control the sensor process or generate scans."
        )


def main():
    st.set_page_config(
        page_title="Blue Cheese | Network operations", page_icon="🧀", layout="wide"
    )
    apply_design()
    st.sidebar.markdown("## 🧀 Blue Cheese")
    st.sidebar.caption("Network evidence · Analyst workspace")
    try:
        runtime = get_runtime(
            str(
                Path(
                    os.environ.get("BLUECHEESE_STATE", "bluecheese-operations")
                ).resolve()
            )
        )
        page = st.sidebar.radio(
            "Workspace",
            ["Overview", "Alerts", "Flows", "Investigations", "Sensor health"],
            key="workspace-page",
        )
        learning = st.sidebar.toggle(
            "Learning mode",
            value=True,
            help="Explain the displayed evidence and network fundamentals. Turn off for a compact analyst view.",
        )
        auto_refresh = st.sidebar.toggle(
            "Auto refresh",
            value=True,
            help="Turn off while reading evidence or editing a case. Ingestion continues in the background; changing filters reloads the view.",
        )
        st.sidebar.button("Refresh now", icon=":material/refresh:", width="stretch")
        current = runtime.status()
        with st.sidebar.expander(
            "Sensor connection",
            expanded=not current["counts"]["accepted"] and not current["running"],
        ):
            st.fragment(run_every=2.0 if auto_refresh else None)(source_controls)(
                runtime
            )
        st.sidebar.divider()
        with st.sidebar.expander("Agents and model endpoint"):
            provider_controls(runtime)
        st.sidebar.caption(
            "Local analyst console · "
            + (
                runtime.provider.label
                if runtime.provider
                else "Rule-based investigation · No model provider configured"
            )
        )
        st.title(page)
        st.fragment(run_every=1.0)(agent_activity)(runtime)
        st.fragment(run_every=2.0 if auto_refresh else None)(workspace)(
            runtime, page, learning, auto_refresh
        )
    except (OSError, RuntimeError, ValueError) as error:
        st.error(str(error))


if __name__ == "__main__":
    main()
