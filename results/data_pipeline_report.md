# Data Pipeline Report

## Status: NOT RUN — input dataset unavailable

The first real data pipeline was not executed because no approved dataset file exists in the repository. CTU-13 remains a provisional recommendation, not a locally selected input.

| Report item | Result |
| --- | --- |
| Source dataset | NONE PROCESSED |
| Rows inspected | NOT AVAILABLE |
| Rows retained | NOT AVAILABLE |
| Rows removed | 0; no input was processed |
| Final feature count | NOT AVAILABLE |
| Final label distribution | NOT AVAILABLE |
| Missing values | NOT AVAILABLE |
| Timestamp range | NOT AVAILABLE |
| Leakage exclusions | No field-level exclusions validated; see `docs/FEATURE_LEAKAGE_REPORT.md` |
| Output location | No processed dataset created |
| Schema version | NOT LOCKED |

## Reason for stopping

The requested canonical schema must be based on actual dataset fields, explicit transformations, and SIH requirements. The repository has no actual fields and no official PS text. Guessing a schema or fabricating row counts would violate the project rules.

## Next execution gate

Supply one approved local CTU-13 scenario flow file or approved small CSE-CIC-IDS2018 CSV slice. Then run field profiling first, review the resulting schema with Developer 1, and only then implement the transformation and output contract.
