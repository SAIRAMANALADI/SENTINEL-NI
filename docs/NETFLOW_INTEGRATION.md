# NetFlow Integration

## Status: PLANNED / UNSUPPORTED

NetFlow is a flow-telemetry source, not a packet-capture replacement. This
release defines its source identity and capability declaration but intentionally
does not ship a NetFlow wire decoder, UDP listener, exporter protocol parser,
or state adapter. `CollectorRegistry` rejects `NETFLOW` creation explicitly.

Future work must select the exact NetFlow versions and fields, validate
timestamps, exporter identity, counts, bytes, duplicates, rate limits, packet
size, and malformed records, and prove compatibility with all 17 frozen state
features before enabling forecasts. Any listener must bind to an explicitly
configured private interface and port, enforce maximum datagram size and rate,
and allow-list exporters behind a firewall. NetFlow transport security is not
equivalent to authenticated HTTPS; use a private network or a protected
collector boundary.
