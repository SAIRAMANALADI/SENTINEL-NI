# Phase X — Public Exposure Hardening and Release Tag Reconciliation

Validation date: 2026-09-04  
Project: Sentinel / NI  
Repository: `SENTINEL-NI`  

Final classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

This is the current Phase X coordinator record. It supersedes older release
checklist classifications where they conflict with this report. “Ready” here
means the local source candidate has a server-side dashboard authorization
boundary and passing local gates; it does not mean publicly deployed,
externally validated, committed, tagged, pushed, or published.

## 1 Starting State

**Status: BLOCKED**

Phase W classified the candidate as blocked because the Next dashboard used a
deployment-wide server-side `SIH_API_TOKEN` without end-user session or role
authorization. Phase W also recorded a dirty working tree, an existing
`v0.1.0` tag pointing to an older commit, and missing external TruffleHog,
public TLS, Linux, multi-host, and soak evidence.

The Phase X starting revision was `41dbec11a433370e28aa083274202b1f92ddd5c5`
on `main`. The worktree was preserved; no pre-existing changes were discarded.

## 2 Dashboard Authorization Audit

**Status: PASS**

The audit found and closed the material dashboard exposure paths:

- the Next catch-all route is now the only `/api/*` frontend path; the prior
  broad `next.config.mjs` rewrite was removed because it could bypass the
  allowlist;
- dashboard auth is server-side and can be enabled explicitly with
  `SIH_DASHBOARD_AUTH_ENABLED=true` (or follows enabled Central auth/production
  settings when the explicit flag is absent);
- anonymous dashboard data/control requests receive `401` in auth mode;
- the allowlist still excludes enrollment, registration, telemetry ingestion,
  credential rotation, and other control-plane paths;
- customer application requests remain directly between the customer and its
  application. Sentinel is out-of-band and is not a reverse proxy.

## 3 Authorization Changes

**Status: PASS**

Implemented the smallest local dashboard adapter without adding a dependency:

- `frontend/lib/dashboard-session.ts` stores opaque random session IDs in a
  process-local, expiring in-memory map;
- `POST /api/auth/login` accepts a role token only server-side, compares it
  with `timingSafeEqual`, and issues an `HttpOnly`, `SameSite=Strict` cookie;
- `GET /api/auth/session` reports only authenticated state and role;
- `POST /api/auth/logout` deletes the session and clears the cookie;
- the proxy maps viewer/operator/admin sessions to matching server-only Central
  role tokens and returns `401`/`403` before forwarding unauthorized calls;
- state-changing routes enforce same-origin checks and proxy responses use
  `Cache-Control: no-store`;
- `AuthGate` blocks dashboard data loading until session state is known, and
  viewer sessions do not render operator control buttons;
- Compose now passes the dashboard auth flag, role tokens, and session TTL to
  the frontend container. No token value was added to source.

Known v0.1 limitation: the session store is process-local. A frontend restart
invalidates sessions; multi-instance deployments require sticky routing. This
adapter is not OIDC/OAuth2 and does not claim federated identity management.

## 4 Authorization Test Results

**Status: PASS**

Evidence collected locally:

- `py -m pytest -q tests/test_next_dashboard_contract.py`: **5 passed**;
- `npm run typecheck`: **PASS**;
- `npm run build`: **PASS**; the build exposes `/api/[...path]` and all three
  auth routes as dynamic server routes;
- runtime Next smoke on a development HTTP port with dummy test tokens:
  anonymous `GET /api/v1/live` **401**, viewer login **200**, viewer live read
  **200**, viewer demo POST **403**, cross-origin demo POST **403**, logout
  **200**, and the old session after logout **401**;
- production-mode cookie smoke showed `Secure; HttpOnly; SameSite=strict`;
  the cookie was intentionally not sent over the HTTP test port;
- full Python regression after the changes: **322 passed, 2 warnings**.

Runtime browser E2E coverage across refresh, expiry, and a real TLS endpoint
is not available in this Windows validation environment.

## 5 Git Tag Analysis

**Status: PARTIAL**

Read-only local and remote tag inspection produced:

| Item | Observed value |
| --- | --- |
| Branch | `main` |
| Current commit | `41dbec11a433370e28aa083274202b1f92ddd5c5` |
| Local `v0.1.0^{commit}` | `3798a588fc19461a766b7a2debba7e80be9529a3` |
| Local tag object | `25bcc43aa02d50963fa8dd5e6964476afb95018c` |
| Remote `refs/tags/v0.1.0` | tag object `25bcc43aa02d50963fa8dd5e6964476afb95018c` |
| `git describe` | `v0.1.0-9-g41dbec1-dirty` |

The remote tag exists and agrees with the local annotated tag, but it does not
point to the current candidate. The tag was not moved, deleted, recreated, or
force-updated. The owner must choose a new release tag or explicitly approve a
retargeting strategy after a clean source commit exists.

## 6 Release Candidate Integrity

**Status: PARTIAL**

The local package rebuild completed and the wheel/sdist names remain
`sih26_26153-0.1.0`. Current local SHA-256 evidence is recorded in
`docs/RELEASE_ARTIFACT_SHA256SUMS.txt`:

- wheel: 153306 bytes,
  `F19B7B7AB64898621351AC56EBD70D7EA1AFB26EB5D3CECE10BBCF92B116A7F0`;
