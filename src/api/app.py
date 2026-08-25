"""FastAPI application for the production-oriented forecasting MVP."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.auth import require_role
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
        self.live_runtime = LiveRuntimeStore()
        self.telemetry = self._build_telemetry_adapter()

    def _on_live_event(self, event: dict[str, Any]) -> None:
        self.live_runtime.ingest_event(event)

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
        if self._readiness is not None and not refresh:
            return self._readiness
        checks = {"configuration": False, "schema": False, "policy": False, "model": False, "telemetry": False}
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
        if status_payload.get("stale"):
            status_payload["service_state"] = ServiceState.DATA_STALE.value
        elif not status_payload.get("available"):
            status_payload["service_state"] = ServiceState.TELEMETRY_UNAVAILABLE.value
        else:
            status_payload["service_state"] = ServiceState.HEALTHY.value
        return status_payload

    def start_telemetry(self) -> dict[str, Any]:
        if self.settings.telemetry_mode != "live":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "LIVE_MODE_REQUIRED", "message": "set SIH_TELEMETRY_MODE=live before starting capture"},
            )
        try:
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
        self.live_runtime.start_session()
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
    app = FastAPI(title="SIH26 Forecast Service", version="1.0.0", docs_url="/docs", redoc_url="/redoc")
    app.state.runtime = Runtime(runtime_settings)

    @app.middleware("http")
    async def request_middleware(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()
        runtime = request.app.state.runtime
        runtime.metrics.increment("request_count")
        try:
            response = await call_next(request)
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
            content=_error_payload("VALIDATION_ERROR", "request validation failed", request, details=exc.errors()),
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
