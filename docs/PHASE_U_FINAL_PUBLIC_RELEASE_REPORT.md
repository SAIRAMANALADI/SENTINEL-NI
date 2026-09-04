# Phase U — Final Public Release Report

Validation date: 2026-09-04  
Repository: `SIH26` / `sih26-26153`

This report is the final public open-source release gate for the current
working tree. It records evidence that was actually available and preserves
environment boundaries rather than upgrading them by inference.

## 1. Release version

The release line is **`v0.1.0`**, intentionally pre-1.0 because physical,
public-ingress, soak, and broader deployment validation remain incomplete.
`pyproject.toml`, frontend metadata, changelog, release notes, README release
references, and the public manifest agree on `0.1.0`. The independently
versioned Sentinel Agent CLI is `0.2.0`; telemetry protocol/schema versions are
both `1`.

## 2. Product definition

Sentinel / NI is an out-of-band network-security forecasting and operator
decision-support platform. It converts observed network activity into fixed
10-second states, applies the existing frozen LSTM path, and presents Forecast
Scores, Predictive Warnings, Candidate Sources where evidence supports them,
and Mitigation Recommendations.

Forecast Score is not a calibrated probability. Candidate Source is not
attacker attribution. Mitigation is human-reviewed and simulation-only.

## 3. Architecture

```text
Customer -> Company Application Server -> Response
                         |
                         +-- observed in parallel --> Sensor / Agent
                                                        |
                                                        +-- authenticated bounded telemetry --> Central Sentinel
                                                                                               |
                                                                                               +--> Dashboard
```

Customer requests do not pass through Sentinel. Sentinel is not a reverse
proxy. The browser communicates with Central Sentinel and does not register
agents or receive admin/runtime credentials. The primary product journey is
Overview → Sensors → Add Sensor → Sensor Detail → Forecast → Sources →
Mitigation; Replay/Demo is secondary.

## 4. Package status

Wheel and sdist builds passed. A fresh temporary virtual environment installed
the wheel without editable mode; package metadata, `sentinel-agent --help`, and
`sentinel-agent --version` (`0.2.0`) passed. The package audit inspected 95
wheel members and 185 sdist members and found no credential, key, runtime,
registry, log, cache, developer-path, test-artifact, or large generated-output
inclusion; the sdist intentionally includes source tests, not generated test
results. `pip check` passed in the current project validation environment.

The clean wheel smoke used `--no-index --no-deps`; a dependency-inclusive clean
environment installation is not claimed as a separate gate.

## 5. Frontend status

`npm run typecheck` and `npm run build` passed. Browser smoke of the rebuilt
dashboard visited Overview, Sensors, Add Sensor, Sensor Detail, Forecast,
Sources, Mitigation, and System. The Add Sensor endpoint field is explicit and
empty by default, with an HTTPS placeholder; it no longer misleadingly uses the
dashboard origin. Offline/stale/error states withheld forecast output and were
distinguished from healthy state. Replay produced labeled prepared-data output.

## 6. Agent status

The documented CLI groups exist and expose help: `init`, `register`, `start`,
`stop`, `restart`, `status`, `config`, `diagnostics`, and `service`. The
non-editable wheel smoke verified the installed CLI. Phase S verified the real
Windows foreground process lifecycle, including graceful `stop`, no remaining
matching process/request state, and restart with the same sensor identity.

## 7. Telemetry status

The actual Windows Wi-Fi/Npcap remote path registered through HTTPS, sent
heartbeat and bounded state telemetry, reached contiguous `L=10`, invoked the
existing direct `K=5` LSTM path, returned five forecast rows, and produced a
rolling update. Central validation retained sequence, duplicate, timestamp,
schema, feature, rate, and sensor-isolation boundaries. Six sensor identities
persisted across the local Compose down/up cycle; process-local runtime history
reset as documented.

## 8. Security status

Focused security and HTTPS enforcement tests passed. Production transport keeps
certificate verification; the validated flow used no insecure TLS bypass. The
central path uses short-lived one-time enrollment credentials, sensor-specific
runtime credentials, central hashing, bounded authenticated state payloads,
sequence/duplicate protection, validation, rate limits, and bounded buffers.
Raw packet payloads are not forwarded by the remote state path. OIDC, mTLS,
tenant isolation, HA, penetration testing, compliance certification, and
automatic response remain outside this release claim.

## 9. Test results

| Check | Result |
| --- | --- |
| Full Python suite | **PASS — 319 passed, 2 warnings** |
| Focused API/security/HTTPS/remote suite | **PASS — 30 passed, 2 warnings** |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS** |
| Wheel and sdist build | **PASS** |
| Installed CLI help/version smoke | **PASS** |
| Current environment `pip check` | **PASS** |
| Release audit | **PASS** |
| Internal link/path/obvious-secret scans | **PASS** |
| `git diff --check` | **PASS** |

## 10. Docker result

Docker Compose was available. `docker compose config -q`, restart, down/up,
health, readiness, frontend/dashboard availability, and final recovery passed.
Backend health and readiness returned HTTP 200. The final backend, dashboard,
and frontend services were healthy and loopback-bound. Registry identities
survived down/up. This is local Docker Desktop evidence, not public staging
capacity or production resilience evidence.

## 11. TLS result

Inherited Phase P/S isolated evidence passed: Nginx HTTPS termination, trusted
temporary private CA, wrong-CA rejection, hostname-mismatch rejection,
production HTTP rejection, and trusted-proxy behavior. Expired certificates,
public DNS/ingress, and public CA deployment were not available and are not
claimed.

