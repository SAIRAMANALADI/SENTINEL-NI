# Sentinel Subagent 6 — Documentation and Release Review

**Review date:** 2026-09-04  
**Scope:** current working tree, including the in-progress source-telemetry
documentation and implementation changes. This review changes documentation
only; it does not establish deployment evidence that is unavailable in this
workspace.

**Historical snapshot; superseded by the Phase Z coordinator report.** Counts
and findings below describe this earlier review and are not current regression
evidence.

## Release position

The repository documents and implements the remote sensor contract through the
following operator workflow:

**Create Sensor → Install Agent → Register → Start → Verify → Monitor**

The workflow is supported by automated and in-process evidence. The honest
release position remains **open-source release ready with environment
validation pending**. Docker runtime, staging TLS/reverse-proxy operation,
physical multi-host deployment, and long-running capacity are not verified and
must not be presented as supported deployment results.

## Workflow audit

| Step | What the operator does | Implementation evidence | Boundary / limitation |
| --- | --- | --- | --- |
| Create Sensor | In the operator workflow, “Create Sensor” means creating a short-lived, one-time enrollment credential. The persistent sensor record is materialized by the later Register step. | `src/api/app.py:366-382`; `tests/api/test_remote_sensors.py::test_enrollment_is_admin_only_and_registration_is_one_time` | The browser does not call the admin enrollment endpoint or receive a global admin credential. The one-time token must be transferred out of band. |
| Install Agent | Install the wheel on the monitored host, then run `sentinel-agent init` with the central URL and exact capture interface. | `pyproject.toml` exposes `sentinel-agent`; `src/agent/cli.py:26-57`; [Agent Installation](AGENT_INSTALLATION.md) | The agent needs host-level Scapy/Npcap/libpcap capture permission. Central Docker containers are not a host packet-capture runtime. |
| Register | Run `sentinel-agent register --enrollment-token ...`; the central API returns the persistent sensor ID and runtime credential once. | `src/agent/cli.py:134-142`; `src/agent/client.py:54-63`; `src/api/app.py:384-442` | Enrollment is one-time and expires. The runtime credential is sensor-scoped; registration alone is not `ONLINE`. |
| Start | Run `sentinel-agent start` on the monitored host. The agent captures metadata, builds flows/states, batches telemetry, and sends it to Central Sentinel. | `src/agent/cli.py:158-164`; `src/agent/client.py:391-461`; `src/agent/collector.py:16-108` | The foreground agent uses the configured interface. Production configuration requires an `https://` server URL and TLS verification. |
| Verify | Use `sentinel-agent status` and `sentinel-agent diagnostics`; confirm central health, capture, connection, heartbeat, telemetry, and buffer state. | `src/agent/cli.py:116-120,143-153`; `src/agent/client.py:466-490`; `docs/SENSOR_HEALTH.md` | `ONLINE` requires both fresh heartbeat and accepted telemetry. Forecast health remains `WAITING` until ten contiguous same-day states are available. |
| Monitor | Open **Sensors**, select the sensor, and inspect health, freshness, state history, forecast readiness, forecast, and optional source status. | `src/api/app.py:444-473`; `src/sensors/manager.py:34-107`; `frontend/components/SensorFleet.tsx:10-23`; `frontend/components/CommandCenter.tsx:59-165` | Remote state-only telemetry cannot identify candidate sources. Optional source-activity telemetry is bounded and still does not identify a person or confirmed attacker. |

The central processing path is authenticated `POST /api/v1/telemetry` followed
by per-sensor validation and `RemoteSensorRuntimeStore[sensor_id]`; it does not
create a second forecasting pipeline. A valid sensor batch reaches the existing
L=10/K=5 inference path only after schema, identity, timestamp, cadence,
sequence, duplicate, size, and rate checks (`src/api/app.py:583-786`).

## Customer-request boundary

**Customer requests do not pass through Sentinel.** The customer application
continues to receive requests directly. The remote agent observes metadata on
its own host and makes outbound requests to the central API for registration,
heartbeat, status, and telemetry (`src/agent/client.py:54-119`). There is no
agent command channel, reverse-proxy handler, inline blocker, or customer
application route in the Sentinel API.

