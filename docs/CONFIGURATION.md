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
| SIH_AUTH_ENABLED | false | Enable bearer-token auth |
| SIH_VIEWER_TOKEN | unset | Development-provided viewer token |
| SIH_OPERATOR_TOKEN | unset | Development-provided operator token |
| SIH_ADMIN_TOKEN | unset | Development-provided admin token |
| SIH_AUDIT_LOG_PATH | results/audit/events.jsonl | JSONL audit path |
| SIH_DEMO_EVENTS_PATH | data/samples/final_demo_events.csv | Demo-only fixture |
| SIH_API_URL | http://localhost:8000 | Streamlit backend URL |
| SIH_API_TOKEN | unset | Optional Streamlit bearer token |

When auth is enabled, at least one role token is required. Use a secret
manager/environment injection in deployment; never commit token values.
