# Release Manifest (Compatibility Pointer)

The canonical public release record is now
[`PUBLIC_RELEASE_MANIFEST.md`](PUBLIC_RELEASE_MANIFEST.md). This file remains
for compatibility with links from earlier release phases; versioned serving
contracts below are retained as historical reference and must agree with the
canonical manifest.

**Current gate:** Phase Z is the current coordinator record. This working-tree
candidate is not published or externally validated; publication remains
pending approved-commit/tag reconciliation and the external validation gates.

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
Full raw/processed datasets, PCAP archives, runtime registries, logs, and most
model outputs are intentionally excluded from source distribution and Git.
Explicitly approved small fixtures, tracked release checkpoints, and release
evidence files are included where required for reproducible validation.

## Current evidence boundary

The current decision is **CONDITIONAL CANDIDATE — PUBLICATION PENDING PROVENANCE RECONCILIATION**. Python, frontend,
package, dependency, contract, local Docker, browser, customer-path, and
isolated TLS checks pass. Physical multi-host/five-sensor operation, a
30-minute soak/resource series, expired certificates, public ingress, and
TruffleHog remain **NOT VERIFIED**. See the [Public Release Manifest](PUBLIC_RELEASE_MANIFEST.md)
and [Phase Z External Validation Report](PHASE_Z_EXTERNAL_VALIDATION_REPORT.md)
for the authoritative status.
