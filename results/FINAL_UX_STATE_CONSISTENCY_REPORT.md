# Final UX State Consistency Report

## Scope

Final product-credibility and UX state pass for the Full Integrated Demo. The model, inference API, target, feature schema, forecast scores, source attribution logic, mitigation logic, threshold, and data pipeline were not modified.

## P0 result

`PASS WITH LIMITATIONS`

All fixable P0 state-consistency issues in the current runtime are addressed. Real live capture cannot be fully exercised in the default mock-telemetry Compose profile, so this is not a claim of live-interface acceptance.

## Corrections

- Backend freshness now reports `DATA FRESH` only while running, `DATA STALE` when a running adapter is stale, `LAST LIVE UPDATE: <timestamp>` after a stopped session with an event, and `NOT CURRENT` when stopped without an event.
- Frontend outage state clears live and demo data and shows only `BACKEND UNAVAILABLE`, `Sentinel cannot reach the processing service.`, and `Retry connection`.
- Demo mode is explicit and isolated: `DEMO MODE`, `PREPARED DATA`, `No live capture`, and `NOT LIVE`.
- Demo history uses only the demo response's `history_length`; live totals and buffers are not mixed into it.
- Live presentation separates total `Network states` from the authoritative `Forecast history x / 10` buffer.
- Forecast wording retains `Forecast Score`, explains threshold semantics, and never presents a warning as confirmed attack detection.
- Candidate sources remain ranked evidence, never attacker attribution. Mitigation remains separate and displays `Simulation only: TRUE` with automatic blocking disabled.
- Technical contract details are progressively disclosed under `View technical details`.

## Executed validation

| Scenario | Result | Evidence |
| --- | --- | --- |
| A. Startup / stopped | PASS | Browser DOM snapshot after rebuild: `REPLAY READY`, `STOPPED`, `NOT CURRENT`, `Forecast history 0 / 10`. |
| B. Demo | PASS | Browser snapshot and screenshot: `DEMO MODE`, `Predictive warning`, `Forecast Score 0.3215`, `NOT LIVE`, `Forecast history 10 / 10`. |
| C. Replay separation | PASS | Browser startup identifies `REPLAY MODE`; no demo result is present before Run demo. |
| D. Live before capture | NOT EXECUTED | Default Compose uses mock telemetry; no real capture interface was authorized for this run. |
| E. Live capture / F. history build / G. live forecast ready | NOT EXECUTED | Requires `SIH_TELEMETRY_MODE=live`, a permitted interface, and capture permissions. |
| H. Warning semantics | PASS | Demo browser snapshot shows threshold context and explicitly says a warning does not mean an attack is confirmed. |
| I. No-warning semantics | NOT EXECUTED | Current prepared demo is warning-positive; no no-warning fixture was introduced. |
| J. Stopped state | PASS | Backend unit/API consistency tests plus browser startup show no `DATA FRESH` while stopped. |
| K. Stale state | COVERED BY CONTRACT | Backend state logic and existing stale/restart tests cover retained forecasts; live stale timing needs a real live adapter. |
| L. Backend outage | PASS | Backend container was stopped; browser rendered only `BACKEND UNAVAILABLE` and `Retry connection`; no score/source/recommendation data remained visible. |
| M. Recovery | PASS | Backend was restarted with health wait; browser returned to `REPLAY READY` and `NOT CURRENT`. |
| N. Restart isolation | PASS | `tests/test_live_restart_isolation.py` passed; active history/source/recommendation state resets and old forecast is stale-only. |
| O. Invalid interface | COVERED BY EXISTING TESTS | Existing telemetry/API tests passed; real interface selection was not attempted. |
| P. Model unavailable | COVERED BY EXISTING TESTS | Existing readiness/API tests passed. |
| Q. Malformed telemetry | COVERED BY EXISTING TESTS | Existing live API and telemetry contract tests passed. |

## Test and build evidence

- `python -m pytest -q` → **214 passed** in 67.01s.
- `npm run typecheck` → passed.
- `npm run build` → passed.
- `npm audit --audit-level=high` → 0 vulnerabilities.
- `docker compose up -d --build --wait` → backend, dashboard, and frontend healthy.
- Browser viewport: 1366×768; `scrollWidth=1351`, so no horizontal overflow.
- Screenshot: `results/frontend_state_consistency_1366x768.png`.

## Known limitations

- The default local Compose profile is mock telemetry; live capture lifecycle and permission failures need a host configured for live capture.
- Source ranking only shows fields returned by the backend. No timestamp window is invented when absent.
- No no-warning demo fixture was added, because fabricating product data was out of scope.
- The frontend refreshes runtime state every five seconds; an outage is displayed after the failed request completes.
