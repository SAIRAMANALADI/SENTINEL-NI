# Sentinel / NI Public Release Manifest

Validation date: 2026-09-04

This is the canonical public release manifest for the current repository.
It describes the open-source code boundary and the evidence available on the
validation host. It is not a staging-capacity, production-certification, or
universal-platform-support claim.

**Current gate:** Phase AB is the current coordinator record. This repository
contains base commit `db8886fa2d25867b34d3d658901f32ef16e638f8` plus the
uncommitted Phase AB working-tree candidate, which is not a published or
externally validated release. Publication remains
pending the required external validation and human release approval.

## Release identity

| Item | Value | Status |
| --- | --- | --- |
| Project release candidate | `v0.1.0` | **IMPLEMENTED / TESTED — NOT PUBLISHED** |
| Candidate source revision | `db8886fa2d25867b34d3d658901f32ef16e638f8` + Phase AB working-tree delta | **UNCOMMITTED CANDIDATE; TAG MAPPING PENDING** |
| Python package | `sih26-26153==0.1.0` | **IMPLEMENTED / TESTED** |
| Agent CLI | `0.2.0` | **IMPLEMENTED / TESTED** |
| Telemetry protocol/schema | protocol `1`, schema `1` | **IMPLEMENTED / TESTED** |
| Network-state schema | `network-state-v1.0` | **IMPLEMENTED / TESTED** |
| Model | `LSTM-DEVELOPMENT-V1-direct-multistep-K5` | **IMPLEMENTED / TESTED** |
| Operating policy | `operating-policy-v1`, threshold `0.19` | **IMPLEMENTED / TESTED** |
| License | MIT for project-owned code | **IMPLEMENTED / TESTED** |

The project deliberately remains pre-1.0. The package, frontend, changelog,
release notes, and public documentation use `0.1.0`; the independently
versioned agent CLI remains `0.2.0`.

## Product boundary

Sentinel is an out-of-band network-security decision-support platform. A
sensor or remote agent observes traffic on the monitored host, builds bounded
state telemetry, and sends that telemetry to Central Sentinel. Customer
requests remain on the customer application path. Sentinel is not a reverse
proxy, does not delay or forward customer requests, and does not automatically
block traffic.

| Product term | Meaning | Status |
| --- | --- | --- |
| Forecast Score | Raw model score for each of five future horizons; not a calibrated probability | **IMPLEMENTED / TESTED** |
| Predictive Warning | Operating-policy outcome when the configured boundary is met | **IMPLEMENTED / TESTED** |
| Candidate Source | Evidence-based source ranking only where telemetry supports it; not attacker attribution | **IMPLEMENTED / TESTED** |
| Mitigation Recommendation | Human-reviewed, simulation-only recommendation; no firewall mutation | **IMPLEMENTED / TESTED** |
| Replay | Deterministic prepared-data demonstration, visibly labeled as demo mode | **IMPLEMENTED / TESTED** |

The existing annotated `v0.1.0` tag points to an earlier commit. It is
preserved unchanged; publication requires an owner-approved source revision
and non-ambiguous tag mapping.

## Frozen serving contract

- Fixed 10-second state cadence.
- Exactly 17 numeric flow-derived features in the approved schema order.
- Ten chronological states (`L=10`) are required before forecast output.
- Five direct horizons (`K=5`): +10s, +20s, +30s, +40s, and +50s.
- `future_attack_state(t)` is the approved next-state target within the same
  capture day; terminal states are unavailable rather than fabricated.
- Threshold `0.19` is an operating-policy boundary, not “19% probability.”
- Mitigation remains `simulation_only=true` and recommendation-only.

No unintended changes were found in model weights, inference, scaler, feature
schema, target, `L=10`, `K=5`, or threshold `0.19` during the release gates;
the Phase AB protected-path review remains the current record.

## Environment matrix

The detailed matrix is maintained in
[Environment Support](ENVIRONMENT_SUPPORT.md). The release-level summary is:

| Environment or capability | Classification | Evidence boundary |
| --- | --- | --- |
| Windows agent | **TESTED** | Windows 11 / Python 3.14, Scapy/Npcap capture, real remote forecast path, graceful stop |
| Linux agent | **SUPPORTED BUT NOT FULLY TESTED** | Platform-neutral package and documented libpcap/systemd path; physical host/service boot not verified |
| Central Docker Compose | **TESTED** | Local Docker Desktop config, health, readiness, restart, down/up, frontend, and registry identity persistence |
| Npcap | **TESTED** | Real Wi-Fi capture through the remote agent |
| libpcap | **SUPPORTED BUT NOT FULLY TESTED** | Documented Linux prerequisite; no physical Linux capture run |
| Nginx reverse proxy | **TESTED** | Isolated localhost HTTPS proxy path |
| TLS | **TESTED LOCALLY** | Private CA trust, wrong CA, hostname mismatch, HTTP rejection, trusted-proxy behavior; public ingress/expiry not verified |
| Remote agent | **TESTED** | Enrollment, registration, heartbeat, bounded telemetry, online state, `L=10` readiness, and `K=5` forecast |
| Physical multi-host/five sensors | **NOT VERIFIED** | No second physical host was available |
| Zeek | **IMPLEMENTED PARTIAL / TESTED CONTRACT** | JSON-lines/TSV normalization exists; input is not forecast-compatible without required fields |
| NetFlow | **PLANNED** | No enabled listener |
| IPFIX | **PLANNED** | No enabled listener |

