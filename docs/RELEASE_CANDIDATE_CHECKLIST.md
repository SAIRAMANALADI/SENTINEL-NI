# Release Candidate Checklist

Phase L validation date: 2026-09-02
Legend: a checked item has the exact evidence recorded below; an unchecked item is **NOT VERIFIED**, not silently assumed to pass.

## Core release checks

- [x] Package builds — wheel and sdist build passed; see [`PHASE_L_RELEASE_CANDIDATE_REPORT.md`](PHASE_L_RELEASE_CANDIDATE_REPORT.md).
- [x] Clean install — clean wheel import/CLI smoke passed.
- [x] CLI works — `sentinel-agent --help` and version smoke passed.
- [x] Central server works locally — direct Uvicorn `/api/v1/health` and `/api/v1/ready` returned healthy/ready.
- [x] Agent registration contract — automated agent identity/registration tests passed.
- [x] Agent telemetry contract — automated telemetry/authentication tests passed.
- [x] Heartbeat contract — automated heartbeat/lifecycle tests passed.
- [x] Sensor health contract — automated sensor-state tests passed.
- [ ] Multi-sensor physical deployment — no second physical host was available.
- [ ] TLS staging — no live TLS endpoint/certificate chain was available.
- [ ] Reverse proxy — no staging reverse proxy was available.
- [ ] Docker runtime — daemon unavailable; Compose config only was verified.
- [ ] Restart persistence — Docker/physical central restart and registry persistence were not verified.
- [x] Automated outage/retry contracts — automated buffering/retry/stale-state tests passed.
- [ ] Physical outage recovery — no deployed agent/central outage exercise was available.
- [x] Live capture — real Wi-Fi/Npcap capture passed for 10 seconds and an independent approximately 5-minute observation.
- [x] Wrapper startup/release validation — corrected wrapper passed on a fresh port with health, readiness, real capture, forecast readiness, stop/restart state reset, and owned-process cleanup; see [`PHASE_M_WRAPPER_FIX_REPORT.md`](PHASE_M_WRAPPER_FIX_REPORT.md).
- [ ] 30-minute soak — not run; the valid run was `301.79` seconds.
- [ ] Frontend with real sensor — build passed, but browser validation against real sensors was unavailable.
- [x] Security checks — prior secret/path/link/security audit evidence passed.
- [x] Documentation — release audit and documentation consistency checks passed.
- [x] Model integrity — frozen ML/data paths and contract values remained unchanged.

## Explicit release limitations

- Docker runtime is not validated on this host.
- Real TLS/reverse proxy and physical remote deployment are not validated.
- Multi-host and five-sensor behavior are not validated.
- A 30-minute soak with CPU/RAM/queue time series is not validated.
- Docker, TLS/reverse proxy, physical remote deployment, multi-host behavior, and 30-minute resource soak remain unverified.

Final classification: **OPEN-SOURCE RELEASE READY WITH ENVIRONMENT VALIDATION PENDING**.
