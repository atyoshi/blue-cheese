"""Local analyst console for externally supplied Suricata telemetry."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from bluecheese.adapters.agent_provider import AgentModelProvider, completion_endpoint
from bluecheese.adapters.model_provider import ModelProfile, investigation_seconds
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.source_path import readable_eve_path
from bluecheese.interfaces.console_design import (
    apply_design,
    investigation_link,
    record_label,
    start_investigation,
    table_columns,
)
from bluecheese.interfaces.console_workflow import (
    attention,
    chat_panel,
    investigation_workspace,
)
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
            start_investigation(
                runtime,
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
    investigation_workspace(runtime, counts)


def settings(runtime):
    with st.expander("Agents and model endpoint", expanded=True):
        provider_controls(runtime)
    with st.expander("Automatic investigation and retry queue"):
        automatic = st.checkbox(
            "Investigate incoming alerts automatically",
            value=runtime.status()["automatic_investigation"],
        )
        st.caption(
            "Off after restart. One investigation at a time while the sensor is connected."
        )
        if st.button("Save automatic investigation setting"):
            runtime.set_automatic(automatic)
            st.success(
                "Automatic investigations " + ("enabled" if automatic else "disabled")
            )
        queue = runtime.command("work_queue")
        st.caption(
            f"{sum(row['status'] == 'QUEUED' for row in queue)} queued alerts in the latest 100 work items"
        )
        if st.button("Investigate next queued alert"):
            if runtime.schedule_once():
                st.session_state["show-submitted-investigation"] = True
                st.rerun(scope="app")
            else:
                st.info(
                    "No queued work is available, or another investigation is active."
                )
        retryable = [
            row
            for row in queue
            if row["status"] in ("FAILED", "INTERRUPTED", "CANCELLED", "INCOMPLETE")
        ]
        if retryable:
            by_id = {row["event_id"]: row for row in retryable}
            retry = st.selectbox(
                "Retryable alert",
                list(by_id),
                format_func=lambda value: (
                    f"{by_id[value]['status'].title()} · {by_id[value]['created_at'][:19]}"
                ),
            )
            if st.button("Requeue selected alert"):
                runtime.command("retry_work", retry)
                st.success("Alert requeued")
        with st.expander("Queue diagnostics"):
            st.dataframe(queue, hide_index=True, width="stretch")


def workspace(runtime, page, learning=True, auto_refresh=True):
    status = runtime.status()
    counts = runtime.command("counts", *SCOPE)
    snapshot = runtime.command("snapshot")
    alerts = runtime.command("browse_telemetry", *SCOPE, snapshot)
    input_state = "Connected" if status["running"] else "Disconnected"
    if status["running"] and status["source_mode"] == "unix_stream":
        input_state = (
            "Streaming"
            if status["stream_state"] == "Producer connected"
            else "Listening"
        )
    st.caption(
        f"Sensor: {input_state} · Last new record: {status.get('last_accepted') or 'none this session'}"
    )
    with st.expander("Sensor status and stored evidence totals"):
        metrics = st.columns(4)
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
        st.caption(
            f"Last successful sensor check: {status.get('last_poll') or 'none this session'} · Last bytes read: {status['last_ingest'] or 'none this session'}"
        )
    if not status["running"]:
        if not status["status"].startswith("Stopped"):
            st.error(status["status"])
        elif not counts["accepted"]:
            st.info(
                "Connect an EVE file or Unix stream in the sidebar to receive telemetry."
            )
    if status["running"] and status["stream_state"]:
        st.caption("Unix stream: " + status["stream_state"])
    now = datetime.now(UTC).strftime("%H:%M:%S UTC")
    previous = st.session_state.get("last-view-accepted")
    st.session_state["last-view-accepted"] = counts["accepted"]
    delta = counts["accepted"] - previous if previous is not None else None
    refresh_state = "Auto refresh on" if auto_refresh else "Auto refresh off"
    st.caption(
        f"View refreshed {now} · {refresh_state}"
        + (
            f" · {delta:,} newly accepted records"
            if delta and delta > 0
            else " · no new accepted records since previous view"
            if delta == 0
            else ""
        )
    )
    future = runtime.pending_run
    if future is not None and future.done() and future.exception() is not None:
        st.error("The latest investigation failed: " + str(future.exception())[:1024])
    incidents = runtime.command("source_incidents")
    if incidents:
        st.warning(
            f"{len(incidents)} recorded source continuity incident(s). Coverage may be incomplete; inspect Sensor health."
        )
    if page == "Needs attention":
        review, chat = st.columns([3, 2])
        with review:
            attention(runtime, snapshot)
        with chat:
            st.fragment(run_every=1.0)(chat_panel)(runtime)
    elif page == "Overview":
        overview(runtime, snapshot, learning)
    elif page == "Alerts":
        telemetry_table(runtime, snapshot, "alert", learning)
    elif page == "Flows":
        telemetry_table(runtime, snapshot, "flow", learning)
    elif page == "Investigations":
        investigations(runtime, counts)
    elif page == "Settings":
        settings(runtime)
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
        if st.session_state.pop("show-submitted-investigation", False):
            st.session_state["workspace-page"] = "Investigations"
            st.session_state.pop("saved-investigation", None)
            st.session_state["follow-submitted-run"] = True
        if st.session_state.pop("navigate-case", False):
            st.session_state["workspace-page"] = "Investigations"
        navigation = st.session_state.pop("navigate-page", None)
        if navigation:
            st.session_state["workspace-page"] = navigation
        page = st.sidebar.radio(
            "Workspace",
            [
                "Needs attention",
                "Investigations",
                "Overview",
                "Alerts",
                "Flows",
                "Sensor health",
                "Settings",
            ],
            format_func=lambda value: "Network" if value == "Overview" else value,
            key="workspace-page",
        )
        learning = st.sidebar.toggle(
            "Learning mode",
            value=False,
            help="Explain the displayed evidence and network fundamentals. Turn off for a compact analyst view.",
        )
        auto_refresh = st.sidebar.toggle(
            "Auto refresh",
            value=True,
            help="Turn off while reading evidence or editing a case. Ingestion continues in the background; changing filters reloads the view.",
        )
        if st.sidebar.button("Refresh now", icon=":material/refresh:", width="stretch"):
            st.sidebar.success(
                "View refreshed " + datetime.now(UTC).strftime("%H:%M:%S UTC")
            )
        current = runtime.status()
        with st.sidebar.expander(
            "Sensor connection",
            expanded=not current["counts"]["accepted"] and not current["running"],
        ):
            st.fragment(run_every=2.0 if auto_refresh else None)(source_controls)(
                runtime
            )
        st.sidebar.divider()
        st.sidebar.caption(
            "Local analyst console · "
            + (
                runtime.provider.label
                if runtime.provider
                else "Rule-based investigation · No model provider configured"
            )
        )
        st.title("Network" if page == "Overview" else page)
        current_run = runtime.activity.snapshot()["run_id"]
        if current["investigation_pending"] and page != "Investigations":
            st.info(
                "An investigation is running. Open Investigations to follow its actual operations."
            )
            if current_run and st.button("Open active investigation"):
                st.session_state["open-case-run"] = current_run
                st.session_state["navigate-case"] = True
                st.rerun(scope="app")
        st.fragment(run_every=2.0 if auto_refresh else None)(workspace)(
            runtime, page, learning, auto_refresh
        )
    except (OSError, RuntimeError, ValueError) as error:
        st.error(str(error))


if __name__ == "__main__":
    main()
