# Telemetry Source Implementation Report

## Scope

Phase H adds a common collector boundary and source capability contract without
changing the frozen model, 17 features, scaler, target, L=10, K=5, threshold,
operating policy, or state pipeline.

## Architecture

`TelemetryAdapter` now provides bounded `read_events` in addition to the
existing lifecycle/read/status methods. `CollectorRegistry` maps explicit
`SourceType` values to adapters. `ScapyCollector` is a compatibility wrapper
around the existing live capture implementation; it does not duplicate packet
processing.

## Source status

- Local Scapy capture: IMPLEMENTED and state-compatible.
- Remote Agent: IMPLEMENTED through the existing authenticated state contract
  and sensor-scoped runtime.
- Replay: IMPLEMENTED.
- Mock: IMPLEMENTED for tests/demos only.
- Zeek `conn.log`: PARTIAL; parser implemented, state compatibility denied
  honestly because required packet/IAT/flag fields are absent.
- NetFlow/IPFIX: PLANNED / UNSUPPORTED; no fake listeners or decoders.

## API and frontend

Local telemetry status and remote sensor summaries expose `source_type`,
`source_status`, `source_capabilities`, `last_event`, and `last_telemetry` when
provided. Sensor Detail renders these fields without exposing credentials or
collector configuration.

## Security and deployment

The customer application remains out of band. Local capture is host-native;
remote agents push state telemetry; Zeek is an external log source; and
NetFlow/IPFIX remain private-network extension points. See the source security
and integration guides.

## Verification

Focused source tests cover collector registration, bounded reads, capabilities,
unsupported sources, Zeek JSON/TSV parsing, malformed/missing fields,
timestamps, partial writes, rotation, duplicates, late data, and path bounds.
The focused collector/Zeek suite passed: 14 tests. The focused
source/remote-regression slice passed: 21 tests. The full regression suite
passed: 281 tests with 2 existing dependency deprecation warnings.

Frontend typecheck and production build passed. Python wheel and sdist build
passed, `pip check` passed, `docker compose config --quiet` passed, and
`git diff --check` passed. Docker runtime validation was blocked because the
Docker daemon was not running on the host. The protected model/forecasting,
feature, ingestion, dataset, schema, and target paths had no diff.

## Performance and limitations

No production-scale performance claim is made. The Zeek reader is bounded and
tested functionally, but no representative production-rate benchmark or
multi-host soak was performed in this phase. Zeek `conn.log` alone cannot feed
the frozen forecasting pipeline; NetFlow/IPFIX require a future protocol and
security design.

## Future work

Add a separately validated Zeek feature source if full state compatibility is
required, then implement a selected NetFlow/IPFIX protocol with explicit
exporter security and resource limits. Any future source must converge on the
existing state contract rather than introduce source-specific model inputs.
