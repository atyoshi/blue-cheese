import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from bluecheese.application.demo_runtime import DemoRuntime

APP = Path(__file__).parents[1] / "src/bluecheese/interfaces/console.py"
FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def test_gui_configures_agents_probes_only_on_click_and_returns_to_rules(
    tmp_path, monkeypatch
):
    from bluecheese.adapters.agent_provider import AgentModelProvider

    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
    monkeypatch.delenv("BLUECHEESE_MODEL_ENDPOINT", raising=False)
    runtimes, probes = [], []

    def create_runtime(*args, **kwargs):
        runtime = DemoRuntime(*args, **kwargs)
        runtimes.append(runtime)
        return runtime

    def probe(provider):
        probes.append(provider.profile.endpoint)
        return {"status": "passed", "tool_calling": True, "structured_output": True}

    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime", create_runtime
    )
    monkeypatch.setattr(AgentModelProvider, "test_connection", probe)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    runtime = runtimes[0]
    try:
        assert not app.exception
        assert next(
            b for b in app.sidebar.button if b.label == "Test agent connection"
        ).disabled
        next(
            s for s in app.sidebar.selectbox if s.label == "Investigation engine"
        ).set_value("Model agents")
        next(
            s for s in app.sidebar.text_input if s.label == "Investigator model"
        ).set_value("local-model")
        next(
            s for s in app.sidebar.text_input if s.label.startswith("Falsifier model")
        ).set_value("critic-model")
        next(
            s for s in app.sidebar.text_input if s.label.startswith("API key (")
        ).set_value("secret-for-test")
        next(
            b for b in app.sidebar.button if b.label == "Apply agent settings"
        ).click().run()
        assert not app.exception
        assert isinstance(runtime.provider, AgentModelProvider)
        assert (
            runtime.provider.profile.endpoint
            == "http://127.0.0.1:8080/v1/chat/completions"
        )
        assert runtime.provider.falsifier_model == "critic-model"
        assert runtime.provider.profile.api_key == "secret-for-test"
        app.run()
        assert runtime.status()["investigation_runs"] == 0
        assert probes == []
        next(
            b for b in app.sidebar.button if b.label == "Test agent connection"
        ).click().run()
        assert not app.exception
        assert len(probes) == 1
        app.run()
        assert len(probes) == 1
        next(
            s for s in app.sidebar.selectbox if s.label == "Investigation engine"
        ).set_value("Rule-based")
        next(
            b for b in app.sidebar.button if b.label == "Apply agent settings"
        ).click().run()
        assert not app.exception
        assert runtime.provider is None
        assert runtime.status()["investigation_runs"] == 0
    finally:
        runtime.close()


