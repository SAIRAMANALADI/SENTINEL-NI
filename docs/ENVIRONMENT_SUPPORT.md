# Environment Support

This matrix distinguishes code paths that are implemented from environments
that were actually exercised. Package compatibility alone is not evidence of
runtime support.

| Capability | Windows | Linux | Docker | Status / evidence |
| --- | --- | --- | --- | --- |
| Agent CLI | **TESTED** on Windows 11 / Python 3.14, including real foreground stop | Package path documented; physical Linux host **NOT VERIFIED** | Not the intended capture runtime | Help, version, config, diagnostics, and lifecycle checks pass |
| Packet capture | **TESTED** with Scapy/Npcap Wi-Fi capture through the remote agent | Scapy/libpcap path documented; physical host **NOT VERIFIED** | Not supported from the central container | Ten contiguous accepted states reached on the Windows validation host |
| Local live mode | Contracts tested; separate central local-live soak **NOT VERIFIED** | **NOT VERIFIED** | Not supported by Compose | Host capture requires interface and privilege access |
| Remote telemetry | **TESTED** agent-to-central HTTPS path and L=10/K=5 forecast | Protocol is platform-neutral; physical Linux pair **NOT VERIFIED** | Central API path only | Multi-host/five-sensor staging **NOT VERIFIED** |
| systemd service | Windows native service intentionally not included | Unit generation documented; service-manager boot/reboot **NOT VERIFIED** | Not applicable | Use an approved external supervisor on Windows |
| Central Docker | **TESTED** with Docker Desktop Linux containers | Intended deployment target; physical Linux runtime **NOT VERIFIED** | **TESTED** config, build, health, restart, down/up | Local Compose only; not staging capacity evidence |
| TLS | **TESTED** trusted private CA, wrong CA, hostname mismatch, HTTPS proxy path | Same code path; public Linux proxy **NOT VERIFIED** | TLS termination is external | Expiry/public DNS/public CA **NOT VERIFIED** |
| Dashboard | **TESTED** typecheck/build and real-sensor/demo browser smoke | Same web runtime; physical Linux browser **NOT VERIFIED** | **TESTED** frontend container health | Forecast-ready real sensor view observed in Phase S |

## Tested baseline

- Windows 11 Home Single Language, build 10.0.26200.
- Python 3.14.3.
- Scapy 2.7.0 with the configured capture backend.
- Full Python regression suite: 319 passed, 2 warnings in the Phase T pass.

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
service installer remain planned or explicitly outside this release. Local
Compose health is not evidence of public staging or production readiness.
