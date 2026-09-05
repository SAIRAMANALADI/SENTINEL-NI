# Final Public Release Checklist

Validation date: 2026-09-04

**Current gate:** Phase AB is the current coordinator record. Treat this
candidate as unpublished and externally unvalidated until the Phase AB report
and approved external-validation gates are complete.

Legend: **PASS** means verified in the stated environment; **NOT VERIFIED**
means the gate was not available or not exercised; **N/A** means the item is
outside this release scope. No item below is a production-capacity claim.

## REPOSITORY

- **PASS** — MIT `LICENSE` exists and is referenced by package metadata and README.
- **PASS** — README explains the product, architecture, install, operation,
  terminology, evidence, and limitations.
- **PASS** — `SECURITY.md` explains reporting, supported release scope,
  security limitations, and sensitive telemetry handling.
- **PASS** — `CONTRIBUTING.md` explains environment setup, backend, frontend,
  agent, packaging, tests, release checks, and pull requests.
- **PASS** — `CHANGELOG.md` records the `0.1.0` release line and current gate work.
- **PASS** — Public release files are linked without duplicate canonical claims;
  historical phase reports remain clearly labeled as historical evidence.

## PACKAGE

- **PASS** — Wheel built successfully.
- **PASS** — Source distribution built successfully.
- **PASS** — Fresh virtual environment installed the wheel non-editably and
  verified package metadata plus `sentinel-agent --help/--version`.
- **PASS** — `pip check` returned `No broken requirements found` in the current
  project validation environment.
- **PASS** — Wheel/sdist content audit found no credentials, private keys,
  runtime state, registries, logs, caches, developer paths, generated
  test-result artifacts, or large generated outputs; source tests in the sdist
  are intentional.
- **PASS** — Package and frontend project versions are consistently `0.1.0`;
  agent CLI version is consistently `0.2.0`.

## CODE

- **PASS** — Full Python suite and Phase AB concurrency regressions; the exact
  current count is recorded in the Phase AB report.
- **PASS** — Focused security/HTTPS/remote-agent suite: `28 passed, 2 warnings`.
- **PASS** — Frontend typecheck.
- **PASS** — Frontend production build.
- **PASS** — `scripts/release_audit.py`.
- **PASS** — Current tracked-file obvious-secret and developer-path scans.
- **PASS** — Internal Markdown link scan through the release audit.
- **PASS** — `git diff --check` (no whitespace errors).
- **NOT VERIFIED** — TruffleHog; exact status: **NOT VERIFIED — TOOL NOT INSTALLED**.
- **PASS** — Protected ML/data freeze review found no current diff in model,
  forecasting, feature, preprocessing, or dataset contract paths.

## PRODUCT

- **PASS** — Central starts and exposes health/readiness.
- **PASS** — Add Sensor creates an enrollment path without exposing admin or
  runtime credentials to the browser.
- **PASS** — Agent install/init/register/start/status path is documented and CLI
  command groups exist.
- **PASS** — Heartbeat and bounded telemetry move from an actual agent to the
  central service; sensor health is not registration-only.
- **PASS** — Forecast is withheld until fresh telemetry and valid contiguous
  `L=10` history; real `K=5` forecast was observed in Phase S.
- **PASS** — Dashboard uses Forecast Score, Predictive Warning, Candidate Source,
  and Mitigation Recommendation semantics consistently.
- **PASS** — Replay/Demo is visibly secondary and labeled prepared/non-live.
- **PASS** — Mitigation remains recommendation-only with `simulation_only=true`.
- **PASS** — Customer requests remain independent of Sentinel.

## VALIDATION

- **PASS** — Docker Compose config, start, health, readiness, restart, down/up,
  frontend, telemetry/control-plane paths, and registry identity persistence.
- **PASS** — Local isolated TLS: valid private CA, wrong CA, hostname mismatch,
  HTTP rejection, and trusted-proxy behavior.
- **NOT VERIFIED** — Physical multi-host/five-sensor deployment.
- **NOT VERIFIED** — 30-minute soak and resource/capacity series.
- **PASS** — Customer HTTP path remained available during Sentinel backend outage.
- **NOT VERIFIED** — Expired certificate and public ingress/public CA.
- **NOT VERIFIED** — Physical Linux capture and service-manager boot/reboot.
- **N/A** — NetFlow/IPFIX listeners; these are planned extension points, not
  required for this release.

## DECISION

**PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**. The repository is
internally ready for the documented external-validation handoff, subject to
the limitations in the manifest and Phase AB report. This does not claim
staging readiness, production capacity, or universal platform support.
