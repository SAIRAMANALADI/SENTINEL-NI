# Environment Support

This matrix distinguishes code paths that are implemented from environments
that were actually exercised. Package compatibility alone is not evidence of
runtime support.

| Capability | Windows | Linux | Docker | Status / evidence |
| --- | --- | --- | --- | --- |
| Agent CLI | Tested on Windows 11, Python 3.14 | Package path documented; physical host not tested | Not the intended capture runtime | CLI, config, diagnostics, and lifecycle tests pass |
| Packet capture | Scapy/Npcap path available on the validation host; no sustained live soak | Scapy/libpcap path documented; host capture not tested | Not supported from the central container | Partially tested; capture permission and interface are host requirements |
| Local live mode | Interface discovery and capture contracts tested; real long run pending | Not run | Not supported by Compose | Environment-dependent |
| Remote telemetry | Automated agent-to-central path tested | Protocol is platform-neutral; physical Linux pair not tested | Central API path only | Implemented and integration-tested; multi-host staging pending |
| systemd service | Windows service manager intentionally not included | Unit file provided; service-manager run not tested here | Not applicable | Documented/packaged, not runtime-verified |
| Central Docker | Docker CLI present but daemon unavailable | Intended deployment target | Compose config and image build path documented | Config/build checks pass; runtime pending |
| TLS | Agent TLS configuration and fail-closed checks tested | Same code path; reverse proxy not tested | TLS termination is external | Configuration tested; staging certificate path pending |
| Dashboard | Frontend typecheck/build tested | Same web runtime | Frontend image build path documented | Browser workflow with real sensors not tested |

## Tested baseline

- Windows 11 Home Single Language, build 10.0.26200.
- Python 3.14.3.
- Scapy 2.7.0 with the configured capture backend.
- Full Python regression suite: 281 passed, 2 warnings at the Phase J
  baseline; rerun the current suite before release claims.

## Runtime prerequisites

- Python `>=3.12,<3.15` for the Python components.
- Npcap with capture permission on Windows, or libpcap and equivalent
  privileges on Linux.
- A trusted TLS endpoint for production remote agents.
- Node.js/npm only for frontend development/builds.
- Docker Desktop or a Linux Docker Engine for Compose runtime validation.

## Not supported by this release

Docker does not receive arbitrary host packet-capture capability. Run the
agent on the monitored host, or use a supported external telemetry source.
NetFlow/IPFIX listeners, mTLS, OIDC, HA, tenant isolation, and a Windows native
service installer remain planned or explicitly outside this release.
