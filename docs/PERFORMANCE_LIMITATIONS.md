# Performance Limitations

All timing values in this repository are **local development measurements** or
**prototype measurements**. They are not production benchmarks and do not
define a production SLA.

Observed local API read measurement on 2026-08-25:

- 30 sequential `GET /api/v1/live` requests;
- mean: 23.640 ms;
- median: 15.085 ms;
- P95: 36.661 ms;
- maximum: 191.400 ms.

Observed real Wi-Fi startup measurement on the same host:

- first valid state: 66.26 seconds;
- 10-state buffer fill: 296.73 seconds;
- first inference: 296.97 seconds.

These values depend on hardware, OS scheduling, Npcap/Scapy behavior,
interface selection, background network traffic, flow timeout policy, state
production rate, model runtime, and dashboard/browser load. The API read time
does not include the time to produce a new state or forecast. Dashboard health
was verified, but a separate browser-render latency benchmark was not claimed.
