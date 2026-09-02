# Sentinel Agent Security

Production configuration requires an HTTPS server URL with certificate
verification and a registered sensor credential. The server URL cannot contain
embedded credentials, queries, or fragments. Enrollment credentials are
one-time values and runtime credentials are sensor-specific.

The transport accepts a custom CA path and optional client certificate/key
paths. The latter is an mTLS-ready interface only; no PKI or mTLS deployment is
claimed by this release. A development-only `tls_verify=false` setting is
explicit and production configuration rejects it.

The ordinary configuration JSON does not contain the runtime token. The token
is stored in a sibling `credentials.json` file and written atomically with
owner-only mode on POSIX systems. Windows file ACLs remain the responsibility
of the host administrator; this implementation is not an OS credential vault.
Restrict the application-data directory to the service account and never place
it in a shared repository directory.

Logs and CLI output redact tokens and do not include authorization headers or
telemetry payloads. The agent sends completed aggregated states, not packet
payloads, and customer application traffic remains outside the Sentinel path.

The agent uses bounded pending state, retry, disk-buffer, and log resources.
Telemetry delivery uses sensor-scoped monotonic sequences and duplicate hashes;
delayed buffered delivery is supported, but cryptographic anti-replay is not
claimed.
The browser has no agent command channel and never receives an administrator
token. mTLS, OIDC, HA storage, certificate identity, and automatic blocking are
not provided by this release.
