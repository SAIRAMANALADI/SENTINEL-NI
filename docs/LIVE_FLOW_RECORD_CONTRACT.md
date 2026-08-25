# Live Flow Record Contract

## Input

The builder accepts the existing required packet-event fields:

```text
timestamp
source_ip
destination_ip
source_port
destination_port
protocol
packet_length
tcp_flags
```

## Output

Each completed record contains the downstream flow fields plus measured
provenance:

```text
flow_id, source_ip, destination_ip, source_port, destination_port, protocol
capture_date, timestamp_parsed, Dst Port, Flow Duration
Tot Fwd Pkts, Tot Bwd Pkts, TotLen Fwd Pkts, TotLen Bwd Pkts
Flow IAT Mean, Flow IAT Std, SYN Flag Cnt, ACK Flag Cnt, RST Flag Cnt
Pkt Len Mean, Pkt Len Std, first_packet_timestamp, last_packet_timestamp
flow_close_reason, label_available
```

`label_available` is always `false` for live packet-derived records. The
record intentionally does not contain `Label`; adding a guessed label would
turn an unlabeled live event into false target evidence.

## Identity and direction

The flow key is the direction-independent tuple:

```text
(source_ip, source_port, destination_ip, destination_port, protocol)
```

The two endpoints are lexicographically ordered. The lower endpoint is the
canonical forward endpoint and the higher endpoint is the canonical reverse
endpoint. Reverse packets join the same flow. `Dst Port` is the port of the
canonical reverse endpoint.

## Lifecycle

- first packet sets `timestamp_parsed` and flow start;
- every packet updates counts, bytes, flags, packet sizes, and IATs;
- FIN/RST closes immediately;
- idle timeout closes when the next event is at least 30 seconds after the
  last packet;
- active timeout closes when the next event is at least 300 seconds after the
  first packet;
- explicit flush closes remaining flows with reason `flush`;
- maximum tracked flows is 10,000; overflow rejects the new flow.

## State compatibility

The record contains every current non-label flow source field and is
state-compatible with the label-free live inference contract. It is not
supervised-state-compatible: `Label` is unavailable, so no target columns are
generated and no label is inferred.
