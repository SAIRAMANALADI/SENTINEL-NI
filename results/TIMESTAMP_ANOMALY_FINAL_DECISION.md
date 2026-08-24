# Timestamp Anomaly Final Decision

Date: 2026-08-24

## Decision

**Policy A — exclude the 14 records from temporal modeling and fixed-interval state aggregation.**

The raw flow records remain preserved in `data/processed/cic_ids2018_multiday_flow.parquet` with their original `Timestamp`, parsed `timestamp_parsed`, `capture_date`, and `timestamp_capture_date_mismatch=true`. No timestamp was corrected by guesswork.

## Evidence

- All 14 raw values are syntactically parseable under the source `DD/MM/YYYY HH:MM:SS` parser but resolve to January 1970.
- Their file-derived capture days are 2018-02-14 or 2018-02-22.
- The adjacent source rows before/after each anomaly use the expected 2018 capture date, confirming a local timestamp corruption pattern rather than a separate capture day.
- No alternate date field exists in the flow Parquet artifact to establish the correct day/time for these records.
- Every anomalous record is labeled `Benign`; this does not justify replacing its timestamp with a guessed date.

## Records

| Source file | Source row | Capture day | Raw timestamp | Parsed timestamp | Label | Adjacent-row evidence |
|---|---:|---|---|---|---|---|
| `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | 410957 | 2018-02-14 | `05/01/1970 03:01:17` | `1970-01-05 03:01:17` | Benign | rows 410956/410961 are 2018-02-14 |
| `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | 410958 | 2018-02-14 | `08/01/1970 07:32:33` | `1970-01-08 07:32:33` | Benign | rows 410956/410961 are 2018-02-14 |
| `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | 410959 | 2018-02-14 | `12/01/1970 07:17:56` | `1970-01-12 07:17:56` | Benign | rows 410956/410961 are 2018-02-14 |
| `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | 410960 | 2018-02-14 | `12/01/1970 09:15:10` | `1970-01-12 09:15:10` | Benign | rows 410956/410961 are 2018-02-14 |
| `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | 412185 | 2018-02-14 | `12/01/1970 09:44:12` | `1970-01-12 09:44:12` | Benign | rows 412184/412186 are 2018-02-14 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246434 | 2018-02-22 | `10/01/1970 03:04:26` | `1970-01-10 03:04:26` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246435 | 2018-02-22 | `11/01/1970 12:05:36` | `1970-01-11 12:05:36` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246436 | 2018-02-22 | `11/01/1970 05:12:30` | `1970-01-11 05:12:30` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246437 | 2018-02-22 | `11/01/1970 03:51:32` | `1970-01-11 03:51:32` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246438 | 2018-02-22 | `12/01/1970 06:40:49` | `1970-01-12 06:40:49` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246439 | 2018-02-22 | `12/01/1970 01:09:53` | `1970-01-12 01:09:53` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246440 | 2018-02-22 | `12/01/1970 09:18:52` | `1970-01-12 09:18:52` | Benign | rows 246433/246441 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 246716 | 2018-02-22 | `12/01/1970 09:30:03` | `1970-01-12 09:30:03` | Benign | rows 246715/246717 are 2018-02-22 |
| `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | 248315 | 2018-02-22 | `12/01/1970 09:30:26` | `1970-01-12 09:30:26` | Benign | rows 248314/248316 are 2018-02-22 |

## Effect on state data

- Raw multi-day flow rows: unchanged, `3,758,796`.
- Valid flow rows used for temporal state aggregation: `3,758,782`.
- Excluded from state construction: `14`.
- No fabricated replacement timestamp was used.
