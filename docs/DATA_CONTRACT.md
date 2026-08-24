# Data Contract

## Purpose

This is the current interface between the data/network pipeline and the ML/forecasting pipeline for SIH26-26153. The authoritative ML input is the frozen flow-derived network-state artifact. Source labels remain provenance; they are not model features.

## Source and provenance

The selected CSE-CIC-IDS2018 flow files are stored locally under:

```text
data/raw/cse-cic-ids2018/flow/
```

The exact four-file acquisition record, sizes, and SHA-256 values are in `results/DATA_ACQUISITION_MANIFEST.json`. The raw files are ignored by Git and must not be committed. The 28-Feb filename is preserved exactly as `Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv`.

The clean flow artifacts preserve source `Label`, `original_label`, original timestamp text, parsed timestamps, source row numbers, and provenance. The historical `binary_label` convenience column belongs to the earlier flow-level baseline path; the active V1 state target is `future_attack_state`.

## Active state handoff

```text
RAW FLOW CSVs
  -> data/processed/cic_ids2018_multiday_flow.parquet
10-SECOND NETWORK STATES
  -> data/processed/cic_ids2018_network_states.parquet
DAY-AWARE SPLITS
  -> data/processed/states/train.parquet
  -> data/processed/states/validation.parquet
  -> data/processed/states/test.parquet
TEMPORAL WINDOWS
  -> src/forecasting/windowing.py
MODEL / INFERENCE
  -> models/lstm_multistep_k5.pt
  -> src/forecasting/inference.py
```

## Network-state schema

- Schema version: `network-state-v1.0`
- State interval: exactly 10 seconds
- State count: 16,127
- Model features: exactly 17, listed in `configs/state_feature_schema.yaml`
- Metadata: `timestamp`, `capture_day`
- Target metadata: `malicious_flow_count`, `malicious_flow_ratio`, `binary_attack_state`, `future_attack_state`, `future_target_available`
- All model features are numeric and finite in the frozen artifact.

## Target

```text
malicious_flow = 1 if source Label != "Benign", otherwise 0
binary_attack_state(t) = 1 if the 10-second state contains >= 1 malicious flow
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The future target remains within the same `capture_day`. Terminal states use `future_attack_state=-1` and `future_target_available=false` and are excluded from supervised windows. Original `Label` values remain unchanged and are not mapped to MITRE by this contract.

## Splits

- Train: `2018-02-14`, `2018-02-21`
- Validation: `2018-02-22`
- Test: `2018-02-28`

Splits are complete capture-day assignments. Rows are not randomly distributed across partitions, and temporal windows cannot cross day or split boundaries.

## Window and inference contract

The active forecasting model consumes exactly 10 chronological states × 17 numeric features. The window builder rejects missing, duplicate, non-monotonic, cross-date, or non-10-second state timestamps. The inference API additionally requires the exact feature order followed by `timestamp` and `capture_day`.

The direct multi-step model produces K=1, K=3, or K=5 future state scores. The primary offline demo uses K=5, covering +10s through +50s. Scores are raw **Forecast Scores**, not calibrated probabilities. The configured policy displays **Predictive warning** or **No predictive warning**; it does not claim attack confirmation.

## PCAP boundary

The current contract is flow-derived. TTL, fragmentation, retransmission, packet-order/IAT, payload, complete TCP-window, and other packet-only features are unavailable. The matching 28-Feb PCAP archive is not downloaded because canonical flow-to-PCAP identity fields are insufficient for a defensible join. No packet feature is included in V1.
