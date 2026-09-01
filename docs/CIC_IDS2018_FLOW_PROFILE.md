# CSE-CIC-IDS2018 Flow Profile

Date: 2026-08-24  
Inspection mode: read-only; header-first and streamed row audit

## Verdict

**FLOW DATA HAS BLOCKERS**

The real CSV is present and structurally readable at:

```text
<local-repository-root>/Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv
```

It is not at the previously expected `data/raw/cse-cic-ids2018/flow/` path in this workspace. The raw file was not modified. The file is usable for a baseline only after a derived ingestion step handles the embedded repeated headers and non-finite numeric values.

## File facts

| Field | Value |
|---|---|
| File type | CSV text |
| Exact file size | 209,249,758 bytes |
| Encoding check | UTF-8-compatible read; no BOM detected in the sampled bytes |
| Header columns | 80 |
| Data records read after the first header | 613,104 |
| Valid flow records after excluding repeated header records | 613,071 |
| Row widths | All 613,104 records have width 80 |
| Malformed row count | 0 |
| Stream batches | 13 batches of up to 50,000 rows |

The 33 repeated header records occur inside the body at data-record positions: `21839`, `43118`, `63292`, `84014`, `107720`, `132410`, `154206`, `160207`, `202681`, `228584`, `247718`, `271677`, `296995`, `322939`, `344163`, `349510`, `355080`, `360661`, `366040`, `367414`, `368614`, `371160`, `377705`, `399544`, `420823`, `440997`, `461719`, `485425`, `510115`, `534074`, `559392`, `585336`, and `606560`.

## Exact columns

1. `Dst Port`
2. `Protocol`
3. `Timestamp`
4. `Flow Duration`
5. `Tot Fwd Pkts`
6. `Tot Bwd Pkts`
7. `TotLen Fwd Pkts`
8. `TotLen Bwd Pkts`
9. `Fwd Pkt Len Max`
10. `Fwd Pkt Len Min`
11. `Fwd Pkt Len Mean`
12. `Fwd Pkt Len Std`
13. `Bwd Pkt Len Max`
14. `Bwd Pkt Len Min`
15. `Bwd Pkt Len Mean`
16. `Bwd Pkt Len Std`
17. `Flow Byts/s`
18. `Flow Pkts/s`
19. `Flow IAT Mean`
20. `Flow IAT Std`
21. `Flow IAT Max`
22. `Flow IAT Min`
23. `Fwd IAT Tot`
24. `Fwd IAT Mean`
25. `Fwd IAT Std`
26. `Fwd IAT Max`
27. `Fwd IAT Min`
28. `Bwd IAT Tot`
29. `Bwd IAT Mean`
30. `Bwd IAT Std`
31. `Bwd IAT Max`
32. `Bwd IAT Min`
33. `Fwd PSH Flags`
34. `Bwd PSH Flags`
35. `Fwd URG Flags`
36. `Bwd URG Flags`
37. `Fwd Header Len`
38. `Bwd Header Len`
39. `Fwd Pkts/s`
40. `Bwd Pkts/s`
41. `Pkt Len Min`
42. `Pkt Len Max`
43. `Pkt Len Mean`
44. `Pkt Len Std`
45. `Pkt Len Var`
46. `FIN Flag Cnt`
47. `SYN Flag Cnt`
48. `RST Flag Cnt`
49. `PSH Flag Cnt`
50. `ACK Flag Cnt`
51. `URG Flag Cnt`
52. `CWE Flag Count`
53. `ECE Flag Cnt`
54. `Down/Up Ratio`
55. `Pkt Size Avg`
56. `Fwd Seg Size Avg`
57. `Bwd Seg Size Avg`
58. `Fwd Byts/b Avg`
59. `Fwd Pkts/b Avg`
60. `Fwd Blk Rate Avg`
61. `Bwd Byts/b Avg`
62. `Bwd Pkts/b Avg`
63. `Bwd Blk Rate Avg`
64. `Subflow Fwd Pkts`
65. `Subflow Fwd Byts`
66. `Subflow Bwd Pkts`
67. `Subflow Bwd Byts`
68. `Init Fwd Win Byts`
69. `Init Bwd Win Byts`
70. `Fwd Act Data Pkts`
71. `Fwd Seg Size Min`
72. `Active Mean`
73. `Active Std`
74. `Active Max`
75. `Active Min`
76. `Idle Mean`
77. `Idle Std`
78. `Idle Max`
79. `Idle Min`
80. `Label`

## Field classification

### Identifiers / flow-key components

- `Dst Port`
- `Protocol`

The file does not contain `Flow ID`, source IP, destination IP, or source port. `Dst Port` and `Protocol` are the only flow-key/transport identity fields present.

### Timestamp

- `Timestamp`

Observed valid timestamp representation: `DD/MM/YYYY HH:MM:SS`, for example `28/02/2018 08:22:13`. The parsed coverage is `2018-02-28 01:00:00` through `2018-02-28 12:59:59` from 613,071 valid flow rows. The 33 embedded header rows have the literal `Timestamp` token and were not parseable.

