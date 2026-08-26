# SIH26-26153 Industry V2 Roadmap

**Roadmap date:** 2026-08-26  
**Starting revision:** `d3785ee`  
**Scientific baseline:** Frozen Flow/State V1 remains unchanged

## V2 objective

Turn the current single-node production-like demonstrator into a secure,
reproducible, observable, failure-tolerant forecasting service that can be
operated by analysts without overstating model certainty or source identity.

V2 is an operational hardening program. It is not permission to change the
approved target, silently retrain the model, fabricate packet features, or
activate automatic blocking.

## Target architecture

```text
Privileged sensor agent
    -> bounded event transport
    -> durable stream / replay log
    -> flow and 10-second state service
    -> validated inference service
    -> forecast + source-priority evidence
    -> incident/event store
    -> analyst API and dashboard

Cross-cutting controls:
OIDC/RBAC | TLS | signed artifacts | audit integrity | metrics/traces/logs
```

The packet-capture process should eventually be separated from the inference
API. The sensor needs capture privileges; the forecasting service should not.
That boundary reduces blast radius and allows independent scaling and recovery.

## Phase 0 — reproducible engineering gate

Deliver:

- supported Python version policy aligned with the container runtime;
- separate runtime and development dependencies;
- fully pinned, hashable dependency lock;
- `pyproject.toml` for test, lint, formatting, and type-check configuration;
- `.env.example` containing names and safe placeholders only;
- CI for unit/integration tests, lint, type checks, secret scanning, dependency
  review, and Docker build;
- a clean-clone verification script that creates an environment and runs tests.

Acceptance gates:

- one documented command reconstructs a test-capable environment;
- all 202 existing tests pass from a clean checkout;
- missing runtime or test dependencies fail CI immediately;
- no raw data, model checkpoint, PCAP, result artifact, or secret enters Git.

## Phase 1 — serving correctness and bounded resources

Deliver:

- startup-owned model/preprocessor/schema/policy bundle loaded exactly once;
- SHA-256 manifest and compatibility validation for every serving artifact;
- safe checkpoint format or restricted loading path that avoids arbitrary
  pickle execution where practical;
- explicit maximum request bytes, event count, mitigation-source count, and
  explanation size;
- bounded metrics summaries instead of unbounded latency lists;
- one live event-delivery mode: callback or queue, with truthful drop accounting;
- API lifespan hooks for capture stop, resource cleanup, and readiness changes;
- explicit backpressure and overload states.

Acceptance gates:

- repeated inference does not reload artifacts;
- memory reaches a stable plateau during a sustained test;
- queue saturation produces a tested, observable overload result;
- reported packet drops equal events actually rejected before processing;
- graceful shutdown stops capture and leaves no orphan sniffer.

## Phase 2 — security perimeter

Deliver:

- production configuration that fails closed when authentication is absent;
- OIDC/OAuth2 integration with viewer, operator, and admin scopes;
- per-user audit identity and token expiry/revocation;
- TLS at a documented reverse proxy or ingress boundary;
- trusted-host configuration, rate limits, request-size limits, and secure
  response headers;
- production secrets injection and rotation procedure;
- disabled or protected API documentation in production;
- threat model covering sensor, API, dashboard, model supply chain, and audit
  storage.

Acceptance gates:

- no production profile starts with authentication disabled;
- anonymous callers cannot access model, telemetry, forecast, metrics, or admin
  resources;
- operator and admin boundaries have negative tests;
- secrets are absent from images, logs, Git history, and generated reports;
- abuse tests demonstrate body-size and rate-limit enforcement.

## Phase 3 — observability and operational SLOs

Deliver:

- Prometheus-compatible counters, gauges, and bounded histograms;
- OpenTelemetry traces across API, state building, inference, and policy;
- dashboards for capture health, event acceptance, flow closure, state latency,
  buffer readiness, forecast latency, warnings, errors, and restart count;
