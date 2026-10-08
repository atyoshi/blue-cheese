from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "src/bluecheese/interfaces/demo.py"


def test_presentation_rerun_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    runtime = app.session_state  # No report is created on initial rendering.
    assert "report" not in runtime
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["report"]["verdict"] == "SUSPICIOUS"
    saved = app.session_state["report"]
    app.run()
    assert app.session_state["report"] == saved
    assert any("SYNTHETIC" in code.value for code in app.code)
    app.sidebar.selectbox[0].select("benign").run()
    app.button[0].click().run()
    assert app.session_state["report"]["verdict"] == "BENIGN_CONFOUNDER"
    assert not app.exception


def test_ui_reuses_worker_and_saved_live_run(tmp_path, monkeypatch):
    import json

    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    next(b for b in app.button if b.label == "Start / resume ingestion").click().run()

    def status():
        return next(json.loads(j.value) for j in app.json if "worker_starts" in j.value)

    assert status()["worker_starts"] == 1
    app.run()
    assert status()["worker_starts"] == 1
    next(b for b in app.button if b.label == "Stop ingestion").click().run()
    next(b for b in app.button if b.label == "Investigate live snapshot").click().run()
    saved = app.session_state["live_report"]
    app.run()  # status is displayed before the button action in its rendering pass
    count = status()["investigation_runs"]
    app.run()
    assert status()["investigation_runs"] == count
    assert app.session_state["live_report"] == saved
    assert not app.exception


def test_ui_loads_persisted_report_without_new_run(tmp_path, monkeypatch):
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    next(b for b in app.button if b.label == "Run Investigation").click().run()
    original = app.session_state["report"]
    del app.session_state["report"]
    app.run()
    next(b for b in app.button if b.label == "Load saved report").click().run()
    assert not app.exception
    assert app.session_state["report"] == original
    next(
        b for b in app.button if b.label == "Investigate successor revision"
    ).click().run()
    assert not app.exception
    successor = app.session_state["report"]
    assert successor["parent_run_id"] == original["run_id"]
    assert successor["case_revision"] == original["case_revision"] + 1


def test_ui_background_run_completes_without_duplicate_rerun(tmp_path, monkeypatch):
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    next(
        b for b in app.button if b.label == "Start background investigation"
    ).click().run()
    if "background_run" in app.session_state:
        app.session_state["background_run"].result(5)
    app.run()
    assert not app.exception
    report = app.session_state["report"]
    assert report["workflow"]["roles"]
    app.run()
    assert app.session_state["report"] == report
