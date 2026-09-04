# Phase V — Public Release Preparation Report

Validation date: 2026-09-04  
Candidate release: `v0.1.0`  
Agent version: `0.2.0`

This phase prepared the first public open-source release and an external-user
feedback loop. It did not publish to GitHub or PyPI, create a commit/tag, or
change the Sentinel architecture or frozen ML/data contract.

## 1. Release version

The release remains pre-1.0 at **`v0.1.0`**. Package metadata, frontend
metadata, changelog, release notes, public manifest, and release artifacts use
`0.1.0`. The independently versioned Agent CLI is `0.2.0`. No conflicting
project-release version was introduced.

## 2. Product definition

Sentinel / NI is an out-of-band network-security forecasting and operator
decision-support platform. Sensors observe network behavior, construct bounded
telemetry, and send it to Central Sentinel. The dashboard presents Forecast
Score, Predictive Warning, Candidate Source, and Mitigation Recommendation
views.

Forecast Score is not a calibrated probability. Candidate Source is not
attacker attribution. Mitigation remains human-reviewed and simulation-only.

## 3. Architecture

```text
Customer -> Company Application Server -> Response
                         |
                         +-- observed in parallel --> Sensor / Agent
                                                        |
                                                        +-- bounded telemetry --> Central Sentinel -> Dashboard
```

Customer requests do not pass through Sentinel. Sentinel is not a reverse
proxy. Remote agents send telemetry separately and never forward raw packet
payloads through the customer request path.

## 4. Package validation

Final local artifacts were rebuilt successfully:

- `sih26_26153-0.1.0-py3-none-any.whl` — 152,902 bytes, 95 members.
- `sih26_26153-0.1.0.tar.gz` — 165,713 bytes, 185 members.
- Package metadata reports version `0.1.0`, MIT license, and the
  `sentinel-agent` entry point.
- Package-content inspection found zero forbidden credential, key, runtime,
  registry, log, cache, path, PCAP, or dataset members. Source tests in the
  sdist are intentional; generated test results are excluded.
- SHA256 values are recorded in
  [`RELEASE_ARTIFACT_SHA256SUMS.txt`](RELEASE_ARTIFACT_SHA256SUMS.txt).

## 5. Installation validation

A fresh temporary virtual environment installed the wheel non-editably and
verified package metadata plus `sentinel-agent --help` and `--version`.
`pip check` passed in the current project validation environment.

The dependency-inclusive fresh-environment install was not completed after a
prior attempt exceeded the available command window. It is therefore **NOT
VERIFIED**, and no dependency-complete clean-install claim is made.

## 6. CLI validation

The documented command groups were checked: `init`, `register`, `start`,
`stop`, `restart`, `status`, `config`, `diagnostics`, and `service`. `config
validate` was also exercised. Root help and version output passed. Phase S
real-path evidence confirms the Windows `stop` fix stopped the foreground agent
without leaving a matching process, PID, or stop-request file.

## 7. Frontend validation

Frontend typecheck and production build passed. The first page is Overview;
Replay/Demo is optional and secondary. Browser smoke verified Overview,
Sensors, Add Sensor, Sensor Detail, Forecast, Sources, Mitigation, and System.
The Add Sensor flow does not fabricate registration, heartbeat, telemetry, or
online state and does not expose admin/runtime credentials to the browser.

## 8. Agent validation

The public path is documented as central start/create sensor, wheel install on
the remote server, `init`, `register`, `config validate`, `start`, and `status`.
The real Windows/Npcap path reached central registration, heartbeat, telemetry,
online state, contiguous `L=10` history, and the existing `K=5` forecast.

## 9. Telemetry validation

Authenticated state telemetry uses protocol/schema version `1`, per-sensor
sequence and duplicate protection, feature validation, capture-day checks,
bounded buffers, retry behavior, and isolated sensor histories. The agent sends
aggregated state and supported metadata rather than unnecessary raw packet
payloads. Zeek normalization is a tested partial path; NetFlow/IPFIX listeners
remain planned.

## 10. Forecast validation

The frozen serving contract remains 17 numeric features, ten chronological
states (`L=10`), and five direct horizons (`K=5`) at +10s through +50s. The
real remote path produced five forecast rows and a rolling update. Threshold
`0.19` is an operating-policy boundary; public wording never calls it “19%
probability.” Forecast output is withheld when the sensor is stale/offline or
does not have valid contiguous history.

## 11. Security

`SECURITY.md` documents private vulnerability reporting, supported releases,
security scope, telemetry sensitivity, and limitations without compliance
claims. Public issue templates warn against posting tokens, credentials,
private keys, private traffic, PCAPs, or customer data. Vulnerabilities are
routed to the private GitHub advisory process.