## 12. Multi-host result

**NOT VERIFIED — PHYSICAL MULTI-HOST NOT VERIFIED.** No second physical host was
available. Local processes and six registry identities do not constitute Host A
→ Agent A and Host B → Agent B evidence, nor five-sensor staging evidence.

## 13. Soak result

**NOT VERIFIED — 30-MINUTE SOAK NOT VERIFIED.** No 30-minute CPU, memory,
packet-rate, flow-rate, telemetry, queue/buffer, log, or forecast-capacity
series was collected. Short real-path and lifecycle checks passed.

## 14. Customer-path result

**PASS.** An independent local customer HTTP service returned HTTP 200 while the
Sentinel backend was stopped and unreachable. The backend was then restarted
and recovered healthy. This verifies the out-of-band boundary for healthy and
unavailable central states in the local exercise; it is not a general customer
capacity or network-failure guarantee.

## 15. Secret scan result

The deterministic release audit passed and scanned tracked/current release text
for obvious secret markers, developer paths, broken links, protected-path
changes, and package member names. Current tracked sensitive-name review found
no credential/key/log files; intentionally tracked data/model fixtures remain
documented release inputs. A practical Git-history path and obvious-marker
review found no likely credential; one marker-matching historical commit was
the release-audit/documentation commit itself. This is not perfect historical
secret scanning.

**TruffleHog: NOT VERIFIED — TOOL NOT INSTALLED**.

## 16. Documentation result

**PASS.** README, LICENSE, SECURITY, CONTRIBUTING, CHANGELOG, release notes,
environment support, deployment guide, operator quickstart, agent installation
and operations, API/architecture/security/telemetry documents, and historical
release reports were reviewed. Public commands were checked against the
repository and CI: Python setup/tests, frontend `npm ci`/typecheck/build,
package build, release audit, Docker Compose, agent lifecycle, and Linux
service commands exist. Environment-dependent commands are labeled rather than
presented as normal CI requirements.

The canonical current files are the [Public Release Manifest](PUBLIC_RELEASE_MANIFEST.md),
[Final Public Release Checklist](FINAL_PUBLIC_RELEASE_CHECKLIST.md), and this
report. Older phase reports are retained as historical records and are not
used to override current Phase U status.

## 17. Model integrity

**PASS.** The Phase U protected-path review found no unintended changes to model
weights, inference, scaler, the 17-feature schema, target semantics, `L=10`,
`K=5`, or threshold `0.19`. The real Phase S forecast used the existing model
and returned exactly five direct horizons. No new feature, model, dataset, or
architecture was added for Phase U.

## 18. Exact PASS items

- Version and release-document consistency for the `0.1.0` project line.
- MIT license presence and package/README license references.
- README architecture and customer-request boundary.
- Primary dashboard and Add Sensor journey, including honest offline/stale behavior.
- Replay/Demo labeling and separation from live telemetry.
- Agent CLI installation/help/lifecycle surface.
- Real remote registration, heartbeat, telemetry, `ONLINE`, `L=10`, and `K=5` path.
- Forecast, source, terminology, and simulation-only mitigation semantics.
- Python tests, frontend typecheck/build, wheel/sdist, CLI smoke, and pip check.
- Package-content, tracked-path, obvious-secret, documentation-link, and
  protected ML/data audits.
- Docker Compose lifecycle, recovery, health/readiness, frontend, and registry persistence.
- Isolated TLS trust/rejection/proxy evidence.
- Independent customer-path availability during Sentinel backend outage.

## 19. Exact FAIL items

**None.** No release-gate check produced a failure. Unavailable environment
checks are listed separately as **NOT VERIFIED**, not converted into passes.

## 20. Exact NOT VERIFIED items

- TruffleHog: **NOT VERIFIED — TOOL NOT INSTALLED**.
- Physical multi-host and five-sensor deployment.
- 30-minute soak and resource/capacity series.
- Expired certificate behavior.
- Public DNS, public ingress, and public CA deployment.
- Physical Linux capture and service-manager boot/reboot behavior.
- Dependency-inclusive clean wheel install; only the non-editable wheel smoke
  and current-environment pip check are claimed.

## 21. Readiness classification

**OPEN-SOURCE RELEASE READY**

The evidence supports publishing the current code, package, documentation, and
known limitations as an open-source project. The evidence does not support
`STAGING READY` or `PRODUCTION READY WITH LIMITATIONS` because physical,
public-ingress, certificate-expiry, and sustained-capacity gates remain open.

## 22. Remaining blockers

There are no blockers to publishing the repository as an honest open-source
release candidate. Before calling Sentinel staging-ready or production-ready,
run TruffleHog, a second-host/five-sensor exercise, a 30-minute soak with
resource series, expired-certificate and public-ingress validation, and the
physical Linux/service-manager checks. Those are deployment-validation gates,
not reasons to add new architecture in Phase U.

## Final public-release decision

**Can Sentinel be publicly released as an open-source project? Yes —
OPEN-SOURCE RELEASE READY.**

This answer is limited to public code/package/documentation release. No Git tag,
commit, or push was created. Phase U stopped after its final gate; the later
Phase V preparation is recorded separately in
[PHASE_V_PUBLIC_RELEASE_REPORT.md](PHASE_V_PUBLIC_RELEASE_REPORT.md).
