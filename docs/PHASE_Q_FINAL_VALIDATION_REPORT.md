# Phase Q Final Validation Report

Validation date: 2026-09-04  
Final classification: **OPEN-SOURCE RELEASE READY**

## 1. Environment and topology

Docker Desktop/Linux, Python 3.14.3, Scapy/Npcap Wi-Fi capture, the actual
`sentinel-agent` CLI, Python TLS verification, and `nginx:alpine` were
available. No second physical host, host proxy binary, expired-certificate
endpoint, or TruffleHog installation was available.

Validated topology:

`real Wi-Fi capture -> real Sentinel Agent -> HTTPS -> Nginx -> central API -> sensor runtime`

An independent HTTP server represented the customer path and was not routed
through Sentinel.

## 2. Docker runtime and persistence

Compose backend, dashboard, and frontend were healthy. The backend listened
internally on `0.0.0.0:8000` but was published only as
`127.0.0.1:8000->8000/tcp`; dashboard and frontend were also loopback-only.

A registered sensor remained in the host-backed registry across Compose
restart and `down/up`. Runtime history reset after restart as documented and
was not represented as persistent.

## 3. TLS and forwarded-header security

A real Nginx container terminated TLS on `https://localhost:8443` and proxied
to the backend. The temporary CA was trusted by Python `httpx`; wrong CA and
wrong hostname checks failed certificate verification. No insecure TLS option
was used. Expired-certificate behavior is **NOT VERIFIED**.

Production trusted-proxy mode accepted the proxy’s overwritten
`X-Forwarded-Proto: https` and rejected direct HTTP and forged forwarded
headers. The proxy allowlist used the exact container `/32`, not a broad
Docker subnet.

## 4. Real agent and live capture

A fresh agent was initialized, registered, validated, started, inspected, and
stopped through the actual package CLI. It used the Wi-Fi interface and
`tls_verify=true`. Central received authenticated heartbeats and reported the
sensor online while running.

The live collector used Scapy/Npcap and preserved packet capture timestamps.
The measured live probe observed approximately 1,042 packets, emitted valid
states, and reported no drops. The Q continuous real-traffic attempt ran for
approximately 130 seconds.

## 5. Remote L=10 and K=5 forecast

**NOT VERIFIED.** The central runtime rejected duplicate or non-contiguous
10-second states rather than rewriting them to receive time. The Q sensor
ended with `state_count=7`, `history_length=1`, and `history_required=10`; no
forecast update or forecast score occurred. The existing LSTM K=5 artifact was
not changed and no forecast output was injected.

This is a validation limitation caused by the observed live traffic/window
pattern, not evidence that L=10 readiness passed.

## 6. Timing and telemetry semantics

The collector and central contract use packet/state timestamps, distinct from
telemetry receive time. Duplicate/gap rejection demonstrated that delayed
states were not rewritten to arrival time. A complete ten-state cadence and
forecast horizon validation is **NOT VERIFIED** because the live stream did
not produce ten contiguous accepted windows.

## 7. Dashboard and frontend

Frontend typecheck/build and container health passed. The real sensor API
reported ONLINE/FRESH while heartbeats were active and later DEGRADED/OFFLINE
with stale telemetry after the agent stopped. A browser dashboard view showing
that real sensor as ONLINE, FRESH, and FORECAST READY was not verified; no demo
forecast was substituted.

## 8. Multi-sensor and five-sensor tests

No second physical host was available. Existing automated isolation contracts
passed, but physical multi-host and five-sensor behavior, independent live
forecasts, and capacity are **NOT VERIFIED**. Isolated processes are not being
called physical multi-host evidence.

## 9. Central outage and recovery

The real agent was left running while central ingestion was stopped for a
controlled approximately 12-second outage plus container restart. Four
telemetry batches were buffered. Logs showed retry delays of 1 and 2 seconds,
then successful post-restart delivery and buffer flush. Zero loss was not
claimed because affected states were not all valid contiguous runtime states.

## 10. Agent outage and central restart

After controlled agent stop and freshness expiry, central reported the sensor
OFFLINE/STALE. Restarting the same configuration preserved the same sensor ID,
registration, and authenticated heartbeat path; central returned to an online
agent state. The Windows `stop` command’s PID signal path still returned
`[WinError 87]`; Ctrl-C was used for cleanup.

The registry survived central restart/down-up. The process-local runtime
history rebuilt below the required ten states, so forecast recovery is
**NOT VERIFIED**.

## 11. Customer request-path isolation

An independent local application server returned HTTP 200 before, during, and
after Sentinel backend stoppage. Sentinel remained a parallel observer and no
request proxying was introduced.

## 12. Certificate, security, and secrets

Trusted CA, wrong CA, and hostname mismatch were tested with Python TLS. An
expired certificate was not available for a practical endpoint. Release audit,
security tests, diagnostics, and tracked-file/log review found no real token,
private key, or authorization header. A generic documentation phrase about
Bearer tokens was not a credential. TruffleHog was unavailable and is
**NOT VERIFIED**.

## 13. Rate limits, buffers, source intelligence, and mitigation

Automated rate-limit and bounded-buffer tests passed. The live outage observed
bounded buffering and retry, but did not reach overflow or demonstrate noisy
sensor starvation; live load behavior is **NOT VERIFIED**.

Live source activity remained sensor-scoped and was described as candidate
source information, never as attackers. Mitigation responses retained
`simulation_only=true` and `automatic_block=false`; no firewall, blocking, or
customer interception occurred.

## 14. Soak and resource observations

The real continuous-traffic run was approximately 130 seconds, not 30
minutes. No soak CPU/RAM/queue/latency series was collected. Docker reported
4 CPUs and 3.825 GiB, which is an environment observation and not a capacity
claim.

## 15. Package, UI, and model integrity

The full suite passed **311 tests, 2 warnings**. Wheel/sdist builds, clean
install, `pip check`, CLI help, frontend typecheck/build, release audit,
environment checks, Compose validation, and `git diff --check` passed.

Protected model/data paths had no working-tree changes. The existing 17
features, target, L=10, K=5, threshold 0.19, inference implementation, and
model artifacts remained unchanged.

## 16. Exact PASS results

- Docker Compose health/readiness and loopback bindings.
- Registry persistence across restart and `down/up`.
- Real Nginx TLS proxy, trusted CA, wrong-CA rejection, hostname rejection.
- Actual agent registration, HTTPS heartbeats, diagnostics, and live capture.
- Central outage buffering, retry, recovery, and agent offline/recovery state.
- Customer-path independence and simulation-only mitigation.
- 311-test regression, packaging, frontend, release, environment, and diff gates.

## 17. Exact FAIL results

- No product assertion failed in the final automated regression.
- The Windows agent `stop` operation returned `[WinError 87]` during live
  cleanup; this remains a concrete lifecycle defect/limitation.
- Live telemetry included rejected duplicate/gapped states, so the real L=10
  criterion did not pass.

## 18. Exact NOT VERIFIED results

Real L=10 readiness, live K=5 forecast scores, forecast-ready dashboard,
physical multi-host, five-sensor capacity, full cross-sensor live test,
expired certificate, active credential revocation, live network/capture
failure injection, 30-minute soak, latency/resource time series, TruffleHog,
and public production ingress.

## 19. Remaining blockers and final decision

The remaining blockers are external staging capacity and the missing contiguous
real-state run: a second host or controlled multi-host environment, a practical
expired certificate, a 30-minute observation window, and a live stream that
produces ten accepted contiguous 10-second states. The repository remains
**OPEN-SOURCE RELEASE READY** only; it is not being promoted to
`STAGING READY` or production-ready.