## 12. Docker

Local Docker Compose configuration, health/readiness, restart, down/up recovery,
frontend availability, telemetry/control-plane paths, and registry identity
persistence passed. Final backend, dashboard, and frontend services were
healthy. This is local runtime evidence, not staging capacity or production
resilience evidence.

## 13. TLS

Inherited local Nginx evidence passed for a trusted private CA, wrong CA,
hostname mismatch, production HTTP rejection, and trusted-proxy handling.
Expired certificates, public CA, public DNS, and public ingress remain
**NOT VERIFIED**.

## 14. Multi-host

**NOT VERIFIED.** No second physical host or five-sensor deployment was
available. Local processes and persisted sensor identities are not physical
multi-host evidence.

## 15. Soak

**NOT VERIFIED.** No 30-minute CPU, memory, packet-rate, flow-rate,
telemetry-throughput, buffer, log, or forecast-capacity series was collected.

## 16. Privacy

The public docs state that customer requests remain on the company application
path and telemetry is sent separately. Remote telemetry is bounded and state-
oriented; source/activity metadata is only emitted where the selected source
supports it. The docs do not promise zero collection of network identity
metadata when source intelligence is enabled.

## 17. Documentation

README, release notes, manifest, public checklist, Phase U report, environment
support, deployment guide, operator quickstart, agent installation/operations,
security, contributing, external validation, and issue triage documents are
present and internally linked. Public command paths were checked against the
repository and CI. The internal link scan remains part of `release_audit.py`.

## 18. Exact PASS

- `0.1.0` release identity and `0.2.0` Agent identity are consistent.
- Wheel/sdist build, metadata, entry point, checksums, sizes, and content audit.
- Non-editable clean wheel smoke, current-environment `pip check`, and CLI help/version.
- Full Python suite: **319 passed, 2 warnings**.
- Frontend typecheck/build and browser first-run/product journey.
- Real Windows Npcap agent registration, HTTPS telemetry, `ONLINE`, `L=10`, and `K=5` forecast.
- Forecast, Candidate Source, mitigation, privacy, and out-of-band terminology.
- Docker lifecycle/health/readiness and local TLS validation.
- Release audit, path/secret/link scans, and `git diff --check`.
- Public issue templates, external validation guide, and issue triage policy.

## 19. Exact FAIL

**None.** No completed gate failed. Unavailable or unexercised gates are listed
as **NOT VERIFIED**.

## 20. Exact NOT VERIFIED

- TruffleHog: **NOT VERIFIED — TOOL NOT INSTALLED**.
- Dependency-inclusive clean wheel installation.
- Physical multi-host/five-sensor deployment.
- 30-minute soak/resource/capacity series.
- Expired certificate behavior.
- Public DNS, public ingress, and public CA deployment.
- Physical Linux capture and service-manager boot/reboot.
- Production capacity, HA, OIDC, mTLS, tenant isolation, and automatic response.

## 21. Readiness classification

**OPEN-SOURCE RELEASE READY**. The source and artifacts are prepared for owner-
controlled public publication with the limitations above. This does not claim
`STAGING READY` or `PRODUCTION READY WITH LIMITATIONS`.

## 22. Release blockers

There are no blockers to publishing the project as an honest open-source
release candidate. The remaining environment gates block stronger staging or
production classifications, not source publication. The owner must review the
dirty worktree and intended release scope before publication.

## 23. Recommended external-validation workflow

1. Owner reviews the current diff and includes only intended source, docs,
   tests, templates, and release metadata; ignored data/build/runtime artifacts
   remain excluded.
2. Run the CI-equivalent Python, frontend, package, and release-audit checks.
3. Prepare a GitHub release titled **“Sentinel / NI v0.1.0 — First Public
   Open-Source Release Candidate”** using the prepared notes, artifacts, and
   checksum file. An existing `v0.1.0` tag points to an earlier commit; do not
   move or recreate it in this phase.
4. Attach the wheel, sdist, and SHA256 record. Do not upload credentials,
   private keys, runtime state, datasets, or PCAP archives.
5. Publish the repository/release only after owner approval, then invite users
   to follow [External Validation](EXTERNAL_VALIDATION.md).
6. Triage feedback using [Issue Triage](ISSUE_TRIAGE.md); route vulnerabilities
   privately, reproduce bugs, and make only evidence-backed narrow fixes.

## Final decision

**Can Sentinel be publicly released as an open-source project? Yes —
OPEN-SOURCE RELEASE READY.** Publication was prepared but not performed. No
commit, tag mutation, or push was made; the existing `v0.1.0` tag was preserved.
