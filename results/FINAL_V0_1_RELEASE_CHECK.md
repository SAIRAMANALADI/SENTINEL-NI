# SIH26-26153 — Final v0.1 Release Check

**Date:** 2026-09-01
**Scope:** release validation only; the frozen ML/data contract was not
changed.

## Automated validation

| Check | Result | Evidence |
| --- | --- | --- |
| Python test suite | PASS | `python -m pytest -q` — **215 passed in 69.22s**, 0 failed, 0 skipped. |
| Docker daemon | PASS | `docker info` returned a live Docker Desktop Linux server. |
| Docker image build | PASS | `docker compose config --quiet` and `docker compose build` completed successfully. |
| Compose startup | PASS | `docker compose up -d`; backend, dashboard, and frontend all healthy. |
| API health | PASS | `GET /api/v1/health` returned HTTP 200. |
| API readiness | PASS | `GET /api/v1/ready` returned HTTP 200 with all checks true. |
| Dashboard health | PASS | Streamlit `/_stcore/health` returned HTTP 200. |
| Frontend health | PASS | Next.js root returned HTTP 200. |
| Compose restart | PASS | `docker compose restart`; health/readiness recovered with HTTP 200. |
| Down/up recovery | PASS | `docker compose down` followed by `docker compose up -d`; all services healthy. |

The versioned API paths are `/api/v1/health` and `/api/v1/ready`; the literal
unversioned `/health` path is not an application route.

## Real live soak

### Five-minute minimum run

The first real host capture ran for more than five minutes on the physical
`Wi-Fi` interface. It observed 5,835 packets, 5,273 valid events, 562
ignored non-IP packets, 354 completed flows, and 9 valid states. Drops,
rejections, callback errors, and runtime errors were all zero. It did not
reach the 10-state forecast threshold during that run.

### Fifteen-minute run

A second real host capture ran for approximately 15 minutes on `Wi-Fi`:

- 9,438 packets seen;
- 8,133 valid packet events;
- 1,305 ignored non-IP packets;
- 608 completed flows;
- 31 valid network states;
- bounded history buffer held at 10 states;
- 22 forecast updates;
- 0 dropped events;
- 0 rejected events;
- 0 runtime/callback errors;
- final process RAM approximately 425 MB;
- final API read latency samples remained below 0.5 seconds after forecast
  activation.

The run reached `FORECAST_READY` at 12 states and produced the live K=5
forecast path. Observed latency spikes occurred (approximately 1.82 seconds
and 0.51 seconds in individual reads) and recovered without a crash or
backlog. No 30-minute run was performed.

The current runtime snapshot does not expose active flow-table size or queue
depth when the live adapter uses its callback path. Completed-flow count,
drop count, rejection count, state-buffer size, and forecast-update count were
observed instead; active-flow and queue-depth capacity claims are therefore
not made.

## End-to-end verification

### Real live path

PASS for the observed chain:

`real Wi-Fi packets → packet events → completed flows → 10-second states →
10-state history → LSTM K=5 forecast → five forecast updates/horizons →
threshold 0.19 → runtime forecast readiness`

The live run produced real forecast updates. Source prioritization and
simulation-only mitigation remained available in the runtime contract. No
automatic blocking was performed.

### Deterministic API/dashboard path

PASS. The browser dashboard and `POST /api/v1/demo` showed:

- +10/+20/+30/+40/+50 forecast horizons;
- primary Forecast Score and threshold `0.19`;
- Predictive Warning state;
- ranked candidate sources;
- mitigation recommendations;
- explanation/model sensitivity;
- `Simulation only: TRUE`.

### Stop/restart

PASS. Stop returned `LIVE_STOPPED`. After a forecast-bearing session, restart
created a different session ID, reset current history to `0/10`, returned
`WAITING_FOR_LIVE_HISTORY`, and retained the previous result only as an
explicit stale prior forecast. No stale result was presented as current.

### Replay

PASS. The existing command:

```powershell
python scripts/run_replay_demo.py --max-states 20 --speed 0
```

processed the replay source, buffered 10 states, and emitted actual +10/+20/
+30/+40/+50 Forecast Scores with the expected no-warning output. This is the
deterministic replay/demo path, not live network telemetry.

## Known limitations

- No 30-minute soak was run.
- Active flow-table size and callback-path queue depth are not exposed as
  runtime metrics.
- The live capture path is host-dependent and requires Npcap/libpcap,
  permissions, and a selected interface.
- Live network traffic is traffic-dependent; forecast readiness is not
  guaranteed immediately after startup.
- The frozen model is a development checkpoint; no new model or accuracy
  claim was made in this release check.
- Mitigation remains recommendation-only and simulation-only.
- PCAP attribution/fusion remains outside the frozen V1 contract.
- No TLS/OIDC, HA, measured production capacity, or 30-minute soak claim is
  made.

## Final classification

OPEN-SOURCE V0.1:
READY WITH LIMITATIONS
