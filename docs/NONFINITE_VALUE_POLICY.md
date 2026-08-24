# CSE-CIC-IDS2018 Non-Finite Value Policy

Date: 2026-08-24

## Observed cause

The real infiltration-day CSV contains 12,338 non-finite cells:

- `Flow Byts/s`: 4,041 `NaN` and 2,128 `Infinity`;
- `Flow Pkts/s`: 6,169 `Infinity`.

All 6,169 affected rows have `Flow Duration = 0`. The 4,041 `Flow Byts/s = NaN` rows also have zero total bytes. The affected rows still have packet counts, so they are not discarded as malformed flows.

## Treatment

1. The raw CSV is never modified.
2. The exact source tokens are preserved in derived provenance columns:
   - `Flow Byts/s__raw`
   - `Flow Pkts/s__raw`
3. The original numeric columns are converted to numeric values and non-finite values are represented as missing (`NaN`) in the clean derived dataset.
4. No non-finite value is replaced with zero, clipped, or statistically imputed.
5. `Flow Byts/s` and `Flow Pkts/s` are excluded from the model-safe feature table because a defensible imputation rule has not been approved.
6. The model-safe feature table is checked for both missing and non-finite numeric values before it is written.

This policy preserves the evidence needed for later review while preventing invalid values from entering the baseline feature matrix.
