# Sentinel / NI v0.1.0 Release Notes

This is the v0.1.0 public release candidate record. Phase V validation was
performed in the shared Windows development environment. The
release classification is **CONDITIONAL CANDIDATE — PUBLICATION PENDING
PROVENANCE RECONCILIATION**; it is not a staging or production-capacity claim.

The current gate is recorded in the [Phase Z external validation report](PHASE_Z_EXTERNAL_VALIDATION_REPORT.md).

The canonical release contract is the
[Public Release Manifest](PUBLIC_RELEASE_MANIFEST.md). The complete final gate
is recorded in the [Phase U Final Public Release Report](PHASE_U_FINAL_PUBLIC_RELEASE_REPORT.md)
and [Phase V Public Release Report](PHASE_V_PUBLIC_RELEASE_REPORT.md). Artifact
hashes are in [RELEASE_ARTIFACT_SHA256SUMS.txt](RELEASE_ARTIFACT_SHA256SUMS.txt).

## Added

- Out-of-band Central Sentinel and Remote Sentinel Agent operating model.
- Versioned 10-second network-state contract with 17 flow-derived features.
- Frozen L=10, direct K=5 forecast serving path and recommendation-only policy.
- Replay, mock, local live, remote-agent, and partial Zeek telemetry paths with
  explicit capability boundaries.
- Per-sensor enrollment, authentication, heartbeat, bounded buffering, retry,
  and isolated runtime histories.
- FastAPI control/data plane and Next.js plus Streamlit operator surfaces.
- Python wheel/sdist packaging, dependency locks, Docker Compose definition,
  operator documentation, security policy, and open-source CI.

## Changed

- Made the public release manifest, release checklist, external-validation
  workflow, and issue-triage policy explicit and linked from the README.
- Added safe public issue intake for bugs, features, deployment problems, and
  security-report routing.

## Fixed

- Clarified the first-run path so users land on Overview and can choose Replay
  as an optional, clearly labeled evaluation path.
- Clarified package-install scope: the clean wheel smoke is non-editable, while
  dependency-inclusive installation remains separately unverified.

## Security

- Security reports must use the private advisory route in `SECURITY.md`; public
  issue templates explicitly instruct users not to disclose vulnerabilities,
  tokens, credentials, private traffic, or PCAP contents.
- The release audit, package-content audit, path scan, link scan, and Git-history
  review remain separate evidence from the unavailable TruffleHog scan.

## Validation

- Python regression, sensor, security, telemetry, API, remote-agent, and
  dashboard authorization contracts (`323 passed`, `2 warnings`).
- Frontend typecheck, production build, and local runtime smoke of the primary
  operator journey; independent browser validation remains pending.
- Wheel/sdist build, clean non-editable wheel installation, CLI command smoke,
  and package-content audit.
- Docker Compose configuration, health, restart, down/up, and registry
  identity persistence on the local Docker Desktop runtime.
- Real Wi-Fi/Npcap remote capture through the isolated HTTPS reverse proxy,
  contiguous `L=10` readiness, existing `K=5` inference, five forecast rows,
  rolling forecast update, and graceful Windows agent stop.
- TLS trust, wrong-CA, and hostname-mismatch behavior through the local
  private-CA reverse-proxy exercise.
- Independent customer HTTP service availability while Sentinel was stopped.

Exact current results are recorded in
`docs/PHASE_Y_RELEASE_PROVENANCE_REPORT.md`; Phase V, U, and earlier phase
reports remain historical records.

## Known Limitations

- A second physical host, five-sensor deployment, 30-minute soak, and resource
  capacity time series.
- Expired-certificate behavior, public DNS/ingress, and a public CA deployment.
- Linux physical capture/service-manager boot behavior and Windows native
  service installation.
- Production-capacity, HA, OIDC, mTLS, tenant isolation, or automatic-response
  claims.
- TruffleHog scanning: the executable was not installed in this environment;
  repository release-audit and focused security checks are separate evidence.

## Operating truth

Sentinel observes traffic in parallel. Customer requests do not pass through
Sentinel. Forecast Score is a raw model score, Predictive Warning is an
operating-policy outcome, Candidate Sources are evidence-based rankings where
telemetry supports them, and Mitigation is a human-reviewed recommendation.
