# Feature Leakage Report

## Status: BLOCKED — no actual fields available for audit

This report records the field-level audit gate and risks identified from the repository contracts. It does not claim that any field was observed in a dataset. A real exclusion list requires the selected file header, label-generation documentation, and timestamp semantics.

| Field/risk category | Actual field observed | Why it may leak the target | Required action | Current status |
| --- | --- | --- | --- | --- |
| Attack label or label encoding | UNKNOWN | Direct target inclusion makes evaluation invalid | Keep `attack_label` and `original_attack_label` outside `X` | Policy recorded; field audit pending |
| Attack schedule or event log fields | UNKNOWN | Schedule or post-event metadata can reveal the future target | Exclude from model inputs unless available before forecast origin and explicitly justified | Policy recorded; field audit pending |
| Scenario/capture identifier | UNKNOWN | Scenario names, files, or IDs may identify attack classes | Retain as split metadata; exclude from model inputs by default | Policy recorded; field audit pending |
| Source/destination IP identifiers | UNKNOWN | Fixed attack hosts or IP ranges can act as label shortcuts | Audit uniqueness and cross-split distribution; anonymize or exclude if necessary | Pending sample |
| Source/destination ports | UNKNOWN | Dataset labeling may use ports and protocol | Compare with label provenance and evaluate leakage risk | Pending sample |
| Post-event flow statistics | UNKNOWN | Features calculated beyond forecast origin expose future behavior | Enforce timestamp cutoff during aggregation | Policy recorded; implementation pending |
| Timestamp-derived fields | UNKNOWN | Absolute time, day, or attack interval may identify labels | Use timestamp for ordering; audit derived time features | Policy recorded; implementation pending |
| Preprocessing artifacts | NONE CREATED | Fitting on all data would leak validation/test distribution | Fit transforms on training partition only and serialize provenance | Pending pipeline |
| Overlapping temporal windows | NONE CREATED | Shared rows or future intervals can cross partitions | Split timelines before windowing or apply a documented guard gap | Pending pipeline |

## Required evidence before sign-off

- Raw-to-canonical field mapping.
- Label-generation and timestamp provenance.
- Excluded-field list with per-field rationale.
- Split manifest and overlap test output.
- Proof that preprocessing is fitted only on permitted training data.

Until those artifacts exist, no feature schema or model-ready `X` table should be treated as finalized.
