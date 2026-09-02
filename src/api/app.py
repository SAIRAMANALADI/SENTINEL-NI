"""FastAPI application for the production-oriented forecasting MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.auth import require_role
from src.api.sensors import require_sensor, require_telemetry_sensor
from src.api.models import (
    ErrorResponse,
    ForecastRequest,
    ForecastResponse,
    HealthResponse,
    MetricsResponse,
    MitigationRequest,
    MitigationResponse,
    ModelResponse,
    ReadyResponse,
    SourcePriorityRequest,
    SourcePriorityResponse,
    RemoteTelemetryBatch,
    SensorEnrollmentRequest,
    SensorHeartbeatRequest,
    SensorRegisterRequest,
)
from src.api.services import forecast_payload, mitigation_payload, source_priority_payload
from src.evaluation.operating_policy import load_policy
from src.forecasting.inference import _load_feature_contract
from src.models.lstm_world_model import load_checkpoint
from src.platform.audit import AuditLogger
from src.platform.config import Settings
from src.platform.logging import configure_logging, get_logger, log_event, reset_request_id, set_request_id
from src.platform.metrics import MetricsRegistry
from src.platform.state import ServiceState
from src.streaming.final_demo_engine import run_final_demo
from src.api.live_runtime import LiveRuntimeStore
from src.sensors.registry import (
    InvalidEnrollment,
    SensorNotFound,
    SensorRateLimitExceeded,
    SensorRegistry,
    SensorSequenceConflict,
)
from src.sensors.runtime import RemoteSensorRuntimeStore
from src.telemetry.live import (
    LiveTelemetryError,
    LiveTelemetryPermissionDenied,
    LiveTelemetryUnavailable,
    LiveTelemetryAdapter,
)
from src.telemetry.mock import MockTelemetryAdapter
from src.telemetry.replay import ReplayTelemetryAdapter


LOGGER = get_logger(__name__)
MODEL_VERSION = "LSTM-DEVELOPMENT-V1-direct-multistep-K5"


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.metrics = MetricsRegistry()
        self.audit = AuditLogger(settings.audit_log_path)
        self._readiness: dict[str, Any] | None = None
        self._static_readiness: dict[str, Any] | None = None
        self.live_runtime = LiveRuntimeStore()
        self.telemetry = self._build_telemetry_adapter()
        self.sensor_registry = SensorRegistry(
            settings.sensor_registry_path,
            heartbeat_timeout_seconds=settings.sensor_heartbeat_timeout_seconds,
            telemetry_stale_after_seconds=settings.telemetry_stale_after_seconds,
            rate_limit_per_minute=settings.sensor_rate_limit_per_minute,
        )
        self.remote_sensor_runtime = RemoteSensorRuntimeStore()

    def _on_live_event(self, event: dict[str, Any]) -> bool:
        return self.live_runtime.ingest_event(event)

    def _build_telemetry_adapter(self) -> Any:
        if self.settings.telemetry_mode == "live":
            return LiveTelemetryAdapter(
                self.settings.telemetry_interface,
                stale_after_seconds=self.settings.telemetry_stale_after_seconds,
                event_callback=self._on_live_event,
            )
        if self.settings.telemetry_mode == "replay":
            path = self.settings.telemetry_replay_path or self.settings.demo_events_path
            return ReplayTelemetryAdapter(path)
        return MockTelemetryAdapter()

    def readiness(self, *, refresh: bool = False) -> dict[str, Any]:
        if self._static_readiness is None or refresh:
            checks = {"configuration": False, "schema": False, "policy": False, "model": False}
            reasons: list[str] = []
            try:
                self.settings.validate()
                checks["configuration"] = True
            except (FileNotFoundError, ValueError) as exc:
                reasons.append(str(exc))
            try:
                _load_feature_contract(self.settings.feature_schema_path)
                checks["schema"] = True
            except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
                reasons.append(f"schema: {exc}")
            try:
                load_policy(self.settings.operating_policy_path)
                checks["policy"] = True
            except (OSError, ValueError, TypeError, yaml.YAMLError, KeyError) as exc:
                reasons.append(f"policy: {exc}")
            try:
                model, _ = load_checkpoint(self.settings.model_path, device="cpu")
                checks["model"] = bool(model.config.sequence_length == 10 and model.config.input_size == 17)
                if not checks["model"]:
                    reasons.append("model dimensions do not match the frozen 10-state/17-feature contract")
            except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
                reasons.append(f"model: {exc}")
            self._static_readiness = {"checks": checks, "reasons": reasons}
        checks = dict(self._static_readiness["checks"])
        reasons = list(self._static_readiness["reasons"])
        telemetry_status = self.telemetry.status()
        checks["telemetry"] = bool(telemetry_status.get("available"))
        if not checks["telemetry"]:
            reasons.append(str(telemetry_status.get("error") or "telemetry adapter unavailable"))
        ready = all(checks.values()) and not reasons
        if ready:
            service_state = ServiceState.HEALTHY.value
        elif not checks["model"]:
            service_state = ServiceState.MODEL_UNAVAILABLE.value
        elif not checks["telemetry"]:
            service_state = ServiceState.TELEMETRY_UNAVAILABLE.value
        else:
            service_state = ServiceState.DEGRADED.value
        self._readiness = {"ready": ready, "checks": checks, "reasons": reasons, "service_state": service_state}
        return self._readiness

    def require_ready(self) -> None:
        state = self.readiness()
        if not state["ready"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SERVICE_NOT_READY",
                    "message": "forecast service is not ready",
                    "service_state": state["service_state"],
                    "checks": state["checks"],
                    "reasons": state["reasons"],
                },
            )

    def telemetry_status(self) -> dict[str, Any]:
        status_payload = dict(self.telemetry.status())
        status_payload.setdefault("mode", self.settings.telemetry_mode)
        status_payload.setdefault("interface", self.settings.telemetry_interface)
        status_payload.setdefault("status", "RUNNING" if status_payload.get("started") else "STOPPED")
        status_payload.setdefault("started_at", None)
        status_payload.setdefault("last_event_at", None)
        status_payload.setdefault("event_count", status_payload.get("read_count", 0))
        status_payload.setdefault("stale", False)
        if self.settings.telemetry_mode == "live":
            status_payload["source_intervals_completed"] = self.live_runtime.source_intervals_completed
            status_payload["session_id"] = self.live_runtime.session_id
        status_value = str(status_payload.get("status", "STOPPED"))
        running = status_value in {"RUNNING", "LIVE_RUNNING"} or bool(status_payload.get("started"))
        if running and status_payload.get("stale"):
            status_payload["service_state"] = ServiceState.DATA_STALE.value
        elif not status_payload.get("available"):
            status_payload["service_state"] = ServiceState.TELEMETRY_UNAVAILABLE.value
        else:
            status_payload["service_state"] = ServiceState.HEALTHY.value
        if running:
            status_payload["freshness"] = "DATA STALE" if status_payload.get("stale") else "DATA FRESH"
        elif status_payload.get("last_event_at"):
            status_payload["freshness"] = f"LAST LIVE UPDATE: {status_payload['last_event_at']}"
        else:
            status_payload["freshness"] = "NOT CURRENT"
        return status_payload

    def start_telemetry(self) -> dict[str, Any]:
        if self.settings.telemetry_mode != "live":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "LIVE_MODE_REQUIRED", "message": "set SIH_TELEMETRY_MODE=live before starting capture"},
            )
        try:
            telemetry_before_start = self.telemetry.status()
            already_running = telemetry_before_start.get("status") == "LIVE_RUNNING" or bool(
                telemetry_before_start.get("started")
            )
            if not already_running:
                # Reset before starting the sniffer so packets captured
                # immediately during adapter.start() belong to this session.
                self.live_runtime.start_session()
            self.telemetry.start()
        except LiveTelemetryPermissionDenied as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CAPTURE_PERMISSION_DENIED", "message": str(exc)},
            ) from exc
        except (LiveTelemetryUnavailable, LiveTelemetryError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "CAPTURE_UNAVAILABLE", "message": str(exc)},
            ) from exc
        return self.telemetry_status()

    def stop_telemetry(self) -> dict[str, Any]:
        self.telemetry.stop()
        return self.telemetry_status()

    def live_status(self) -> dict[str, Any]:
        return self.live_runtime.snapshot(self.telemetry_status())


def _error_payload(code: str, message: str, request: Request, **details: Any) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", "-"),
            **details,
        }
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    configure_logging(runtime_settings.log_level)
    runtime = Runtime(runtime_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            runtime.telemetry.stop()

    app = FastAPI(
        title="SIH26 Forecast Service",
        version="1.0.0",
        docs_url=None if runtime_settings.environment == "production" else "/docs",
        redoc_url=None if runtime_settings.environment == "production" else "/redoc",
        lifespan=lifespan,
    )
    app.state.runtime = runtime

    @app.middleware("http")
    async def request_middleware(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()
        runtime = request.app.state.runtime
        runtime.metrics.increment("request_count")
        try:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    declared_bytes = int(content_length)
                except ValueError:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content=_error_payload("INVALID_CONTENT_LENGTH", "Content-Length must be an integer", request),
                    )
                if declared_bytes > runtime.settings.max_request_bytes:
                    runtime.metrics.increment("request_too_large_count")
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content=_error_payload(
                            "REQUEST_TOO_LARGE",
                            "request body exceeds the configured limit",
                            request,
                            max_request_bytes=runtime.settings.max_request_bytes,
                        ),
                    )
            response = await call_next(request)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            if response.status_code >= 400:
                runtime.metrics.increment("error_count")
            return response
        except Exception as exc:
            runtime.metrics.increment("error_count")
            LOGGER.exception("unhandled API error", extra={"endpoint": request.url.path, "error_type": type(exc).__name__})
            raise
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            runtime.metrics.observe("request_latency", elapsed)
            reset_request_id(token)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request.app.state.runtime.metrics.increment("validation_error_count")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_payload(
                "VALIDATION_ERROR",
                "request validation failed",
                request,
                details=jsonable_encoder(exc.errors(), custom_encoder={ValueError: str}),
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        code = detail.pop("code", "HTTP_ERROR")
        message = detail.pop("message", "request failed")
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=_error_payload(code, message, request, **detail),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        request.app.state.runtime.metrics.increment("contract_error_count")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_payload("CONTRACT_ERROR", str(exc), request),
        )

    def sensor_view(sensor_id: str) -> dict[str, Any]:
        try:
            sensor = runtime.sensor_registry.get(sensor_id)
        except SensorNotFound as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SENSOR_NOT_FOUND", "message": "sensor was not found"},
            ) from exc
        sensor["runtime"] = runtime.remote_sensor_runtime.snapshot(sensor_id)
        return sensor

    @app.post("/api/v1/sensors/enrollment")
    async def create_sensor_enrollment(
        body: SensorEnrollmentRequest,
        _: str = Depends(require_role("admin")),
    ) -> dict[str, Any]:
        return runtime.sensor_registry.create_enrollment(expires_in_seconds=body.expires_in_seconds)

    @app.post("/api/v1/sensors/register")
    async def register_sensor(body: SensorRegisterRequest) -> dict[str, Any]:
        try:
            registered = runtime.sensor_registry.register(
                enrollment_token=body.enrollment_token,
                hostname=body.hostname,
                agent_version=body.agent_version,
            )
        except InvalidEnrollment as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_ENROLLMENT", "message": "enrollment credential is invalid or expired"},
            ) from exc
        log_event(LOGGER, "sensor registered", event_type="registration_succeeded", sensor_id=registered["sensor_id"])
        runtime.audit.record(
            event_type="sensor_registration",
            model_version="control-plane-v1",
            policy_version="sensor-v1",
            sensor_id=registered["sensor_id"],
            result="accepted",
        )
        return {"schema_version": "1", **registered}

    @app.get("/api/v1/sensors")
    async def list_sensors(_: str = Depends(require_role("viewer"))) -> dict[str, Any]:
        sensors = []
        for sensor in runtime.sensor_registry.list():
            sensor["runtime"] = runtime.remote_sensor_runtime.snapshot(sensor["sensor_id"])
            sensors.append(sensor)
        return {"count": len(sensors), "sensors": sensors}

    @app.get("/api/v1/sensors/{sensor_id}")
    async def get_sensor(sensor_id: str, _: str = Depends(require_role("viewer"))) -> dict[str, Any]:
        return sensor_view(sensor_id)

    @app.get("/api/v1/sensors/{sensor_id}/status")
    async def get_sensor_status(
        sensor_id: str,
        sensor: dict[str, Any] = Depends(require_sensor),
    ) -> dict[str, Any]:
        """Return only the authenticated sensor's operational status."""

        del sensor
        return sensor_view(sensor_id)

    @app.post("/api/v1/sensors/{sensor_id}/heartbeat")
    async def sensor_heartbeat(
        sensor_id: str,
        body: SensorHeartbeatRequest,
        sensor: dict[str, Any] = Depends(require_sensor),
    ) -> dict[str, Any]:
        try:
            runtime.sensor_registry.accept_heartbeat(
                sensor_id,
                buffered_item_count=body.buffered_item_count,
                agent_version=body.agent_version,
            )
        except SensorRateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "SENSOR_RATE_LIMITED", "message": "sensor heartbeat rate limit exceeded"},
            ) from exc
        del sensor
        log_event(
            LOGGER,
            "sensor heartbeat accepted",
            event_type="heartbeat_succeeded",
            sensor_id=sensor_id,
            buffered_item_count=body.buffered_item_count,
        )
        runtime.audit.record(
            event_type="sensor_heartbeat",
            model_version="control-plane-v1",
            policy_version="sensor-v1",
            sensor_id=sensor_id,
            result="accepted",
        )
        return sensor_view(sensor_id)

    @app.post("/api/v1/telemetry")
    async def ingest_remote_telemetry(
        body: RemoteTelemetryBatch,
        sensor: dict[str, Any] = Depends(require_telemetry_sensor),
    ) -> dict[str, Any]:
        sensor_id = str(sensor["sensor_id"])
        if body.sensor_id != sensor_id:
            log_event(
                LOGGER,
                "telemetry identity mismatch",
                event_type="telemetry_rejected",
                sensor_id=sensor_id,
                sequence=body.sequence,
            )
            runtime.audit.record(
                event_type="telemetry_rejected",
                model_version="telemetry-v1",
                policy_version="sensor-v1",
                sensor_id=sensor_id,
                sequence=body.sequence,
                result="identity_mismatch",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "SENSOR_ID_MISMATCH", "message": "telemetry identity does not match the credential"},
            )
        previous = None
        for state_point in body.states:
            if state_point.timestamp.date() != state_point.capture_day:
                raise ValueError("state timestamp must belong to capture_day")
            if previous is not None:
                if state_point.capture_day != previous.capture_day:
                    raise ValueError("one telemetry batch cannot cross capture-day boundaries")
                if state_point.timestamp - previous.timestamp != timedelta(seconds=10):
                    raise ValueError("telemetry states must be contiguous 10-second intervals")
            previous = state_point
        canonical = body.model_dump(mode="json")
        batch_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        try:
            decision = runtime.sensor_registry.check_telemetry(
                sensor_id, sequence=body.sequence, batch_hash=batch_hash
            )
        except SensorSequenceConflict as exc:
            log_event(
                LOGGER,
                "telemetry sequence conflict",
                event_type="telemetry_rejected",
                sensor_id=sensor_id,
                sequence=body.sequence,
            )
            runtime.audit.record(
                event_type="telemetry_rejected",
                model_version="telemetry-v1",
                policy_version="sensor-v1",
                sensor_id=sensor_id,
                sequence=body.sequence,
                result="sequence_conflict",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "SENSOR_SEQUENCE_CONFLICT", "message": str(exc)},
            ) from exc
        if decision == "duplicate":
            log_event(
                LOGGER,
                "duplicate telemetry acknowledged",
                event_type="telemetry_duplicate",
                sensor_id=sensor_id,
                sequence=body.sequence,
            )
            runtime.audit.record(
                event_type="telemetry_duplicate",
                model_version="telemetry-v1",
                policy_version="sensor-v1",
                sensor_id=sensor_id,
                sequence=body.sequence,
                result="duplicate_acknowledged",
            )
            return {
                "schema_version": "1",
                "sensor_id": sensor_id,
                "sequence": body.sequence,
                "status": "DUPLICATE_ACKNOWLEDGED",
                "forecast": runtime.remote_sensor_runtime.snapshot(sensor_id),
            }
        try:
            runtime.sensor_registry.check_rate(sensor_id)
        except SensorRateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "SENSOR_RATE_LIMITED", "message": "sensor telemetry rate limit exceeded"},
            ) from exc
        states = [state.model_dump(mode="json") for state in body.states]
        result = runtime.remote_sensor_runtime.ingest(sensor_id, states)
        try:
            runtime.sensor_registry.accept_telemetry(
                sensor_id,
                sequence=body.sequence,
                batch_hash=batch_hash,
                buffered_item_count=0,
            )
        except SensorRateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "SENSOR_RATE_LIMITED", "message": "sensor telemetry rate limit exceeded"},
            ) from exc
        log_event(
            LOGGER,
            "telemetry batch accepted",
            event_type="telemetry_accepted",
            sensor_id=sensor_id,
            sequence=body.sequence,
            state_count=len(body.states),
        )
        runtime.audit.record(
            event_type="telemetry_accepted",
            model_version="telemetry-v1",
            policy_version="sensor-v1",
            sensor_id=sensor_id,
            sequence=body.sequence,
            result="accepted",
        )
        return {
            "schema_version": "1",
            "sensor_id": sensor_id,
            "sequence": body.sequence,
            "status": "ACCEPTED",
            "forecast": result,
        }

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service_state=ServiceState.HEALTHY.value,
            request_id=request.state.request_id,
        )

    @app.get("/api/v1/ready", response_model=ReadyResponse)
    async def ready(request: Request, response: Response) -> ReadyResponse:
        state = request.app.state.runtime.readiness()
        if not state["ready"]:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(**state, request_id=request.state.request_id)

    @app.get("/api/v1/model", response_model=ModelResponse)
    async def model_info(request: Request, _: str = Depends(require_role("viewer"))) -> ModelResponse:
        runtime: Runtime = request.app.state.runtime
        runtime.require_ready()
        schema_columns, schema_version = _load_feature_contract(runtime.settings.feature_schema_path)
        policy = load_policy(runtime.settings.operating_policy_path)
        mode = str(policy["primary_mode"])
        return ModelResponse(
            model_version=MODEL_VERSION,
            feature_schema_version=schema_version,
            target_version="docs/TARGET_STATE_SPEC.md",
            policy_version=str(policy.get("policy_version", "unknown")),
            sequence_length=10,
            feature_count=len(schema_columns),
            forecast_horizon_seconds=50,
            score_name=str(policy.get("score_name", "Forecast Score")),
            threshold=float(policy["modes"][mode]["threshold"]),
            loaded=True,
        )

    @app.post("/api/v1/forecast", response_model=ForecastResponse)
    async def forecast(request: Request, body: ForecastRequest, _: str = Depends(require_role("viewer"))) -> ForecastResponse:
        runtime: Runtime = request.app.state.runtime
        runtime.require_ready()
        started = time.perf_counter()
        result = forecast_payload(body.sequence, body.top_n, runtime.settings)
        elapsed = (time.perf_counter() - started) * 1000
        runtime.metrics.increment("forecast_count")
        runtime.metrics.observe("inference_latency", elapsed)
        warning = bool(result["forecast"][0]["warning"])
        log_event(LOGGER, "forecast event", endpoint=request.url.path, duration_ms=elapsed, event_type="forecast")
        runtime.audit.record(
            event_type="forecast",
            model_version=result["model_version"],
            policy_version=result["policy_version"],
            forecast_warning=warning,
            session_id=runtime.live_runtime.session_id,
        )
        return ForecastResponse(**result)

    @app.post("/api/v1/source-priority", response_model=SourcePriorityResponse)
    async def source_priority(
        request: Request,
        body: SourcePriorityRequest,
        _: str = Depends(require_role("operator")),
    ) -> SourcePriorityResponse:
        runtime: Runtime = request.app.state.runtime
        started = time.perf_counter()
        result = source_priority_payload(body)
        elapsed = (time.perf_counter() - started) * 1000
        runtime.metrics.increment("source_priority_count")
        runtime.metrics.observe("source_analysis_latency", elapsed)
        log_event(LOGGER, "source-priority event", endpoint=request.url.path, duration_ms=elapsed, event_type="source_priority")
        for row in result["source_priorities"]:
            runtime.audit.record(
                event_type="source_priority",
                model_version=MODEL_VERSION,
                policy_version="operating-policy-v1",
                forecast_warning=bool(row.get("forecast_context", {}).get("network_warning")),
                candidate_source=str(row.get("source_ip")),
                session_id=runtime.live_runtime.session_id,
            )
        return SourcePriorityResponse(**result)

    @app.post("/api/v1/mitigation", response_model=MitigationResponse)
    async def mitigation(
        request: Request,
        body: MitigationRequest,
        _: str = Depends(require_role("operator")),
    ) -> MitigationResponse:
        runtime: Runtime = request.app.state.runtime
        started = time.perf_counter()
        result = mitigation_payload(body)
        elapsed = (time.perf_counter() - started) * 1000
        runtime.metrics.increment("mitigation_recommendation_count", len(result["recommendations"]))
        runtime.metrics.observe("mitigation_latency", elapsed)
        log_event(LOGGER, "mitigation recommendation event", endpoint=request.url.path, duration_ms=elapsed, event_type="mitigation")
        for row in result["recommendations"]:
            runtime.audit.record(
                event_type="mitigation",
                model_version=MODEL_VERSION,
                policy_version="operating-policy-v1",
                candidate_source=str(row.get("source_ip")),
                mitigation_recommendation=str(row.get("recommendation")),
                session_id=runtime.live_runtime.session_id,
            )
        return MitigationResponse(**result)

    @app.post("/api/v1/demo")
    async def demo(request: Request, _: str = Depends(require_role("operator"))) -> dict[str, Any]:
        """Demo-only orchestration endpoint used by the Streamlit client."""

        runtime: Runtime = request.app.state.runtime
        runtime.require_ready()
        started = time.perf_counter()
        result = run_final_demo(runtime.settings.demo_events_path)
        elapsed = (time.perf_counter() - started) * 1000
        runtime.metrics.increment("demo_count")
        runtime.metrics.observe("demo_latency", elapsed)
        log_event(LOGGER, "full integrated demo event", endpoint=request.url.path, duration_ms=elapsed, event_type="demo")
        network = result["network_forecast"]
        runtime.audit.record(
            event_type="forecast",
            model_version=network["model_version"],
            policy_version="operating-policy-v1",
            forecast_warning=bool(network["forecasts"][0]["warning"]),
        )
        for row in result["mitigation_recommendations"]:
            runtime.audit.record(
                event_type="mitigation",
                model_version=network["model_version"],
                policy_version="operating-policy-v1",
                candidate_source=str(row["source_ip"]),
                mitigation_recommendation=str(row["recommendation"]),
            )
        return result

    @app.get("/api/v1/telemetry")
    async def telemetry(request: Request, _: str = Depends(require_role("viewer"))) -> dict[str, Any]:
        return request.app.state.runtime.telemetry_status()

    @app.get("/api/v1/live")
    async def live(request: Request, _: str = Depends(require_role("viewer"))) -> dict[str, Any]:
        """Read the current bounded live runtime state without side effects."""

        return request.app.state.runtime.live_status()

    @app.post("/api/v1/telemetry/start")
    async def telemetry_start(request: Request, _: str = Depends(require_role("operator"))) -> dict[str, Any]:
        return request.app.state.runtime.start_telemetry()

    @app.post("/api/v1/telemetry/stop")
    async def telemetry_stop(request: Request, _: str = Depends(require_role("operator"))) -> dict[str, Any]:
        return request.app.state.runtime.stop_telemetry()

    @app.get("/api/v1/metrics", response_model=MetricsResponse)
    async def metrics(request: Request, _: str = Depends(require_role("operator"))) -> MetricsResponse:
        return MetricsResponse(**request.app.state.runtime.metrics.snapshot())

    @app.get("/api/v1/security-contract", response_model=dict[str, Any])
    async def security_contract(_: str = Depends(require_role("admin"))) -> dict[str, Any]:
        return {
            "automatic_blocking": False,
            "raw_payload_logging": False,
            "cors": "not enabled by default",
            "upload_endpoints": False,
        }

    return app


app = create_app()
