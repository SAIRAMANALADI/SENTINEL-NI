# Phase K Public Release Report

## 1. Public product definition

Sentinel / NI is an out-of-band predictive network-security monitoring
platform. A local or remote Sentinel Agent observes network activity in
parallel with the customer application, sends authenticated aggregate
telemetry to Central Sentinel, and receives no customer requests in its path.
Central Sentinel builds 10-second network states, produces short-horizon
Forecast Scores, ranks Candidate Sources where the telemetry supports it, and
returns human-reviewed Mitigation Recommendations.

This release does not claim confirmed intrusion detection, calibrated
probabilities, automatic blocking, guaranteed prevention, or production
capacity.

## 2. Release structure

- Python package: `sih26-26153==0.1.0`.
- Remote Agent version: `0.2.0`.
- Network-state schema: `network-state-v1.0`.
- Telemetry schema/protocol: `1` / `1`.
- Model identifier: `LSTM-DEVELOPMENT-V1-direct-multistep-K5`.
- Operating policy: `operating-policy-v1`, primary threshold `0.19`.
- Distribution: wheel, sdist, or source install; frontend uses the checked-in
  npm lockfile.

The exact contract is in [RELEASE_MANIFEST.md](RELEASE_MANIFEST.md).

## 3. Package status

| Check | Result | Evidence |
| --- | --- | --- |
| Package metadata | PASS | `pyproject.toml` has name, version, description, MIT license, Python range, URLs, and entry point |
| Wheel and sdist | PASS | `.venv\\Scripts\\python.exe -m build --wheel --sdist` |
| Package contents | PASS | `scripts/release_audit.py --strict` inspected both `dist` artifacts; no raw data, PCAP, credential, or local-path members |
| Clean wheel import/CLI smoke | PASS | isolated venv installed wheel; `import src.agent` and `sentinel-agent --version` succeeded |
| Dependency consistency | PASS | `.venv` `pip check`: no broken requirements |

The source distribution intentionally contains source/tests/docs selected by
the packaging configuration but no runtime datasets, PCAP archives, local
registries, or developer-specific credentials.

## 4. Installation experience

The new-user path is documented in [README.md](../README.md),
[OPERATOR_QUICKSTART.md](OPERATOR_QUICKSTART.md), and
[DEVELOPMENT.md](DEVELOPMENT.md). It uses actual commands for Python setup,
central API startup, health/readiness checks, dashboard startup, enrollment,
agent registration, diagnostics, and lifecycle operations.

Known assumptions are explicit: Python 3.12–3.14, Node/npm for frontend work,
Npcap/libpcap and capture permission for live collection, a trusted HTTPS
endpoint for production agents, and Docker Desktop/Linux Engine for Compose
runtime validation.

## 5. Operator experience

The operator path is now explicit:

`Create Sensor -> Enrollment -> Install Agent -> Register -> Start -> Heartbeat -> Telemetry -> Forecast Ready`

The dashboard distinguishes Agent Health, Telemetry Health, and Forecast
Health. Empty states do not show invented telemetry or charts. The sensor empty
state says `No sensors connected yet.` and forecast waiting states explain that
valid network-state history is required.

## 6. Frontend readiness

- TypeScript typecheck: PASS (`npm run typecheck`).
- Production build: PASS (`npm run build`).
- Agent version is visible in sensor cards from the API contract.
- Central API, sensor, agent, telemetry, and forecast status are represented
  separately.
- Frontend browser validation with real sensors was not run in this environment.

## 7. Documentation audit

Added or updated:

