# Phase Z — External Validation Pilot and Release Candidate Freeze

Validation date: 2026-09-04  
Project: Sentinel / NI (`SIH26-26153`)  

Final classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

This is the final Phase Z coordinator record. No unrelated external validator
or public staging environment was available in this run, so this report
records a prepared pilot package and a frozen local candidate. It does not
claim external validation, public TLS, Linux host, physical multi-host, or soak
evidence.

## 1. Candidate identity

**Status: VERIFIED** for the recorded local candidate identity.

- Git commit: `41dbec11a433370e28aa083274202b1f92ddd5c5`.
- Branch: `main`; `origin/main` resolves to the same commit.
- Working-tree status at freeze: 103 entries before this report was added;
  57 modified, 46 untracked, and 0 staged. The final report itself is excluded
  from the hash below so the identity remains stable after this document is
  added.
- Working-tree diff hash, covering status, path, and content digests for all
  other candidate files: `ca3911bcd970355150b00b1cf007da6acf7bf2b02f8893baeff3ad068e44808d`.
- Wheel SHA256:
  `6C3B89ED8FED44B549DF2BB0859B74976B7872D75A8784FEAB52DEB024B21768`.
- Sdist SHA256:
  `C947138D69D8462EFA08218957F719864C12A6D32290756627C0FB56D4E6286C`.

The artifact record is [RELEASE_ARTIFACT_SHA256SUMS.txt](RELEASE_ARTIFACT_SHA256SUMS.txt).

## 2. Git provenance

**Status: VERIFIED** for ancestry; **Status: BLOCKED** for clean release
binding.

The current candidate is HEAD plus a preserved dirty worktree. The existing
annotated `v0.1.0` tag object is
`25bcc43aa02d50963fa8dd5e6964476afb95018c`, targeting
`3798a588fc19461a766b7a2debba7e80be9529a3`. That target is an ancestor of
HEAD, and the same tag object is present remotely. The candidate is not the
contents of that tag, and no commit or tag mutation was performed.

## 3. Validator environment

**Status: BLOCKED** for an unrelated pilot environment.

No unrelated validator, public hostname, public certificate, second physical
host, usable Linux host, or practical 30-minute soak environment was supplied.
The local validation host is Windows with Python 3.14 and Docker Desktop. Its
results are local evidence only and are not substituted for the external pilot.

## 4. Installation result

**Status: NOT PERFORMED** for external validation; **Status: VERIFIED** for
local package smoke.

The current wheel installed into the local virtual environment with
`--no-deps`; `sentinel-agent.exe --version` reported `0.2.0`, and `--help`
listed the documented command groups. The quickstart also provides a clean
checkout build fallback and a POSIX installation variant.

## 5. Authentication result

**Status: NOT PERFORMED** for the external pilot; **Status: VERIFIED** for
local implementation and smoke evidence.

The server-side dashboard session boundary, opaque HttpOnly/SameSite cookie,
viewer/operator/admin role separation, logout invalidation, CSRF origin checks,
allowlisted proxy, and 401 re-authentication path are implemented and covered
by local runtime/static evidence. External browser TTL and HTTPS authorization
were not exercised.

## 6. Sensor registration result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** for the documented
admin enrollment and one-time agent registration path in local automated and
historical evidence.

The quickstart makes the administrator-controlled enrollment handoff explicit;
the browser is not the enrollment authority.

## 7. Heartbeat result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** in existing local
agent/Central regression evidence.

No external sensor host was available to repeat the heartbeat and `ONLINE`
transition during this phase.

## 8. Telemetry result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** in existing local
agent-to-Central regression evidence.

The external protocol requires real sensor telemetry and rejects mock/replay
results as live evidence.

## 9. Live capture result

**Status: NOT PERFORMED** externally; **Status: PARTIAL** overall.

Existing Windows/Npcap evidence covers the local live path. The Phase Z pilot
did not repeat capture on an unrelated host, and Docker Compose's backend uses
mock telemetry for platform smoke rather than packet capture.

## 10. L=10 result

**Status: NOT PERFORMED** for the external pilot.

The documented protocol requires ten contiguous accepted live states. Local
historical evidence exists, but it is not new unrelated-environment evidence.

## 11. K=5 result

**Status: NOT PERFORMED** for the external pilot; **Status: VERIFIED** in the
existing local regression and historical live path.

The frozen contract remains the existing LSTM direct K=5 path. No model,
feature, threshold, or forecasting behavior was modified in Phase Z.

## 12. Five-horizon forecast result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** as a frozen contract.

The required horizons remain +10s, +20s, +30s, +40s, and +50s. No forecast
score is described as a probability.

## 13. Candidate source result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** for the documented
state-only/source-evidence boundary.

The validator is instructed to inspect Candidate Source information where
available and record it as evidence-scoped, never as attacker attribution.

## 14. Mitigation result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** for the
recommendation-only and simulation-only operating boundary.

