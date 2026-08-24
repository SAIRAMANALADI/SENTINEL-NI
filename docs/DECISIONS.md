# Architecture Decisions

## Decision 001 — First temporal model

**Decision:** The first advanced forecasting model will be LSTM/GRU unless later evidence justifies a different architecture.

**Reason:** It is fast to implement, naturally handles sequences, and is easier to validate under the deadline.

**Status:** Provisional

Transformer/GNN work must **not** start until the baseline and first temporal model are working, evaluated, and reproducible. This decision does not authorize implementation of an advanced model during the foundation phase.

## Decision log rules

- Record the context, alternatives, evidence, and impact for material changes.
- Mark decisions as Provisional, Accepted, Superseded, or Rejected.
- Do not convert a provisional decision into an SIH requirement without official source evidence.
