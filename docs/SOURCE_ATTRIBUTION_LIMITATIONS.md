# Source Attribution Limitations

The system produces candidate-source prioritization from observed network
activity and forecast context. It does not identify an attacker, a malicious
user, or a confirmed threat actor.

Use these labels in UI, API, and review language:

- Candidate Source
- Low Priority Source
- Medium Priority Source
- High Priority Source

An observed source IP may represent a NAT gateway, proxy, shared host,
service, legitimate high-volume client, or another intermediary. An IP is not
equivalent to a human, process, organization, or threat identity.

The reasons shown by the system are measured activity signals such as flow
growth, packet rate, byte rate, destination count, and destination-port count.
They are operational prioritization reasons, not attribution evidence.

Any stronger attribution requires separately validated host identity,
flow-to-PCAP matching, and corroborating forensic evidence. Those inputs are
outside the frozen Version 1 live forecast contract.
