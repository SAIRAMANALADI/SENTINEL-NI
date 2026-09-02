# Telemetry Sources

Sentinel uses one collector contract (`start`, `stop`, bounded `read_event`/
`read_events`, and `status`) and one frozen 10-second network-state contract.
Source identity and capability metadata are operational metadata only; they are
not model features.

| Source | Status | State-compatible | Notes |
| --- | --- | --- | --- |
| `LOCAL_PACKET_CAPTURE` | IMPLEMENTED | Yes | Existing Scapy/Npcap/libpcap metadata-only path. |
| `REMOTE_AGENT` | IMPLEMENTED | Yes | Authenticated HTTPS batches of approved states; sensor-scoped. |
| `REPLAY` | IMPLEMENTED | Yes | Existing validated replay/demo source. |
| `MOCK` | IMPLEMENTED (test/demo only) | No | In-memory test adapter, never production telemetry. |
| `ZEEK` | PARTIAL | No from `conn.log` alone | Real JSON-lines/TSV `conn.log` parser; missing packet/IAT/flag fields. |
| `NETFLOW` | PLANNED / UNSUPPORTED | No | No wire decoder or listener is enabled. |
| `IPFIX` | PLANNED / UNSUPPORTED | No | No template decoder or listener is enabled. |

Compatible sources converge on the existing pipeline:

```text
source -> collector -> existing flow/state contract -> sensor-scoped runtime -> LSTM K=5
```

An adapter must declare unavailable fields and must not synthesize them. A
partial source is rejected before forecasting when it cannot satisfy all 17
frozen state features. See the source-specific integration guides for the
deployment and security boundaries.

## Deployment modes

1. **Sentinel Agent on the monitored server** — implemented; the agent
   observes locally and pushes authenticated aggregate states.
2. **Sentinel Agent on a dedicated sensor host** — implemented where that host
   has the required capture interface and permissions.
3. **Zeek sensor to Sentinel** — partial; `conn.log` normalization is
   implemented, but the current log alone cannot feed the frozen model.
4. **NetFlow exporter to Sentinel** — planned; no listener is enabled.
5. **IPFIX exporter to Sentinel** — planned; no listener or template decoder is
   enabled.

In every mode the customer's application traffic stays on its normal path and
is observed or exported out of band.
