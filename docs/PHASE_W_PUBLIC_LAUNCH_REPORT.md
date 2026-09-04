# Phase W — Public Launch and External Validation Report

Validation date: 2026-09-04  
Project: Sentinel / SIH26-26153  
Final classification: **BLOCKED**

This report records the release-coordinator result. It does not claim public
publication, public staging, or external-user validation.

## 1. Starting release state

**STATUS: PASS / PARTIAL.** Phase W started from the Phase V open-source
release candidate with project/package version `0.1.0`, Agent CLI version
`0.2.0`, 319 passing tests, passing frontend/package checks, local Docker/TLS
evidence, and no publication performed. The starting-state record is in
[`PHASE_W_RELEASE_SAFETY_REPORT.md`](PHASE_W_RELEASE_SAFETY_REPORT.md).

Phase W added one endpoint-level regression test, so the final suite contains
321 tests. No ML weights, preprocessing, feature schema, target, `L=10`,
`K=5`, threshold, or customer request path was changed.

## 2. Git state

**STATUS: BLOCKED for reproducible publication.**

- Branch: `main`.
- HEAD: `41dbec11a433370e28aa083274202b1f92ddd5c5`.
- HEAD subject: `Harden release validation and document V0.1 operations`.
- Tracked files: 416.
- Current worktree: 51 modified files and 39 nonignored untracked files; all
  existing changes were preserved.
- Remote: `origin` → `https://github.com/SAIRAMANALADI/SENTINEL-NI.git`.
- Existing tag: annotated `v0.1.0` points to
  `3798a588fc19461a766b7a2debba7e80be9529a3`, not the current HEAD.

The existing tag was not moved, deleted, recreated, or pushed. The current
candidate is therefore working-tree evidence, not a cryptographically tied
published release.

## 3. Repository audit

**STATUS: PASS with publication-scope PARTIAL.** The anonymous first-time-user
review covered README, installation, Central, dashboard, agent onboarding,
API/security docs, deployment, issue templates, release notes, limitations,
and links. The six required read-only specialist reviews completed with no
agent edits:

| Ownership | Result |
| --- | --- |
| Frontend / user journey | **PARTIAL** — fixed readiness-state conflation and mock labeling |
| Backend / API / runtime | **PARTIAL** — fixed exact remote feature-name validation and added endpoint regression coverage |
| Sensor agent / packaging | **PASS locally / external environment pending** |
| Security | **PARTIAL** — high-severity browser authorization gap remains open |
| QA / release validation | **PASS locally / reproducibility and external coverage pending** |
| Documentation / publication | **PARTIAL** — fixed stale instructions and made A–N protocol executable; Git/tag scope remains owner-controlled |

The release audit scanned 719 text files, 24 required release files,
and two package artifacts. It passed link/path/obvious-secret/package-member
checks. Ignored local artifacts were reported as warnings, not publication
inputs.

## 4. Clean installation result

**STATUS: PARTIAL.**

- Non-editable source installation in an isolated venv: **PASS**.
- Installed `sentinel-agent.exe --version`: **PASS**, reported `0.2.0`.
- Wheel and sdist build: **PASS**.
- Current environment `pip check`: **PASS**.
- Dependency-inclusive clean install from a fresh environment: **NOT
  VERIFIED**; the available validation window did not complete that network-
  and dependency-resolution claim. An external validator must create a fresh
  venv and run the lockfile installation from the clean checkout.
- Central startup, configuration validation, registration, telemetry, and
  forecast paths: **PASS locally** through the existing API/agent evidence and
  automated suite.

## 5. First-time-user journey result

**STATUS: PARTIAL.** The documented journey was exercised locally through
Overview, Sensors, Add Sensor, Sensor Detail, Forecast, Sources, Mitigation,
System, labeled Replay/Demo, central health/readiness, agent registration,
heartbeat, telemetry, contiguous `L=10`, existing LSTM `K=5`, five horizons,
agent stop/restart, and customer-path independence during central outage.

The dashboard’s Add Sensor page is intentionally an operator handoff surface:
it does not perform browser enrollment or expose the admin token. This is
documented, but an unrelated operator must still perform the server-side
enrollment and agent steps.

The local browser journey is **NOT VERIFIED as an external-user journey**.
The frontend has no configured browser component-test runner; its current
static contract tests and local manual smoke are not a substitute for an
unrelated browser/session environment.

## 6. Security review

**STATUS: PARTIAL; PUBLIC INTERNET-FACING DASHBOARD BLOCKED.**

Verified locally: role auth, one-time enrollment, hashed per-sensor runtime
credentials, sensor identity binding/isolation, HTTPS/trusted-proxy policy,
deny-by-default CORS behavior, validation and size/rate limits, security
headers, safe package contents, and no current-tree secret/private-key finding.

Open high-severity blocker: the Next dashboard proxy uses one deployment-wide
server-side `SIH_API_TOKEN`; the browser has no end-user session or role
boundary, while allowlisted POST actions include demo and live capture
start/stop. An internet-facing deployment therefore requires an external
identity/session layer or removal of those control actions behind a trusted
operator boundary. The repository now states this limitation in the README
and frontend architecture guide; no unsafe default or unsupported public-
exposure claim was added.

Additional **NOT VERIFIED** or residual items are TruffleHog (tool not
installed), failed-auth log rotation/flood controls, freshness-bound replay
protection, high-rate accumulation limits, tenant isolation, and public TLS.

## 7. Release verification

**STATUS: PASS locally.** Final evidence:

