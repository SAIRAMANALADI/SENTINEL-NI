# Changelog

## [0.1.0] - 2026-09-01

- Released the frozen 10-second network-state forecasting contract with the
  L=10, K=5 serving path.
- Added reproducible Python and frontend installation instructions, Docker
  Compose deployment guidance, security boundaries, and operational runbooks.
- Added validated live telemetry, replay, API, dashboard, and failure-recovery
  release evidence.
- Kept PCAP fusion, automatic blocking, enterprise identity, and high-
  availability deployment outside the v0.1 scope.

## [Unreleased]

The entries below describe the current working-tree release candidate. They
are not evidence that the existing `v0.1.0` tag or a GitHub release contains
these changes.

- Added the Phase U public release manifest, final checklist, and final report;
  refreshed the current release notes, checklist, environment support matrix,
  README journey, and deployment runbook with evidence-backed status.
- Added an explicit first-time operator path: Overview, Sensors, Add Sensor,
  Sensor Detail, Forecast, Sources, and Mitigation; Replay remains a labeled
  secondary walkthrough.
- Added a deterministic release audit for tracked-file hygiene, documentation
  links, obvious secret patterns, local paths, and frozen-path changes.
- Extended CI coverage to the frontend typecheck/build, package build, and the
  public release audit.
- Added package metadata and direct private security-advisory instructions.
- Documented that local Docker runtime, isolated TLS, browser smoke, and the
  real Windows remote forecast path pass, while public ingress, physical
  multi-host deployment, TruffleHog, and sustained live soak remain validation
  gates outside this environment.
- Added public issue templates, external-user validation guidance, issue triage
  policy, release artifact checksums, and a publication preparation report.
