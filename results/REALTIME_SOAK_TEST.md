# Real-Time Soak Test

## Status

PASS WITH LIMITATIONS — a real five-minute minimum capture and a second
approximately 15-minute capture were completed on the host `Wi-Fi` interface.

The first run observed 5,835 packets, 354 completed flows, and 9 states in
more than five minutes. The second run observed 9,438 packets, 608 completed
flows, 31 states, 22 forecast updates, and a full 10-state buffer in
approximately 15 minutes.

Across the final run, dropped events, rejected events, callback errors, and
runtime errors remained zero. Process RAM ended near 425 MB. Individual API
read latency spikes were observed and recovered without a crash.

The runtime snapshot does not expose active flow-table size or callback-path
queue depth. Completed-flow count, state-buffer size, forecast updates,
drops, rejections, and errors were measured; no active-flow or queue-capacity
claim is made. No 30-minute run was performed.
