# Limitations and Future Work

## Current limitations

- The network-state representation is flow-derived rather than packet-native.
- Packet-level enrichment is incomplete and the current PCAP matching path is blocked by missing canonical identity fields and archive scope.
- Capture-day diversity is limited to four available days.
- Validation/test distribution shift is present and broad temporal generalization is not established.
- Raw LSTM outputs are Forecast Scores, not calibrated probabilities.
- Explainability is deterministic masking sensitivity; no validated causal explanation is provided.
- There is no production live packet-capture or streaming ingestion path.
- The target represents observed future malicious-traffic presence, not compromise, intent, attack stage, or MITRE technique.
- Completed-flow aggregates can include information from a flow’s full duration and are not an intra-flow packet-cutoff early-warning signal.

## Future work

- Acquire and validate matched packet-level enrichment with preserved flow identity and capture provenance.
- Add additional capture days and scenarios before making stronger generalization claims.
- Evaluate an approved calibration procedure for Forecast Scores using training/validation data only.
- Run stronger unseen-day and distribution-shift evaluation.
- Compare Transformer/GNN approaches only after data coverage and matching quality are stronger.
- Build an online/streaming deployment with state aggregation, monitoring, alert deduplication, and model/policy version control.
