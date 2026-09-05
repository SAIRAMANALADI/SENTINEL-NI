"""Authentication dependency for dedicated remote sensor credentials."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Header, HTTPException, Request, status

from src.api.models import RemoteTelemetryBatch
from src.sensors.registry import InvalidSensorCredentials, SensorNotFound, SensorRegistry


SENSOR_TOKEN_HEADER = "X-Sentinel-Sensor-Token"


def _sensor_security_event(request: Request, *, sensor_id: str, result: str, reason: str) -> None:
    try:
        request.app.state.runtime.audit.record(
            event_type="sensor_authentication_failed",
            model_version="security-v1",
            policy_version="security-policy-v1",
            sensor_id=sensor_id,
            result=result,
            reason=reason,
            request_id=getattr(request.state, "request_id", None),
            source_ip=request.client.host if request.client else None,
        )
    except Exception:
        return


def require_sensor(
    request: Request,
    sensor_id: str,
    sensor_token: Annotated[str | None, Header(alias=SENSOR_TOKEN_HEADER)] = None,
) -> dict[str, Any]:
    registry: SensorRegistry = request.app.state.runtime.sensor_registry
    try:
        return registry.authenticate(sensor_id, sensor_token)
    except (InvalidSensorCredentials, SensorNotFound) as exc:
        _sensor_security_event(request, sensor_id=sensor_id, result="rejected", reason="invalid or inactive sensor credential")
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
        _sensor_security_event(request, sensor_id=body.sensor_id, result="rejected", reason="invalid or inactive sensor credential")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SENSOR_CREDENTIAL", "message": "sensor authentication failed"},
            headers={"WWW-Authenticate": "Sensor"},
        ) from exc


async def require_locked_telemetry_sensor(
    request: Request,
    body: RemoteTelemetryBatch,
    sensor_token: Annotated[str | None, Header(alias=SENSOR_TOKEN_HEADER)] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Hold the sensor transaction lock for the complete telemetry request."""

    sensor = require_telemetry_sensor(request, body, sensor_token)
    registry: SensorRegistry = request.app.state.runtime.sensor_registry
    with registry.telemetry_transaction(str(sensor["sensor_id"])):
        yield sensor
