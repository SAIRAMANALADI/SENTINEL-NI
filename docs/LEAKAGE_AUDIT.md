# Leakage Audit Plan

## Status

This is a prevention plan. No dataset, labels, windows, or model pipeline exist yet, so no leakage claim has been validated.

| Risk | Detection method | Prevention method | Status |
| --- | --- | --- | --- |
| Attack label encoded directly or indirectly in a feature | Compare every feature with label-generation rules; inspect feature provenance and single-feature performance | Exclude label-derived, post-event, and schedule-derived fields from model inputs | Pending |
| Random row split mixes the same scenario across splits | Review split code and split manifest; assert scenario/time grouping | Use chronological and scenario-aware splitting; forbid random row split for temporal evaluation | Pending |
| Overlapping adjacent windows cross train/test boundaries | Calculate source-row and timestamp overlap between windows | Split source timelines before window construction or apply an explicit guard gap | Pending |
| Timestamp leakage | Review whether absolute timestamp, attack schedule, file/day ID, or future-derived time fields identify the target | Use timestamps only for ordering or carefully derived periodic features; document any retained time feature | Pending |
| Scenario leakage | Compare scenario IDs, hosts, IP ranges, capture files, and attack tools across partitions | Hold out complete scenarios or clearly report when only chronological within-scenario validation is possible | Pending |
| Derived fields expose the target | Trace every transformation back to source packets/flows and event logs | Fit transformations only on permitted historical data and remove fields created after the prediction time | Pending |
| Preprocessing fitted on the full dataset | Inspect fit/transform call order and serialized artifacts | Fit encoders, scalers, imputers, and selectors on training data only | Pending |
| Label alignment uses future information too early | Unit-test window end, forecast origin, and target timestamps | Define target intervals explicitly and enforce `target_start > forecast_origin` | Pending |
| Duplicate or near-duplicate rows cross partitions | Hash normalized records and compare flow keys/timestamps across partitions | Deduplicate before splitting and retain a duplicate audit report | Pending |
| Class balancing uses validation/test data | Review sampling and weighting code | Apply balancing only within the training partition | Pending |

## Dataset-specific watch items

- CSE-CIC-IDS2018 labels are described by the source as derived from attack schedules, IPs, ports, and protocol; those fields need a provenance review before modeling.
- CTU-13 is manually labeled at flow level and offers scenario identifiers; scenario identity must not become a shortcut feature.
- A packet/flow extractor must not use packets after the forecast origin when computing the current state.

## Sign-off evidence

The audit is complete only when the repository contains the split manifest, feature provenance table, overlap checks, and test output for the selected dataset. Syntax or smoke checks alone are insufficient.
