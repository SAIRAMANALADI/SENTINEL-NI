# FIRST 6 HOURS — EXECUTION CHECKLIST

## Hour 0–1

### Project Lead / You
- [ ] Create GitHub repo
- [ ] Add all 4 developers
- [ ] Add task board
- [ ] Add these files
- [ ] Freeze schema draft
- [ ] Assign branches

### Dev 1
- [ ] Create Python/PyTorch environment
- [ ] Build training skeleton
- [ ] Start baseline

### Dev 2
- [ ] Prepare selected dataset subset
- [ ] inspect columns
- [ ] separate flow vs packet features
- [ ] draft schema

### Dev 3
- [ ] Create Streamlit shell
- [ ] Build static dashboard
- [ ] Create inference placeholder

### Dev 4
- [ ] Build PS requirement matrix
- [ ] Start data/leakage audit
- [ ] Create smoke-test skeleton

## Hour 1–3
Target:
```text
raw data → clean canonical feature table
```

Dev 2 owns it.
Dev 1 consumes it.
Dev 4 verifies it.
Dev 3 keeps the UI progressing.

## Hour 3–6
Target:
```text
feature table → Logistic Regression → metrics
```

At hour 6:
- baseline runs
- sample metrics exist
- UI loads sample output
- schema is frozen

## Hard Gate
If the basic data/baseline path is not stable, do not start Transformer/GNN work.
