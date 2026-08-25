# Observability

The API emits JSON logs containing timestamp, level, logger, request ID,
endpoint, event type, duration, and error/model metadata. Tokens, passwords,
secrets, and raw traffic payloads are excluded.

The local in-process metrics registry exposes:

- request_count
- error_count
- validation_error_count
- contract_error_count
- forecast_count
- source_priority_count
- mitigation_recommendation_count
- demo_count
- request, inference, source-analysis, mitigation, and demo latency summaries

Read them from GET /api/v1/metrics with operator authorization when auth is
enabled. Metrics are process-local and reset on restart; this is an MVP
observability boundary, not a Prometheus or distributed tracing deployment.

