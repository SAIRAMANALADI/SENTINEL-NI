# Developer 4 — BACKUP DEVELOPER / QA / RESEARCH / INTEGRATION

## Mission
Keep the main three developers moving and make the final submission reliable.

## Standing Responsibilities

### 1. Reproducibility
Create:
- setup script
- environment check
- smoke test
- end-to-end test

Example:
```bash
python scripts/smoke_test.py
```

### 2. Leakage Audit
Inspect:
- train/test split
- duplicate windows
- adjacent-window contamination
- target leakage
- attack-label leakage

Write:
`docs/LEAKAGE_AUDIT.md`

### 3. Dataset Audit
Record:
- source
- license/access
- selected subset
- preprocessing
- attack types
- timestamps
- flow/packet availability

Write:
`docs/DATA_AUDIT.md`

### 4. SIH Requirement Matrix
Create:
`docs/PS_REQUIREMENT_MATRIX.md`

Columns:
- requirement
- implementation
- file/module
- evidence
- demo proof
- status

### 5. MITRE Review
Validate Developer 2's mapping for:
- unsupported mappings
- misleading terminology
- fabricated chronology

### 6. Integration QA
At least twice daily:
- pull current branches
- run tests
- run sample pipeline
- report blockers

### 7. Documentation
Own:
- architecture summary
- limitations
- evaluation methodology
- reproducibility
- demo runbook

### 8. Backup Implementation
If Dev 1 is blocked:
- implement baseline
- help with preprocessing

If Dev 2 is blocked:
- implement sample feature extractor
- write schema tests

If Dev 3 is blocked:
- build CLI fallback
- integrate inference outputs

## Critical Safety Net
Build:
```bash
python run.py --input sample.csv
```
It should still print:
- current risk
- forecast
- predicted stage
- explanation

## Done when
The project remains demonstrable even if one person's branch becomes unavailable.
