# Final v0.1 Freeze Report

**Date:** 2026-09-01
**Branch:** `main`
**Release:** `v0.1.0` (local tag created after validation)

## Frozen product contract

- Input: `data/processed/cic_ids2018_network_states.parquet`
- Aggregation: fixed 10-second network states
- Model input: 17 numeric flow-derived state features
- Temporal context: L=10 states
- Forecast: direct K=5 horizons at +10/+20/+30/+40/+50 seconds
- Primary operating threshold: `0.19`
- Target: `future_attack_state(t) = binary_attack_state(t + 10 seconds)`
  within the same capture day, with terminal states lacking a future target
  excluded
- State count: 16,127
- Day-aware split: 2018-02-14 and 2018-02-21 train; 2018-02-22 validation;
  2018-02-28 final test

## Validation evidence

- Python suite: 215 passed, 0 failed, 0 skipped (`python -m pytest -q`,
  69.22 seconds).
- Python clean installation and `pip check`: passed.
- Frontend `npm ci`, typecheck, and production build: passed.
- Docker Compose build, startup, health/readiness, restart, and down/up
  recovery: passed.
- Deterministic replay and dashboard demo: passed.
- Real live capture: passed for the five-minute minimum and an approximately
  fifteen-minute run, with 22 forecast updates and zero recorded drops or
  runtime errors.

## Known limitations

The live soak did not run for 30 minutes. Active flow-table size and callback
queue depth are not exposed as runtime metrics. Live capture depends on host
interface visibility, Npcap/libpcap, and permissions. The service has no
measured production capacity, TLS/OIDC boundary, HA coordination, or automatic
blocking. PCAP fusion remains outside the frozen V1 contract because a safe
flow-to-PCAP mapping is not available.

The freeze is a release boundary, not a claim of universal forecasting
accuracy.
