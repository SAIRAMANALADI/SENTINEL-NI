# API Contract

Base path: /api/v1.

Health and readiness are public. With SIH_AUTH_ENABLED=true, forecast/model
requires viewer and source-priority/mitigation/demo/metrics require operator.
admin has all roles and can read the security contract.

Telemetry status is viewer-readable. Live start/stop controls are operator-only
and only work when the backend is explicitly configured for live mode.

## GET /health

Returns 200 while the process is responding:

{"status":"ok","service_state":"HEALTHY","request_id":"..."}

## GET /ready

Checks configuration, schema, policy, model dimensions/load, and telemetry
mode. Returns 200 when all checks pass and 503 otherwise. A not-ready body
contains ready=false, checks, reasons, and an explicit service state.

## GET /model

Returns the loaded model contract: model version, schema/target/policy
versions, 10-state sequence length, 17 features, 50-second horizon, score name,
and the configured threshold. Filesystem paths are not returned.

## POST /forecast

Request fields are sequence and optional top_n. The real request contains
exactly 10 state points and exactly the 17 feature names from
configs/state_feature_schema.yaml. The response reuses the frozen inference
output, including five Forecast Score rows and explanation/timing.

## POST /source-priority

Accepts validated packet events and optional forecast context. It calls the
existing source aggregation and prioritization modules and returns ranked source
records. It does not infer an attacker identity.

## POST /mitigation

Accepts source IP, priority, and measured priority points. It calls the existing
recommendation policy and returns simulation_only=true; no blocking action is
performed.

## POST /demo

Demo-only operator endpoint. It runs the configured deterministic event fixture
through the existing Full Integrated Demo engine. It is used by Streamlit and
is not a claim of live production telemetry.

## GET /metrics

Returns local counters and latency summaries for requests, errors, forecasts,
source analysis, mitigation, and demo runs.

## GET /telemetry

Returns mode, selected interface, lifecycle status, timestamps, event counters,
freshness, and safe source-activity counters. Raw packet contents are never
returned.

## POST /telemetry/start and POST /telemetry/stop

Operator-only explicit controls for live capture. Start requires
`SIH_TELEMETRY_MODE=live` and an exact `SIH_TELEMETRY_INTERFACE`. The service
reports permission, unavailable-backend, and stale states without crashing the
application.

## GET /security-contract

Admin-only read-only statement of API safety boundaries.

## Error contract

All handled errors include an error object with code, message, request_id, and
optional details. Codes include VALIDATION_ERROR, CONTRACT_ERROR,
AUTHENTICATION_REQUIRED, INVALID_TOKEN, INSUFFICIENT_ROLE, and
SERVICE_NOT_READY. Invalid timestamps, IPs, ports, NaN/Inf, wrong sequence
length, and wrong feature names are rejected. No raw request payload is logged.
