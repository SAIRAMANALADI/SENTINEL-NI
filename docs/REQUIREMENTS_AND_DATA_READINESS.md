# Requirements and Data Readiness

**Assessment date:** 2026-08-24

## 1. What SIH explicitly requires

Nothing could be verified as an official SIH requirement because the repository contains no official problem-statement file, PDF, or copied official text. The internal planning documents describe a desired prototype, but they are not sufficient evidence for PS compliance. See [PS_REQUIREMENT_MATRIX.md](PS_REQUIREMENT_MATRIX.md).

## 2. What data we have

No local dataset files were found. The repository contains only empty data locations and documentation. No model training or dataset download was performed.

## 3. What data we can derive

From a selected flow-capable candidate, the team can potentially derive time-window states, rates, directional ratios, fan-out, port diversity, inter-arrival summaries, attack-state targets, and scenario-aware split metadata. Packet-level features require permitted PCAP/header artifacts and a separate extractor.

## 4. What data is missing

- Official SIH problem statement and version/date.
- Final dataset choice and access approval.
- A small local sample for field/header inspection.
- Exact timestamp, label, and scenario fields in the selected files.
- Target definition, forecasting horizon, and attack-stage requirements.
- MITRE evidence sources and human-approved mapping.
- Leakage-safe split manifest and data-quality profile.

## 5. Unavoidable assumptions

- The current CTU-13 recommendation is provisional and based on the internal flow-first prototype goal.
- Candidate window sizes and horizon values are experiments, not final requirements.
- Dataset labels are not assumed to be MITRE labels or chronological attack stages.
- No field name is accepted as final until a selected-file sample is inspected.

## 6. What can be completed within the deadline

- Obtain the official PS and freeze a requirement matrix.
- Download only one or two approved CTU-13 scenario flow artifacts, or an explicitly approved small CSE-CIC-IDS2018 CSV slice.
- Validate fields, timestamps, labels, duplicates, and scenario boundaries.
- Implement the canonical data contract and leakage tests.
- Build the deterministic temporal-window and baseline path after the data audit.

## 7. What should not be attempted yet

- Full-dataset downloads or raw-PCAP processing before scope approval.
- LSTM/GRU, Transformer, GNN, dashboard, or live capture work.
- MITRE mappings without evidence review.
- Claims of attack chronology, future prediction, calibrated probability, or SIH compliance.

## Readiness scores

| Area | Score | Evidence basis |
| --- | ---: | --- |
| Requirements readiness | **1/10** | Internal plans exist, but the official PS is absent and all source-dependent rows are blocked. |
| Dataset readiness | **2/10** | Two authoritative candidates are documented and a provisional CTU-13 subset is proposed, but no local sample has been inspected or approved. |
| Engineering readiness | **6/10** | Foundation directories, contracts, configuration, package placeholders, smoke test, and structure tests exist; ingestion, data validation, models, and UI do not. |

## Exact next gate

Obtain the official SIH problem statement and one small, explicitly approved dataset artifact. Then run a field-level reconnaissance before writing the canonical schema.
