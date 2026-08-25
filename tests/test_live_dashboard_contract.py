"""Static contract checks for API-only live dashboard integration."""

from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_dashboard_reads_live_endpoint_and_does_not_load_model_for_live_state() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert 'get_json("/api/v1/live")' in source
    assert "BACKEND UNAVAILABLE" in source
    assert "WAITING_FOR_LIVE_HISTORY" in source
    assert '"LIVE", "REPLAY", "MOCK / STATIC", "Full Integrated Demo"' in source
    assert "BUILDING NETWORK HISTORY" in source
    assert "PACKET QUALITY" in source
    assert "Packets seen" in source
    assert "Valid events" in source
    assert "Ignored / unsupported" in source
    assert "simulation_only" in source
    assert "no traffic is automatically blocked" in source
    assert "predict_network_state_sequence(" in source  # static/replay modes remain supported


def test_dashboard_uses_safe_live_terminology() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "Attack Detected" not in source
    assert "Forecast Score" in source
    assert "calibrated probability" in source
