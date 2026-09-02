# Telemetry Source Security

Telemetry sources are untrusted input boundaries. Source type, sensor ID, and
capability metadata are for isolation and observability; they never become
model features.

- Local Scapy capture uses the host's capture permissions and does not retain
  raw packet objects or payload bytes.
- Remote Agent telemetry uses the existing per-sensor authenticated HTTPS
  contract, sequence checks, bounded batches, rate limits, and isolated
  runtime history.
- Zeek reads only an explicitly configured file, rejects path escapes when an
  allowed directory is supplied, bounds line size and duplicate memory, and
  never executes a command or accepts arbitrary dashboard paths.
- NetFlow/IPFIX are not listeners in this release. A future deployment must
  use a private interface, firewall, exporter allow-list, datagram/record
  limits, malformed-record rejection, and rate limiting. These controls are
  not a substitute for authenticated application transport.

Bad records must increment source error state and leave other sensors running.
No source may silently coerce unavailable packet information into a value.
