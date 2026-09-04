# Phase Y — Release Provenance and External Validation Gate

Validation date: 2026-09-04  
Project: Sentinel / NI (`SIH26-26153`)  

Final classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

This report is the Phase Y coordinator record. It establishes the relationship
between the existing public tag and the current working-tree candidate without
claiming that the candidate has been committed, tagged, pushed, or published.

## 1. Starting state

**Status: VERIFIED**

Phase X recorded the local candidate as `PUBLIC LAUNCH READY — EXTERNAL
VALIDATION PENDING`. The verified local baseline was 322 passed tests, frontend
typecheck/build, dashboard authentication smoke, Compose configuration, strict
release audit, and local TLS/auth evidence. Phase Y added the external handoff
quickstart, result template, and this provenance record, then fixed the
release-facing Live navigation, 401 re-authentication, Compose auth default,
Python-version guidance, and stale release wording.

The worktree was intentionally preserved dirty. No reset, checkout, commit,
tag mutation, push, GitHub release, or PyPI publication was performed.

## 2. Git provenance

**Status: VERIFIED** for the repository and ancestry relationship; **Status:
BLOCKED** for release binding.

- Repository: the current Git root (`1`).
- Branch: `main`.
- HEAD: `41dbec11a433370e28aa083274202b1f92ddd5c5`.
- `origin/main` also resolves to `41dbec11a433370e28aa083274202b1f92ddd5c5`.
- `git describe`: `v0.1.0-9-g41dbec1-dirty`.
- Final audit: 101 status entries, 57 modified files, 44 untracked entries,
  and 0 staged paths.
- The current candidate is therefore HEAD plus preserved dirty changes, not a
  clean release commit.

## 3. v0.1.0 tag analysis

**Status: VERIFIED**

- `v0.1.0` is an annotated tag object
  `25bcc43aa02d50963fa8dd5e6964476afb95018c`.
- Its target commit is `3798a588fc19461a766b7a2debba7e80be9529a3`.
- The tag target is an ancestor of current HEAD.
- `origin` exposes the same tag object at `refs/tags/v0.1.0`, so the tag is
  existing and public/immutable for this workflow, not local-only.
- The tag is not cryptographically signed; no signed-tag claim is made.

The existing public `v0.1.0` must remain untouched. The current candidate must
not be presented as the contents of that tag.

## 4. Release commit recommendation

**Status: PARTIAL**

No exact release commit exists yet because creating one was expressly outside
this run. The candidate source base is the exact HEAD listed in section 2 plus
the intended release files in the dirty worktree. An owner must review the
101-entry status, select the intended release files, and create one clean
release commit. A release-only commit is required before publication.

Recommended strategy:

1. Preserve public `v0.1.0` unchanged.
2. Review and commit the intended current candidate, including the refreshed
   docs, auth fixes, tests, and artifact record.
3. Because package metadata is still `0.1.0`, deliberately bump the package
   release metadata to `0.1.1` in the approved release commit (and update its
   release notes/checksum filenames if the owner chooses that release path).
4. Rebuild from that clean commit, audit and verify hashes, then create a new
   annotated `v0.1.1` tag.

A future `v0.1.0` replacement is technically possible only through an explicit,
coordinated remote tag replacement and matching package publication. **Status:
BLOCKED** as a release strategy: it would rewrite an existing public release
and is not recommended. No tag-rewrite commands were run or supplied here.

## 5. Artifact reproducibility

**Status: PARTIAL**

Fresh wheel and sdist builds were performed from the current candidate after
the Phase Y changes. The current checksum record matches the files in `dist/`:

| Artifact | Version / metadata | Members | Size | SHA256 |
| --- | --- | ---: | ---: | --- |
| `sih26_26153-0.1.0-py3-none-any.whl` | `0.1.0`; Requires-Python `>=3.12,<3.15` | 95 | 153306 | `434B9A790DA6B2C8BE758C671638AA17212576305D27DD5C90F255E5E78CABD0` |
| `sih26_26153-0.1.0.tar.gz` | `0.1.0`; runtime dependencies from `pyproject.toml` | 185 (166 files) | 167182 | `08C7A17DD911A88DEA2B1E61F04C2F5F642BAD2B357F2CA8B90B72A6472E816A` |

The previously recorded Phase X values (`F19B7B...` wheel and `0BD23E...`
sdist) were superseded after the candidate changed; the checksum document was
updated explicitly rather than silently treating the old values as current.

With `SOURCE_DATE_EPOCH=1788470400`, two wheel builds produced the same bytes.
The sdist content was audited, but repeated gzip-wrapped sdist builds did not
produce a stable byte hash, so full byte-for-byte reproducibility is not
claimed. Build requirements remain range-pinned rather than hash-pinned.

**Status: VERIFIED** for bounded package-content audit: the strict release
audit scanned 804 text files and both artifacts, and a separate bounded scan
found no private-key material, provider-token patterns, bearer credentials, or
local Windows/Linux filesystem paths. The sdist contains the repository test
suite as source distribution content; no test credentials or private artifacts
were found.

## 6. TruffleHog status

**Status: NOT VERIFIED**

`trufflehog` is not installed in the current environment, and the CI workflow
does not provide a TruffleHog step. The available strict release audit and
bounded history/tree checks found no bounded secret-pattern findings. That is
not a TruffleHog or full-history guarantee.

## 7. Public TLS status

**Status: PARTIAL**

