"""Authentication dependency for dedicated remote sensor credentials."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header, HTTPException, Request, status

from src.api.models import RemoteTelemetryBatch
from src.sensors.registry import InvalidSensorCredentials, SensorNotFound, SensorRegistry


SENSOR_TOKEN_HEADER = "X-Sentinel-Sensor-Token"


def require_sensor(
    request: Request,
    sensor_id: str,
    sensor_token: Annotated[str | None, Header(alias=SENSOR_TOKEN_HEADER)] = None,
) -> dict[str, Any]:
    registry: SensorRegistry = request.app.state.runtime.sensor_registry
    try:
        return registry.authenticate(sensor_id, sensor_token)
    except (InvalidSensorCredentials, SensorNotFound) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SENSOR_CREDENTIAL", "message": "sensor authentication failed"},
            headers={"WWW-Authenticate": "Sensor"},
        ) from exc


def require_telemetry_sensor(
    request: Request,
    body: RemoteTelemetryBatch,
    sensor_token: Annotated[str | None, Header(alias=SENSOR_TOKEN_HEADER)] = None,
) -> dict[str, Any]:
    """Authenticate the sensor identity carried by a telemetry batch."""
    registry: SensorRegistry = request.app.state.runtime.sensor_registry
    try:
        return registry.authenticate(body.sensor_id, sensor_token)
    except (InvalidSensorCredentials, SensorNotFound) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SENSOR_CREDENTIAL", "message": "sensor authentication failed"},
            headers={"WWW-Authenticate": "Sensor"},
        ) from exc
