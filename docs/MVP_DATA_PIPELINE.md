# MVP Data Pipeline

Date: 2026-08-24  
Project: SIH26-26153 — AI Based Network Attack Forecasting

This is a design contract for the selected CSE-CIC-IDS2018 slice. It does not implement ingestion, extraction, feature generation, or modeling.

## Pipeline boundary

```text
RAW TRAFFIC
  ├── generated flow CSVs
  └── matching raw PCAPs
        │
        ├── FLOW EXTRACTION
        └── PCAP FEATURE EXTRACTION
                    │
                    v
          TIMESTAMP ALIGNMENT
                    │
                    v
          CANONICAL FEATURE TABLE
                    │
                    v
          TEMPORAL STATE WINDOWS
                    │
                    v
             MODEL INPUT
```

The raw source files remain immutable. Every derived artifact must retain a source-file reference and extraction version.

## Stage contract

| Stage | Input | Output | Tool / method | Format | Owner |
|---|---|---|---|---|---|
| Raw traffic registration | Original CSE flow CSV and matching PCAP | Acquisition manifest with file identity, size, checksum, source URL, and license note | Read-only inventory plus SHA-256 | `JSON` manifest | Data engineer |
| Flow extraction | Generated per-machine flow CSV | Validated flow table with original columns and preserved source label | Delimited-text reader selected after header/encoding inspection; no assumed schema | `Parquet` derived table plus original CSV retained | Developer 1 |
| PCAP feature extraction | Matching raw PCAP | Packet evidence keyed by capture/file, packet time, and flow join keys | Versioned packet reader/extractor; derive only observable packet fields | `Parquet` packet table | Developer 2 |
| Timestamp alignment | Flow table, packet table, source metadata | One documented UTC/internal-time representation and alignment report | Explicit timezone/unit conversion; source timestamps preserved | `Parquet` tables plus `JSON` report | Data engineer |
| Flow/packet join validation | Aligned flow and packet tables | Match-rate and unmatched-record report | Five-tuple plus time tolerance, with collision handling; never silent many-to-one joins | `JSON` report and validation table | Developer 1 + Developer 2 |
| Canonical feature table | Validated flow fields, packet-derived fields, and labels | One row per flow with provenance and missingness flags | Schema implementation after actual headers are approved | `Parquet` | Developer 1 |
| Temporal state windows | Canonical feature table | Ordered fixed-window states with aggregate features and original-label distributions | Time-bucket aggregation; chronological ordering | `Parquet` | Developer 1 |
| Forecast target construction | Ordered state windows and documented schedule/labels | Future-state targets for `t+1` and `t+1..t+K` | Forward-only label construction; no future feature leakage | `Parquet` | ML/world-model developer |
| Model input | Context windows and targets | Offline-ready tensors/records plus provenance | Deterministic windowizer and schema validator | `Parquet`/`JSONL` | ML/world-model developer |

## Required raw inputs

The first usable slice must contain both:

1. the generated flow CSV for the selected CSE day and machines; and
2. the raw PCAP for the same capture scope.

The official CSE documentation says the dataset is organized per day, with raw PCAPs and event logs per machine and extracted CSVs per machine. The acquisition manifest must prove that the chosen flow and PCAP files refer to the same day/machine/capture scope before either is joined.

## Canonical table minimum

The final schema is not approved until the real CSV headers and PCAP metadata are inspected. At minimum, it should contain:

- stable source row/file identifiers;
- source timestamp plus normalized timestamp;
- flow identity fields that are actually present;
- directly exported flow measures;
- packet-derived fields only when supported by PCAP evidence;
- original source label;
- missingness indicators for unavailable measurements;
- flow-to-PCAP match status;
- extraction version; and
- source-file checksum/reference.

No field should be fabricated, silently defaulted, or presented as packet-derived when it came only from an aggregate flow export.

## Alignment rules

- Preserve the source timestamp before normalization.
- Record timestamp units and timezone explicitly.
- Use the same interval convention for flow and packet records.
- Validate five-tuple directionality and handle reverse-direction flows explicitly.
- Use a documented time tolerance for packet-to-flow matching.
- Report unmatched and multiply matched records.
- Keep original labels unchanged; derived forecast targets are separate columns.
- Fit no scaling, imputation, or feature-selection state on future windows.

## Temporal-state contract

The MVP proposes one-minute state windows with a 15-minute historical context and horizons `K=1` and `K=3`. Each state must include:

- window start/end;
- flow and packet evidence counts;
- aggregate traffic features;
- original-label counts/proportions;
- source coverage and missingness;
- a state-validity flag; and
- provenance to the canonical rows used.

Forecast targets must be constructed only from future windows. A state at time `t` must not include labels, packet statistics, or aggregate values from `t+1` onward.

## PCAP-derived feature plan

The packet module is separate from the flow module and is required for fields that cannot be proven from the CSV alone:

- TTL distributions;
- IP fragmentation flags/counts;
- retransmission evidence from sequence/acknowledgement behavior;
- packet-level IAT and burst statistics;
- packet payload-size distributions;
- packet-level TCP flag ordering; and
- packet-level window observations.

The module must emit a field-level availability report. If the selected PCAP does not contain an observable field, the result is `unavailable`, not an imputed value.

## Stopping criteria before model work

Do not build the ML/world-model stage until all of the following are true:

- exact source files, sizes, checksums, and formats are recorded;
- the flow CSV headers and label values are inventoried;
- the PCAP is proven to match the selected flow capture scope;
- timestamp units and timezone are resolved;
- packet-to-flow match rates are reported;
- missing required fields are listed;
- original labels are preserved in a checked derived table; and
- a leakage audit confirms that future windows do not enter current-state features.

## Ownership handoff

Developer 1 owns flow-table validation, canonical schema approval, and temporal aggregation. Developer 2 owns PCAP parsing, packet-level feature extraction, and flow/packet alignment evidence. The ML/world-model developer receives only the validated temporal-state artifact and its manifest.
