# Developer 2 — NETWORK TELEMETRY / FEATURE ENGINEERING

## Mission
Turn raw traffic into trustworthy temporal network-state features.

## Deliverables
1. canonical schema
2. CSV ingestion
3. PCAP parsing
4. flow aggregation
5. packet features
6. validation
7. attack/state labeling support
8. MITRE evidence mapping

## Task 1 — Canonical Schema
Create `src/features/schema.py`.
Document:
- column
- type
- source
- units
- aggregation rule
- missing-value behavior

Treat the schema as an API contract.

## Task 2 — CSV Path
Normalize the selected dataset into the canonical schema.

## Task 3 — PCAP Path
Preferred architecture:
```text
PCAP
 ↓
extract.py
 ↓
canonical feature rows
 ↓
same downstream pipeline as CSV
```
Keep heavy packet parsing outside the UI where possible.

## Task 4 — Feature Engineering
Candidate flow features:
- bytes
- packets
- duration
- packet rate
- bytes/sec
- bidirectional ratios
- source/destination fan-out
- port diversity

Candidate packet features:
- TTL statistics
- TCP window statistics
- flags
- retransmissions
- fragmentation
- payload-size distribution
- inter-arrival statistics

Validate before declaring usefulness.

## Task 5 — Temporal State Labels
Create `src/features/state_builder.py`.
Preserve:
- timestamp range
- attack label
- source label
- attack-stage evidence/source

## Task 6 — MITRE Mapping
Create `src/mitre/mapping.py`.
Store:
- source attack label
- MITRE technique/tactic
- reasoning
- confidence
- reference/source

Do not invent attack chronology.

## Task 7 — Data Tests
Check:
- missing values
- invalid ports
- negative durations
- timestamp order
- duplicates
- label contamination
- leakage-prone columns

Create `tests/test_features.py`.

## Done when
Developer 1 can train without manual cleanup and Developer 3 can use the same feature interface.