- alert rules for stale telemetry, flow-table saturation, dropped events,
  missing states, inference failure, and model-contract mismatch;
- structured log retention and redaction tests.

Acceptance gates:

- every forecast can be traced to model, schema, policy, request/session, and
  input-state timestamps without storing raw payloads;
- operators can distinguish no traffic, stale traffic, overload, model failure,
  and a valid no-warning forecast;
- service-level objectives are based on measured load-test evidence, not
  invented numbers.

## Phase 4 — durable real-time pipeline

Deliver:

- independent capture/sensor process;
- durable event transport with sequence IDs and replay support;
- idempotent flow/state processing;
- persistent operational state needed for restart recovery;
- partitioning strategy that preserves host/day/stream boundaries;
- late, duplicate, out-of-order, and missing-event policy;
- dead-letter handling for invalid events.

Acceptance gates:

- process restart does not silently lose or duplicate accepted events;
- replay produces deterministic states and forecasts for the same artifact set;
- cross-day and cross-stream sequence creation remains impossible;
- failure injection demonstrates recovery without fake telemetry.

## Phase 5 — MLOps and model governance

Deliver:

- immutable model release manifest containing artifact hashes, data lineage,
  feature schema, target version, split definition, policy, metrics, and owner;
- model registry and promotion states: development, candidate, approved,
  deployed, retired;
- shadow deployment and rollback support;
- data-quality and feature/score drift monitoring;
- threshold-change approval and audit workflow;
- scheduled evaluation on newly acquired, eligible capture days.

Acceptance gates:

- deployment refuses an unsigned or incompatible artifact bundle;
- every production response identifies the exact approved release;
- model or threshold promotion cannot use the frozen final test day for tuning;
- rollback restores the previous full bundle, not only the model file.

## Phase 6 — attribution and PCAP evidence track

Deliver:

- preserve the 53.25 GB PCAP archive and verified inventory;
- obtain authoritative machine/IP/flow mapping metadata or declare fusion
  unsupported;
- extract only the smallest evidence-supported capture subset;
- build a separate packet-feature contract with provenance and matching
  confidence;
- validate packet/flow joins before any enriched model experiment.

Acceptance gates:

- every packet-derived feature traces to an exact archive member and extraction
  command;
- matching confidence and unmatched records are reported;
- no hostname, IP, attacker identity, or packet feature is guessed;
- the frozen V1 pipeline remains reproducible without PCAP enrichment.

## Phase 7 — production qualification

Deliver:

- hardened non-root container images and software bill of materials;
- vulnerability and image scanning gates;
- resource requests/limits, restart behavior, and deployment probes;
- load, soak, failover, and chaos tests;
- backup/restore and disaster-recovery runbooks;
- penetration test and remediation record;
- incident response, privacy, retention, and access-review procedures.

Acceptance gates:

- measured performance and capacity envelope is published;
- sustained operation shows bounded memory and controlled degradation;
- restore and rollback are demonstrated, not merely documented;
- all P0/P1 audit findings are closed with evidence.

## First engineering sprint

The first sprint should remain focused and should not change the model or data
contract.

1. Add deterministic runtime/development dependency definitions and a lock.
2. Add CI for tests, lint, type checks, secret scan, and Docker build.
3. Add a production configuration profile that requires authentication.
4. Cache and integrity-check the serving artifact bundle at startup.
5. Bound API collection sizes and metrics memory.
6. Correct live callback/queue accounting and add saturation tests.
7. Add lifespan shutdown handling for telemetry.
8. Reconcile architecture/runbook documentation with the implemented live path.

## Definition of industry-ready

The project may use the term **industry-ready** only when:

- clean-clone and CI evidence are green;
- the production profile fails closed;
- artifact integrity and model lineage are enforced;
- telemetry overload and restart behavior are measured;
- service resources remain bounded under soak testing;
- observability and analyst audit identity are operational;
- security testing and remediation are complete;
- model and source-attribution limitations remain visible in every relevant
  interface and runbook.

