# Sentinel Agent Upgrades

Upgrade the installed package in place while retaining the application-data
directory:

```text
sentinel-agent stop
python -m pip install --upgrade .\dist\sih26_26153-0.1.0-py3-none-any.whl
sentinel-agent config validate
sentinel-agent start
```

Replace the wheel filename with the versioned artifact from the approved
release you are installing. The current public candidate artifact is
`sih26_26153-0.1.0-py3-none-any.whl`; no `0.2.1` project wheel is published.

For a systemd-managed Linux agent, use `systemctl --user stop`, install the
wheel, then `systemctl --user start`. The configuration, credential store,
sensor ID, sequence counter, and queued telemetry remain at their existing
paths. Do not delete the application-data directory during package removal.

Agent version, telemetry schema version, and model version are separate
values. The current agent speaks telemetry schema version `1`; an incompatible
server response is surfaced as a delivery error and is not silently retried
forever.

Credential renewal is not automatic in this release. Re-enrollment is an
explicit administrator operation and must not be used as a routine restart or
upgrade step.
