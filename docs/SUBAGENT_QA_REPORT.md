# Sentinel Subagent 5 — QA/E2E Report

Date: 2026-09-04  
Workspace: repository root  
Owner scope: test additions/updates and this report only. No commit or push was performed.

## Outcome

The in-process and loopback remote-sensor path is passing through registration,
sensor-token authentication, telemetry ingestion, the existing LSTM K=5
checkpoint, sensor-scoped forecast state, and dashboard-facing API contracts.
Retry/buffering, heartbeat health, restart isolation, and multi-sensor
separation are covered by automated tests. The Next dashboard builds and its
local empty-fleet/onboarding states were verified in a browser.

This is not production deployment evidence. Docker Compose, production TLS,
separate hosts, physical packet capture, process-crash recovery, and a
30-minute soak were not proven in this environment.

## Test additions

- `tests/api/test_remote_sensor_journey.py` — one acceptance journey proving
  registration → heartbeat (`DEGRADED` while telemetry is unknown) →
  authenticated ten-state telemetry → real five-row forecast readiness →
  `ONLINE` fleet/detail visibility.
- `tests/test_next_dashboard_contract.py` — static contracts for the Next
  dashboard's backend outage/retry/polling state, selected-sensor forecast and
  source scoping, and stable sensor identity/detail selection. The repository
  has no configured frontend unit-test runner, so these checks run in the
  Python suite until browser component tests are introduced.

## Exact validation commands and results

All commands below were run from the workspace path above unless noted.

| Command | Result |
|---|---|
| `python -m pytest -q` | **PASS** — 300 passed, 2 dependency deprecation warnings, 67.16s. |
| `python -m pytest -q tests/api/test_remote_sensor_journey.py tests/test_next_dashboard_contract.py` | **PASS** — 4 passed, 7.04s. |
| `python -m pytest -q tests/test_sensor_control_plane.py::test_agent_identity_and_production_transport_policy tests/api/test_security_hardening.py` | **PASS** — 7 passed, 7.72s. |
| `npm run typecheck` (from `frontend`) | **PASS**. |
| `npm run build` (from `frontend`) | **PASS** — static `/` and `/_not-found` generated. Next emitted only the workspace-root/package-lock warning. |
| `python scripts/check_environment.py` | **PASS** — Python 3.14.3, Windows 11, required packages and model/config artifacts found. |
| `git diff --check` | **PASS** — only expected CRLF normalization warnings. |
| `docker info` | **BLOCKED** — Docker CLI 29.6.2 is installed, but the `desktop-linux` daemon is unavailable at `npipe:////./pipe/dockerDesktopLinuxEngine`. |

## Coverage by requested journey

| Requested behavior | Evidence | Status |
|---|---|---|
| Remote Server → Sentinel Agent | `tests/api/test_remote_agent_e2e.py` starts a real `SensorAgent`; `tests/api/test_remote_sensor_journey.py` covers the central acceptance boundary. | **PASS**, loopback/in-process host only. |
| Registration | `tests/api/test_remote_sensors.py`, `tests/test_sensor_control_plane.py`, and the new journey cover admin-only enrollment, one-time registration, identity persistence, and non-online registration state. | **PASS** |
| Authenticated telemetry | Remote token, body identity, schema/cadence, deduplication, ordering, rate limits, and rejection contracts are covered in `tests/api/test_remote_sensors.py` and API security tests. | **PASS** |
| Central Sentinel → Sensor Runtime | Remote ingestion routes to a sensor-keyed runtime; journey/detail tests assert sensor identity, history, and readiness. | **PASS** |
| Existing LSTM K=5 → real forecast | `test_real_agent_posts_to_central_and_reaches_lstm`, `test_remote_telemetry_reaches_the_real_lstm_after_ten_states`, and the new journey use `models/lstm_multistep_k5.pt` and assert forecast readiness/five forecast rows. | **PASS** |
| Forecast → dashboard | API forecast/detail contracts pass; Next typecheck/build pass; local browser rendered the dashboard. | **PASS** for API/build/browser shell; **not claimed** as a seeded browser forecast E2E. |
| Sensor A vs Sensor B isolation | `test_two_remote_sensors_keep_forecast_histories_isolated`, three-sensor concurrent ingest, credential-scoped status/security tests, and runtime isolation tests. | **PASS** |
| Registration, telemetry, heartbeat | Remote API tests and the new journey assert `DEGRADED` after heartbeat-only and `ONLINE` after fresh telemetry plus heartbeat. | **PASS** |
| Retry and outage recovery | `tests/test_sensor_agent.py` covers transient buffering, bounded backoff, ordering, permanent rejection, and heartbeat failure; `test_real_agent_buffers_during_network_outage_and_recovers` exercises endpoint failure then flushes to a live loopback API. | **PASS** automated; no physical outage. |
| Restart | Agent sequence/config restart tests and `tests/test_live_restart_isolation.py` cover local restart state isolation and stale prior forecast behavior. | **PASS** automated; central process restart/Docker restart not run. |
| Frontend state | New static Next contracts cover backend unavailable/retry, five-second refresh, selected-sensor detail/forecast scoping, and stable sensor keys. Browser smoke verified empty fleet and seven-step onboarding. | **PASS** for available evidence; no frontend component runner. |
| Multi-sensor | Two-sensor forecast separation, three-sensor concurrent identity/state separation, five-sensor fleet counts, and selected sensor contracts pass. | **PASS** automated; not multi-host. |

## Browser smoke evidence

Temporary local processes were started with:

```powershell
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --log-level warning
$env:BACKEND_URL='http://127.0.0.1:8000'; npm run dev
```

The local browser opened `http://localhost:3000/` and visibly showed:

1. the dashboard overview with a waiting/no-fake-forecast state;
2. the Sensors view with the empty-fleet state; and
3. Add Sensor with the documented lifecycle: admin-only enrollment, agent-side
   capture, one-time registration, start, heartbeat, authenticated telemetry,
   and `ONLINE` only when heartbeat and telemetry are fresh.

No sensor was registered through the browser smoke and no user data or
credentials were transmitted. The temporary processes were stopped afterward.

## Limitations and blocked evidence

- **Docker/Compose:** blocked by the unavailable Docker Desktop Linux daemon;
  no container startup, restart, registry-volume persistence, or Compose
  healthcheck result is claimed.
- **Production TLS/mTLS:** only the agent configuration fail-closed contract
  was tested. No real certificate, reverse proxy, mTLS, hostname verification,
  or rotation run was performed.
- **Multi-host:** all automated remote tests use loopback or in-process
  `TestClient`/Uvicorn. No second physical/virtual host or network namespace
  was available.
- **Physical outage/packet capture:** no physical link outage, Scapy/Npcap
  capture run, or capture-permission failure was soaked. `check_environment.py`
  validates package/artifact availability only.
- **Long run:** no 30-minute soak, capacity, recovery-time, CPU, memory, or
  queue-growth measurement was performed.
- **Central restart/process crash:** runtime-history rebuild behavior is tested
  at the local runtime boundary and documented, but no live central process
  kill/restart or persisted-runtime recovery was executed.
- **Seeded browser forecast:** the real K=5 forecast is proven at the API
  boundary and the dashboard shell/onboarding is browser-proven separately;
  this environment did not provide a browser fixture that seeded an
  authenticated remote sensor and displayed its forecast end-to-end.

## Worktree safety

The repository already contained concurrent application and test changes. They
were not reverted or reformatted. This QA work added only the two test files
listed above and this report, and removed only the two `AGENTS.md`/`CLAUDE.md`
files generated inside `frontend` by the temporary Next dev server.
