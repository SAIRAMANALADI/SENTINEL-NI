# Raw Data Profile

## Status: BLOCKED — no actual dataset is present

The Developer 2 pipeline task requires inspection of an actual selected dataset file. The repository was searched recursively for CSV, PCAP, PCAPNG, Parquet, archive, and PDF artifacts. None were found under `data/` or elsewhere in the project.

The dataset recommendation in `docs/DATASET_SELECTION.md` is provisional CTU-13, but no CTU-13 scenario has been approved or supplied locally. The official SIH problem statement is also absent.

## Profile fields

| Profile item | Result |
| --- | --- |
| Dataset actually profiled | NONE |
| Files inspected | 0 |
| Rows | NOT AVAILABLE |
| Columns | NOT AVAILABLE |
| Column names | NOT AVAILABLE |
| Dtypes | NOT AVAILABLE |
| Missing-value percentages | NOT AVAILABLE |
| Duplicate count | NOT AVAILABLE |
| Timestamp range | NOT AVAILABLE |
| Class/attack distribution | NOT AVAILABLE |
| Suspicious columns | NOT AVAILABLE |
| Identifier columns | NOT AVAILABLE |
| Columns requiring transformation | NOT AVAILABLE |
| Rows removed | 0; no input was processed |

No columns were silently removed. No data was downloaded, generated, or presented as a real sample.

## Required unblock evidence

Provide one approved local CTU-13 scenario flow artifact, or an explicitly approved small CSE-CIC-IDS2018 CSV slice, together with:

1. source and license/access confirmation;
2. the authoritative timestamp field;
3. the ground-truth label field and label semantics;
4. scenario/capture identity;
5. confirmation that the artifact is permitted by the official SIH PS.

Only after that evidence is available can the profile be populated and the canonical schema locked.
