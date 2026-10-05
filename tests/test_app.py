"""UI smoke tests using Streamlit's AppTest (no network, no API key)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("BACKEND", "gemini")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_app_boots(monkeypatch):
    at = _run(monkeypatch)
    assert not at.exception
    assert "FirstPR Pilot" in at.title[0].value


def test_missing_key_shows_friendly_error(monkeypatch):
    at = _run(monkeypatch)
    at.text_area[0].set_value("TypeError: x is undefined")
    at.button[0].click().run()
    assert not at.exception
    assert any("GEMINI_API_KEY" in e.value for e in at.error)


def test_empty_input_shows_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Nothing to analyze" in e.value for e in at.error)
