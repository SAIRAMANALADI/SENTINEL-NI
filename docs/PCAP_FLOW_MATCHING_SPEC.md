# PCAP-to-Flow Matching Specification

Status: **BLOCKED — no defensible flow-to-PCAP join can be performed with the current canonical flow artifact.**

## Available PCAP source

The local workspace contains no `.pcap`, `.pcapng`, or downloaded archive. The official public object inventory identifies:

```text
s3://cse-cic-ids2018/Original Network Traffic and Log data/Wednesday-28-02-2018/pcap.zip
```

Object metadata:

- compressed size: `53,251,694,487` bytes (`53.25 GB` decimal; `49.59 GiB`);
- content type: `application/zip`;
- ETag: `b688b1c7c529c8754fe11aec1a963270-3175`;
- byte-range access: supported (`AcceptRanges: bytes`).

The ZIP central directory was inspected through a 4 MiB tail range only. It contains 438 entries: one directory and 437 machine capture files under `pcap/`. The listed files have approximately `63,669,689,649` bytes uncompressed (`63.67 GB` decimal; `59.31 GiB`). The smallest listed capture is approximately 758,523 bytes, but its relevance to the selected flow CSV cannot be established from the current flow data.

## Existing flow identity

The schema of `data/processed/cic_ids2018_multiday_flow.parquet` contains 88 columns. Matching-relevant fields actually available are:

- `Timestamp` and parsed `timestamp_parsed`;
- `capture_date` and `source_file` provenance;
- `Dst Port`;
- `Protocol`.

The artifact does **not** contain `src_ip`, `dst_ip`, `src_port`, a source `Flow ID`, packet sequence numbers, capture-interface identifiers, or a machine identifier. The network-state artifact intentionally contains only aggregate state fields and also cannot identify a PCAP member.

## Canonical key and current result

The intended packet connection key would be the bidirectional canonical 5-tuple:

```text
(src_ip, dst_ip, src_port, dst_port, protocol)
```

Reverse-direction packets would be canonicalized by ordering the two endpoint tuples, while retaining packet direction for directional statistics. That key cannot be constructed for the current CSV because four endpoint fields and the original flow identifier are absent.

Timestamp + destination port + protocol is not a safe substitute: concurrent connections can collide, and timestamp semantics/tolerance between CICFlowMeter completed-flow records and packet capture events have not been established. No timestamp tolerance is approved. A tolerance must be measured from a matched flow/PCAP pair before implementation.

## Subset and ambiguity policy

The ZIP is a single large archive containing per-machine captures. Byte-range access is technically available, but selecting a smaller member requires a defensible mapping from the flow CSV to machine/IP scope. That mapping is absent. Therefore no member is selected or downloaded. No many-to-many or heuristic packet-to-flow association is permitted.

If a future approved artifact supplies endpoint identity and capture scope, the matcher must:

1. require the canonical 5-tuple and protocol;
2. apply a measured timestamp tolerance documented with evidence;
3. reject ambiguous matches rather than assign them arbitrarily;
4. report matched, unmatched, and collision counts;
5. preserve capture-day and source-file provenance;
6. validate that each packet/flow association is one-to-one or explicitly aggregated by a documented rule.

## Decision

Packet parsing and feature extraction are stopped at the availability/matching gate. No packet feature, match rate, processing metric, or enriched state dataset is claimed.
