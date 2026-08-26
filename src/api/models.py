"""Pydantic request and response contracts for API v1."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, IPvAnyAddress, field_validator


MAX_SOURCE_PRIORITY_EVENTS = 4096
MAX_MITIGATION_SOURCES = 1024


class StatePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    capture_day: date
    features: dict[str, FiniteFloat] = Field(min_length=17, max_length=17)


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: list[StatePoint] = Field(min_length=10, max_length=10)
    top_n: int = Field(default=5, ge=1, le=20)


class ForecastRow(BaseModel):
    step: int
    horizon_seconds: int
    timestamp: str
    score: FiniteFloat
    warning: bool


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str
    feature_schema_version: str
    target_version: str
    policy_version: str
    capture_day: str
    reference_timestamp: str
    forecast_horizon_seconds: int
    forecast: list[ForecastRow]
    operating_mode: str
    threshold: FiniteFloat
    explanation: dict[str, Any]
    timing_ms: dict[str, FiniteFloat]
    service_state: str = "HEALTHY"


class PacketEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    source_ip: IPvAnyAddress
    destination_ip: IPvAnyAddress
    source_port: int = Field(ge=0, le=65535)
    destination_port: int = Field(ge=0, le=65535)
    protocol: str = Field(min_length=1, max_length=32)
    packet_length: FiniteFloat = Field(ge=0)
    tcp_flags: str = ""

    @field_validator("protocol")
    @classmethod
    def protocol_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("protocol must not be blank")
        return value


class SourcePriorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[PacketEvent] = Field(min_length=1, max_length=MAX_SOURCE_PRIORITY_EVENTS)
    forecast_score: FiniteFloat | None = None
    network_warning: bool | None = None
    reference_timestamp: datetime | None = None


class SourcePriorityResponse(BaseModel):
    service_state: str
    source_count: int
    source_priorities: list[dict[str, Any]]


class SourcePriorityInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_ip: IPvAnyAddress
    priority: str
    priority_points: int = Field(ge=0)


class MitigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourcePriorityInput] = Field(min_length=1, max_length=MAX_MITIGATION_SOURCES)


class MitigationResponse(BaseModel):
    service_state: str
    simulation_only: bool
    recommendations: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    service_state: str
    request_id: str


class ReadyResponse(BaseModel):
    ready: bool
    service_state: str
    checks: dict[str, bool]
    reasons: list[str]
    request_id: str


class ModelResponse(BaseModel):
    model_version: str
    feature_schema_version: str
    target_version: str
    policy_version: str
    sequence_length: int
    feature_count: int
    forecast_horizon_seconds: int
    score_name: str
    threshold: FiniteFloat
    loaded: bool


class MetricsResponse(BaseModel):
    counters: dict[str, int]
    latencies: dict[str, dict[str, Any]]


class ErrorResponse(BaseModel):
    error: dict[str, Any]
