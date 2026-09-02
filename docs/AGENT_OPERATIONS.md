# Sentinel Agent Operations

## Native service management

Linux supports a real per-user systemd unit. After installing the wheel and
initializing/registering the agent:

```text
sentinel-agent service install
systemctl --user enable sentinel-agent
systemctl --user start sentinel-agent
systemctl --user status sentinel-agent
systemctl --user stop sentinel-agent
systemctl --user restart sentinel-agent
sentinel-agent service uninstall
```

`service install` writes and enables the unit, and fails if `systemctl` is not
available. It does not delete configuration or identity on uninstall. Enable
lingering for the service account if the user service must start without an
interactive login; that is an explicit host-administrator action.

Windows service installation is intentionally not claimed in this release.
Use an administrator-approved Windows Service Manager or scheduled service
wrapper that launches the installed `sentinel-agent ... start` command and
forwards stop signals. The repository does not silently pretend that a process
wrapper is a Windows service.

## Operational states

The agent reports independent `process_status`, `capture_status`,
`connection_status`, and `telemetry_status`. A central `ONLINE` status requires
fresh heartbeat and telemetry; registration alone is insufficient.

## Logs and bounded resources

Logs are JSON lines at the configured application-data path and rotate at the
configured byte limit with a bounded backup count. Tokens, authorization
headers, payloads, and enrollment credentials are excluded. The telemetry
buffer is bounded by batch count and bytes; `DROP_OLDEST` is an explicit loss
policy and `REJECT_NEW` is available when loss must be surfaced instead.

## Restart behavior

Configuration, sensor identity, credential store, next sequence, and buffered
telemetry survive process restart. Central runtime history is process-local;
the sensor must rebuild ten states before a forecast is available again.