The monitored application server therefore does not need to accept inbound
Sentinel traffic. Existing documentation that says the agent requires outbound
connectivity to Central Sentinel is current and necessary; it is not stale
remote-connectivity language. The central endpoint still requires a real
deployment boundary such as a trusted TLS terminator and firewall/private
network, which has not been exercised here.

## Evidence ledger

The following claims are supported by repository tests or local checks:

- Admin-only enrollment, one-time registration, sensor credential binding,
  heartbeat, lifecycle status, disable/rotation, and sensor-scoped reads.
- A real `SensorAgent`/`SensorClient` in-process path posting telemetry to a
  central API and reaching the existing LSTM forecast after ten valid states.
- Duplicate/sequence protection, schema and cadence validation, bounded
  buffering, transient retry, permanent rejection, and multi-sensor logical
  isolation. The focused tests are named in
  `tests/api/test_remote_agent_e2e.py`, `tests/api/test_remote_sensors.py`,
  `tests/test_sensor_agent.py`, and `tests/test_sensor_control_plane.py`.
- Python package/build and release-audit checks, frontend typecheck/build, and
  `docker compose config` have been used as release gates. These are local or
  CI-style checks, not deployment evidence.

The working tree also contains an optional authenticated source-activity path
alongside state telemetry. It is not a basis for claiming universal source
attribution: it requires endpoint/port metadata, is bounded, and remains
labelled **Candidate Source**.

## Explicit non-claims

| Capability | Honest status |
| --- | --- |
| Docker | Compose defines central API/dashboard services and has a configuration/build path. Docker daemon startup, health, restart, and capture runtime were not verified here. |
| TLS | Agent production URL and certificate-verification fail-closed checks are implemented and tested. A live staging certificate chain, hostname, reverse proxy, and HTTPS handshake were not tested. mTLS is not implemented. |
| Multi-host / multi-sensor | Per-sensor logical isolation and concurrent in-process tests exist. No two-physical-host soak, five-sensor capacity run, shared multi-worker store, HA, or restart-persistence deployment proof exists. |
| Service supervision | Linux user-systemd unit generation is documented. A real boot/reboot/service-manager run was not verified; Windows-native service installation is not included. |
| Production readiness | No production-capacity, 30-minute soak, penetration-test, OIDC, tenant-isolation, or automatic-response claim is made. |

The central registry persists identity metadata, but remote runtime history and
forecasts are process-local. A central restart requires sensors to reconnect
and rebuild their ten-state history. The bounded agent disk buffer is local
durability with bounded at-least-once delivery, not a distributed queue or
exactly-once guarantee.

## Documentation hygiene result

The stale historical statement in
`docs/DISTRIBUTED_SENSOR_ARCHITECTURE.md` describing packet metadata as not yet
connected to model inference was reconciled on this review. Current docs now
describe the implemented packet-metadata → flow → state path while preserving
the separate state-only/source-activity limitations.

No obsolete outbound-connectivity requirement was removed: agent-to-central
outbound connectivity is a real prerequisite. No documentation in this review
claims Docker runtime, live TLS/reverse-proxy deployment, or physical
multi-host operation.

## Checks run for this review

- `python scripts/release_audit.py --strict` — **PASS**. The audit included
  required release files, internal Markdown links, obvious secret/local-path
  scans, and package artifact checks. It reported only the expected warning
  about ignored local runtime artifacts.
- `git diff --check` — **PASS** (line-ending normalization warnings from Git
  are not whitespace errors).
- Focused remote-agent/sensor suite — **41 passed, 2 warnings**.
- Full `python -m pytest -q` — **293 passed, 2 failed, 2 warnings**. The two
  failures are `tests/api/test_remote_sensor_journey.py::test_remote_sensor_journey_heartbeat_telemetry_forecast_and_dashboard_contract`
  and `tests/test_next_dashboard_contract.py::test_sensor_fleet_uses_stable_identity_and_explicit_selected_detail`.
  They are current working-tree application/frontend contract failures and
  remain outside this documentation-only review.
