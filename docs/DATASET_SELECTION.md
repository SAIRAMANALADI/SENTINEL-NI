# Dataset Selection and Reconnaissance

**Reconnaissance date:** 2026-08-24  
**Local data found:** none  
**Official SIH PS found locally:** none; see [PS_REQUIREMENT_MATRIX.md](PS_REQUIREMENT_MATRIX.md).

## Sources inspected

- [CSE-CIC-IDS2018, Canadian Institute for Cybersecurity / UNB](https://www.unb.ca/cic/datasets/ids-2018.html)
- [CSE-CIC-IDS2018, AWS Open Data Registry](https://registry.opendata.aws/cse-cic-ids2018/)
- [CTU-13, Stratosphere Laboratory](https://www.stratosphereips.org/datasets-ctu13)
- [Stratosphere dataset overview](https://www.stratosphereips.org/datasets-overview)

The facts below are limited to those sources. Where a source page does not establish a field or size, the value is marked **UNKNOWN**.

## Candidate 1 — CSE-CIC-IDS2018

| Item | Finding | Evidence/status |
| --- | --- | --- |
| Dataset name | CSE-CIC-IDS2018 / CSE-CIC-IDS 2018 | Official UNB/CIC page |
| Official source | Canadian Institute for Cybersecurity and CSE, hosted through AWS Open Data | [UNB/CIC](https://www.unb.ca/cic/datasets/ids-2018.html), [AWS registry](https://registry.opendata.aws/cse-cic-ids2018/) |
| Download/access method | AWS CLI `s3 sync --no-sign-request`; no download performed | Explicit source command; use only with an approved subset/path |
| File types | Per-day PCAPs, generated CSV flow files, and machine event logs | Official page describes all three |
| Flow-level availability | YES; CICFlowMeter-V3 produces bidirectional flows with more than 80 traffic features | Strong |
| Packet-level availability | PARTIAL; raw packet data is available through PCAP, while the documented CSV is flow-derived | Exact MVP artifact must be chosen |
| PCAP availability | YES | Official page describes raw captured PCAPs |
| Timestamp availability | PARTIAL; daily organization and attack start/finish records are documented, but the exact selected CSV timestamp field must be verified from a file sample | Do not assume a column name |
| Attack labels | YES; source describes labeling by attack schedule, IPs, ports, and protocol | Label provenance must be preserved |
| Attack categories | Seven scenarios: Brute-force, Heartbleed, Botnet, DoS, DDoS, Web attacks, and infiltration from inside | Official source |
| Approximate size | UNKNOWN from the authoritative page; the AWS collection is large and includes multiple artifact types | Query inventory before any download |
| Number of scenarios | Seven attack scenarios; the source also organizes data by day | Official source |
| Known limitations | Testbed-generated traffic; labels depend on schedule and network identifiers; flow timeout and feature extraction choices affect the output; raw/processed artifact sizes are large | Must be measured on selected subset |
| License/access | The UNB page permits redistribution/republishing/mirroring with citation and an AWS link | Verify citation obligations before sharing |
| Temporal forecasting suitability | MEDIUM-HIGH; daily organization, attack intervals, and ordered flow timestamps can support windows once the exact field is verified | Requires strict time/scenario split |
| Multi-step prediction suitability | MEDIUM; attack intervals exist, but a future-state target and stage labels must be derived | No official K-step target found |
| MITRE ATT&CK suitability | MEDIUM-LOW; behavior descriptions can support candidate mappings, but dataset labels are not MITRE techniques or tactics | Human review required |
| Deadline suitability | Full collection: LOW. A small processed CSV slice covering benign lead-in, one attack interval, and a holdout interval: PROVISIONALLY MEDIUM-HIGH | Depends on local storage and PS |

## Candidate 2 — CTU-13

| Item | Finding | Evidence/status |
| --- | --- | --- |
| Dataset name | CTU-13 | Official Stratosphere page |
| Official source | Stratosphere Laboratory / Malware Capture Facility Project | [Official dataset page](https://www.stratosphereips.org/datasets-ctu13) |
| Download/access method | One 1.9 GB tar archive or capture-by-capture downloads; no download performed | Official page |
| File types | Botnet PCAPs, labeled bidirectional NetFlow `.biargus` files, plus other scenario artifacts; overview also documents Binetflow and truncated PCAPs | Strong for flow-first MVP |
| Flow-level availability | YES; bidirectional NetFlows for all traffic with manual labels | Official source recommends bidirectional over unidirectional flows |
| Packet-level availability | PARTIAL; complete PCAP containing all traffic is unavailable for privacy, while botnet and truncated/header captures are available | Exact package must be selected |
| PCAP availability | YES, but complete mixed PCAP is not available; botnet-only and truncated variants are documented | Important limitation |
| Timestamp availability | PARTIAL; scenario capture duration is documented, but exact flow timestamp field must be verified after selecting the file format | Do not assume a column name |
| Attack labels | YES; manually labeled flow classes include Background, Botnet, C&C Channels, and Normal | Official source |
| Attack categories | Thirteen botnet scenarios involving different malware samples and behaviors | No official attack-stage taxonomy |
| Approximate size | 1.9 GB for the official all-data tar archive | Official source |
| Number of scenarios | Thirteen | Official source |
| Known limitations | Captured in 2011; complete mixed PCAP unavailable; bidirectional files may require Argus-compatible tooling; labels describe traffic classes rather than a complete attack chronology | Must be documented in results |
| License/access | Stratosphere overview lists Creative Commons CC-BY | Verify attribution requirements before redistribution |
| Temporal forecasting suitability | HIGH for a flow-first prototype if scenario timestamps and ordering are validated; scenario holdout is available | Avoid scenario-ID shortcut features |
| Multi-step prediction suitability | MEDIUM-HIGH for botnet/C&C onset experiments; future state and early-warning targets still need to be derived | No official K-step target found |
| MITRE ATT&CK suitability | LOW-MEDIUM; C&C and observed behavior can support candidate evidence, but labels are not MITRE mappings | Human review required |
| Deadline suitability | One or two capture-by-capture scenarios: HIGH. Full archive: MEDIUM/LOW under a short deadline | Start with labeled bidirectional flows |

## Recommended MVP dataset

### RECOMMENDED MVP DATASET

**CTU-13, provisionally.** The recommendation is based on the available repository planning goal of a temporal flow-level prototype, not on an official SIH requirement, because the PS is missing.

### RECOMMENDED SUBSET

Two individually downloaded CTU-13 scenario packages: one development scenario and one untouched scenario for a final temporal/scenario holdout. Start with the labeled bidirectional NetFlow artifact and its metadata; do not download the complete archive, executables, or unnecessary PCAP payloads for the MVP.

### REASON

CTU-13 provides manually labeled bidirectional flows, multiple scenarios, capture-by-capture access, and a smaller documented full archive. That combination is a better fit for validating temporal aggregation and leakage controls under a deadline than beginning with the much larger CSE-CIC-IDS2018 collection.

### WHAT IT COVERS

- Flow-level network telemetry.
- Ordered scenario captures suitable for temporal windows after field verification.
- Botnet, C&C, normal, and background traffic labels.
- Scenario-level holdout evaluation.
- A path to derive packet features later from the permitted PCAP variants.

### WHAT IT DOES NOT COVER

- Official SIH requirements, because the PS is absent.
- A validated multi-stage attack chronology.
- Direct MITRE ATT&CK technique/tactic labels.
- Complete mixed packet payloads for all traffic.
- Evidence that the selected dataset generalizes to the SIH target environment.

### WHAT WE NEED TO DERIVE OURSELVES

- Canonical numeric feature schema and units.
- Fixed aggregation window and sequence experiments.
- Future-state and early-warning targets.
- Attack-stage vocabulary, if required after PS verification.
- MITRE evidence mapping with human review.
- Leakage-safe split manifest and evaluation protocol.

### Decision gate

Do not call CTU-13 the final dataset until the official PS is obtained and the first selected scenario files pass the data audit. If the PS explicitly requires the broader attack categories or raw PCAP workflow represented by CSE-CIC-IDS2018, revisit this decision.
