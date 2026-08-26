# Production-Oriented MVP Architecture

## Runtime flow

TELEMETRY
   ↓
EVENT / STATE BUFFER
   ↓
NETWORK STATE
   ↓
FORECAST SERVICE
   ↓
SOURCE ATTRIBUTION
   ↓
MITIGATION POLICY
   ↓
API
   ↓
DASHBOARD

The current deployable boundary is a single-node production-like service. Mock
and replay adapters remain available for deterministic demonstrations, while
the live adapter supports metadata-only packet capture through Scapy/Npcap.
Live operation still requires a host interface with capture permission and is
not equivalent to a highly available production deployment.

## Component boundaries

- src/telemetry/: input adapters only; no model or policy logic.
- src/streaming/: state buffering, aggregation, replay, and source activity.
- src/forecasting/inference.py: frozen validation, preprocessing, K=5 model
  inference, policy application, and explanation.
- src/streaming/source_forecast.py: transparent source-priority calculations.
- src/evaluation/mitigation_policy.py: recommendation-only mitigation policy.
- src/api/: Pydantic contracts and FastAPI transport/service composition.
- app/streamlit_app.py: presentation client; Full Integrated Demo calls the
  backend /api/v1/demo endpoint.
- src/platform/: configuration, structured logging, audit, metrics, and
  service states.

## Failure boundaries

- Invalid telemetry is rejected before aggregation.
- Missing or incompatible model/schema/policy makes /api/v1/ready false and
  forecast requests return 503 SERVICE_NOT_READY.
- Invalid request shape, timestamps, feature sets, IPs, ports, NaN, and Inf are
  rejected with structured 422 errors.
- Source-priority failures do not change forecast output; they are reported as
  a source-analysis request failure.
- Mitigation is recommendation-only. No traffic blocking is executed.

## Trust boundaries

- API callers are untrusted and cross the bearer-token boundary when auth is
  enabled.
- Request bodies are validated by Pydantic and existing domain validators.
- The API does not accept a client-supplied filesystem path or shell command.
- Audit/log output is server-owned; secrets, tokens, and raw payloads are not
  written.
- Streamlit communicates with the backend using SIH_API_URL; it is not the
  model execution boundary for the integrated demo.

## Data contracts

- Frozen state contract: 10 chronological states, 17 numeric features, one
  capture day, 10-second intervals.
- Forecast target and threshold remain defined by the frozen target and policy
  documents.
- Packet source requests require timestamp, validated IPs, valid ports,
  protocol, packet length, and flags.
- Mitigation responses always include simulation_only=true and
  automatic_block=false.

## Current prototype limitations

- Live capture is host-dependent and requires Scapy/Npcap, an exact interface,
  and appropriate permissions; Docker Compose runs deterministic mock mode by
  default.
- PCAP attribution is not validated against the frozen flow artifact.
- In-process metrics are local to one process and are not a distributed
  monitoring backend.
- JSONL audit storage is append-only at the application layer, not a tamper-
  evident enterprise audit store.
- Authentication is configurable bearer/API-token auth, not an identity
  provider integration.
- Docker deployment is production-like packaging, not proof of production
  infrastructure, penetration testing, or high availability.
