# Sensor Security

Remote sensors connect out-of-band to the central Sentinel API. Customer
requests continue directly to the company application server; they never pass
through Sentinel.

## Current controls

- administrator-created, expiring, one-time enrollment credentials;
- distinct persistent sensor IDs and runtime credentials;
- runtime secret hashes only in the central registry;
- strict versioned telemetry schema and finite numeric validation;
- payload size, rate, date, interval, sequence, and duplicate checks;
- bounded restart-safe local telemetry buffering;
- no raw packet payload forwarding or credential logging;
- per-sensor state, forecast, and health isolation.

Enrollment is a server-side control-plane operation. The Next dashboard does
not call the admin-only enrollment endpoint and must not be configured with a
global administrator token. The one-time enrollment credential is the only
secret intended to be handed to the remote operator; it is consumed during
registration and is not returned by sensor GET endpoints.

The agent configuration has an explicit environment. Development may use
HTTP for a local central service. Production rejects an HTTP server URL and
requires HTTPS; the agent does not silently upgrade or downgrade the URL.

## Required deployment topology

```text
Internet -> firewall/private network -> TLS reverse proxy
         -> Sentinel API (internal :8000)
         -> runtime + sensor registry
         <- Agent A / Agent B / Agent C over authenticated HTTPS
```

Do not expose the application port directly to the public internet. Use
environment or secret-manager injection for role tokens. Keep each agent's
configuration private and rotate credentials by re-enrolling when required.

## Not yet implemented

mTLS/certificate rotation, OIDC, tenant isolation, and high-availability
registry storage remain future hardening work. The current implementation is a
single central process with an authenticated, bounded, multi-sensor contract.
