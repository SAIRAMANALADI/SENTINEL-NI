# Public Release Checklist

Validation date: 2026-09-04  
Candidate release: `v0.1.0`

Legend: **PASS** is verified in the stated environment; **NOT VERIFIED** is an
unavailable or unexercised environment gate; **N/A** is outside this release
scope. The owner must review this checklist before publishing.

**Current gate:** Phase AB is the current coordinator record. This checklist is
historical/local evidence only; publication is pending provenance reconciliation
and external validation. See [`PHASE_AB_FINAL_RELEASE_GATE_REPORT.md`](PHASE_AB_FINAL_RELEASE_GATE_REPORT.md).

## REPOSITORY

- **PASS** — README, LICENSE, SECURITY.md, CONTRIBUTING.md, and CHANGELOG.md exist.
- **PASS** — Public release manifest, release notes, Phase AB report, and
  final publication runbook exist; earlier phase reports remain historical.
- **PASS** — Architecture states that Sentinel observes out-of-band and is not a reverse proxy.
- **PASS** — Existing worktree and tags were inspected; no commit, tag mutation, or push was made. Existing `v0.1.0` points to an earlier commit.

## PACKAGE

- **PASS** — `sih26_26153-0.1.0-py3-none-any.whl` built.
- **PASS** — `sih26_26153-0.1.0.tar.gz` built.
- **PASS** — Wheel metadata reports package version `0.1.0`, MIT license, and `sentinel-agent` entry point.
- **PASS** — Non-editable wheel install and CLI help/version smoke passed in a fresh virtual environment.
- **PASS** — Current validation environment `pip check` passed.
- **NOT VERIFIED** — Dependency-inclusive clean installation; retrieval/installation of the full dependency set in a new environment was not completed.
- **PASS** — SHA256 checksums and artifact sizes recorded.
- **PASS** — Package contents contain no forbidden credentials, keys, runtime state, logs, caches, or large generated outputs.

## SECURITY

- **PASS** — Release audit, obvious-secret scan, path scan, link scan, and bounded Git-history review.
- **NOT VERIFIED** — TruffleHog: **NOT VERIFIED — TOOL NOT INSTALLED**.
- **PASS** — SECURITY.md routes vulnerabilities to private GitHub advisories and documents limitations.
- **PASS** — Public templates warn users not to disclose secrets or sensitive telemetry.

## DOCUMENTATION

- **PASS** — README-first installation and central → sensor → telemetry → forecast path reviewed.
- **PASS** — Release notes contain Added, Changed, Fixed, Security, Known Limitations, and Validation sections.
- **PASS** — Environment matrix distinguishes TESTED, SUPPORTED BUT NOT FULLY VERIFIED, NOT VERIFIED, and PLANNED.
- **PASS** — Public demo/replay and Forecast Score terminology are bounded honestly.
- **PASS** — External validation and issue triage guidance are published.

## FRONTEND

- **PASS** — First page is Overview; Replay is optional and secondary.
- **PASS** — Add Sensor does not fabricate registration, heartbeat, telemetry, or online state.
- **PASS** — Stale/offline/backend-outage states and forecast readiness are distinguished.

## AGENT

- **PASS** — Documented `init`, `register`, `start`, `stop`, `restart`, `status`, `config`, `config validate`, and `diagnostics` paths exist.
- **PASS** — Windows stop fix remains covered by prior real-path evidence and tests.

## TELEMETRY

- **PASS** — Real HTTPS enrollment, heartbeat, bounded telemetry, sensor isolation, and remote forecast path were verified.
- **PASS** — Privacy docs explain aggregated states, supported metadata, and no unnecessary raw packet payload forwarding.

## FORECAST

- **PASS** — `L=10`, `K=5`, 17 features, target, and threshold `0.19` remain documented.
- **PASS** — Forecast Score is not described as “19% probability.”
- **PASS** — Predictive Warning and Candidate Source semantics remain bounded.

## DOCKER

- **PASS** — Compose config, health/readiness, restart, down/up, frontend, and registry identity persistence.
- **NOT VERIFIED** — Public staging capacity or production resilience.

## TLS

- **PASS** — Isolated private-CA Nginx HTTPS, wrong CA, hostname mismatch, HTTP rejection, and trusted proxy.
- **NOT VERIFIED** — Expired certificate, public CA, public DNS, and public ingress.

## MULTI-HOST

- **NOT VERIFIED** — Physical Host A/Host B and five-sensor deployment.

## SOAK

- **NOT VERIFIED** — 30-minute resource and capacity series.

## PRIVACY

- **PASS** — Customer requests remain independent; agent sends bounded telemetry separately.
- **PASS** — Public issue guidance excludes tokens, credentials, private traffic, and PCAP contents.

## LICENSE

- **PASS** — Project-owned code is MIT licensed; dataset, PCAP, and model-artifact terms remain separate.

## PUBLICATION DECISION

**PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**.
The owner must complete the Phase AB provenance and external-validation gates
before publishing the source or artifacts.
