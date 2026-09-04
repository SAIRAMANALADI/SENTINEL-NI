# Phase N Source-Identity Telemetry Report

## Outcome

Phase N adds an optional source-intelligence path beside the frozen V1/V0.1
forecasting path. It does not modify model weights, the LSTM architecture, the
17 features, the target, L=10, K=5, threshold 0.19, or the existing local,
replay, and mock modes.

## Implemented path

`packet metadata -> AgentCollector -> 10-second source activity -> authenticated
TelemetryBatcher -> POST /api/v1/telemetry -> per-sensor RemoteSensorRuntime ->
existing deterministic source prioritization -> API sensor detail -> Sources UI`

The existing state path continues independently:

`packet metadata -> FlowBuilder -> 10-second network state -> authenticated
telemetry -> per-sensor L=10 runtime -> existing forecast`

Source IP is not inserted into state features. Source rows are scoped by the
authenticated enclosing sensor ID.

## Ranking and output

Ranking reuses `src/streaming/source_forecast.py`. Reasons are measured from
flow growth, packet/byte rates, destination counts, port counts, and current
network forecast context. Results are deterministic and labelled Candidate
Source. Recommendation output reuses the existing mitigation policy and keeps
`simulation_only=true` and automatic blocking disabled.

The frontend supports source status, ranked source cards, a selected source
detail view with activity/trend/destination/port/reason/forecast context, and a
separate recommendation section. Sensor detail identifies the parent sensor.

## Validation performed

- Pydantic source envelope validation: version, IP, timestamps, fixed interval,
  finite/non-negative values, duplicate rows, and bounds.
- Remote runtime ranking, stale state, and sensor isolation tests.
- Remote API authenticated end-to-end source telemetry test.
- Existing source aggregation/prioritization, remote-agent, and sensor API
  regression tests.

## Known limitations

- source telemetry is available only when the agent has real endpoint/port
  metadata; aggregate state-only telemetry cannot reconstruct it;
- no cross-sensor correlation or identity resolution is performed;
- source history is bounded, so old source rows leave the in-memory view;
- no payload, process, user, organization, or confirmed-attacker attribution
  is produced;
- NetFlow/IPFIX ingestion is not implemented;
- source-only batches are not emitted when no state batch is available; rows
  remain bounded in the agent queue until the next state batch.
