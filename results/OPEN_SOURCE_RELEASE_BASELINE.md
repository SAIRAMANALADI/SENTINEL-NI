# Open-Source Release Baseline

**Date:** 2026-09-01
**Branch:** `main`
**HEAD:** `568acca` — `Refresh public project README`
**Remote:** `origin/main` points to the same revision at baseline.

## Working tree at baseline

The previous real-time hardening pass was present as uncommitted changes. It
included runtime session identity, production configuration checks, security
headers, public-operation docs, and tests. No model or data artifact was
modified.

## Baseline validation

| Check | Result |
| --- | --- |
| Full test suite | PASS — 215 passed, 0 failed, 0 skipped |
| Test runtime | 96.05 seconds |
| Current branch | `main` |
| Current commit | `568acca` |
| Docker Compose config render | PASS |
| Smoke test | PASS |

## Baseline release risks

- No project license existed at the start of this sprint.
- `requirements-dev.txt` referenced `httpx2`, which is not the published test
  client package.
- Three tracked documents contained a local Windows username/path.
- Clean-clone installation and real live soak were not yet verified.
