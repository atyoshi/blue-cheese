from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / 'src/bluecheese/interfaces/demo.py'


def test_presentation_rerun_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv('BLUECHEESE_STATE', str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    runtime = app.session_state  # No report is created on initial rendering.
    assert 'report' not in runtime
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['report']['verdict'] == 'SUSPICIOUS'
    saved = app.session_state['report']
    app.run()
    assert app.session_state['report'] == saved
    assert any('SYNTHETIC' in code.value for code in app.code)
    app.sidebar.selectbox[0].select('benign').run()
    app.button[0].click().run()
    assert app.session_state['report']['verdict'] == 'BENIGN_CONFOUNDER'
    assert not app.exception
