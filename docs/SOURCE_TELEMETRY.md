# Source Telemetry Contract

## Version

Source activity uses `source_schema_version: "1"` inside the existing
authenticated `schema_version: "1"` remote telemetry envelope. It is optional;
state-only agents remain valid and produce `NO_SOURCE_ATTRIBUTION`.

## Transport

The remote agent sends source rows to `POST /api/v1/telemetry` with the same
`X-Sentinel-Sensor-Token`, sequence number, retry behavior, and disk buffer as
network states. Source rows are included in the same batch when available and
are never sent to an unauthenticated or sensor-mismatched endpoint.

## Record shape

Each row uses the actual source activity fields emitted by
`src/streaming/source_activity.py`:

`source_ip`, `capture_day`, `interval_start`, `interval_end`, `flow_count`,
`packet_count`, `byte_count`, `unique_destinations`,
`unique_destination_ports`, `mean_packet_size`, `mean_iat`, `syn_count`,
`ack_count`, `rst_count`, `packet_rate`, and `byte_rate`.

Intervals are UTC-aware, aligned to the fixed 10-second cadence, and belong to
their declared capture day. `sent_at` is the sender timestamp; central receipt
time is recorded separately for freshness decisions.

## Central processing

`RemoteSensorRuntime` keeps a bounded history per `sensor_id`, reuses the
existing deterministic `prioritize_sources` rules, and exposes only current
interval rows as ranked Candidate Sources. It adds first seen, last seen,
active status, recent activity, measured reasons, and forecast context. The
frozen 17 state features, target, LSTM, threshold, and model input contract
are untouched.

The status values are explicit:

- `NO_SOURCE_ATTRIBUTION` — no source rows have been received;
- `SOURCE_ATTRIBUTION_AVAILABLE` — current source rows are available;
- `SOURCE_DATA_STALE` — rows exist but receipt freshness exceeded the configured
  telemetry stale interval;
- `NO_CANDIDATE_SOURCES` — source telemetry exists but no current ranked row is
  available.

## Capability boundary

Local packet capture and the remote agent can provide source identity only when
the actual packet metadata contains endpoint and port fields. Zeek is partial
and is not frozen-state compatible by itself. NetFlow/IPFIX remain unsupported
in this release. Payload inspection is outside the contract.