No automatic response or customer-traffic routing was introduced.

## 15. Restart/recovery result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** in existing local
agent stop/restart and identity-persistence evidence.

The pilot package instructs the validator to confirm the same sensor identity
after restart and to record any expected offline/stale transition.

## 16. Outage buffering/retry result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** in existing local
buffer/retry/flush regression evidence.

The quickstart explicitly says not to claim delivery during Central outage and
to record recovery only after Central is restored.

## 17. Customer-path independence result

**Status: NOT PERFORMED** externally; **Status: VERIFIED** as an architectural
boundary and existing local exercise.

Customer requests must continue directly to the customer application while
security telemetry travels Sensor → Central Sentinel. Sentinel is not a
reverse proxy.

## 18. Security validation

**Status: PARTIAL**

Local evidence covers role boundaries, invalid credentials, logout, session
invalidation, sensor identity binding, production HTTP rejection, trusted-proxy
peer/protocol checks, and bounded package secret checks. External execution of
expired-session browser behavior, public TLS certificate validation, and
full-history secret scanning was not performed. The legacy Streamlit surface
remains loopback/private and must not be exposed as the public end-user
dashboard.

## 19. Environment gate results

**Status: BLOCKED** for unconditional release; individual gate statuses are:

- TruffleHog: **NOT VERIFIED** — tool not installed.
- Public TLS: **PARTIAL** — local trusted-CA/reverse-proxy evidence only; no
  public DNS, public CA, ingress, expiry, or external browser run.
- Linux: **NOT VERIFIED** — no usable native Linux host; Docker Linux smoke is
  container-only.
- Multi-host: **NOT VERIFIED** — no independent physical host pair.
- Soak: **NOT VERIFIED** — no genuine 30-minute run.

## 20. Failures and fixes

**Status: VERIFIED** for the scoped P1 fixes made before the freeze.

- The quickstart now invokes the installed venv executable explicitly and
  documents the sensor-host activation requirement.
- The quickstart now distinguishes local Compose smoke from public TLS and
  includes direct-Uvicorn TLS options plus a POSIX installation path.
- Starting Live now clears stale Demo state, preventing live telemetry from
  being labeled as DEMO.
- Current test counts and current-gate pointers were reconciled to Phase Z.
- A pinned release-only `requirements-release.txt` was added for the human
  publication procedure.

No P0 was found. P2/P3 residuals, including unbounded failed-auth audit I/O,
telemetry freshness limitations, process-local sessions, and older historical
documentation wording, remain outside the frozen release-fix scope.

## 21. Remaining limitations

**Status: BLOCKED** for unconditional `PUBLIC LAUNCH READY`.

The missing unrelated pilot, public TLS, TruffleHog, Linux, physical
multi-host, and soak evidence remain the release limitations. The candidate is
also not yet a clean approved commit and is not bound to a new release tag.

## 22. Release-freeze status

**Status: VERIFIED**

Candidate Z is frozen at the identity in section 1 after the final local
regression, artifact build, documentation audit, and package-content audit.
No external pilot has begun, so there has been no silent candidate mutation
under a validator. If an external validator later finds a P0/P1 defect,
Candidate Z must remain unchanged; create Candidate B, fix the scoped defect,
rebuild/reidentify it, and rerun the affected checks.

## 23. Exact publication procedure

**Status: NOT PERFORMED**

The current public `v0.1.0` tag must not be moved. The recommended future
release path is an owner-approved clean commit with package version `0.1.1`, a
new annotated `v0.1.1` tag, and freshly rebuilt artifacts:

```powershell
git status --short
git diff --check
# Review and stage only the intended release files.
git add <approved-release-files>
git diff --cached --check
# Update package/release metadata to 0.1.1 in the approved release commit.
git commit -m "Release Sentinel / NI v0.1.1"
$releaseCommit = git rev-parse HEAD

$env:SOURCE_DATE_EPOCH = (git show -s --format=%ct $releaseCommit)
py -m build --wheel --sdist
py scripts/release_audit.py --strict
Get-FileHash .\dist\sih26_26153-0.1.1-py3-none-any.whl -Algorithm SHA256
Get-FileHash .\dist\sih26_26153-0.1.1.tar.gz -Algorithm SHA256
py -m pip install --requirement requirements-release.txt
py -m twine check .\dist\sih26_26153-0.1.1-*

git tag -a v0.1.1 -m "Sentinel / NI v0.1.1"
git push origin main
git push origin v0.1.1
gh release create v0.1.1 .\dist\sih26_26153-0.1.1-* docs\RELEASE_ARTIFACT_SHA256SUMS.txt --title "Sentinel / NI v0.1.1" --notes-file docs\RELEASE_NOTES.md
py -m twine upload .\dist\sih26_26153-0.1.1-*
```

These commands are a human publication procedure only. They were not run in
Phase Z.
