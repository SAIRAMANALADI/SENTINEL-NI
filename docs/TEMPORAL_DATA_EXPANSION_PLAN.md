# CSE-CIC-IDS2018 Temporal Data Expansion Plan

Date: 2026-08-24

## Decision

Acquire the smallest additional set that supports a chronological multi-day experiment while keeping the existing 28-Feb infiltration day as an unseen test day/scenario:

| Day | AWS object | Officially documented activity | Role |
|---|---|---|---|
| 2018-02-14 | `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv` | FTP-BruteForce and SSH-Bruteforce | Train |
| 2018-02-21 | `Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv` | DDoS-LOIC-UDP and DDoS-HOIC | Train |
| 2018-02-22 | `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv` | Web brute force, XSS, and SQL injection | Validation |
| 2018-02-28 | `Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv` | Infiltration | Test; already present locally |

The official CSE-CIC-IDS2018 attack schedule documents these activities and dates. Filenames alone are not treated as evidence of attack content; each selected CSV must be profiled after download.

## Why three additional days is the minimum

The current experiment has one day only. To satisfy all three split requirements simultaneously:

1. training must contain multiple days, requiring at least two earlier days;
2. validation must be a different later day; and
3. test must be a later unseen day or scenario.

Using the existing 28-Feb file as test means two new earlier training days plus one new validation day are sufficient. Fewer than three additional CSVs cannot provide multiple training days, a separate validation day, and a separate held-out test day/scenario.

## Expected storage

AWS inventory sizes:

- 14-Feb: `358,223,333` bytes
- 21-Feb: `328,893,673` bytes
- 22-Feb: `382,636,202` bytes
- Total new download: `1,069,753,208` bytes, approximately `1.07 GB` decimal

The existing 28-Feb file is `209,249,758` bytes and is not downloaded again. No PCAP is included in this acquisition.

## Expected labels and conditions

The source schedule documents benign traffic plus attack activity on these days. Expected attack conditions are:

- 14-Feb: FTP and SSH brute force;
- 21-Feb: DDoS using LOIC-UDP and HOIC;
- 22-Feb: web brute force, XSS, and SQL injection;
- 28-Feb: infiltration.

The exact CSV label strings, counts, timestamp coverage, and non-finite values remain an empirical result of the per-day profiles. Original labels must be preserved; no MITRE mapping or cross-day label normalization is authorized here.

## Planned temporal split

After profiling and schema compatibility checks:

- Train: complete 14-Feb and 21-Feb days;
- Validation: complete 22-Feb day;
- Test: complete 28-Feb day.

Rows will not be randomly distributed across days. Any within-day ordering, duplicate handling, timestamp normalization, and guard-gap decision will be recorded in `results/multiday_split_report.json`.

## Risks

- The AWS filenames contain a source typo for some dates in the public inventory; acquisition must use the exact object key.
- Daily CSVs may differ in headers, repeated-header rows, malformed values, or label spelling. No merge occurs before each day is profiled.
- The official schedule gives attack timing, but the CSV label summaries are the authoritative observed-flow evidence for this repository.
- The 28-Feb file currently exists at the historical workspace path rather than the canonical raw-day directory; its original path will be retained in the acquisition manifest and its `source_file` provenance.
- This expansion improves cross-day evaluation but still does not provide raw packet-level features or a world-model-ready fixed-interval state representation.

## Sources

- Official documentation: https://www.unb.ca/cic/datasets/ids-2018.html
- AWS Open Data registry: https://registry.opendata.aws/cse-cic-ids2018/
- Processed-flow inventory command: `aws s3 ls --no-sign-request "s3://cse-cic-ids2018/Processed Traffic Data for ML Algorithms/" --recursive`
