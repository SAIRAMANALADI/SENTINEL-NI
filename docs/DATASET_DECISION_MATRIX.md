# Dataset Decision Matrix

Date: 2026-08-24  
Project: SIH26-26153 — AI Based Network Attack Forecasting

## Decision context

The official SIH problem statement was not present in the repository at the time of this audit. The comparison therefore uses only the verified internal requirements recorded in `docs/PS_REQUIREMENT_MATRIX.md`:

- flow-level traffic features;
- packet-level traffic features;
- a temporal network-state representation;
- future-state forecasting;
- K-step forward simulation;
- infiltration probability;
- attack-stage mapping;
- explainability; and
- an offline inference interface.

No local dataset is currently present under `data/raw/`. Scores below describe dataset capability, not a claim that any data has already been downloaded, parsed, or validated in this workspace.

## Official source evidence

- [CTU-13 official dataset page](https://www.stratosphereips.org/datasets-ctu13) documents bidirectional NetFlows, labels, scenario PCAP limitations, and the available file types.
- [CTU-13 official overview](https://www.stratosphereips.org/datasets-overview) identifies Binetflow text files, Biargus binary files, botnet PCAPs, and truncated PCAP headers.
- [Official UNB/CIC IDS2018 page](https://www.unb.ca/cic/datasets/ids-2018.html) documents seven attack scenarios, per-day raw PCAPs and event logs, generated per-machine CSVs, bidirectional CICFlowMeter features, attack schedules, and the stated label-construction method.
- [AWS Open Data registry entry for CSE-CIC-IDS2018](https://registry.opendata.aws/cse-cic-ids2018/) is the official registry reference for the public object store.

## Scoring

`0` means unavailable or unusable for the requirement. `5` means directly available from the documented source with a practical path to validate it. Scores are feasibility scores and include alignment risk, not model quality.

| Requirement | CTU-13 | CIC-IDS-2018 | Winner | Reason |
|---|---:|---:|---|---|
| Flow-level feature coverage | 4/5 | 5/5 | CIC-IDS-2018 | CTU provides labeled bidirectional flow products, but the exact feature schema varies by product. CIC documents bidirectional CICFlowMeter CSVs with more than 80 traffic features, including duration, packet/byte counts, rates, IATs, flags, payload statistics, and windows. |
| Packet-level feature coverage | 2/5 | 5/5 | CIC-IDS-2018 | CTU has botnet PCAPs and only truncated PCAP headers for all traffic; its complete mixed-traffic PCAP is unavailable. CIC documents raw PCAPs per day and machine, enabling packet extraction from real captures. |
| Timestamp availability | 4/5 | 4/5 | Tie | Both are capture-based datasets with temporal information. Exact timestamp units, timezone handling, and alignment still require an ingestion audit on the selected files. |
| Temporal progression | 3/5 | 4/5 | CIC-IDS-2018 | CTU scenarios and flow timestamps support ordering, but the documented labels are traffic categories rather than a complete attack-stage timeline. CIC publishes attack schedules and multi-day infiltration activity, giving a stronger starting point for chronological state windows. |
| Attack progression / infiltration | 2/5 | 4/5 | CIC-IDS-2018 | CTU labels include botnet/background/C&C/normal, but the selected scenario does not by itself establish a reliable infiltration-stage sequence. CIC explicitly documents infiltration as malicious file delivery, exploitation, backdoor installation, and internal scanning/exploitation. |
| Label availability | 4/5 | 3/5 | CTU-13 | CTU provides flow-by-flow manual labels. CIC labels are derived from attack schedules plus IP, port, and protocol information, so label semantics and boundary leakage need validation before use. |
| PCAP availability | 2/5 | 5/5 | CIC-IDS-2018 | CTU’s complete mixed capture is unavailable for privacy reasons. CIC documents raw PCAPs as part of the dataset organization. |
| TCP flags, IATs, bidirectional ratios, TTL, windows, fragments | 2/5 | 4/5 | CIC-IDS-2018 | Flow-level flags, IATs, directional counts, payload sizes, and TCP windows are documented for CIC. TTL, fragment flags, and packet-accurate retransmission logic still require parsing the matching PCAP; CIC is better positioned to provide it. |
| Port scans and retransmissions | 2/5 | 4/5 | CIC-IDS-2018 | Both can expose some scan behavior in flows, but packet-accurate retransmission and fragment analysis require PCAP. CIC’s documented PortScan activity and raw PCAPs make this more testable. |
| Preprocessing effort | 4/5 | 2/5 | CTU-13 | CTU’s flow-first artifacts are smaller and simpler for a deadline MVP. CIC requires source-file inventory, CSV/PCAP alignment, packet extraction, and larger storage/processing capacity. |
| Deadline feasibility | 4/5 | 3/5 | CTU-13 | A single CTU scenario is faster to ingest, but it cannot satisfy the packet-level requirement alone. A bounded CIC infiltration slice is feasible; the full archive is not an MVP target. |
| Reproducibility | 4/5 | 4/5 | Tie | Both have official public documentation and reproducible source references. The exact CIC object names and selected-file checksums must be recorded at acquisition time. |
| SIH requirement coverage as a single MVP source | 2/5 | 4/5 | CIC-IDS-2018 | CTU-13 alone does not provide the required packet evidence for all labeled traffic. CIC provides the more complete flow-plus-PCAP starting point, although attack-stage mapping and the final forecast target remain project-defined and must not be inferred without evidence. |

## Recommendation

Choose **Option B: CSE-CIC-IDS2018**, restricted to a small, matched infiltration-centered slice containing both the generated flow CSV and the corresponding raw PCAP for the same day and machine set. Do not download the full archive for the MVP.

CTU-13 remains useful as a secondary flow-label benchmark, but it is not sufficient as the sole source for this SIH scope because the official documentation states that the complete mixed-traffic PCAP is unavailable and that the available full PCAP is botnet-only.

## Limits of this decision

The repository does not contain the official SIH problem statement or any downloaded data. The exact CSE object filenames, byte sizes, checksums, and CSV-to-PCAP correspondence must be captured from an AWS inventory before acquisition. No claim is made here that the recommended files already exist locally.
