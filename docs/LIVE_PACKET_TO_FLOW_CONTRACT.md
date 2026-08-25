# Live Packet-to-Flow Contract

## Status

**FLOW CONVERSION READY WITH LIMITATIONS**

`src/streaming/flow_builder.py` converts normalized packet events into
completed bidirectional flow records. It does not create labels, targets, or a
second state aggregation implementation.

## Downstream fields

The exact required source fields are taken from
`src/features/network_state.py::REQUIRED_COLUMNS`.

| Field | Type | Packet source | Definition | Status |
|---|---|---|---|---|
| `capture_date` | string | `timestamp` | ISO date of first packet | SUPPORTED |
| `timestamp_parsed` | timestamp | `timestamp` | First packet timestamp | SUPPORTED |
| `Label` | string | none | Dataset label used for malicious-flow target | NOT DERIVABLE |
| `Dst Port` | integer | endpoint ports | Canonical reverse endpoint port | DERIVABLE WITH LIMITATION |
| `Flow Duration` | float | packet timestamps | Last minus first timestamp, microseconds | DERIVABLE WITH LIMITATION |
| `Tot Fwd Pkts` | integer | packet direction | Canonical forward packet count | DERIVABLE WITH LIMITATION |
| `Tot Bwd Pkts` | integer | packet direction | Canonical reverse packet count | DERIVABLE WITH LIMITATION |
| `TotLen Fwd Pkts` | integer | `packet_length` | Sum of forward packet lengths | SUPPORTED |
| `TotLen Bwd Pkts` | integer | `packet_length` | Sum of reverse packet lengths | SUPPORTED |
| `Flow IAT Mean` | float | packet timestamps | Mean adjacent interval, microseconds | DERIVABLE WITH LIMITATION |
| `Flow IAT Std` | float | packet timestamps | Sample standard deviation of intervals | DERIVABLE WITH LIMITATION |
| `SYN Flag Cnt` | integer | `tcp_flags` | Packets containing SYN | SUPPORTED |
| `ACK Flag Cnt` | integer | `tcp_flags` | Packets containing ACK | SUPPORTED |
| `RST Flag Cnt` | integer | `tcp_flags` | Packets containing RST | SUPPORTED |
| `Pkt Len Mean` | float | `packet_length` | Mean packet length | SUPPORTED |
| `Pkt Len Std` | float | `packet_length` | Sample standard deviation of lengths | DERIVABLE WITH LIMITATION |

## Limitations

- `Label` cannot be inferred from packet metadata. The builder never inserts
  `Benign`, a malicious label, or any placeholder label.
- Canonical direction is deterministic lexicographic ordering of the two
  `(IP, port)` endpoints. It is not guaranteed to equal CICFlowMeter's
  original forward direction.
- Duration and IAT use microseconds to align with documented flow-source units,
  but equivalence to CICFlowMeter's implementation is not yet proven.
- A packet event has no packet identifier, so duplicate rows are retained.
- A flow closes on FIN/RST, idle timeout, active timeout, or explicit flush.
- No state or target is valid until the label gap and unit/direction equivalence
  are separately resolved.
