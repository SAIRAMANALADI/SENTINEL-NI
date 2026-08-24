# MVP Data Strategy

Date: 2026-08-24  
Project: SIH26-26153 — AI Based Network Attack Forecasting

## Selected option

**Option B — CSE-CIC-IDS2018, using a bounded real-data slice with matched flow CSV and raw PCAP.**

This is a source-selection decision only. No dataset has been downloaded, parsed, transformed, or copied by this audit.

## Why this source

The official UNB/CIC documentation describes seven attack scenarios, including infiltration, and states that the dataset is organized by day with raw PCAPs and event logs per machine plus generated CSV flow files. It also documents bidirectional CICFlowMeter output and more than 80 traffic features. The same page publishes attack schedules and identifies infiltration activity on 2018-02-28 and 2018-03-01.

This combination is the smallest credible route to both required data levels:

1. flow-level features from the documented generated CSVs; and
2. packet-level features extracted from the corresponding raw PCAPs.

## Exact MVP acquisition scope

Acquire only the following real source material first:

| Item | Scope | Status |
|---|---|---|
| Attack period | Infiltration day 2018-02-28, with benign lead-in and the documented attack interval | Required |
| Holdout period | Infiltration day 2018-03-01, if the first-day inventory confirms a usable matching capture | Recommended |
| Flow source | Generated per-machine CICFlowMeter CSV files for the selected day/machines | Required |
| Packet source | Raw PCAP files for the same day/machines and capture interval as the flow CSVs | Required |
| Labels | Original dataset labels and schedule-derived annotations as delivered; preserve before any project mapping | Required |
| Event logs | Keep only if needed to resolve attack boundaries or validate labels; do not make them a hidden label source | Optional |

The official page does not expose a complete object listing in this repository, so the exact downloaded filenames, object paths, sizes, and checksums are **UNKNOWN until the official AWS inventory is inspected**. Record them before any parsing under a future acquisition manifest. The official source reference is the [UNB/CIC IDS2018 page](https://www.unb.ca/cic/datasets/ids-2018.html) and its linked [AWS Open Data registry entry](https://registry.opendata.aws/cse-cic-ids2018/).

Recommended repository destination after the user explicitly acquires the files:

```text
data/raw/cse-cic-ids2018/
└── infiltration/
    ├── 2018-02-28/
    │   ├── original-flow-csv-files/
    │   └── original-pcap-files/
    └── 2018-03-01/
        ├── original-flow-csv-files/
        └── original-pcap-files/
```

Preserve original filenames and formats. Do not rename or convert raw files during acquisition.

## Feature availability plan

### Directly available from generated flow CSVs

Use only fields actually present in the selected files. The official feature documentation includes the flow identity fields and examples of the following groups:

- source/destination IP, source/destination port, and protocol;
- flow duration;
- forward/backward packet and byte counts;
- packet-size statistics;
- bytes-per-second and packets-per-second rates;
- overall and directional inter-arrival times;
- forward/backward TCP flag counts;
- forward/backward header sizes;
- payload-size statistics; and
- forward/backward TCP window-byte fields.

The exact CSV header must be inventoried from the real files before the canonical schema is finalized.

### Derivable from flow CSVs

Subject to the actual headers and timestamp representation:

- bidirectional byte and packet ratios;
- forward/backward rate ratios;
- flow duration and burst summaries;
- unique destination count, destination-port diversity, and fan-out within a temporal state window;
- per-window flow counts, byte/packet totals, and protocol mix;
- label counts and original-label proportions per state window.

These are derived aggregates, not fabricated packet measurements.

### Requires the matching PCAP

Extract these only from the real corresponding packets:

- packet-level TTL distributions;
- IP fragment flags and fragment counts;
- packet-accurate TCP window observations;
- retransmission indicators based on packet sequence/acknowledgement evidence;
- packet-level IAT distributions and burst structure;
- packet payload-size distributions when the flow export is insufficient;
- packet-level flag ordering and handshake evidence; and
- any packet-to-flow join validation needed to prove source alignment.

If a PCAP is missing or cannot be matched to a flow file, mark these fields unavailable. Do not fill them with zeros or estimates.

## Forecasting target for the MVP

Keep the original dataset label as the source label. Do not map it to MITRE ATT&CK at ingestion time.

For the first forecasting experiment, define a target state as:

> whether an infiltration-related labeled activity occurs in a future state window, with the original source labels retained alongside the target.

The state label and the exact positive boundary must be reviewed against the source schedule and flow labels. A binary malicious/not-malicious view may be added only as a documented derived view; it must not replace the original labels.

## Temporal unit, context, and horizon

These are MVP experiment settings, not claims from the SIH problem statement:

- state window: 1 minute, aligned to a documented timestamp convention;
- context: the previous 15 state windows (15 minutes), subject to sparsity analysis;
- forecast horizon: the next 1 state window first, then 3 windows for K-step evaluation;
- K-step output: predicted state sequence for `S(t+1)` through `S(t+K)`;
- chronological split: earlier windows for development and later windows for validation/holdout; no random row split.

If one-minute windows are too sparse or too dense after real-file inspection, revise the window size in a recorded experiment decision. Do not silently change it.

## Attack-stage mapping and explainability

The official CSE description gives a narrative infiltration progression, but the repository currently lacks the official SIH statement and a validated project-specific stage taxonomy. Therefore:

- preserve source labels first;
- use the source attack schedule and packet/flow evidence to define stage boundaries;
- map stages to MITRE only in a later, separately evidenced annotation step;
- expose feature contributions, source label, window time, and evidence provenance in the eventual offline output.

No attack-stage label is created by this document.

## Reproducibility and storage gate

Before processing begins, the acquisition record must include:

- official source URL and access date;
- exact object path and original filename;
- byte size and SHA-256 checksum;
- local relative path;
- file type and timestamp convention;
- selected machine/day/capture scope;
- flow-to-PCAP matching method; and
- license/citation notice.

The official CSE page identifies the dataset as redistributable with citation and links its AWS source. The actual local storage requirement must be measured from the selected files; the full archive is explicitly outside this MVP scope.