Local trusted-CA/Nginx evidence covers direct HTTPS, wrong CA, hostname
mismatch, HTTP rejection, trusted-proxy forwarding, forged forwarded-header
handling, and HSTS behavior. The local dashboard runtime smoke also verified
production `Secure`, `HttpOnly`, `SameSite=Strict` cookie behavior.

No public hostname, DNS, publicly trusted certificate, internet ingress,
certificate-expiry check, or unrelated external HTTPS browser validation was
available. Those claims remain **Status: NOT VERIFIED**.

## 8. Linux status

**Status: NOT VERIFIED**

The host is Windows. WSL did not provide a usable Ubuntu/Linux validation
environment; Docker Linux-engine CLI smoke is container-only evidence. Physical
libpcap capture, Linux interface permissions, systemd lifecycle, reboot
recovery, and native Linux telemetry were not exercised.

## 9. Multi-host status

**Status: NOT VERIFIED**

No independent physical sensor host plus Central host, and no two-sensor
network-separated exercise, was available. Process isolation is not being
represented as multi-host validation.

## 10. Soak status

**Status: NOT VERIFIED**

No genuine 30-minute stability run with CPU, memory, uptime, reconnect,
buffer, telemetry continuity, forecast continuity, and dashboard observations
was performed in this gate. Short local smoke runs are not extrapolated.

## 11. External validation package

**Status: VERIFIED** for handoff readiness; **Status: NOT VERIFIED** for the
external execution itself.

The package now contains:

- [`EXTERNAL_VALIDATION_QUICKSTART.md`](EXTERNAL_VALIDATION_QUICKSTART.md),
  with clean-checkout/source-build fallback, Central, dashboard auth, admin
  enrollment handoff, agent registration, heartbeat, telemetry, live capture,
  `L=10`, `K=5`, five horizons, restart, outage buffering, customer-path
  independence, evidence, troubleshooting, and report instructions.
- [`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md),
  with all requested validator, environment, result, notes, evidence, failure,
  and recommended-fix fields.
- [`EXTERNAL_VALIDATION.md`](EXTERNAL_VALIDATION.md), linked from the new
  quickstart and template and retaining the A–N plus dashboard authorization
  protocol.

## 12. Full regression

**Status: VERIFIED**

- `pytest -q`: 323 passed, 2 warnings.
- `npm run typecheck`: completed successfully.
- `npm run build`: completed successfully; Next emitted only the known
  package-lock-root warning.
- `py -m build --wheel --sdist`: completed successfully.
- `pip check`: no broken requirements.
- `docker compose config --quiet`: completed successfully.
- `py scripts/release_audit.py --strict`: completed successfully after the
  report's local-path wording was removed.
- `git diff --check`: completed with line-ending warnings only.
- The bounded wheel/sdist package audit found no sensitive-pattern or local-path
  findings.

The full regression and packaging gates are local evidence for the preserved
working tree. They do not establish external, Linux, multi-host, public-TLS,
TruffleHog, or soak validation.

## 13. Remaining blockers

**Status: BLOCKED** for unconditional publication; **Status: VERIFIED** for
the following documented boundary:

- **NOT VERIFIED** — unrelated external validation completion.
- **NOT VERIFIED** — TruffleHog/full-history secret scan.
- **NOT VERIFIED** — public CA/DNS/TLS ingress and external HTTPS browser path.
- **NOT VERIFIED** — physical Linux capture/systemd validation.
- **NOT VERIFIED** — physical multi-host/two-sensor or five-sensor validation.
- **NOT VERIFIED** — genuine 30-minute soak/resource evidence.
- **PARTIAL** — clean approved release commit, package-version reconciliation,
  new tag, and final release artifact binding remain for the human operator.

These blockers prevent the stronger `PUBLIC LAUNCH READY` classification.
They do not prevent the evidence-supported `PUBLIC LAUNCH READY — EXTERNAL
VALIDATION PENDING` classification.

## 14. Exact human publication procedure

**Status: NOT PERFORMED**

After reviewing the dirty worktree and completing the missing external gates,
the human release operator should run an equivalent sequence. The following is
an instruction only; none of these publication commands was executed:

```powershell
git status --short
git diff --check
# Review and stage only the approved release files, not unrelated dirty work.
git add <approved-release-files>
git diff --cached --check
git commit -m "Release Sentinel / NI v0.1.1"
$releaseCommit = git rev-parse HEAD
git show --stat --oneline $releaseCommit

$env:SOURCE_DATE_EPOCH = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
py -m build --wheel --sdist
py scripts/release_audit.py --strict
Get-FileHash .\dist\sih26_26153-0.1.1-py3-none-any.whl -Algorithm SHA256
Get-FileHash .\dist\sih26_26153-0.1.1.tar.gz -Algorithm SHA256

git tag -a v0.1.1 -m "Sentinel / NI v0.1.1"
git push origin main
git push origin v0.1.1
py -m pip install --requirement requirements-release.txt
py -m twine check dist\sih26_26153-0.1.1-*
py -m twine upload dist\sih26_26153-0.1.1-*
```

The operator must replace the placeholder file list and ensure every versioned
artifact/checksum reference agrees before the first push or upload. The
existing `v0.1.0` tag is not to be deleted or moved.

## 15. Actions NOT performed

**Status: NOT PERFORMED**

This gate did not create a Git commit, create or mutate a tag, force-update a
remote, push a branch, create a GitHub release, upload to PyPI, expose a public
TLS endpoint, install TruffleHog, claim Linux host validation, claim physical
multi-host validation, or claim a 30-minute soak result.
