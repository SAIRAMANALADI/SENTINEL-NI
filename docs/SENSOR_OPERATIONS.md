# Sensor Operations

```powershell
python -m src.agent status
python -m src.agent config
python -m src.agent stop
python -m src.agent start
```

Use a host service manager to supervise the agent in production. The local
buffer is bounded and sequence ordered. For a `DEGRADED` sensor, check
connectivity, capture permission, interface name, and buffered batch count. A
full buffer is a delivery failure and must not be treated as successful
collection.

Operators with viewer credentials can use `GET /api/v1/sensors`,
`GET /api/v1/sensors/{sensor_id}`, `/api/v1/health`, and `/api/v1/ready`. The
dashboard Connected servers view reports freshness, buffers, states, and
history readiness; it does not claim central capture of remote packets.
