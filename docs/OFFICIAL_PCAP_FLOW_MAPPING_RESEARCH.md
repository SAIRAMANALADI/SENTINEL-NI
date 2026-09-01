# Official PCAP-to-Flow Mapping Research

## Decision

**MAPPING NOT VERIFIED**

This research was limited to official documentation, repository metadata, and the ZIP central directory. No PCAP member was extracted or parsed, and no production code or frozen forecasting artifact was changed.

## Official source

Primary source: [CSE-CIC-IDS2018 official dataset documentation](https://www.unb.ca/cic/datasets/ids-2018.html).

The official page states that:

1. The dataset is organized per day and includes raw network traffic (PCAPs) and event logs per machine.
2. CICFlowMeter-V3 generated more than 80 traffic features and saved the generated data as a CSV file per machine.
3. The flow CSV output includes `FlowID`, `SourceIP`, `DestinationIP`, `SourcePort`, `DestinationPort`, and `Protocol`, followed by the traffic features.
4. Flow labels were assigned using the attack schedule together with source/destination IPs, ports, and protocol.

These statements establish the intended official data model: a day-scoped, machine-scoped raw capture and a machine-scoped flow export. They do not publish a per-machine filename manifest for the local combined CSV or a member-by-member mapping for the ZIP archive inspected here.

## Official 28-February evidence

The official attack schedule lists the following infiltration entries:

| Attacker | Victim / internal host | Date | Time |
|---|---|---|---|
| `13.58.225.34` | `18.221.148.137-172.31.69.24` | `Wed-28-02-2018` | `10:50–12:05` |
| `13.58.225.34` | `18.221.148.137-172.31.69.24` | `Wed-28-02-2018` | `13:42–14:40` |

This is authoritative evidence that `172.31.69.24` is in the documented 28-February infiltration scope. It is not, by itself, a proof that every packet in a particular archive member belongs to the selected combined flow CSV, nor that a hostname in a capture filename identifies the attacker.

## Local archive evidence

Archive path:

```text
<local-data-root>/cse-cic-ids2018/pcap/pcap.zip
```

The ZIP central directory was inspected without extraction:

- actual PCAP file members: `437`;
- directory entries: `1`;
- compressed member-size total: `53,251,610,825` bytes;
- uncompressed member-size total: `63,669,689,649` bytes;
- ZIP container size: `53,251,694,487` bytes.

The members are under `pcap/` and their names generally contain a hostname and an internal `172.31.x.x` address. Two members contain the official-schedule internal IP `172.31.69.24`:

```text
pcap/capEC2AMAZ-O4EL3NG-172.31.69.24- part1
pcap/capEC2AMAZ-O4EL3NG-172.31.69.24-part2
```

Their inventory values are:

| Archive member | Compressed size (bytes) | Uncompressed size (bytes) |
|---|---:|---:|
| `pcap/capEC2AMAZ-O4EL3NG-172.31.69.24- part1` | `90,027,418` | `98,445,934` |
| `pcap/capEC2AMAZ-O4EL3NG-172.31.69.24-part2` | `298,278,501` | `347,870,553` |

The IP overlap makes these members relevant for follow-up investigation, but they are **not verified candidates** for fusion with the current flow artifact.

## Archive structure classification

The best-supported classification is **A: machine-scoped capture files**, with the qualification that one machine's capture may be split across multiple archive members. The exact traffic inclusion rule for each member is not established by the available metadata.

- **Supported:** the official documentation says raw traffic and logs are recorded per machine; the local member names also contain machine-like hostnames and internal IPs.
- **Not supported:** the documentation does not establish whether a member contains only traffic originating from that machine, all traffic involving that machine, or a split/part of a longer machine capture. The `part1`/`part2` names show splitting, not the traffic inclusion rule.
- **Rejected:** there is no evidence that the archive is one mixed undifferentiated capture, but there is also no basis to assign attacker/victim role from filename text.

## Flow-export relationship

The official page describes per-machine CSV generation, so an original per-machine flow export should conceptually correspond to the same day/machine scope as the raw data used to generate it. However, the repository’s active flow input is a combined file:

```text
data/raw/cse-cic-ids2018/flow/Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv
```

The current artifact lacks `SourceIP`, `DestinationIP`, `SourcePort`, `FlowID`, and machine identity. It therefore cannot be joined to a ZIP member using the official flow identity fields. The repository also contains no authoritative machine-to-flow-file manifest for this combined export.

The following substitutions are explicitly unsupported:

- matching by hostname text alone;
- treating `172.31.69.24` filename overlap as a complete flow-to-PCAP match;
- assuming `EC2AMAZ-O4EL3NG` is the attacker or victim;
- assuming the two `172.31.69.24` members contain all and only the infiltration flows;
- joining on timestamp, destination port, and protocol without a measured tolerance and collision audit.

## Mapping result

The official schedule gives an authoritative **attack-scope IP**, not an authoritative mapping from the current combined flow CSV to an archive member. Therefore no exact PCAP member can be safely selected for packet fusion at this time.

## Missing information

At least one of the following is required before PCAP fusion can be approved:

1. The original per-machine flow CSV for `2018-02-28` and `172.31.69.24`, retaining the official six identifier columns and an unambiguous machine/file provenance field.
2. An official machine/capture manifest that maps each ZIP member to the corresponding per-machine flow export and defines whether the capture contains source-only, destination-only, or all traffic involving that machine.
3. A verified flow-to-member join artifact containing canonical bidirectional five-tuples, timestamp semantics, and a measured matching tolerance.

## Exact next acquisition step

Do not extract either `172.31.69.24` member yet. Obtain, through an approved manual acquisition, the official per-machine flow export or machine/capture manifest for the 28-February infiltration host and preserve its original filename and checksum. First verify that it contains `FlowID`, both IPs, both ports, protocol, timestamp, and machine/date provenance. Only after that review should the smallest corresponding PCAP member subset be selected.

Until that evidence exists, PCAP fusion with the current combined flow dataset must remain stopped.
