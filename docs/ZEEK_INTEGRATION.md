# Zeek Integration

## Status: PARTIAL

`ZeekCollector` reads one configured Zeek `conn.log` in either of these stable
formats:

1. Zeek JSON-lines records with `ts`, `id.orig_h`, `id.resp_h`, `id.orig_p`,
   `id.resp_p`, and `proto`.
2. Standard Zeek TSV records preceded by a `#fields` header containing those
   same fields.

Optional `duration`, `orig_bytes`, `resp_bytes`, `orig_pkts`, `resp_pkts`,
`conn_state`, `local_orig`, and `local_resp` values are validated when present.
Ports, counts, bytes, duration, and timestamps are rejected when malformed or
impossible. The event timestamp remains separate from `arrival_timestamp`.

The reader is bounded and operationally safe: it only reads a configured file,
limits line size, waits for newline-terminated records during partial writes,
handles truncation/rotation by resetting its offset, suppresses bounded
duplicates, counts malformed records, and reports late events without changing
their event time. It does not watch arbitrary directories, execute Zeek, or
accept dashboard-supplied paths.

`conn.log` alone cannot provide the frozen state's flow IAT statistics, TCP
SYN/ACK/RST counts, or packet-size statistics. Therefore the adapter is
`PARTIAL` and does not produce a misleading forecast. A future compatible Zeek
deployment must add a documented, validated source for those fields or use a
separate approved feature contract.
