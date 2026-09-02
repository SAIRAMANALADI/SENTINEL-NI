# Release Manifest

## Identity

| Item | Value |
| --- | --- |
| Release | `v0.1.0` open-source release candidate |
| Python package | `sih26-26153==0.1.0` |
| Agent version | `0.2.0` |
| Telemetry protocol | `1` |
| Telemetry schema | `1` |
| Network-state schema | `network-state-v1.0` |
| Model version | `LSTM-DEVELOPMENT-V1-direct-multistep-K5` |
| Operating policy | `operating-policy-v1`, primary threshold `0.19` |
| License | MIT; see [LICENSE](../LICENSE) |

## Frozen serving contract

- Ten chronological states (`L=10`) at a 10-second cadence.
- Five direct forecast horizons (`K=5`): +10s, +20s, +30s, +40s, +50s.
- Exactly 17 numeric flow-derived state features in
  `configs/state_feature_schema.yaml`.
- `future_attack_state(t)` is the approved next-state target within the same
  capture day; terminal states are unavailable rather than fabricated.
- The threshold is an operating-policy boundary. Forecast Score is not a
  calibrated probability.
- Mitigation is recommendation-only and simulation-only.

## Distribution

The supported Python distribution is a wheel or source distribution built from
`pyproject.toml`. `requirements.lock.txt` records the verified Python 3.14
dependency set. `frontend/package-lock.json` locks the frontend dependencies.
Raw/processed datasets, PCAP archives, runtime registries, logs, and most model
outputs are intentionally excluded from source distribution and Git.

## Evidence boundary

Automated Python, frontend, package, dependency, and contract checks are part
of the release validation. Docker runtime, staging TLS/reverse proxy,
physical multi-host operation, browser validation with real sensors, and
sustained live capture soak require infrastructure not available in the
current development environment. See [Environment Support](ENVIRONMENT_SUPPORT.md)
and [Phase J validation](STAGING_VALIDATION_REPORT.md).
