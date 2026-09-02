# Release Candidate Environment Inventory

Phase: L — release-candidate environment validation
Host: `RAMANA`
Validation date: 2026-09-02
Repository: active Git workspace

## Inventory

| Capability | Status | Evidence |
|---|---|---|
| Operating system | AVAILABLE | Windows 11 Home Single Language, build `26200` (`10.0.26200`) |
| Python | AVAILABLE | Python `3.14.3`; project `.venv` is present |
| Docker CLI | AVAILABLE | Docker `29.6.2`; Compose `v5.3.1` |
| Docker daemon/Desktop runtime | NOT AVAILABLE | `docker info` cannot connect to `npipe:////./pipe/dockerDesktopLinuxEngine`; `com.docker.service` is `Stopped` |
| Npcap | AVAILABLE | Windows service `npcap` is `Running` |
| Local packet interface | AVAILABLE | `Wi-Fi` is `Up`; Ethernet is disconnected |
| Linux host/runtime | NOT AVAILABLE | WSL lists only `docker-desktop`, version 2, state `Stopped`; no usable Linux staging host was supplied |
| Second physical host | NOT AVAILABLE | No second host was supplied or reachable for Phase L |
| Local name resolution | AVAILABLE | `localhost` resolves to `::1` and `127.0.0.1` |
| Staging DNS | NOT AVAILABLE | `sentinel.example` does not resolve; no staging hostname was supplied |
| TLS certificate material | NOT AVAILABLE | No repository staging `.pem`, `.crt`, `.cer`, `.p12`, or `.key` files were found outside excluded data/build/runtime paths |
| Reverse proxy | NOT AVAILABLE | No nginx, Caddy, Traefik, or HAProxy process/service was found |

## Interpretation boundary

`AVAILABLE` means the capability was observed in this environment. `NOT AVAILABLE` means the required local prerequisite was absent. These findings do not claim that the capability is impossible on another host. No staging or production infrastructure was inferred from configuration files alone.

The local API can be started directly on loopback for bounded validation. That does not substitute for Docker, TLS, reverse-proxy, or multi-host validation.

## Network/topology observations

The intended Sentinel topology remains out-of-band: customer application traffic does not route through Sentinel. The available local capture path is a host-side Wi-Fi capture using Npcap/libpcap-compatible capture support. No externally reachable staging endpoint was available for the agent-to-central path.
