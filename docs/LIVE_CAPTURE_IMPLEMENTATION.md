# Live Capture Implementation

## Backend selected

The adapter uses Scapy's `AsyncSniffer` with the platform packet-capture
provider. On Windows this requires Npcap; on Linux it normally requires
libpcap and capture permissions. Scapy was selected because it provides
cross-platform interface discovery and packet-layer access while allowing the
adapter to keep only the approved metadata event fields.

The adapter does not enable payload storage, write PCAPs, or extract the
CSE-CIC-IDS2018 archive.

## Operating requirements

- Windows 11 or Linux host.
- Python dependency: `scapy>=2.5,<3`.
- Windows: install Npcap with the approved host security policy.
- Linux: install libpcap and grant the process the minimum capture permission.
- Set `SIH_TELEMETRY_MODE=live` explicitly.
- Set `SIH_TELEMETRY_INTERFACE` to an exact name returned by
  `python scripts/list_capture_interfaces.py --json`.
- Start capture through the operator API or dashboard control. Page load never
  starts capture.

## Interface selection

No interface name is hard-coded. Discovery reports the name, description,
address, and whether the capture backend can expose the interface. Discovery
does not open a capture.

## Failure behavior

The adapter reports `LIVE_READY`, `LIVE_RUNNING`, `LIVE_STOPPED`,
`LIVE_UNAVAILABLE`, `LIVE_PERMISSION_DENIED`, or `LIVE_ERROR`. A malformed or
unsupported packet is counted and discarded; it cannot terminate the service.
The API exposes safe counters and timestamps only.

## Integration boundary

Live events feed the existing `SourceActivityAccumulator` for source activity.
The frozen L=10/K=5 model still accepts the approved 17 flow-derived state
features. Raw packet metadata is not fabricated into those features, so live
source activity and live model inference remain explicitly separate until a
packet-to-state contract is approved.

## Container status

The current Docker Compose files intentionally do not add `privileged`, host
networking, device mappings, or capture capabilities. Live capture has not been
verified in the container and is therefore supported as host-level telemetry
only. Do not weaken the container security defaults to enable it.
