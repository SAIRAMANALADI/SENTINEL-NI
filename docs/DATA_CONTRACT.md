# Data Contract

## Purpose

This document defines the current interface between Developer 2 (network telemetry and feature engineering) and Developer 1 (ML and world model) for the verified CSE-CIC-IDS2018 flow slice. The official SIH problem statement is still not present in this repository, so packet-level and forecast-specific requirements remain explicitly bounded below.

## Verified CSE-CIC-IDS2018 flow path

The inspected source is the real `Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv` file. The raw source remains immutable. The implemented handoff is:

```text
RAW INPUT
  -> data/raw/.../Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv
CLEAN FLOW DATASET
  -> data/processed/cic_ids2018_flow_clean.parquet
MODEL-SAFE FLOW FEATURES
  -> data/processed/cic_ids2018_model_features.parquet
```

The clean dataset preserves the original 80 source columns, source row provenance, original timestamp string, parsed `timestamp_parsed`, `Label`, `original_label`, `binary_label`, and raw non-finite token companions for the two affected rate fields. The model-safe table contains only finite numeric CSV-derived features; targets, timestamps, identifiers/proxies, provenance, and the affected rate fields are excluded according to `configs/model_feature_exclusions.yaml`.

The source has 613,104 records after its first header, 33 repeated header artifacts, and 613,071 legitimate flow records. Original labels are preserved exactly; `binary_label` is a separate convenience mapping of `Benign -> 0` and `Infilteration -> 1`.

Packet-level requirements are **NOT yet satisfied by the flow CSV**. TTL, fragmentation, retransmissions, packet-level IAT/burst ordering, packet payload distributions, complete TCP window observations, packet flag order, source IP/port, and complete flow identifiers require a matching PCAP and a separate extraction module.

## Final network-state handoff to Nikhil

The finalized flow-to-state handoff is:

```text
RAW FLOW
  -> data/processed/cic_ids2018_multiday_flow.parquet
CLEAN / ANOMALY-FILTERED NETWORK STATES
  -> data/processed/cic_ids2018_network_states.parquet
FIXED DAY-AWARE STATE SPLITS
  -> data/processed/states/train.parquet
  -> data/processed/states/validation.parquet
  -> data/processed/states/test.parquet
TEMPORAL WINDOWS
  -> owned by Nikhil; not created in this task
WORLD MODEL
  -> owned by Nikhil; not created in this task
```

### State schema

- Schema: `network-state-v1.0`
- Feature schema: `configs/state_feature_schema.yaml`
- State specification: `docs/NETWORK_STATE_SPEC.md`
- Target specification: `docs/TARGET_STATE_SPEC.md`
- Selected aggregation interval: `10` seconds
- State count: `16,127`
- Model-input feature count: `17`
- Metadata columns: `timestamp`, `capture_day`
- Target metadata columns: `malicious_flow_count`, `malicious_flow_ratio`, `binary_attack_state`, `future_attack_state`, `future_target_available`

### Guarantees

- State timestamps are ascending within each `capture_day`.
- No state aggregation crosses a capture-day boundary.
- No model-input feature contains NaN or Inf.
- Attack labels and target metadata are separate from model-input features.
- The complete-day split is fixed: 14/21-Feb train, 22-Feb validation, 28-Feb test.
- The 14 timestamp anomalies are excluded from temporal aggregation, never corrected, and remain preserved in the flow artifact.
- `future_attack_state=-1` and `future_target_available=false` identify terminal states with no future interval; modeling must exclude those target rows.

### Build commands

```powershell
python scripts/build_network_states.py `
  --input data/processed/cic_ids2018_multiday_flow.parquet `
  --interval 10

python scripts/build_state_splits.py `
  --input data/processed/cic_ids2018_network_states.parquet `
  --split-report results/multiday_split_report.json
```

The source flow artifact is immutable. PCAP enrichment is tracked separately in `docs/PCAP_ENRICHMENT_TODO.md`.

## PCAP enrichment gate — current status