- `py -m pytest -q`: **321 passed, 2 warnings**.
- Focused API/remote/dashboard checks: **23 passed**.
- `npm run typecheck`: **PASS**.
- `npm run build`: **PASS**; Next emitted only the known package-lock-root
  warning because the lockfile is outside the repository root.
- `py -m build --wheel --sdist`: **PASS**.
- `py scripts/release_audit.py --strict`: **PASS**.
- `.venv\Scripts\python.exe -m pip check`: **PASS**.
- `git diff --check`: **PASS**; Git emitted only line-ending warnings.
- Artifact hash/size equality against the recorded checksum file: **PASS**.
- Existing local Docker/TLS health, restart, down/up, browser smoke, and real
  Windows/Npcap remote forecast evidence: **PASS within documented local
  limits**; this is not public staging evidence.

Phase W artifact snapshot (historical; superseded by the current checksum
record) is shown below. Current artifact values are recorded in
[`RELEASE_ARTIFACT_SHA256SUMS.txt`](RELEASE_ARTIFACT_SHA256SUMS.txt):

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `sih26_26153-0.1.0-py3-none-any.whl` | 153233 | `8D93182BE5F37B5F2A519D05DE48232997222F6FC0A9B673355F2A67E38235D7` |
| `sih26_26153-0.1.0.tar.gz` | 166135 | `017E0C25AFA1D92FA8D950F7E62FE1427414BE4076C8DE8B409662F203410874` |

## 8. External-validation protocol

**STATUS: PASS as documentation / NOT VERIFIED as execution.**

[`EXTERNAL_VALIDATION.md`](EXTERNAL_VALIDATION.md) now provides executable
A–N checks for installation, Central, dashboard, sensor onboarding, agent
registration, HTTPS telemetry, heartbeat, live capture, `L=10`, `K=5`,
dashboard semantics, restart/recovery, outage buffering/retry, and customer-
path independence. It separates **VERIFIED LOCALLY**, **NOT VERIFIED
LOCALLY**, and **REQUIRES EXTERNAL ENVIRONMENT**.

No unrelated developer, public user, second physical host, public DNS/TLS
endpoint, physical Linux/libpcap host, five-sensor run, expired certificate,
or long soak was available in this task.

## 9. Exact blockers

1. **BLOCKED — browser authorization for internet-facing use.** Add an
   external user/session/role boundary or remove browser-reachable operator
   actions and deploy behind an explicitly trusted control plane.
2. **BLOCKED — release provenance.** The owner must choose the exact source
   revision and resolve the existing `v0.1.0` tag collision. The current dirty
   tree cannot be represented as the existing tag without an owner-approved
   commit/tag decision.
3. **NOT VERIFIED — external execution.** An unrelated developer/environment
   must complete the A–N protocol before any public-validation claim.
4. **NOT VERIFIED — security/tooling boundary.** TruffleHog, dependency-
   inclusive clean installation, public TLS, multi-host/five-sensor, Linux
   capture/service boot, expiry behavior, and soak/resource evidence remain
   open.

## 10. Exact publication readiness

**STATUS: BLOCKED.** The open-source source surface and local release checks
are prepared, but this task did not produce a publishable Git revision, did
not resolve the existing tag mapping, did not provide an end-user authorization
boundary for internet-facing dashboard use, and did not obtain external-user
validation.

The candidate may be reviewed as a conditional local release candidate. It
must not be described as publicly published or publicly validated.

## 11. Exact commands required for final publication

**STATUS: NOT PERFORMED.** The following owner-controlled sequence is prepared
but was not executed. Replace placeholders only after selecting the approved
source revision and resolving the existing tag collision:

```text
git status --short
git diff --check
git rev-parse <approved-commit>^{commit}
git tag --list <approved-tag>
py -m build --wheel --sdist
py scripts/release_audit.py --strict
git push origin <approved-branch>
git push origin <approved-tag>
gh release create <approved-tag> dist/sih26_26153-0.1.0-py3-none-any.whl dist/sih26_26153-0.1.0.tar.gz docs/RELEASE_ARTIFACT_SHA256SUMS.txt --title "Sentinel / NI <approved-tag>" --notes-file docs/RELEASE_NOTES.md
```

No `git add`, commit, tag creation, push, GitHub release, PyPI upload, or
remote publication was performed by Phase W.

## 12. What was NOT performed

**STATUS: NOT PERFORMED / NOT VERIFIED.**

- No commit, tag mutation/creation, push, GitHub release, or PyPI publication.
- No public hosting, public ingress, public CA, DNS, or internet-facing
  dashboard deployment.
- No unrelated external user or external environment completed A–N.
- No end-user authentication/session integration was added.
- No physical second host, five-sensor run, physical Linux capture, expired
  certificate, or 30-minute soak.
- No TruffleHog scan because the tool was not installed.
- No model, ML pipeline, threshold, target, source-attribution claim, reverse
  proxy customer path, fake metric, fake detection, or automatic mitigation
  was introduced.

## Changes made in Phase W

- Added exact frozen feature-name validation to remote telemetry and endpoint
  regression coverage for structured 422 responses.
- Corrected frontend handling of reachable-but-unready Central responses and
  labeled mock/static telemetry distinctly from replay/live.
- Corrected stale release instructions, dataset/checkpoint wording, lockfile
  guidance, historical checklist ordering, security-policy links, candidate
  version/tag wording, and release artifact checksums.
- Converted the external guide into the A–N executable protocol and created
  this report.
