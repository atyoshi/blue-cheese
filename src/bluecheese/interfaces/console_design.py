"""Operational UI styles and plain-language labels; no telemetry HTML rendering."""

import streamlit as st


def apply_design():
    st.html("""<style>
      .stMainBlockContainer { max-width: 1440px; padding-top: 1.6rem; padding-bottom: 2rem; }
      h1 { font-size: 2rem !important; letter-spacing: -.045em; padding-bottom: .3rem !important; }
      h2 { font-size: 1.3rem !important; letter-spacing: -.02em; }
      h3 { font-size: 1.1rem !important; }
      h4 { font-size: 1rem !important; }
      [data-testid="stMetricValue"] { font-size: 1.65rem; font-variant-numeric: tabular-nums; }
      [data-testid="stMetric"] { border-radius: 12px; }
      [data-testid="stMetricValue"] > div { white-space: normal; overflow-wrap: anywhere; }
      [data-testid="stMetricLabel"] p { white-space: normal; }
      @media (max-width: 1100px) {
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
        [data-testid="stColumn"] { flex: 1 1 260px !important; min-width: min(100%, 260px) !important; }
      }
      [data-testid="stSidebar"] h2 { font-size: 1.25rem !important; }
      [data-testid="stSidebarUserContent"] { padding-top: 1.4rem; }
      [data-testid="stCaptionContainer"] { line-height: 1.5; }
      .stButton button, .stDownloadButton button { border-radius: 8px; transition: border-color .12s ease; }
      .stButton button:hover, .stDownloadButton button:hover { border-color: #38bdb4; }
      button:focus-visible, input:focus-visible { outline: 2px solid #38bdb4 !important; outline-offset: 3px; }
      @media (max-width: 760px) {
        .stMainBlockContainer { padding: 1rem; }
        [data-testid="stMetricValue"] { font-size: 1.3rem; }
      }
      @media (prefers-reduced-motion: reduce) { .stButton button, .stDownloadButton button { transition: none; } }
    </style>""")


def record_label(row):
    detail = (row.get("alert_signature") or row.get("flow_state") or row["event_type"])[
        :72
    ]
    return f"{detail} · {row.get('src_ip') or '?'} → {row.get('dest_ip') or '?'} · {row.get('timestamp') or 'Time unknown'}"


def table_columns():
    return {
        "timestamp": st.column_config.TextColumn("Event time", width="medium"),
        "event_type": "Type",
        "severity": "Severity",
        "alert_signature": st.column_config.TextColumn("Detection rule", width="large"),
        "src_ip": "Source IP",
        "dest_ip": "Destination IP",
        "src_port": "Source port",
        "dest_port": "Destination port",
        "protocol": "Protocol",
        "flow_state": "Flow state",
        "id": st.column_config.TextColumn("Evidence ID", width="small"),
        "bytes_toserver": "Bytes to server",
        "bytes_toclient": "Bytes to client",
    }


def open_investigations():
    st.session_state["workspace-page"] = "Investigations"


def investigation_link(key):
    if st.button(
        "Open investigations",
        icon=":material/arrow_forward:",
        key=key,
        on_click=open_investigations,
    ):
        st.rerun(scope="app")


def start_investigation(runtime, scenario, variant, **settings):
    """Only called by explicit UI actions; route to the submitted work."""
    runtime.begin_run(scenario, variant, **settings)
    st.session_state["show-submitted-investigation"] = True
    st.rerun(scope="app")
