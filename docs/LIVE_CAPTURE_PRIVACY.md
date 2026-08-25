# Live Capture Privacy

The default live adapter is metadata-only. It emits:

- timestamp
- source and destination IP addresses
- source and destination ports
- protocol
- packet length
- TCP flags
- optional TTL, fragment indicator, TCP window, and payload length when the
  packet layer exposes them reliably

It does not retain packet objects, payload bytes, passwords, application
content, or packet dumps. The queue is bounded and contains only normalized
event dictionaries. API telemetry status never exposes raw packet contents.

Source IP is an observed network endpoint, not a human identity or confirmed
attacker. The dashboard uses candidate-source and mitigation-recommendation
language. No automatic blocking is implemented.

Operators should treat IP addresses and timestamps as sensitive operational
telemetry, restrict API tokens, and rotate audit logs under the existing access
controls. A separate diagnostic capture mode would require a new approval and
is intentionally not implemented.
