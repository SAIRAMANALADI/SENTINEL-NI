# Temporal Granularity Comparison

The comparison was computed from the real multi-day Parquet artifact after excluding the 14 documented timestamp anomalies. Empty fixed intervals are included between the valid per-day minimum and maximum timestamps; intervals never cross capture-day boundaries.

- Input load time: `0.277` seconds
- Selected MVP interval: `10` seconds

| Interval | States | Total flows | Mean flows/state | Median | P95 | Empty % | Attack-state frequency | Output bytes | Aggregation seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 161,256 | 3,758,782 | 23.31 | 7.00 | 72.00 | 37.97% | 0.1303 | 9,953,430 | 5.871 |
| 5 | 32,252 | 3,758,782 | 116.54 | 43.00 | 335.00 | 35.33% | 0.1418 | 2,495,571 | 4.507 |
| 10 | 16,127 | 3,758,782 | 233.07 | 94.00 | 643.00 | 34.35% | 0.1468 | 1,378,644 | 4.619 |
| 30 | 5,376 | 3,758,782 | 699.18 | 345.00 | 1823.75 | 32.50% | 0.1656 | 529,710 | 4.601 |
| 60 | 2,689 | 3,758,782 | 1397.84 | 766.00 | 3539.00 | 31.87% | 0.1856 | 278,500 | 4.652 |

## Recommendation

Select **10 seconds** for the MVP. The 1-second option creates a much larger table with approximately 38% empty states and very sparse per-state observations. The 60-second option reduces sparsity but leaves only a few thousand states across four days, which is weak for day-separated temporal development. The selected 10-second interval retains 16,127 measured states, keeps the table compact, and provides substantially more temporal resolution than 30/60 seconds. This is a state-representation choice, not a model-performance claim.

Attack-state frequency means the proportion of all fixed states containing at least one non-Benign labeled flow. It does not mean that one malicious flow proves compromise. Raw labels remain target metadata and are not state features.