- `docs/OPERATOR_QUICKSTART.md`
- `docs/ENVIRONMENT_SUPPORT.md`
- `docs/RELEASE_MANIFEST.md`
- `docs/DEVELOPMENT.md`
- `docs/RELEASE_NOTES.md`
- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`

The release audit scanned current public docs/scripts/frontend text, required
release files, internal Markdown links, obvious secrets, developer-local paths,
and protected-path changes. Result: `RELEASE_AUDIT=PASS`.

## 8. Security documentation

The repository links the security policy, security architecture, threat model,
credential lifecycle, TLS deployment, and agent security documents. The public
security policy now gives a private GitHub advisory path and requests version,
deployment mode, reproduction, impact, and redacted logs. No private contact
details or credentials are published.

The implementation remains bearer-token based and single-node. mTLS, OIDC,
tenant isolation, durable external audit, and HA are not represented as
implemented features.

## 9. CI status

The workflow at `.github/workflows/ci.yml` now covers:

- Python dependency installation and `pip check`.
- Strict release audit.
- Full pytest.
- Wheel/sdist build.
- Frontend `npm ci`, typecheck, and production build.
- Container image build.

These workflow changes are committed to the working tree but GitHub Actions
has not executed them from a new commit in this Phase K run. The equivalent
local checks listed below passed.

## 10. Release audit and scans

- Secret scan: PASS for the audit's intentionally narrow obvious-token/private-
  key patterns; this is not a complete secret scanner.
- Local path scan: PASS for tracked/current public text files; intentional
  placeholders and container service paths are excluded by rule.
- Documentation link scan: PASS.
- Protected model/data/forecasting diff: EMPTY.
- Git diff check: PASS; Git emitted only normal Windows line-ending warnings.
- No unsafe untracked runtime/sensitive artifact was reported by strict mode.
- The local workspace does contain intentionally ignored datasets, model
  outputs, build caches, frontend dependencies, and graph output; the audit
  reports these as non-commit candidates. They remain outside the public
  release and were not deleted.

## 11. Model/data integrity

The Phase K changes did not modify `data/raw/`, `data/processed/`,
`src/ingestion/`, `src/features/`, `src/forecasting/`, `src/models/`, the
frozen feature schema, target contract, L=10 context, K=5 horizons, threshold
`0.19`, checkpoints, or operating semantics. The protected diff is empty.

## 12. Exact automated checks

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **281 passed, 2 warnings** in 70.76s |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |
| `.venv\\Scripts\\python.exe -m build --wheel --sdist` | **PASS** |
| isolated wheel import/CLI smoke | **PASS** |
| `.venv\\Scripts\\python.exe -m pip check` | **PASS** |
| `.venv\\Scripts\\python.exe scripts/check_environment.py` | **PASS** |
| `python scripts/release_audit.py --strict` | **PASS** |
| `docker compose config --quiet` | **PASS** |
| `git diff --check` | **PASS** |
| `python -m src.agent --version/help` | **PASS** |

The two pytest warnings are existing dependency deprecation warnings from the
remote-agent HTTP test stack.

## 13. Environment-dependent checks

Not executed and not claimed as passed:

- Docker daemon startup, health, restart, and shutdown/recovery.
- Real staging reverse-proxy TLS, certificates, and DNS.
- Physical two-host sensor deployment.
- Five-sensor or 30-minute live soak.
- Long-duration host packet capture.
- Physical network outage/recovery.
- Browser workflow with real sensors.

The current `docker info` check confirms the Docker CLI is installed but the
Docker Desktop Linux engine is unavailable at
`npipe:////./pipe/dockerDesktopLinuxEngine`.

## 14. Known limitations

- Central remote histories and forecasts are process-local and rebuild after a
  central restart.
- Live capture depends on host permissions and Npcap/libpcap; Docker Compose
  does not provide arbitrary host capture capability.
- NetFlow/IPFIX listeners are not enabled; Zeek support is partial and not
  forecast-compatible without the required fields.
- Remote state-only telemetry cannot provide defensible packet-level source
  attribution.
- Windows native service installation, mTLS, OIDC, HA, tenant isolation,
  production capacity, and automatic enforcement remain outside v0.1.

## 15. Readiness classification

**OPEN-SOURCE RELEASE READY WITH ENVIRONMENT VALIDATION PENDING**

This classification is limited to reproducible source/package installation,
documented operator workflows, automated contract coverage, frontend/package
checks, and honest security/deployment boundaries. It is not `PRODUCTION
READY` and does not upgrade the unverified Docker, staging, multi-host, or live-
soak gates.

## 16. Recommended next phase

Run an administrator-approved staging validation with a live Docker Engine,
trusted TLS reverse proxy, at least two physical sensor hosts, and measured
five-sensor/30-minute soak. Keep the frozen data/model contracts unchanged and
record operational evidence before considering a production deployment claim.
