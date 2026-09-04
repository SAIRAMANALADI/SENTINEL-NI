# Phase P Final Staging Report

Validation date: 2026-09-04  
Repository: current SIH26 checkout

## 1. Release gate

**OPEN-SOURCE RELEASE READY**

This is the only final classification for this run. It means the package,
automated contracts, local Docker runtime, isolated TLS proxy, and release
checks are ready for an open-source release. It does not mean `STAGING READY`
or production-ready: no second host, five-sensor run, active outage recovery,
30-minute soak, or public ingress was available.

## 2. Environment

Docker Desktop was started successfully. `docker info` reported Docker CLI
29.6.2, a WSL2 Linux daemon, 4 CPUs, and 3.825 GiB. Python 3.14.3,
`cryptography`, Python `ssl`/`httpx`, Scapy/Npcap, and the actual
`sentinel-agent` entry point were available. Host Nginx/Caddy/Traefik,
`mkcert`, OpenSSL, a second physical host, and TruffleHog were unavailable.
See [`PHASE_P_ENVIRONMENT.md`](PHASE_P_ENVIRONMENT.md).

## 3. Docker Compose stack

The existing backend, Streamlit dashboard, and Next.js frontend were started
with Compose. All three reached healthy state. Backend `/api/v1/health` and
`/api/v1/ready` returned HTTP 200; frontend `/` and dashboard `/_stcore/health`
also returned HTTP 200.

## 4. Bindings and runtime isolation

The backend listened internally on `0.0.0.0:8000`, while the host binding was
`127.0.0.1:8000->8000/tcp`. Dashboard and frontend were likewise loopback-only
on ports 8501 and 3000. Backend model, configuration, and sample-data mounts
were read-only; audit and sensor registry paths were writable.

## 5. Persistence and restart

The original named registry volume produced a real registration failure because
the unprivileged container process could not write the root-owned mount. The
Compose mount was changed to `./results/sensors:/app/results/sensors`, and the
registration contract test was updated accordingly. A sensor registered before
`docker compose down` remained present after `docker compose up -d`; the
process-local runtime history reset to zero as designed.

## 6. TLS reverse proxy

An actual `nginx:alpine` container was run on the Compose network at
`https://localhost:8443`, proxying to `backend:8000`. The temporary certificate
chain included `localhost` and `127.0.0.1` SANs. A trusted Python `httpx` request
returned HTTP 200 for `/api/v1/health`; Python TLS verification rejected both a
wrong CA and a wrong hostname. No `verify=False`, `curl -k`, or insecure
production fallback was used. Expired-certificate behavior was not verified.

## 7. Trusted-proxy enforcement

The backend was run in production trusted-proxy mode with the actual Nginx
container IP restricted to a `/32` CIDR. Direct host HTTP access to the live
API returned `403 HTTPS_REQUIRED`; a forged forwarded header from the direct
host path was also rejected. The proxy overwrote `X-Forwarded-Proto` with
`https` and successfully forwarded authenticated requests.

An initial broad Docker-subnet allowlist made a direct forged-header request
reach authentication, demonstrating why deployment must use the exact proxy
CIDR rather than `172.20.0.0/16`. The configuration was narrowed to the actual
proxy address before the final check.

## 8. Actual agent package

The real CLI completed `init`, `register`, `config validate`, `start`, and
`status` flows. A temporary production agent configuration used
`https://localhost:8443`, the generated CA, the Wi-Fi interface, and
`tls_verify=true`. Registration succeeded through Nginx, and central observed
authenticated heartbeats with the sensor in `ONLINE`/`CONNECTED` state during
the run.

The Windows `stop` subcommand returned `[WinError 87]` when attempting its PID
signal path; Ctrl-C was used for controlled cleanup. This is recorded as an
agent lifecycle limitation for follow-up rather than hidden as a pass.

## 9. Live capture

The Wi-Fi adapter was genuinely available. A 22-second live collector probe
observed approximately 1,042 packets, emitted three valid timestamped states,
and reported no drops. The collector retained the approved 17-feature boundary;
raw payloads were not used.

## 10. Telemetry contract

The first real Compose registration worked but live telemetry exposed a concrete
contract defect: the collector emitted flat feature fields while the remote API
requires a nested `features` object. `TelemetryBatcher` now nests the approved
17 fields, and `tests/test_sensor_agent.py` covers the regression. After the
fix, direct live-captured batches and actual agent sequences were accepted over
the HTTPS proxy. The focused agent/API/HTTPS suite passed 28 tests.

The long run still had rejected or gapped states; the central response recorded
`state_count=9`, `rejected_state_count=12`, and a history reset due to an
interval gap. This is reported as observed behavior, not converted into a
fabricated success.