- sdist: 166760 bytes,
  `0BD23E36AD3AF18B0125EB2E66CC359C0C687B14E1CF227B12B57BFEAA8080D4`.

`pip check`, package build, strict source audit after the report was added, and
`git diff --check` are local gates. The candidate is not yet a clean approved
commit: the preserved worktree contains pre-existing and Phase X changes, and
the artifacts are not attached to the existing `v0.1.0` tag.

## 7 External Validation Package

**Status: PASS**

`docs/EXTERNAL_VALIDATION.md` now contains the clean-checkout protocol,
dashboard authorization sequence, safe evidence rules, locked-install
requirements, and explicit O–R checks for dashboard auth, Linux, multi-host,
and soak validation. It distinguishes local browser/runtime evidence from
external HTTPS evidence and repeats that a local pass is not an external pass.

Six required ownership audits were completed and closed without edits:
frontend, backend authorization, sensor/agent boundaries, security, QA/release,
and documentation. Their common conclusion was that the local auth boundary
is now addressable, but external deployment and provenance gates remain
unverified.

## 8 TLS Validation

**Status: PARTIAL**

Existing local evidence covers an isolated TLS reverse proxy, trusted private
CA, wrong-CA rejection, hostname mismatch, HTTP rejection, and trusted proxy
behavior. The external package documents the required public checks. A public
DNS/CA/ingress endpoint, certificate expiry exercise, and unrelated-user HTTPS
dashboard session were not run.

## 9 Secret Scanning

**Status: NOT VERIFIED**

TruffleHog is not installed on the validation host, so no TruffleHog result is
claimed. The existing bounded release-audit/current-tree checks found no
credential or private-key finding, but they are not a substitute for a
full-history TruffleHog scan. No token values were written to the repository.

## 10 Linux Validation

**Status: NOT VERIFIED**

This validation host is Windows. Linux/libpcap capture, exact interface and
permission behavior, systemd start/status, and reboot recovery were not
physically exercised.

## 11 Multi-Host Validation

**Status: NOT VERIFIED**

The code and tests cover sensor identity separation and sensor-scoped runtime
behavior, but two physical hosts with five independently registered sensors
were not available. No multi-host isolation or capacity claim is made.

## 12 Soak Validation

**Status: NOT VERIFIED**

A 30-minute resource/capacity run recording CPU, memory, packet/flow/state and
telemetry rates, queue depth, errors, logs, and forecast latency was not run.
No SLA or production-capacity claim is made.

## 13 Full Regression Results

**Status: PASS**

| Gate | Result |
| --- | --- |
| Python regression | **PASS** — `322 passed, 2 warnings` |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS** |
| Package wheel + sdist | **PASS** |
| `pip check` | **PASS** |
| `docker compose config --quiet` | **PASS** |
| `git diff --check` | **PASS** |
| Focused dashboard contract tests | **PASS** — 5 passed |
| Strict release audit | **PASS** after the Phase X report was added |

The Next build emitted only the existing warning that the package lockfile is
outside the repository root. No build or test command committed or published
anything.

## 14 Remaining Blockers

**Status: BLOCKED**

The following are still required before a public release claim can be made:

| Status | Remaining item |
| --- | --- |
| **NOT VERIFIED** | Unrelated external operator completes the auth/browser/TLS journey |
| **NOT VERIFIED** | TruffleHog scan, preferably including the intended release history |
| **NOT VERIFIED** | Physical Linux/libpcap and service-manager validation |
| **NOT VERIFIED** | Two-host/five-sensor validation and isolation evidence |
| **NOT VERIFIED** | 30-minute soak/resource observation |
| **PARTIAL** | Owner-approved clean commit, tag strategy, and artifact provenance |

These blockers do not reopen the Phase W dashboard shared-token defect in the
current source candidate; they are evidence/provenance gates that cannot be
truthfully completed by this local Windows run.

## 15 Publication Procedure

**Status: NOT PERFORMED**

After owner review, the safe sequence is:

1. Freeze the intended working-tree changes and create an approved clean source
   commit; do not include unrelated local artifacts.
2. Preserve the existing remote `v0.1.0` unless the owner explicitly approves
   a version/tag strategy. Do not attach current artifacts to the old tag.
3. Rebuild the wheel and sdist from the approved commit, add the approved
   commit SHA/build timestamp to the checksum evidence, and verify hashes.
4. Run the locked clean-install smoke, full regression, frontend gates, strict
   release audit, TruffleHog, link scan, and `git diff --check`.
5. Have an unrelated operator complete the external O–R protocol, including
   HTTPS dashboard role authorization, Linux, multi-host, and soak checks.
6. Only after those gates pass may the owner push the approved commit/tag,
   create a GitHub release, or publish package artifacts. All three actions
   remain outside this Phase X run.

## 16 Exact Actions NOT Performed

**Status: NOT PERFORMED**

- no `git commit`;
- no `git push` or remote branch update;
- no tag creation, deletion, movement, or force-update;
- no GitHub release creation or release-asset upload;
- no PyPI or other package-index publication;
- no public DNS, public ingress, or public certificate deployment;
- no external user/environment validation was represented as local evidence;
- no customer application request was routed through Sentinel;
- no TruffleHog installation or substitute claim was made;
- no unrelated dirty-worktree change was reset, checked out, or discarded.