The packet-enrichment attempt is currently **BLOCKED**. No local `.pcap`, `.pcapng`, or archive exists. The documented 2018-02-28 source is the 53,251,694,487-byte object `s3://cse-cic-ids2018/Original Network Traffic and Log data/Wednesday-28-02-2018/pcap.zip`, which contains 437 machine capture files. The object supports byte-range access, but the current canonical flow artifact lacks source/destination IPs, source port, Flow ID, and machine identity; only timestamp, destination port, and protocol are available for a potential join. Timestamp/port/protocol matching is collision-prone and no tolerance has been validated.

Consequently, no packet parser, packet-derived feature, flow/PCAP match rate, or enriched state Parquet is claimed. The blocker and exact source evidence are recorded in `docs/PCAP_FLOW_MATCHING_SPEC.md`, `results/PCAP_FEATURE_COVERAGE_REPORT.md`, and `results/PCAP_PROCESSING_REPORT.md`. The flow-only handoff remains the valid ML input until an approved matched PCAP subset or an identity-preserving flow export is supplied.

## A. Raw traffic input

Accepted formats and fields are not finalized. Candidate inputs are CSV traffic records and, only if approved for the final scope, PCAP files. The ingestion layer must preserve source identifiers, timestamps, labels when supplied, and enough provenance to audit transformations.

Required questions before implementation:

- Which dataset and subset are approved?
- What are the license and access conditions?
- Are records flow-level, packet-level, or both?
- Which column is the authoritative timestamp?
- Which labels are ground truth, and at what time granularity?
- Is a PCAP path required by the official SIH statement?

## B. Canonical feature table

The canonical table is the stable handoff from feature engineering to preprocessing. Every candidate below is **PROVISIONAL** until verified against the actual dataset and official SIH statement.

| Candidate field | Status | Notes |
| --- | --- | --- |
| `timestamp` | PROVISIONAL | Authoritative event or flow time is not selected. |
| `src_ip` | PROVISIONAL | Retention, anonymization, and model-use policy are not selected. |
| `dst_ip` | PROVISIONAL | Retention, anonymization, and model-use policy are not selected. |
| `src_port` | PROVISIONAL | Valid range and missing behavior require validation. |
| `dst_port` | PROVISIONAL | Valid range and missing behavior require validation. |
| `protocol` | PROVISIONAL | Encoding depends on the selected dataset. |
| `tcp_flags` | PROVISIONAL | May be absent for non-TCP traffic. |
| `bytes` | PROVISIONAL | Direction and aggregation rule require definition. |
| `packets` | PROVISIONAL | Direction and aggregation rule require definition. |
| `duration` | PROVISIONAL | Units and invalid-value behavior require definition. |
| `inter_arrival_statistics` | PROVISIONAL | Exact statistics and window scope require definition. |
| `bidirectional_statistics` | PROVISIONAL | Directional aggregation requires definition. |
| `ttl_statistics` | PROVISIONAL | Packet availability and aggregation require verification. |
| `tcp_window_statistics` | PROVISIONAL | Packet availability and aggregation require verification. |
| `fragmentation_indicators` | PROVISIONAL | Source availability requires verification. |
| `payload_size_statistics` | PROVISIONAL | Privacy and availability require verification. |
| `retransmission_indicators` | PROVISIONAL | Detection rule requires definition. |
| `fan_out_and_port_diversity` | PROVISIONAL | Window and entity scope require definition. |
| `label` | PROVISIONAL | Ground-truth source and time alignment require verification. |

For each finalized field, add type, units, source column, aggregation rule, missing-value behavior, leakage risk, and version history.

## C. Temporal sequence input

The preprocessing layer will transform ordered canonical rows into sequences of the form:

```text
S(t-n+1), ..., S(t)  →  target(s) at t+1 ... t+K
```

Sequence length and forecast horizon are configurable placeholders in `configs/project.yaml`, not final SIH values. The window builder must record timestamp coverage, scenario identity where available, label alignment, and split membership. Adjacent or overlapping windows must not cross train/test boundaries.

## D. Model output

The future inference interface is expected to return structured data, not presentation text. Candidate fields are:

```python
{
    "current_state": {},
    "forecast": [
        {"step": 1, "probability": None, "state": {}},
    ],
    "attack_stage": {
        "name": None,
        "confidence": None,
        "evidence": [],
    },
    "explanation": [],
}
```

The probability meaning, state dimensions, stage vocabulary, calibration, and explanation format must be defined and validated before model implementation. No placeholder values may be presented as measured results.
