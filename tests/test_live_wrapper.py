"""Focused contract checks for the Windows live-validation wrapper."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "run_live_rc_validation.ps1"


def _wrapper_text() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_wrapper_uses_health_and_readiness_before_capture() -> None:
    source = _wrapper_text()

    assert '"$apiBase/health"' in source
    assert '"$apiBase/ready"' in source
    assert 'health.payload.status -eq "ok"' in source
    assert 'readiness.payload.ready -eq $true' in source
    assert "$startupDeadline" in source
    assert "$PollIntervalMilliseconds" in source


def test_wrapper_rejects_conflicting_listener_and_tracks_its_process() -> None:
    source = _wrapper_text()

    assert "stale_or_conflicting_listener" in source
    assert "$serverProcessId = $server.Id" in source
    assert "process_exited_before_readiness" in source
    assert "Stop-Process -Id $server.Id -Force" in source


def test_wrapper_captures_redacted_startup_diagnostics() -> None:
    source = _wrapper_text()

    assert "-RedirectStandardOutput $stdoutLog" in source
    assert "-RedirectStandardError $stderrLog" in source
    assert "stderr_tail=$(Read-LogTail $stderrLog)" in source
    assert "stdout_tail=$(Read-LogTail $stdoutLog)" in source
    assert "Redact-Text" in source
    assert "Remove-Item -LiteralPath $logRoot -Recurse -Force" in source


def test_wrapper_keeps_live_request_timeout_separate_from_startup_timeout() -> None:
    source = _wrapper_text()

    assert "[int]$StartupTimeoutSeconds = 60" in source
    assert "[int]$LiveRequestTimeoutSeconds = 15" in source
    assert '"$apiBase/live" -TimeoutSec $LiveRequestTimeoutSeconds' in source
