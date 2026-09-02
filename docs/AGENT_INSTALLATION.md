# Sentinel Agent Installation

This guide is for an operator installing a sensor on a server that should be
observed out of band. Sentinel does not proxy application requests or forward
raw packets.

## Prerequisites

- Python 3.12, 3.13, or 3.14.
- A supported Scapy capture backend: Npcap on Windows or libpcap on Linux.
- Permission to capture the selected interface.
- Outbound HTTPS access from the server to the central Sentinel endpoint.
- A one-time enrollment token created by a central administrator.

## Install

Install the release wheel on the monitored server. For a source checkout,
build first with `python -m build` and install the generated wheel; the
installed command does not require the checkout afterwards.

```powershell
python -m pip install .\dist\sih26_26153-0.1.0-py3-none-any.whl
sentinel-agent --version
```

On Linux, use the equivalent `python3 -m pip install ./dist/...whl` command.

## Initialize and register

```text
sentinel-agent init --server-url https://sentinel.example --interface "Ethernet" --environment production
sentinel-agent register --enrollment-token <one-time-token>
sentinel-agent config validate
```

`register` consumes the enrollment token once and prints only the sensor ID;
the runtime credential is written to the protected sibling credential store,
not to command output or the ordinary configuration JSON.

## Start and verify

```text
sentinel-agent start
```

The foreground process handles SIGTERM and SIGINT, stops capture, flushes
completed state batches where practical, flushes the bounded retry buffer, and
then exits. In another terminal:

```text
sentinel-agent status
sentinel-agent diagnostics
```

The central dashboard shows the sensor only as `ONLINE` after fresh heartbeat
and accepted telemetry. A healthy process with unavailable capture is not
reported as fully healthy.

## Stop and restart

```text
sentinel-agent stop
sentinel-agent restart
```

For unattended operation, install the native service described in
`AGENT_OPERATIONS.md`.

## Configuration and storage

Defaults use the platform application-data location. Set
`SENTINEL_AGENT_HOME` to an approved base directory or
`SENTINEL_AGENT_CONFIG` to an explicit configuration path. The directory holds
configuration, credentials, the bounded telemetry buffer, PID state, and
rotating logs. `config` and `diagnostics` redact the runtime credential.

## Troubleshooting

- `production sensor transport requires https`: use the central TLS endpoint.
- `agent is not registered`: run `register` with a fresh enrollment token.
- `capture interface not found`: inspect interface names with the host capture
  tooling and rerun `init`.
- `Npcap/libpcap is not available`: install the capture backend and grant the
  service account capture permission.
- `UNREACHABLE` or `DEGRADED`: check outbound firewall rules, central health,
  and the local buffer with `status`.

See `AGENT_TROUBLESHOOTING.md` and `AGENT_SECURITY.md` before production use.
