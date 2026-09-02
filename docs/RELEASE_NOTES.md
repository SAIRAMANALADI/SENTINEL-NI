# Sentinel / NI v0.1.0 Release Notes

## Implemented

- Out-of-band Central Sentinel and Remote Sentinel Agent operating model.
- Versioned 10-second network-state contract with 17 flow-derived features.
- Frozen L=10, direct K=5 forecast serving path and recommendation-only policy.
- Replay, mock, local live, remote-agent, and partial Zeek telemetry paths with
  explicit capability boundaries.
- Per-sensor enrollment, authentication, heartbeat, bounded buffering, retry,
  and isolated runtime histories.
- FastAPI control/data plane and Next.js plus Streamlit operator surfaces.
- Python wheel/sdist packaging, dependency locks, Docker Compose definition,
  operator documentation, security policy, and open-source CI.

## Validated

- Python regression, sensor, security, telemetry, and API contracts.
- Frontend typecheck and production build.
- Wheel/sdist build, clean dependency-inclusive wheel smoke, and `pip check`.
- Docker Compose configuration validation.

Exact current results are recorded in
`docs/PHASE_K_PUBLIC_RELEASE_REPORT.md` after the Phase K validation run.

## Not validated in this environment

- Docker daemon startup/restart and container health checks.
- Real reverse-proxy TLS with staging certificates and DNS.
- Two physical remote hosts, five-sensor soak, and long-duration live capture.
- Browser workflow against real sensors.
- Production-capacity, HA, OIDC, mTLS, tenant-isolation, or automatic-response
  claims.

## Operating truth

Sentinel observes traffic in parallel. Customer requests do not pass through
Sentinel. Forecast Score is a raw model score, Predictive Warning is an
operating-policy outcome, Candidate Sources are evidence-based rankings where
telemetry supports them, and Mitigation is a human-reviewed recommendation.
