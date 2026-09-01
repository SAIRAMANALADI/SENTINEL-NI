# PCAP Handoff Notice — SIH26-26153

## Why this file matters

This archive is the original packet-level evidence for the CSE-CIC-IDS2018
infiltration capture on **2018-02-28**. It is important because the current
forecasting pipeline is based on processed flow/state data, while this archive
contains the raw network packets needed for deeper source attribution and
packet-level analysis.

## Archive

- **Local path:** `<local-data-root>/cse-cic-ids2018/pcap/pcap.zip`
- **Compressed member-size total:** `53,251,610,825` bytes (about 53.25 GB)
- **Verified archive members:** 437 PCAP captures
- **Capture day:** 2018-02-28

## Why the PCAP is important

The current flow CSV does not contain the canonical fields needed to safely
connect a flow to a particular capture machine. It lacks:

- source IP
- destination IP
- source port
- full five-tuple
- Flow ID
- machine identity

The PCAP can potentially provide the packet-level evidence required to recover
or validate these details, including packet timing, packet flags, payload-size
behavior, retransmissions, and host/source attribution. These details must be
derived from the actual packets; they must never be fabricated from aggregate
flow data.

## Current project status

The frozen Version 1 forecasting pipeline is valid and flow/state based. It
must not be changed merely because the PCAP is available. PCAP enrichment is a
separate research path and is currently **not fused** with the production
forecasting dataset because an authoritative flow-to-PCAP mapping has not yet
been verified.

## Important handling rules

1. Do not commit this archive to normal Git or GitHub.
2. Do not extract all 437 captures automatically.
3. Do not guess which machine is the attacker.
4. Do not create packet features until the relevant capture and matching
   evidence are established.
5. Keep the archive unchanged and share it through a secure drive/cloud
   transfer or an external disk.

## Recommended next step

First review the repository's PCAP mapping audit and official-metadata
research. If a defensible mapping is established, process only the smallest
supported capture subset. If mapping remains unverified, keep the PCAP as
separate evidence and do not fuse it with the current flow dataset.

## Ownership boundary

- **Data/network side:** preserve the archive, document provenance, establish
  matching evidence, and validate any packet-derived fields.
- **ML/forecasting side:** continue using the frozen flow/state contract until
  a separately validated packet-enriched contract is approved.