Release artifacts and their SHA256 values are recorded in
[Release Artifact Checksums](RELEASE_ARTIFACT_SHA256SUMS.txt). An existing
annotated `v0.1.0` tag points to an earlier commit, not the current candidate;
the owner must resolve that mapping before publication. Publication and tag
mutation remain owner-controlled and were not performed by this phase.

## Implemented capabilities

- Central FastAPI API with health/readiness, sensor control plane, telemetry
  validation, isolated sensor histories, and forecast endpoints.
- Next.js dashboard with Overview, Sensors, Add Sensor, Sensor Detail,
  Forecast, Sources, Mitigation, and clearly secondary Replay/Demo.
- Remote Sentinel Agent CLI: `init`, `register`, `start`, `stop`, `restart`,
  `status`, `config`, `diagnostics`, and `service` command groups.
- Short-lived enrollment credentials, sensor-specific runtime credentials,
  authentication, sequence/duplicate checks, feature validation, bounded
  buffering, retry, heartbeat, and explicit stale/offline health.
- Local live, remote sensor, replay, mock, and partial Zeek source paths with
  bounded capability declarations.
- Wheel/sdist packaging, locked dependencies, Docker Compose, MIT license,
  security policy, contributing guide, CI, and operator runbooks.

## Tested evidence

- `py -m pytest -q`: **323 passed, 2 warnings**.
- Focused dashboard authorization contract tests: **6 passed**; existing API/security/remote tests are included in the full suite.
- Frontend `npm run typecheck`: **PASS**; `npm run build`: **PASS**.
- `py -m build`: wheel and sdist **PASS**.
- Fresh virtual environment, non-editable wheel install, package metadata,
  `sentinel-agent --help`, and `sentinel-agent --version`: **PASS**.
- Current environment `pip check`: **PASS** (`No broken requirements found`).
- `py scripts/release_audit.py`: **PASS**.
- Docker Compose config, health/readiness, restart, down/up, and final healthy
  services: **PASS**.
- Browser smoke of the primary journey and labeled Replay/Demo: **PASS**.
- Independent customer HTTP service remained available while Sentinel backend
  was stopped: **PASS**.
- Real Windows Wi-Fi/Npcap agent path reached contiguous `L=10`, existing
  LSTM `K=5`, five forecast rows, rolling update, and graceful stop: **PASS**.

## Security and release hygiene

- Release audit covers required release files, tracked obvious-secret patterns,
  developer-local paths, documentation links, protected ML/data changes, and
  package member names.
- Current tracked-source/package audit found no credentials, private keys,
  runtime registry, logs, caches, developer paths, or large generated output
  in wheel/sdist contents; the source distribution intentionally contains the
  source test suite, but no generated test-result artifacts.
- Git-history review was bounded to practical path and obvious-marker searches;
  it is not a guarantee of perfect historical secret discovery. The one
  matching historical commit was the release-audit/documentation commit, not a
  credential-bearing file.
- TruffleHog: **NOT VERIFIED — TOOL NOT INSTALLED**.
- Security limitations, reporting path, sensitive telemetry handling, and
  unsupported identity/compliance claims are documented in [SECURITY.md](../SECURITY.md).

## Known limitations

The following remain outside the evidence available for this release gate:

- Physical multi-host/five-sensor deployment.
- A 30-minute soak and CPU, memory, packet-rate, flow-rate, queue, log, and
  forecast-capacity series.
- Expired-certificate behavior, public DNS, public ingress, and public CA
  deployment.
- Physical Linux capture and service-manager boot/reboot behavior.
- TruffleHog scanning.
- HA, OIDC, mTLS, tenant isolation, automatic response, Windows native service
  installation, NetFlow/IPFIX listeners, and production capacity.

## Validation classification

**PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

This classification means the public code/package/docs boundary is coherent,
the available release checks pass, and limitations are explicit. It does not
promote the repository to `STAGING READY` or `PRODUCTION READY WITH LIMITATIONS`.
See the [Phase AB report](PHASE_AB_FINAL_RELEASE_GATE_REPORT.md) and
[final checklist](FINAL_PUBLIC_RELEASE_CHECKLIST.md) for the complete gate.
