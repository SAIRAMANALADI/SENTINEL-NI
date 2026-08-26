# SIH26-26153 Industry V2 Readiness Audit

**Audit date:** 2026-08-26  
**Audited revision:** `d3785ee` (`main`)  
**Verdict:** VALIDATED SINGLE-NODE PRODUCTION-LIKE SYSTEM; NOT YET INDUSTRY PRODUCTION READY

## Executive finding

SIH26-26153 is beyond a school prototype. It has a frozen data contract,
day-aware temporal evaluation, multi-step forecasting, live packet capture,
flow/state construction, a typed API, an operator dashboard, bounded runtime
state, audit records, and recommendation-only mitigation. The application test
suite passes.

The system is not yet safe to describe as an industry production platform.
Its largest gaps are reproducible delivery, production authentication, request
and resource controls, durable streaming, artifact loading, distributed
observability, high availability, and model/attribution governance.

## Evidence from this audit

| Check | Result | Evidence |
| --- | --- | --- |
| Git baseline | PASS | `main` and `origin/main` both point to `d3785ee` |
| Working tree isolation | PASS WITH LOCAL NOTE | Only `PCAP_HANDOFF_NOTICE.md` was untracked before this audit |
| Full tests after dependency reconciliation | PASS | 202 passed, 45 warnings, 78.25 seconds |
| First clean local test attempt | FAIL | FastAPI was declared but absent from the active virtual environment |
| Second local test attempt | FAIL | API test client dependency `httpx2` was not declared |
| Dependency consistency after local installation | PASS | `pip check` reported no broken requirements before the missing test dependency was discovered |
| Docker Compose rendering | PASS | `docker compose config` completed successfully |
| Docker runtime validation | BLOCKED | Docker Desktop daemon was not running during this audit |
| Secret-pattern scan | PASS | No matching committed plaintext token/private-key pattern was found |
| CI/CD | FAIL | No `.github` workflow directory exists |
| Reproducible dependency lock | FAIL | Broad version ranges only; no lockfile or dedicated development dependency set |

The 45 test warnings are joblib/NumPy deprecation warnings. They are not test
failures, but they are a compatibility signal that must be resolved before a
future NumPy/joblib upgrade.

## What is already strong

- The V1 scientific contract is explicit: 10-second states, 17 model features,
  fixed temporal windows, and day-aware splits.
- Inference rejects wrong feature sets, wrong ordering, invalid timestamps,
  cross-day sequences, NaN, and infinity.
- API request models reject unknown fields and validate finite numeric values,
  IP addresses, ports, and sequence length.
- Live state storage and flow tables are bounded.
- Capture restart isolation and stale-forecast behavior are tested.
- Packet payload bytes are not retained by the live adapter.
- Mitigation remains recommendation-only and explicitly reports
  `simulation_only=true`.
- Structured logging avoids known secret-field names and uses request IDs.
- Raw data, processed data, checkpoints, PCAPs, secrets, and generated results
  are excluded from ordinary Git commits.

## Critical production gaps

### P0 — must be fixed before an exposed deployment

1. **Authentication is disabled by default.** Compose publishes the API on
   `0.0.0.0:8000` while `SIH_AUTH_ENABLED=false`. When disabled, every role
   dependency—including the admin contract—returns development access.
2. **Static bearer tokens are not enterprise identity.** There is no token
   expiry, rotation protocol, revocation, subject identity, tenant boundary,
   OIDC/OAuth2 integration, or per-user audit identity.
3. **No ingress protection exists.** There is no TLS termination, trusted-host
   policy, request-body limit, API rate limit, abuse control, or reverse-proxy
   security configuration.
4. **Request collections are not bounded everywhere.** Source-priority events
   and mitigation-source arrays have minimum lengths but no maximum lengths,
   allowing an authenticated caller to submit arbitrarily large bodies.
