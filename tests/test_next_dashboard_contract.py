"""Static checks for the executable Next dashboard state boundaries.

The frontend has no configured unit-test runner in this repository. These
checks keep the critical state wiring visible to the Python validation suite
until browser component tests are introduced.
"""

from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
COMMAND_CENTER = FRONTEND / "components" / "CommandCenter.tsx"
SENSOR_FLEET = FRONTEND / "components" / "SensorFleet.tsx"
API_CLIENT = FRONTEND / "lib" / "api.ts"
API_PROXY = FRONTEND / "app" / "api" / "[...path]" / "route.ts"
AUTH_GATE = FRONTEND / "components" / "AuthGate.tsx"
SESSION = FRONTEND / "lib" / "dashboard-session.ts"
LOGIN_ROUTE = FRONTEND / "app" / "api" / "auth" / "login" / "route.ts"
LOGOUT_ROUTE = FRONTEND / "app" / "api" / "auth" / "logout" / "route.ts"
COMPOSE = FRONTEND.parent / "docker-compose.yml"
EXTERNAL_QUICKSTART = FRONTEND.parent / "docs" / "EXTERNAL_VALIDATION_QUICKSTART.md"
EXTERNAL_TEMPLATE = FRONTEND.parent / "docs" / "EXTERNAL_VALIDATION_RESULT_TEMPLATE.md"


def test_command_center_has_backend_outage_retry_and_polling_state() -> None:
    source = COMMAND_CENTER.read_text(encoding="utf-8")

    assert "Promise.all([getLive(), getReady()])" in source
    assert "setInterval(() => void refresh(), 5000)" in source
    assert "setLive(null)" in source
    assert "setDemo(null)" in source
    assert 'state === "BACKEND_UNAVAILABLE"' in source
    assert "Retry connection" in source
    assert "onRetry={() => void refresh()}" in source
    assert 'state === "BACKEND_DEGRADED"' in source
    assert "CENTRAL SERVICE NOT READY" in source
    assert 'live.telemetry.mode === "mock"' in source
    assert 'const nav: View[] = ["Overview", "Live"' in source
    assert "onUnauthorized" in source
    assert 'if (action === "start") { await startTelemetry(); setDemo(null); }' in source


def test_command_center_scopes_forecast_and_sources_to_selected_fresh_sensor() -> None:
    source = COMMAND_CENTER.read_text(encoding="utf-8")

    assert "const [selectedSensorId, setSelectedSensorId]" in source
    assert "getSensor(selectedSensorId)" in source
    assert "getSensorForecast(selectedSensorId)" in source
    assert 'sensor.status === "ONLINE" && sensor.telemetry_status === "FRESH"' in source
    assert 'const remoteForecastReady = selectedSensorState === "SENSOR_ONLINE"' in source
    assert "selectedSensor ? remoteForecastReady" in source
    assert "selectedSensorForecast?.forecast?.forecast || []" in source
    assert 'const sourceDataFresh = selectedSensor?.runtime?.source_status === "SOURCE_ATTRIBUTION_AVAILABLE"' in source
    assert "remoteForecastReady && sourceDataFresh" in source
    assert "selectedSensorId={selectedSensorId}" in source
    assert "const selectSensor = (sensorId: string | null)" in source
    assert "onSelect={selectSensor}" in source


def test_sensor_fleet_uses_stable_identity_and_explicit_selected_detail() -> None:
    source = SENSOR_FLEET.read_text(encoding="utf-8")

    assert "key={sensor.sensor_id}" in source
    assert "selectedSensorId === sensor.sensor_id" in source
    assert "const selected = selectedSensorId === sensor.sensor_id" in source
    assert "aria-pressed={selected}" in source
    assert "Selected sensor · detail is scoped to this server." in source
    assert "onOpenDetail" in source


def test_frontend_does_not_embed_bearer_tokens_and_uses_allowlisted_server_proxy() -> None:
    client_source = API_CLIENT.read_text(encoding="utf-8")
    proxy_source = API_PROXY.read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_SIH_API_TOKEN" not in client_source
    assert "process.env.SIH_API_TOKEN" in proxy_source
    assert "isAllowed" in proxy_source
    assert "/api/v1/sensors/register" not in proxy_source


def test_dashboard_auth_is_server_side_and_fail_closed_when_enabled() -> None:
    client_source = API_CLIENT.read_text(encoding="utf-8")
    proxy_source = API_PROXY.read_text(encoding="utf-8")
    gate_source = AUTH_GATE.read_text(encoding="utf-8")
    session_source = SESSION.read_text(encoding="utf-8")
    login_source = LOGIN_ROUTE.read_text(encoding="utf-8")
    logout_source = LOGOUT_ROUTE.read_text(encoding="utf-8")
    compose_source = COMPOSE.read_text(encoding="utf-8")

    assert "SIH_DASHBOARD_AUTH_ENABLED" in session_source
    assert 'process.env.SIH_ENV === "production"' in session_source
    assert "HttpOnly" not in session_source  # cookie flags are set through Next's typed cookie API
    assert "httpOnly: true" in login_source
    assert 'sameSite: "strict"' in login_source
    assert "DASHBOARD_AUTH_MISCONFIGURED" in login_source
    assert "timingSafeEqual" in session_source
    assert "randomBytes(32)" in session_source
    assert "getDashboardSession" in proxy_source
    assert "DASHBOARD_AUTH_REQUIRED" in proxy_source
    assert "CSRF_ORIGIN_MISMATCH" in proxy_source and "sameOrigin" in proxy_source
    assert "configuredRoleTokens" in proxy_source
    assert "type=\"password\"" in gate_source
    assert "NEXT_PUBLIC_SIH_API_TOKEN" not in gate_source
    assert "onLogout" in gate_source
    assert "DashboardUnauthorizedError" in client_source
    assert "maxAge: 0" in logout_source
    assert "SIH_ENV: ${SIH_ENV:-development}" in compose_source
    assert "SIH_AUTH_ENABLED: ${SIH_AUTH_ENABLED:-false}" in compose_source
    assert "SIH_DASHBOARD_AUTH_ENABLED: ${SIH_DASHBOARD_AUTH_ENABLED:-${SIH_AUTH_ENABLED:-false}}" in compose_source


def test_external_validation_handoff_is_self_contained() -> None:
    quickstart = EXTERNAL_QUICKSTART.read_text(encoding="utf-8")
    template = EXTERNAL_TEMPLATE.read_text(encoding="utf-8")

    for command in ["sentinel-agent init", "sentinel-agent register", "sentinel-agent status", "sentinel-agent diagnostics", "sentinel-agent stop", "sentinel-agent restart", "python.exe -m build --wheel --sdist", "sentinel-agent.exe --version", "sentinel-agent.exe --help"]:
        assert command in quickstart
    for section in ["Dashboard startup and authentication", "Sensor creation and agent registration", "Capture, L=10, and K=5", "Restart, outage, and customer-path checks", "Troubleshooting", "Report format"]:
        assert section in quickstart
    assert "--ssl-certfile" in quickstart and "--ssl-keyfile" in quickstart
    assert "python3.14 -m venv .venv" in quickstart
    for field in ["Validator:", "Dashboard authentication:", "Sensor registration:", "Five forecast horizons:", "Central outage buffering:", "Customer-path independence:", "## Recommended fixes"]:
        assert field in template
