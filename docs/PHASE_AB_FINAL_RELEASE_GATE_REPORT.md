# Phase AB — Final Release Gate and Publication Preparation

Validation date: 2026-09-04
Project: Sentinel / NI (`SIH26-26153`)

Final classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

No publication, tag mutation, push, GitHub release, or PyPI upload was
performed in Phase AB.

## 1. Starting state

**Status: VERIFIED**

Phase AB started from clean `main` at
`db8886fa2d25867b34d3d658901f32ef16e638f8`, with `origin/main` at the same
commit and no staged or unstaged changes. The prior Phase AA brief described
the pre-push state; this report records the actual post-push state. The public
annotated `v0.1.0` tag remains unchanged and points to its earlier commit
`3798a588fc19461a766b7a2debba7e80be9529a3`.

## 2. Concurrency investigation

**Status: VERIFIED — THREE P1 DEFECTS REPRODUCED AND FIXED**

Forced interleavings reproduced three same-sensor/live-runtime defects in the
Phase AB working tree:

- Same-sensor telemetry admission and registry commit were not one critical
  section. A second request could pass admission while the first request was
  blocked in runtime processing, leaving registry sequence state divergent from
  the runtime state count.
- Live inference ran outside the store lock and an older, slower result could
  overwrite a newer forecast.
- Concurrent live-capture starts could each create a sniffer, leaving one
  orphaned after stop.

The fixes serialize the complete per-sensor telemetry transaction, reject
older forecast publication by reference timestamp, and hold the capture
adapter lifecycle lock across sniffer creation/start/stop. Regression tests
were added for all three forced interleavings. The focused affected suites
passed (`31 passed`), and the full regression below passed. No P0/P1 defect
remains reproduced in the current working tree.

## 3. Release audit

**Status: PASS**

`scripts/release_audit.py --strict` passed after the Phase AB documentation
updates. It scanned the tracked release text and two package artifacts and
reported only ignored local-artifact warnings.

## 4. Artifact rebuild

**Status: VERIFIED**

Fresh build command:

```text
$env:SOURCE_DATE_EPOCH = (git show -s --format=%ct HEAD)
python -m build --wheel --sdist
```

Candidate base: `db8886fa2d25867b34d3d658901f32ef16e638f8` plus the uncommitted
Phase AB working-tree delta
Package version: `0.1.0`
Wheel: `sih26_26153-0.1.0-py3-none-any.whl`, 153696 bytes, SHA256
`B029FC8C7CF4D80278A6385803E7235C970F25CD19AC2CE766A8727E15D948F7`
Sdist: `sih26_26153-0.1.0.tar.gz`, 167989 bytes, SHA256
`827A09B7AD86597E95D5620438F8D77CC41805AF17436FEE5EDEC61733395819`
Wheel members: 95
Sdist members/files: 185 / 166

The checksum record was updated to these artifacts. They are not uploaded or
bound to the existing `v0.1.0` tag.

## 5. Secret scanning

**Status: PARTIAL**

The strict release audit, bounded package-content scan, path scan, and focused
security checks passed. TruffleHog, Gitleaks, detect-secrets, Semgrep, Bandit,
pip-audit, OSV-Scanner, Grype, Syft, and git-secrets were unavailable.

Exact external scanner status: **NOT VERIFIED — TOOL NOT INSTALLED**.

## 6. TLS status

**Status: PARTIAL**

Local HTTPS enforcement, wrong-CA, hostname-mismatch, HTTP rejection, trusted
proxy, forged-header, and loopback exception contracts passed in the available
focused tests. Public DNS/ingress, public CA, certificate expiry, and an
independent TLS handshake remain **NOT VERIFIED — ENVIRONMENT LIMIT**.

## 7. Linux status

**Status: NOT VERIFIED — ENVIRONMENT LIMIT**

No genuine Linux agent installation, libpcap capture, service-manager startup,
heartbeat, telemetry, or shutdown run was available.

## 8. Multi-host status

**Status: NOT VERIFIED — ENVIRONMENT LIMIT**

No independently controlled Central host and Sensor host pair was available.

## 9. Soak status

**Status: NOT VERIFIED — ENVIRONMENT LIMIT**

No genuine 30-minute operation and resource/capacity series was run.

## 10. External handoff status

**Status: VERIFIED** for documentation readiness; **Status: NOT VERIFIED** for
execution.

The quickstart, guide, result template, and new explicit “DO NOT USE
DEVELOPMENT MACHINE” sections identify the exact candidate/hash, topology,
commands, expected results, safe evidence, and failure format. No unrelated
validator has completed the workflow.

## 11. Git provenance

**Status: VERIFIED** for the current candidate; **Status: NOT VERIFIED** for a
published release binding.

`HEAD` and `origin/main` both resolve to
`db8886fa2d25867b34d3d658901f32ef16e638f8`; Phase AB changes are intentionally
uncommitted in the working tree. The remote annotated `v0.1.0` still targets
`3798a588...`; it must not be rewritten. The safe future strategy is a
human-approved `0.1.1` release commit and new annotated `v0.1.1` tag.

## 12. Publication procedure

**Status: NOT PERFORMED**

[`FINAL_PUBLIC_RELEASE_RUNBOOK.md`](FINAL_PUBLIC_RELEASE_RUNBOOK.md) contains
the exact human-only procedure: final metadata/version review, clean commit,
artifact rebuild and hashes, audit, `v0.1.1` tag, GitHub release assets,
release notes, PyPI upload, and post-publication verification. The old
`v0.1.0` tag is explicitly preserved.

## 13. Final regression

**Status: VERIFIED** locally; **Status: NOT VERIFIED** independently.

- Python suite: `326 passed, 2 warnings`.
- Frontend typecheck: PASS.
- Frontend production build: PASS.
- Wheel/sdist rebuild: PASS.
- `pip check`: PASS.
- Strict release audit/package audit: PASS.
- `git diff --check`: PASS with existing line-ending warnings only.
- Docker Compose config: PASS.
- Focused security/HTTPS/agent tests: `28 passed, 2 warnings`.

## 14. Remaining blockers

**Status: BLOCKED** for unconditional `PUBLIC LAUNCH READY`.

Independent external validation, public TLS/ingress, TruffleHog, native Linux,
physical multi-host, five-sensor, 30-minute soak, and post-publication gates
remain outstanding. These are environment/evidence blockers, not remaining
P0/P1 defects. The current candidate is internally coherent for the verified
local boundary, but is not yet externally validated or publication-approved.

## 15. Final release recommendation

**Status: VERIFIED**

Retain **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**. Hand the exact
candidate and artifact hashes to an unrelated validator. Do not publish during
Phase AB, do not rewrite `v0.1.0`, and do not infer Linux, multi-host, soak,
public TLS, or external-validation success from local evidence. If a genuine
P0/P1 defect is found, create a new candidate, rerun affected validation, and
rebuild its artifacts before any release decision.
