"""Read-only live agent activity view, independent of telemetry refresh."""

import streamlit as st

ROLES = (
    "Orchestrator",
    "Triage",
    "Correlation",
    "Investigator",
    "Falsifier",
    "Reporter",
)
KINDS = {
    "software": "Software",
    "rules": "Rule policy",
    "model": "Model call",
    "tool": "Evidence tool",
}
STATES = {
    "working": "Working",
    "queued": "Queued",
    "complete": "Done",
    "completed": "Done",
    "handoff": "Passed work",
    "skipped": "Skipped",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "incomplete": "Incomplete",
    "cancel_requested": "Stopping",
}


def agent_activity(runtime):
    activity = runtime.activity.snapshot()
    events, state = activity["events"], activity["state"]
    if not events:
        st.caption(
            "Agent activity · Idle — start an investigation to follow the workflow."
        )
        return
    active = state in ("RUNNING", "QUEUED")
    current = events[-1]
    panel_state = (
        "running" if active else ("complete" if state == "COMPLETED" else "error")
    )
    with st.status(
        "Agent activity · " + (current["role"] if active else state.title()),
        state=panel_state,
        expanded=active,
    ):
        st.text(current["message"])
        st.caption(
            f"Elapsed: {activity['elapsed_seconds']:.1f}s · "
            + (f"Run {activity['run_id'][:8]} · " if activity["run_id"] else "")
            + "Activity updates every second, independently of telemetry refresh."
        )
        latest = {event["role"]: event for event in events}
        columns = st.columns(3)
        for index, role in enumerate(ROLES):
            event = latest.get(role)
            with columns[index % 3].container(border=True):
                st.markdown("**" + role + "**")
                label = (
                    STATES.get(event["status"], event["status"].title())
                    if event
                    else "Not started"
                )
                if event and event["status"] == "handoff":
                    label = "Passed to " + event["handoff_to"]
                if (
                    not active
                    and event
                    and event["status"] in ("working", "cancel_requested", "queued")
                ):
                    label = "Stopped · " + state.title()
                st.text(label)
                st.caption(KINDS.get(event["kind"], "Software") if event else "")
        with st.expander("Agent handoffs and activity timeline"):
            st.dataframe(
                [
                    {
                        "Elapsed": f"{event['elapsed_seconds']:.1f}s",
                        "Role": event["role"],
                        "Activity": event["message"],
                        "Execution": KINDS.get(event["kind"], "Software"),
                    }
                    for event in events
                ],
                hide_index=True,
                width="stretch",
                height=240,
            )