def test_operational_runtime_has_no_synthetic_evidence_and_search_is_scoped(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        assert runtime.command("snapshot") == 0
        with pytest.raises(ValueError, match="disabled"):
            runtime.start(replay=True)
        runtime.start(path=FIXTURE, replay=False, interval=3600)
        runtime.stop()
        snapshot = runtime.command("snapshot")
        result = runtime.command(
            "browse_telemetry",
            "live",
            "external",
            snapshot,
            ip="10.1.17.215",
            severity=2,
            signature="teamviewer",
        )
        assert result["total"] == 1
        assert result["rows"][0]["alert_signature"].startswith("ET INFO")
        assert (
            runtime.command(
                "browse_telemetry",
                "live",
                "external",
                snapshot,
                signature="' OR TRUE --",
            )["total"]
            == 0
        )
        assert (
            runtime.command("browse_telemetry", "live", "replay", snapshot)["total"]
            == 0
        )
        report = runtime.begin_run("live", "external").result(10)
        assert not report["synthetic"]
    finally:
        runtime.close()


def test_console_real_file_evidence_and_saved_investigation(tmp_path, monkeypatch):
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("BLUECHEESE_EVE", str(FIXTURE))
    runtimes = []

    def create_runtime(*args, **kwargs):
        runtime = DemoRuntime(*args, **kwargs)
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime", create_runtime
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    assert all(
        w.label not in ("Scenario", "Variant", "Inspect evidence")
        for w in app.selectbox
    )
    next(b for b in app.sidebar.button if b.label == "Connect sensor").click().run()
    assert not app.exception
    assert any("TeamViewer" in code.value for code in app.code)
    assert next(b for b in app.sidebar.button if b.label == "Connect sensor").disabled
    assert not next(
        b for b in app.sidebar.button if b.label == "Disconnect sensor"
    ).disabled
    # No UI rerender may dispatch a second ingestion worker or investigation.
    runtime = runtimes[0]
    try:
        app.run()
        assert runtime.status()["worker_starts"] == 1
        assert runtime.status()["investigation_runs"] == 0
        app.sidebar.radio[0].set_value("Investigations").run()
        next(b for b in app.button if b.label == "Start investigation").click().run()
        runtime.pending_run.result(10)
        app.run()
        assert not app.exception
        assert any(b.label == "Export JSON" for b in app.get("download_button"))
        assert any(b.label == "Export Markdown" for b in app.get("download_button"))
        assert any("Verify cited evidence" in e.label for e in app.expander)
        assert any(e.label == "Reasoning and retrieval audit" for e in app.expander)
        app.run()
        assert runtime.status()["investigation_runs"] == 1
        app.sidebar.radio[0].set_value("Sensor health").run()
        assert not app.exception
        assert str(FIXTURE.resolve()) in str([e.value for e in app.markdown])
    finally:
        runtime.close()


def test_console_pagination_snapshot_and_quarantine(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        row = json.loads(FIXTURE.read_text().splitlines()[0])
        source = tmp_path / "eve.json"
        source.write_text((json.dumps(row) + "\n") * 55 + "invalid\n")
        runtime.start(path=source, replay=False, interval=3600)
        runtime.stop()
        snapshot = runtime.command("snapshot")
        page = runtime.command("browse_telemetry", "live", "external", snapshot, page=2)
        assert page["total"] == 55
        assert len(page["rows"]) == 5
        assert runtime.command("quarantine_records", "live", "external")
        with source.open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        runtime.poll_once()
        assert (
            runtime.command("browse_telemetry", "live", "external", snapshot)["total"]
            == 55
        )
        assert (
            runtime.command(
                "browse_telemetry", "live", "external", runtime.command("snapshot")
            )["total"]
            == 56
        )
    finally:
        runtime.close()


def test_console_missing_source_does_not_start_worker_or_record_coverage_gap(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
    monkeypatch.delenv("BLUECHEESE_EVE", raising=False)
    runtimes = []

    def create_runtime(*args, **kwargs):
        runtime = DemoRuntime(*args, **kwargs)
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime", create_runtime
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    runtime = runtimes[0]
    try:
        field = next(
            w for w in app.sidebar.text_input if w.label == "Suricata EVE file"
        )
        assert field.value == ""
        field.set_value(str(tmp_path / "missing/eve.json"))
        next(b for b in app.sidebar.button if b.label == "Connect sensor").click().run()
        assert not app.exception
        assert any("does not exist" in error.value for error in app.sidebar.error)
        assert runtime.status()["worker_starts"] == 0
        assert runtime.command("source_incidents") == []
        next(
            w for w in app.sidebar.text_input if w.label == "Suricata EVE file"
        ).set_value(str(FIXTURE))
        next(b for b in app.sidebar.button if b.label == "Connect sensor").click().run()
        assert not app.exception
        assert runtime.status()["worker_starts"] == 1
        assert runtime.command("counts", "live", "external")["accepted"] == 2
    finally:
        runtime.close()


def test_overview_filters_chart_population_evidence_and_learning_mode(
    tmp_path, monkeypatch
):
    row = json.loads(FIXTURE.read_text().splitlines()[1])
    row["src_ip"] = "192.0.2.99"
    row["dest_ip"] = "192.0.2.100"
    eve = tmp_path / "eve.json"
    eve.write_bytes(FIXTURE.read_bytes() + (json.dumps(row) + "\n").encode())
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("BLUECHEESE_EVE", str(eve))
    runtimes = []

    def create_runtime(*args, **kwargs):
        runtime = DemoRuntime(*args, **kwargs)
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime", create_runtime
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    runtime = runtimes[0]
    try:
        assert app.sidebar.radio[0].value == "Overview"
        next(b for b in app.sidebar.button if b.label == "Connect sensor").click().run()
        assert not app.exception
        assert next(m for m in app.metric if m.label == "Alerts in view").value == "1"
        assert (
            next(m for m in app.metric if m.label == "Flow records in view").value
            == "2"
        )
        next(s for s in app.selectbox if s.label == "Focus on an endpoint").set_value(
            "192.0.2.99"
        ).run()
        assert not app.exception
        assert next(m for m in app.metric if m.label == "Alerts in view").value == "0"
        assert (
            next(m for m in app.metric if m.label == "Flow records in view").value
            == "1"
        )
        assert (
            len(
                next(
                    s for s in app.selectbox if s.label == "Inspect visual evidence"
                ).options
            )
            == 1
        )
        assert not any(b.label == "Investigate this alert" for b in app.button)
        assert any("Reading this record" in m.value for m in app.markdown)
        app.sidebar.toggle[0].set_value(False).run()
        assert not any("Reading this record" in m.value for m in app.markdown)
        next(b for b in app.button if b.label == "Reset focus").click().run()
        assert (
            next(s for s in app.selectbox if s.label == "Focus on an endpoint").value
            == "All endpoints"
        )
        assert (
            next(s for s in app.selectbox if s.label == "Inspect a connection").value
            == "All connections"
        )
        assert next(m for m in app.metric if m.label == "Alerts in view").value == "1"
        next(s for s in app.selectbox if s.label == "Inspect a connection").set_value(
            "192.0.2.99 → 192.0.2.100"
        ).run()
        assert next(m for m in app.metric if m.label == "Alerts in view").value == "0"
        assert (
            next(m for m in app.metric if m.label == "Flow records in view").value
            == "1"
        )
        next(b for b in app.button if b.label == "Reset focus").click().run()
        next(r for r in app.radio if r.label == "Evidence type").set_value(
            "Flows"
        ).run()
        assert (
            len(
                next(
                    s for s in app.selectbox if s.label == "Inspect visual evidence"
                ).options
            )
            == 2
        )
        assert not any(b.label == "Investigate this alert" for b in app.button)
        next(t for t in app.sidebar.toggle if t.label == "Auto refresh").set_value(
            False
        ).run()
        assert runtime.status()["running"]
        next(b for b in app.sidebar.button if b.label == "Refresh now").click().run()
        assert runtime.status()["worker_starts"] == 1
        assert runtime.status()["investigation_runs"] == 0
        next(b for b in app.button if b.label == "Open investigations").click().run()
        assert not app.exception
        assert app.sidebar.radio[0].value == "Investigations"
        assert runtime.status()["investigation_runs"] == 0
    finally:
        runtime.close()


def test_console_stream_receiver_uses_same_evidence_and_stops_on_disconnect(
    monkeypatch,
):
    import socket
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="bc-ui-", dir="/tmp") as directory:
        root = Path(directory)
        monkeypatch.chdir(root)
        monkeypatch.setenv("BLUECHEESE_STATE", str(root / "state"))
        runtimes = []

        def create_runtime(*args, **kwargs):
            runtime = DemoRuntime(*args, **kwargs)
            runtimes.append(runtime)
            return runtime

        monkeypatch.setattr(
            "bluecheese.application.demo_runtime.DemoRuntime", create_runtime
        )
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        runtime = runtimes[0]
        producer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            next(
                s for s in app.sidebar.selectbox if s.label == "Telemetry input"
            ).set_value("Unix stream").run()
            assert not app.exception
            assert not any(
                w.label == "Suricata EVE file" for w in app.sidebar.text_input
            )
            next(
                w for w in app.sidebar.text_input if w.label == "Unix socket path"
            ).set_value("sensor.sock").run()
            path = str(root.resolve() / "sensor.sock")
            assert any('filename: "' + path + '"' in code.value for code in app.code)
            next(
                b for b in app.sidebar.button if b.label == "Connect sensor"
            ).click().run()
            assert not app.exception
            assert (
                next(m for m in app.metric if m.label == "Sensor").value == "Listening"
            )
            producer.connect(path)
            producer.sendall(FIXTURE.read_bytes())
            runtime.poll_once()
            app.run()
            assert not app.exception
            assert (
                next(m for m in app.metric if m.label == "Sensor").value == "Streaming"
            )
            assert (
                next(m for m in app.metric if m.label == "Alerts in view").value == "1"
            )
            assert runtime.status()["worker_starts"] == 1
            assert runtime.status()["investigation_runs"] == 0
            next(
                b for b in app.sidebar.button if b.label == "Disconnect sensor"
            ).click().run()
            assert not runtime.status()["running"]
            assert next(
                b for b in app.sidebar.button if b.label == "Disconnect sensor"
            ).disabled
            assert not next(
                b for b in app.sidebar.button if b.label == "Connect sensor"
            ).disabled
            assert not Path(path).exists()
            assert runtime.command("counts", "live", "external")["accepted"] == 2
            assert any(
                "delivery completeness" in incident["diagnostic"]
                for incident in runtime.command("source_incidents")
            )
        finally:
            producer.close()
            runtime.close()
