# Sensor Credential Lifecycle

Sentinel deliberately separates enrollment, identity, runtime access, and
revocation.

```text
short-lived enrollment credential
              |
              v
      one-time registration
              |
              v
 persistent sensor_id + runtime credential
              |
              v
             ACTIVE
          /          \
  rotate/admin       disable/admin
        |                 |
        v                 v
 new runtime token     DISABLED / INVALID
 old token invalid     identity retained
```

## Enrollment

An admin-only endpoint creates a short-lived, one-time enrollment value. It is
scoped only to registration. It cannot enumerate sensors, read telemetry, or
perform administration. Registration consumes it; reuse returns `401`. The
frontend does not call this endpoint or embed its result.

## Registration and storage

Registration creates a stable generated `sensor_id` and a random runtime
credential. The token is returned only in the registration response so the
operator can place it in the agent credential store. The central registry
stores a SHA-256 hash, never the token. The agent stores the token in a sibling
`credentials.json`, atomically written with mode `0600` where POSIX permissions
apply. Windows ACLs must be restricted to the service account by the operator;
the file is not an OS credential vault.

## Disable/revocation

`POST /api/v1/sensors/{sensor_id}/disable` is operator-authorized and
non-destructive. The registry record remains for audit and is marked
`DISABLED`/`OFFLINE`. Authentication rejects future telemetry, heartbeat, and
status requests using the old token. No automatic re-enable exists.

## Rotation

`POST /api/v1/sensors/{sensor_id}/rotate-credential` is admin-only. It issues
one new token, immediately replaces the stored hash, and preserves the same
sensor identity and runtime history. The response contains the new token once;
it must be delivered to the agent through a secure operator channel and saved
locally before restart. A brief delivery interruption is possible because the
old token is invalidated immediately. There is no automatic rotation or grace
period in this release.

Audit records include lifecycle event, sensor identity where known, request ID,
result, reason, and source address. They never include either token.
