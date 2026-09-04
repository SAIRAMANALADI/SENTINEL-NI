# Source Telemetry Privacy

## Scope

Sentinel source telemetry is optional, metadata-only network observation. It
supports operator review of **Candidate Sources**; it does not identify a
person, process, organization, or confirmed attacker.

The customer application traffic does not pass through Sentinel. The remote
agent observes packet metadata on the configured host and sends bounded,
authenticated 10-second source-activity rows alongside the existing network
state telemetry.

## Collected fields

The source schema contains source/destination IPs, transport ports, protocol,
packet and flow counts, byte counts, destination cardinalities, packet-size
and inter-arrival summaries, TCP flag counts, and rates. Payload bytes and raw
packet objects are not retained or transmitted.

`source_ip` is an observed network endpoint. It must be presented as a
Candidate Source and must not be relabeled as “attacker” without separate,
validated evidence.

## Identity and isolation

Every source row is inside a versioned telemetry envelope authenticated by the
registered sensor credential. The enclosing `sensor_id` is the ownership
boundary. Central runtime history, freshness, ranking, first/last-seen values,
and recommendations are maintained independently per sensor; there is no
cross-sensor actor correlation.

## Retention and controls

- source history in the central runtime is bounded to 512 rows per sensor;
- source rows are bounded per telemetry batch and per 10-second window;
- the agent queue is bounded and uses the existing disk buffer/retry path;
- timestamps distinguish event interval time from central receipt time;
- source telemetry is validated for IPs, finite non-negative values, 10-second
  alignment, duplicate source/window rows, and oversized lists;
- mitigation output remains recommendation-only with `simulation_only=true`;
- Sentinel does not automatically block, firewall, intercept, or rewrite
  customer traffic.

## Availability states

The API distinguishes `NO_SOURCE_ATTRIBUTION`,
`SOURCE_ATTRIBUTION_AVAILABLE`, `SOURCE_DATA_STALE`, and
`NO_CANDIDATE_SOURCES`. Transport failure is surfaced by the existing central
API/backend availability state rather than being represented as source data.
