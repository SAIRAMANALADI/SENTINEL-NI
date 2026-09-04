# Configuration

Configuration is loaded by src/platform/config.py from environment variables.
Relative paths resolve from the repository root. No credentials are stored in
source code.

| Variable | Default | Meaning |
|---|---|---|
| SIH_API_HOST | 0.0.0.0 | Bind host |
| SIH_API_PORT | 8000 | Bind port |
| SIH_MODEL_PATH | models/lstm_multistep_k5.pt | Frozen checkpoint |
| SIH_FEATURE_SCHEMA | configs/state_feature_schema.yaml | 17-feature schema |
| SIH_OPERATING_POLICY | configs/operating_policy.yaml | Frozen policy |
| SIH_LOG_LEVEL | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| SIH_TELEMETRY_MODE | replay | mock, replay, or explicitly enabled live |
| SIH_TELEMETRY_INTERFACE | unset | Exact discovered interface name required for live |
| SIH_TELEMETRY_REPLAY_PATH | data/samples/inference_demo_sequence.csv | Replay source |
| SIH_TELEMETRY_STALE_AFTER_SECONDS | 30 | Freshness window for live status |
| SIH_ENV | development | `development`, `test`, or fail-closed `production` |
| SIH_TRANSPORT_MODE | development_http (development), direct_https (production) | `development_http`, `direct_https`, or `trusted_proxy` |
| SIH_TRUSTED_PROXY_CIDRS | unset | Comma-separated proxy IP/CIDR values required by `trusted_proxy` |
| SIH_AUTH_ENABLED | false | Enable bearer-token auth; required in production |
| SIH_VIEWER_TOKEN | unset | Development-provided viewer token |
| SIH_OPERATOR_TOKEN | unset | Development-provided operator token |
| SIH_ADMIN_TOKEN | unset | Development-provided admin token |
| SIH_AUDIT_LOG_PATH | results/audit/events.jsonl | JSONL audit path |
| SIH_DEMO_EVENTS_PATH | data/samples/final_demo_events.csv | Demo-only fixture |
| SIH_API_URL | http://localhost:8000 | Streamlit backend URL |
| SIH_API_TOKEN | unset | Optional Streamlit bearer token |
| SIH_DASHBOARD_AUTH_ENABLED | false | Enable the Next dashboard's server-side role-token login/session boundary |
| DASHBOARD_SESSION_TTL_SECONDS | 28800 | In-memory dashboard session lifetime; accepted range is 300–86400 seconds |
| SIH_SENSOR_REGISTRY_PATH | results/sensors/registry.json | Central sensor registry; keep private and backed up |
| SIH_SENSOR_ENROLLMENT_TTL_SECONDS | 600 | Lifetime of one-time enrollment credentials |
| SIH_SENSOR_HEARTBEAT_TIMEOUT_SECONDS | 90 | Age after which a sensor is OFFLINE without heartbeat |
| SIH_SENSOR_RATE_LIMIT_PER_MINUTE | 60 | Per-sensor heartbeat/telemetry request limit |

When auth is enabled, all three role tokens are required: viewer, operator,
and admin. Use a secret manager/environment injection in deployment; never
commit token values.

For an internet-facing Next dashboard, set `SIH_DASHBOARD_AUTH_ENABLED=true`,
`SIH_AUTH_ENABLED=true`, and supply all three role tokens through deployment
secret injection. The dashboard accepts a role token only at its HTTPS login
route, stores an opaque `HttpOnly`, `SameSite=Strict` session cookie, and uses
the matching server-side role token when calling Central. The session store is
process-local and in-memory: a restart invalidates sessions, and multiple
frontend instances require sticky routing or a future shared session store.
`SIH_API_TOKEN` is retained only for the explicitly disabled local dashboard
fallback and is not an end-user authentication mechanism.