## 11. LSTM readiness

The installed model remained the existing LSTM K=5 artifact. Central required
10 contiguous states, but the live run ended at `history_length=2` with
`history_required=10`, `forecast_status=BUILDING_HISTORY`, and no forecast.
Therefore real L=10 forecast readiness is **NOT VERIFIED**.

## 12. Multi-sensor behavior

Automated registry/isolation contracts passed and the Docker registry contained
three registered test identities. A simultaneous physical multi-sensor or
five-sensor run was not available, so capacity and cross-sensor isolation in
staging are **NOT VERIFIED**.

## 13. Dashboard and frontend

The dashboard and frontend containers were healthy, the frontend typecheck and
production build passed, and the backend BFF route compiled. A browser/customer
journey against a real sensor and production-authenticated dashboard was not
run; that path is **NOT VERIFIED**.

## 14. Health transitions

Central reported heartbeat freshness and `ONLINE`/`CONNECTED` while the agent
was running. After the run stopped and telemetry became stale, the sensor
response reported `telemetry_status=STALE`, `status=DEGRADED`, and forecast
waiting/building history. No forecast was emitted while history was incomplete.

## 15. Outage and recovery simulation

Automated retry, buffering, malformed-telemetry, stale-state, invalid-credential,
revocation, and restart-isolation tests passed. A real central outage, network
cut, live credential revocation, active-agent reconnect, or controlled capture
failure was not injected. Those scenarios remain **NOT VERIFIED** live.

## 16. Mitigation policy

The live sensor response exposed source-priority recommendations with
`simulation_only=true` and `automatic_block=false`. No blocking or destructive
network action was performed.

## 17. Resource observations

Only Docker engine capacity was observed: 4 CPUs and 3.825 GiB. No valid
30-minute CPU, RAM, queue, buffer, latency, or throughput time series was
collected. Resource capacity is **NOT VERIFIED**.

## 18. Security and secret handling

Production agent configuration used a CA path and `tls_verify=true`; bearer
tokens were supplied through process configuration and were not written into
the repository report. Direct HTTP and forged forwarded-protocol paths were
blocked under trusted-proxy mode. Existing security tests, release audit, and
diff checks passed. TruffleHog was unavailable, so its scan is **NOT VERIFIED**.

## 19. Model and data integrity

The existing logistic baseline, preprocessor, and LSTM K=5 artifacts were not
modified. The model/data diff check found no protected artifact changes.

## 20. Packaging

Wheel and sdist builds passed after the telemetry serializer change. Clean
installation, CLI smoke, and `pip check` passed. `py scripts/release_audit.py
--strict` and `py scripts/check_environment.py` passed.

## 21. Automated regression

The post-fix full suite passed **311 tests** with two existing deprecation
warnings. Frontend `npm run typecheck` and `npm run build` passed. Compose
configuration validation and `git diff --check` passed.

## 22. Failures found and fixed

1. Root-owned named registry mount caused HTTP 500 on live registration. Fixed
   with the host-backed persistent sensor mount and matching contract test.
2. Live collector feature shape caused HTTP 422 at the remote telemetry API.
   Fixed by nesting the approved feature columns in `TelemetryBatcher` and
   adding a regression test.
3. A broad trusted-proxy CIDR allowed a direct forged forwarded header to reach
   authentication. Fixed operationally by using the exact Nginx `/32`; the
   report documents this deployment requirement.

## 23. Remaining failures or limitations

- Windows agent `stop` signal path returned `[WinError 87]`.
- Some live states were rejected or gapped, preventing L=10 forecast readiness.
- Expired certificate, active outage recovery, credential revocation against a
  running agent, five sensors, physical multi-host, customer path, public
  ingress, and 30-minute soak were not verified.

## 24. Release checklist

The synchronized checklist is in
[`RELEASE_CANDIDATE_CHECKLIST.md`](RELEASE_CANDIDATE_CHECKLIST.md). The failure
matrix is in [`FAILURE_RECOVERY_MATRIX.md`](FAILURE_RECOVERY_MATRIX.md).
Both distinguish PASS from NOT VERIFIED and preserve the staging limitations.

## 25. Cleanup state

The temporary Nginx container and temporary certificate material are test-only.
The Compose stack is restored to its development defaults after the proxy
exercise, with the host-backed `results/sensors` mount retained. Runtime files
under `results/` are local ignored artifacts and were not broadly deleted.

## 26. Final decision

**OPEN-SOURCE RELEASE READY** — package and local/runtime security gates pass;
staging and production deployment gates remain open pending a real multi-host,
multi-sensor, outage, soak, and forecast-readiness run.
