# Telemetry Adapter Specification

src/telemetry/base.py defines four operations:

- start(): begin reading.
- stop(): release the adapter and stop reading.
- read_event(): return one event or None when no event is available.
- status(): return adapter name, availability, lifecycle state, and safe
  counters.

Implemented adapters:

- MockTelemetryAdapter: deterministic in-memory events for tests.
- ReplayTelemetryAdapter: reads the existing validated replay fixture through
  src.streaming.replay.iter_replay_events.
- LiveTelemetryAdapter: optional Scapy/Npcap/libpcap metadata capture. It is
  constructed with an explicitly configured interface and starts only after an
  operator calls the live start control.

Live events contain only the required packet metadata. Packet objects and
payload bytes are not retained. Live events can be consumed by the existing
SourceActivityAccumulator; this does not create a second network-state
aggregator. The frozen 17-feature state path remains flow-field based, so raw
live packet metadata is not silently converted into model state features.

When telemetry is absent, callers should report DATA_STALE or
TELEMETRY_UNAVAILABLE; they must not fabricate forecasts.
