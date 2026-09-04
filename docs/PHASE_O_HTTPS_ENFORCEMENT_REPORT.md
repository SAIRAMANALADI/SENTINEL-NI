# Phase O — Central API HTTPS Enforcement Report

**Date:** 2026-09-04  
**Scope:** Central API transport enforcement and the related production
deployment contract.  No ML weights, feature definitions, ingestion logic,
forecasting code, or telemetry semantics were changed.

## Executive result

The central API now fails closed for public plaintext HTTP in production. The
application supports two explicit production topologies:

1. `direct_https`: the ASGI request scheme must be `https`.
2. `trusted_proxy`: the API may receive internal HTTP only from a configured
   proxy peer and only with an exact `X-Forwarded-Proto: https` header.

Development and test HTTP remain available only when the explicit
`development_http` mode is selected. Production configuration rejects that
mode. The API returns a sanitized `403` with error code `HTTPS_REQUIRED`; it
does not redirect authenticated API calls.

This closes the application-level security gap. It does not prove that a live
TLS terminator, certificate, ingress ACL, Docker network, or multi-host
deployment is correctly configured. Production readiness therefore remains
conditional on the deployment validation listed below.

## Original gap and root cause

Before Phase O, production authentication could be enabled while the central
API still accepted direct HTTP. Agent-side HTTPS validation did not protect
browser, administrator, or incorrectly exposed API callers, and reverse-proxy
documentation alone was not an enforcement mechanism. Forwarded headers also
could not be trusted globally because a public caller can forge them.

## Implemented policy

| Mode | Intended boundary | Allowed public request | Forwarded-header behavior |
| --- | --- | --- | --- |
| `development_http` | Development/test only | HTTP and HTTPS | Forwarded headers are irrelevant |
| `direct_https` | TLS terminates at the API process | ASGI scheme `https` | `X-Forwarded-Proto` is ignored |
| `trusted_proxy` | Trusted TLS proxy with private HTTP upstream | ASGI scheme `https`, or exact forwarded `https` from a configured peer | Peer IP must match `SIH_TRUSTED_PROXY_CIDRS`; comma/mixed values are rejected |

The production default from `Settings.from_env()` is `direct_https`. A
production configuration cannot validate with `development_http`, and
`trusted_proxy` requires at least one valid CIDR. The application checks the
immediate ASGI peer; it does not parse or trust an arbitrary client-IP chain.

Loopback `/api/v1/health` and `/api/v1/ready` remain available over internal
HTTP for local process/container health checks. This exception is limited to
loopback peers and does not make a publicly reachable API HTTP endpoint valid.

## Topology and configuration

The intended production path is:

```text
agent/browser/admin -- HTTPS --> trusted TLS reverse proxy -- private HTTP --> API :8000
```

For direct TLS at the application boundary:

```text
SIH_ENV=production
SIH_TRANSPORT_MODE=direct_https
```

For a private HTTP upstream behind a TLS proxy, configure a narrow proxy
source range, for example:

```text
SIH_ENV=production
SIH_TRANSPORT_MODE=trusted_proxy
SIH_TRUSTED_PROXY_CIDRS=127.0.0.1/32
```

The proxy must overwrite, rather than append to, `X-Forwarded-Proto` and must
keep port `8000` private. Compose keeps the backend and dashboard host
bindings on loopback by default; a real ingress/firewall validation is still
required before exposure beyond the host.

## Caller behavior

- Production agents must use the public HTTPS API URL and retain certificate
  verification. They must not be configured with the internal `:8000` URL.
- The Next.js dashboard uses its server-side allowlisted API proxy; the browser
  does not receive a bearer token or call the internal backend directly.
- Development HTTP remains documented as an explicit local-only mode.
- The central API rejects forged `X-Forwarded-Proto` values from untrusted
  peers, including when a framework has already reflected the header into the
  request scheme.

## Files changed

- `src/platform/config.py` — transport mode and trusted CIDR configuration and
  production validation.
- `src/api/app.py` — peer-aware transport gate, sanitized rejection response,
  and loopback health exception.
- `tests/api/test_https_enforcement.py` — focused policy and regression tests.
- `docker-compose.yml`, `.env.example`, and `docs/CONFIGURATION.md` — explicit
  environment wiring.
- `docs/SECURITY_ARCHITECTURE.md`, `docs/TLS_DEPLOYMENT.md`,
  `docs/AGENT_SECURITY.md`, `docs/DEPLOYMENT_GUIDE.md`, and
  `docs/REAL_DEPLOYMENT_RUNBOOK.md` — deployment contract.
- `docs/RELEASE_CANDIDATE_CHECKLIST.md` and this report — release evidence and
  residual boundary.

## Verification evidence

The focused Phase O suite passed:

```text
py -m pytest -q tests/api/test_https_enforcement.py tests/api/test_security_hardening.py tests/api/test_auth_and_platform.py
20 passed
```

It covers:

- production direct HTTP rejection;
- forged forwarded-proto rejection;
- direct HTTPS success and failed-authentication behavior;
- trusted-proxy success only for a configured peer and exact forwarded HTTPS;
- mixed forwarded-proto rejection;
- explicit development HTTP behavior;
- production configuration rejection of `development_http`;
- authenticated HTTPS enrollment and telemetry;
- internal loopback readiness.

The repository-wide regression suite also passed:

```text
py -m pytest -q
310 passed, 2 warnings
```

Frontend checks passed with `npm run typecheck` and `npm run build`. A wheel
and sdist were built with `py -m build --sdist --wheel --no-isolation`. A fresh
temporary virtual environment installed the wheel, passed `pip check`, and
imported the installed configuration module. `py -m pip check` also passed in
the working environment.

## Residual risks and release decision

The application policy is **implemented and regression-tested**. The change
is **not by itself a production-ready TLS deployment claim**. Before calling a
deployment production-ready, run the release checklist with:

- a real TLS handshake and certificate/hostname validation;
- a real reverse proxy that overwrites the forwarded scheme and reaches the
  private upstream;
- an untrusted-peer forged-header test at the ingress boundary;
- Docker/container startup and network reachability checks;
- authenticated browser/admin, agent registration, and telemetry journeys
  through the deployed HTTPS hostname.

Docker runtime was not verified because the Docker daemon was unavailable.
No commit or push was performed.