5. **Model artifacts are deserialized during requests.** Forecast inference
   reloads the checkpoint and joblib preprocessor for every call. The checkpoint
   uses `torch.load(..., weights_only=False)` and joblib uses pickle semantics.
   Artifacts must be trusted, integrity-checked, loaded once at startup, and
   never accepted from callers.
6. **The live callback/queue path is ambiguous.** The API consumes packet events
   through a callback while the adapter also enqueues every event. The API does
   not drain that queue, so it eventually fills and increments `dropped_count`
   even though callback processing can still succeed. Packet-loss reporting is
   therefore not operationally defensible in callback mode.
7. **No graceful application lifecycle owns the sniffer.** The API has no
   explicit lifespan/shutdown hook that guarantees live capture is stopped and
   runtime state is finalized during process termination.

### P1 — required for a reliable production service

1. **No automated delivery gate.** There is no CI workflow for tests, linting,
   type checking, secret scanning, dependency review, image scanning, or build
   verification.
2. **Environment reconstruction is not deterministic.** Runtime and test
   dependencies are mixed, broad ranges resolve to future versions, Python
   support is not enforced, and the documented installation path did not
   recreate a test-capable environment during this audit.
3. **Metrics memory grows without a bound.** `MetricsRegistry` stores every
   latency observation in Python lists for the process lifetime.
4. **Operational state is process-local.** Forecast history, counters, source
   activity, readiness, and live flow state disappear on restart and cannot be
   shared across workers.
5. **Audit storage is not durable or tamper-evident.** JSONL append logging is
   useful locally but has no rotation, retention enforcement, integrity chain,
   remote replication, access policy, or analyst identity.
6. **Container hardening is incomplete.** The image runs as root, has no
   multi-stage dependency boundary, uses broad package resolution during build,
   and Compose has no resource limits, restart policy, read-only root filesystem,
   capability drop, or production secrets mechanism.
7. **Model loading is duplicated.** Readiness loads a model, then each forecast
   loads it again. This increases latency and makes readiness different from the
   actual serving object.
8. **No load, soak, or chaos evidence exists.** Unit and integration coverage is
   substantial, but there is no verified sustained packet rate, API concurrency,
   memory plateau, restart recovery time, or dropped-event SLO.

### P2 — required for a mature security product

1. **No model registry or signed artifact manifest.** Model, preprocessor,
   feature schema, threshold policy, training metadata, and checksums are not
   promoted as one immutable deployable release.
2. **No drift or data-quality monitoring.** The service does not track feature
   drift, state completeness, forecast-score drift, warning rate, missing
   intervals, or capture-distribution changes against approved baselines.
3. **No feedback/incident lifecycle.** Warnings cannot be acknowledged,
   assigned, investigated, resolved, suppressed, or linked to retained evidence.
4. **Source attribution remains unverified.** Source priority is transparent
   operational ranking, not proof of attacker identity. The current combined
   flow export still cannot be defensibly joined to a PCAP member.
5. **Scientific generalization remains limited.** The frozen model uses four
   capture days and one unseen final test day. Passing software tests does not
   establish broad operational forecasting performance.
6. **Documentation has drifted.** `PRODUCTION_ARCHITECTURE.md` still describes
   live capture as unimplemented even though the repository now contains a live
   adapter and runtime integration.

## Industry-safe product claim

The defensible current claim is:

> SIH26-26153 is a tested, single-node, production-like network-state
> forecasting and analyst-decision demonstrator with live capture support and
> recommendation-only mitigation.

Do not claim high availability, enterprise authentication, calibrated attack
probability, confirmed attacker attribution, autonomous blocking, or general
production readiness until the corresponding V2 gates pass.

## Non-negotiable boundaries

- Preserve the frozen V1 dataset, target, feature schema, and day-aware split.
- Never call the Forecast Score a calibrated probability unless calibration is
  separately demonstrated and approved.
- Never label source priority as confirmed attacker attribution.
- Never enable automatic mitigation from the current evidence path.
- Never fabricate packet fields or PCAP-to-flow joins.

