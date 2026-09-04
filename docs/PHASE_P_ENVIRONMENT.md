# Phase P Environment Record

Validation date: 2026-09-04  
Repository: current SIH26 checkout

## Available and used

- Windows 11, Python 3.14.3, Docker CLI 29.6.2, Docker Desktop Linux daemon, WSL2, and a 4-CPU/3.825-GiB Docker engine.
- Docker Compose and the existing backend, dashboard, and frontend images.
- `nginx:alpine` pulled and run as a real TLS reverse-proxy container on the Compose network.
- `cryptography`, Python `ssl`, and `httpx` for certificate-chain and hostname verification.
- Wi-Fi interface `Wi-Fi` (`10.16.129.129`) with Scapy/Npcap live capture. A 22-second collector probe observed approximately 1,042 packets, emitted three valid states, and reported no drops.
- The actual `sentinel-agent` package entry point and `py -m src.agent` CLI.

## Unavailable or not suitable for this run

- No host-installed `nginx`, Caddy, Traefik, `mkcert`, or OpenSSL binary. The proxy was therefore run from the official Nginx container image and certificates were generated in a temporary directory with Python `cryptography`.
- No second physical host or independently administered staging network was available.
- TruffleHog was not installed (`TRUFFLEHOG=unavailable`). The repository release audit and targeted security tests were still run.
- Windows curl/Schannel did not accept the temporary private CA because its revocation status was unknown. Python certificate verification was used for the authoritative CA, wrong-CA, and hostname-mismatch checks; no `--insecure`/`-k` request was used.

## Explicitly not verified

Expired-certificate behavior, a 30-minute soak, five physical sensors, multi-host routing, customer-path isolation, live network-outage recovery, active-agent recovery across central restart, credential revocation against a running agent, and a public/production ingress were not verified in this environment.

The limitations above are why this run does not qualify the system as `STAGING READY` or production-ready.