### Label

- `Label`

Original label values and counts, including the embedded-header artifact:

| Raw value | Count | Interpretation |
|---|---:|---|
| `Benign` | 544,200 | Original source label |
| `Infilteration` | 68,871 | Original source label; spelling preserved exactly |
| `Label` | 33 | Repeated header artifact, not an attack label |

Valid labeled flow records excluding the 33 repeated headers: 613,071.

### Flow-level features

All columns from `Flow Duration` through `Idle Min` are flow-export features. They include duration, directional packet/byte totals, packet-size statistics, rates, inter-arrival summaries, TCP flag counts, header lengths, subflow aggregates, initial TCP window bytes, and active/idle timing summaries.

## Feature availability

| Requirement | Present in CSV | Exact evidence | Limitation |
|---|---|---|---|
| TCP flags | Yes, flow aggregates | `Fwd PSH Flags`, `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `FIN Flag Cnt`, `SYN Flag Cnt`, `RST Flag Cnt`, `PSH Flag Cnt`, `ACK Flag Cnt`, `URG Flag Cnt`, `CWE Flag Count`, `ECE Flag Cnt` | No per-packet flag order or handshake sequence |
| Packet counts | Yes | `Tot Fwd Pkts`, `Tot Bwd Pkts`, `Subflow Fwd Pkts`, `Subflow Bwd Pkts`, `Fwd Act Data Pkts` | Aggregate counts only |
| Byte counts | Yes | `TotLen Fwd Pkts`, `TotLen Bwd Pkts`, `Subflow Fwd Byts`, `Subflow Bwd Byts` | Aggregate counts only |
| IAT features | Yes, summarized | `Flow IAT *`, `Fwd IAT *`, `Bwd IAT *` | No raw packet-level IAT sequence/distribution |
| Bidirectional features | Yes | Fwd/Bwd fields, `Down/Up Ratio`, directional rates and sizes | No source/destination IP or source port |
| TTL | No | No TTL-named column | Requires PCAP |
| TCP window | Partial | `Init Fwd Win Byts`, `Init Bwd Win Byts` | Initial values only; full packet-level window observations require PCAP |
| Fragment indicators | No | No fragment/IP-ID fields | Requires PCAP |
| Payload-size statistics | Partial proxy | Packet-length and segment-size fields, including `Pkt Len *`, `Fwd/Bwd Pkt Len *`, `Fwd/Bwd Seg Size *` | No explicit raw payload-length distribution; requires PCAP for packet-accurate derivation |
| Retransmission features | No | No retransmission/sequence/ack analysis columns | Requires PCAP |

## Missing-value and non-finite summary

No blank cells or null tokens (`null`, `none`, `NA`, `N/A`) were found in the streamed records.

Non-finite numeric values were found:

| Column | `NaN` | `Infinity` | Total |
|---|---:|---:|---:|
| `Flow Byts/s` | 4,041 | 2,128 | 6,169 |
| `Flow Pkts/s` | 0 | 6,169 | 6,169 |
| **Total** | **4,041** | **8,297** | **12,338** |

These values must be handled in a derived ingestion artifact; the raw CSV must remain unchanged.

## Potential target leakage

- `Label` is direct target leakage and must never be used as an input feature.
- The 33 embedded rows with `Label` as their label value are structural contamination and must be excluded from derived flow records.
- `Timestamp` should be used for ordering and chronological splitting. Using it as an unrestricted predictive feature can leak day/time or attack-schedule information.
- Every flow statistic is an end-of-flow aggregate. For forecasting at an intra-flow cutoff, using a completed flow’s duration, totals, IAT summaries, flags, or active/idle summaries can expose information that was not available at prediction time. The ingestion/forecasting design must define flow completion and cutoff handling explicitly.
- `Dst Port` and `Protocol` are not direct labels, but they may be strong attack proxies. Their use requires a leakage review against the target definition.

## Features still requiring raw PCAP

The following cannot be obtained from this CSV alone and should be derived only from a real matching PCAP:

- source IP and destination IP;
- source port and a complete five-tuple/flow identifier;
- packet-level TTL observations and distributions;
- IP fragmentation flags/counts and fragment-related fields;
- packet-level TCP window observations beyond the initial forward/backward values;
- packet sequence/acknowledgement evidence for retransmission detection;
- raw packet IAT sequence/distribution and burst ordering;
- packet payload lengths and payload-size distributions;
- per-packet TCP flag order, handshake evidence, and direction transitions; and
- flow-to-PCAP alignment evidence.

No packet features were fabricated or inferred from missing columns.

## Next task

Build the flow ingestion/validation step that preserves the raw CSV, excludes the 33 repeated header records in a derived table, records the original labels unchanged, and explicitly handles the `NaN`/`Infinity` values before any baseline model work.
