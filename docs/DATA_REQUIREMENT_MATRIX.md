# Data Requirement Matrix

**Status:** reconnaissance only. `UNKNOWN` means the authoritative source or a local sample does not establish the value.

| Requirement | Required By | Dataset Candidate | Available? | Source | Exact Field | Transformation Needed | Confidence | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. Flow-level** |||||||||
| Flow identifier | Internal data contract; PS alignment pending | CSE-CIC-IDS2018 | YES | UNB/CIC | `FlowID` | Preserve for audit; exclude from model unless justified | High | Dev 2 | Provisional |
| Flow identifier | Internal data contract; PS alignment pending | CTU-13 | UNKNOWN | Stratosphere | UNKNOWN | Inspect selected `.biargus`/text representation | Low | Dev 2 | Pending |
| Source/destination IP | Internal data contract | CSE-CIC-IDS2018 | YES | UNB/CIC | `SourceIP`, `DestinationIP` | Anonymization/encoding decision; leakage review | High | Dev 2 + Dev 4 | Provisional |
| Source/destination port | Internal data contract | CSE-CIC-IDS2018 | YES | UNB/CIC | `SourcePort`, `DestinationPort` | Validate range; inspect label leakage | High | Dev 2 | Provisional |
| Protocol | Internal data contract | CSE-CIC-IDS2018 | YES | UNB/CIC | `Protocol` | Normalize categories | High | Dev 2 | Provisional |
| Duration, packets, bytes | Internal data contract | CSE-CIC-IDS2018 | YES | UNB/CIC | `fl_dur`, packet/byte feature fields | Normalize units and missing values | High | Dev 2 | Provisional |
| Bidirectional flow statistics | Internal data contract | CSE-CIC-IDS2018 | YES | UNB/CIC | CICFlowMeter-V3 feature set | Select non-leaking numeric subset | High | Dev 1 + Dev 2 | Provisional |
| Bidirectional labeled flows | Internal data contract | CTU-13 | YES | Stratosphere | `.biargus` labeled bidirectional flows | Parse/normalize with a documented adapter | High | Dev 2 | Provisional |
| Duration, packets, bytes | Internal data contract | CTU-13 | PARTIAL | Stratosphere | Exact field names UNKNOWN | Inspect selected file and map fields | Medium | Dev 2 | Pending |
| **B. Packet-level** |||||||||
| Raw packet capture | Internal contract; PS alignment pending | CSE-CIC-IDS2018 | YES | UNB/CIC | PCAP artifact | Optional extractor outside UI | High | Dev 2 | Provisional |
| Raw packet capture | Internal contract; PS alignment pending | CTU-13 | PARTIAL | Stratosphere | Botnet PCAP and truncated PCAP variants | Do not assume complete mixed payload capture | High | Dev 2 | Provisional |
| Inter-arrival statistics | Candidate feature contract | CSE-CIC-IDS2018 | YES | UNB/CIC | CICFlowMeter IAT fields | Map and aggregate by chosen window | High | Dev 2 | Provisional |
| TTL/window/fragmentation/retransmission | Candidate feature contract | CSE-CIC-IDS2018 | UNKNOWN | UNB/CIC | UNKNOWN in source summary | Derive from PCAP only if required and available | Low | Dev 2 | Pending |
| Payload-size statistics | Candidate feature contract | CSE-CIC-IDS2018 | PARTIAL | UNB/CIC | CICFlowMeter packet-size fields; raw payload availability separate | Derive only from permitted artifacts | Medium | Dev 2 | Pending |
| TTL/window/fragmentation/retransmission | Candidate feature contract | CTU-13 | UNKNOWN | Stratosphere | UNKNOWN | Derive from permitted PCAP/header data if justified | Low | Dev 2 | Pending |
| **C. Temporal** |||||||||
| Ordered event timestamp | Forecasting design | CSE-CIC-IDS2018 | PARTIAL | UNB/CIC | Exact selected CSV timestamp field UNKNOWN | Verify file header; normalize timezone | Medium | Dev 2 + Dev 4 | Blocked on sample |
| Ordered flow timestamp | Forecasting design | CTU-13 | PARTIAL | Stratosphere | Exact selected field UNKNOWN | Inspect and normalize selected flow file | Medium | Dev 2 + Dev 4 | Blocked on sample |
| Scenario/capture identity | Leakage-safe split | CSE-CIC-IDS2018 | YES/PARTIAL | UNB/CIC | Day/file identity; exact field UNKNOWN | Store as metadata, not model input by default | Medium | Dev 4 | Provisional |
| Scenario identity | Leakage-safe split | CTU-13 | YES | Stratosphere | Scenario package identity | Group split; exclude from model inputs | High | Dev 4 | Provisional |
| Attack interval or future label | Forecast target | Both | PARTIAL | Dataset sources | Dataset labels/attack schedule; exact time alignment UNKNOWN | Define future target after timestamp audit | Medium | Dev 1 + Dev 2 | Pending |
| **D. Attack labels** |||||||||
| Per-flow attack label | Forecast target | CSE-CIC-IDS2018 | YES/PARTIAL | UNB/CIC | Exact label column UNKNOWN; source describes schedule/IP/port/protocol labeling | Preserve raw label and create audited target | Medium | Dev 2 + Dev 4 | Pending |
| Flow class label | Forecast target | CTU-13 | YES | Stratosphere | Background, Botnet, C&C Channels, Normal | Normalize spelling while retaining source value | High | Dev 2 | Provisional |
| Attack stage label | PS-dependent output | Both | NO/UNKNOWN | OFFICIAL PS TEXT REQUIRED | UNKNOWN | Must be derived only if PS requires it and evidence supports it | High | Dev 1 + Dev 4 | Blocked |
| **E. Network topology** |||||||||
| Host/network context | Feature provenance | CSE-CIC-IDS2018 | PARTIAL | UNB/CIC | Topology described; exact machine-role field UNKNOWN | Store scenario metadata; avoid identifier shortcut | Medium | Dev 2 | Pending |
| Host/network context | Feature provenance | CTU-13 | PARTIAL | Stratosphere | Scenario context; exact topology field UNKNOWN | Store scenario metadata and source notes | Medium | Dev 2 | Pending |
| Fan-out/port diversity | Candidate features | Both | DERIVABLE | Flow rows plus timestamps | UNKNOWN | Aggregate by source/destination and time window | Medium | Dev 2 | Planned |
| **F. MITRE mapping evidence** |||||||||
| Dataset-to-technique evidence | Explainability/stage mapping | CSE-CIC-IDS2018 | PARTIAL | UNB/CIC + MITRE | Dataset attack descriptions, not ATT&CK IDs | Build evidence-linked review table | Medium | Dev 4 | Pending |
| Dataset-to-technique evidence | Explainability/stage mapping | CTU-13 | PARTIAL | Stratosphere + MITRE | Botnet/C&C labels and behavior descriptions, not ATT&CK IDs | Build evidence-linked review table | Low-Medium | Dev 4 | Pending |
