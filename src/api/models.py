"""Pydantic request and response contracts for API v1."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, IPvAnyAddress, field_validator, model_validator

from src.features.network_state import FEATURE_COLUMNS


MAX_SOURCE_PRIORITY_EVENTS = 4096
MAX_MITIGATION_SOURCES = 1024
MAX_REMOTE_STATES_PER_BATCH = 60
MAX_REMOTE_SOURCE_ACTIVITY_PER_BATCH = 120
MAX_REMOTE_SOURCES_PER_WINDOW = 256


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


class SensorHealthResponse(BaseModel):
    """Read-only health contract for one registered sensor."""

    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    status: str
    registration_state: str
    disabled: bool
    health: dict[str, str]
    source_status: str
    telemetry_freshness_seconds: FiniteFloat | None = None
    heartbeat_freshness_seconds: FiniteFloat | None = None
    capture_status: str
    connection_status: str
    last_seen: str | None = None
    last_heartbeat: str | None = None
    last_telemetry_at: str | None = None


class SensorForecastResponse(BaseModel):
    """Current cached forecast for one sensor; pending history is not an error."""

    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    status: str
    forecast_ready: bool
    forecast: dict[str, Any] | None = None


class SensorSourcesResponse(BaseModel):
    """Candidate-source evidence scoped to one sensor."""

    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    status: str
    source_count: int
    source_priorities: list[dict[str, Any]]
    source_attribution: dict[str, Any]


class SensorMitigationResponse(BaseModel):
    """Recommendation-only mitigation output scoped to one sensor."""

    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    source_status: str
    simulation_only: bool
    recommendations: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: dict[str, Any]


class SensorEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_in_seconds: int = Field(default=600, ge=60, le=86_400)


class SensorRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: str = Field(min_length=20, max_length=256)
    hostname: str = Field(min_length=1, max_length=255)
    agent_version: str = Field(min_length=1, max_length=64)


class SensorHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buffered_item_count: int = Field(default=0, ge=0, le=100_000)
    buffered_bytes: int = Field(default=0, ge=0, le=1_000_000_000)
    agent_version: str | None = Field(default=None, min_length=1, max_length=64)
    capture_status: str = Field(default="UNKNOWN", min_length=1, max_length=32)
    last_telemetry_at: datetime | None = None
    last_state_timestamp: str | None = Field(default=None, max_length=64)
    last_sent_sequence: int = Field(default=0, ge=0)
    last_acknowledged_sequence: int = Field(default=0, ge=0)
    last_error: str | None = Field(default=None, max_length=240)

    @field_validator("last_telemetry_at")
    @classmethod
    def telemetry_timestamp_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("last_telemetry_at must include a timezone")
        return value


class RemoteStatePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    capture_day: date
    features: dict[str, FiniteFloat] = Field(min_length=17, max_length=17)

    @field_validator("features")
    @classmethod
    def features_must_match_frozen_schema(cls, value: dict[str, FiniteFloat]) -> dict[str, FiniteFloat]:
        expected = set(FEATURE_COLUMNS)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            detail = []
            if missing:
                detail.append(f"missing={missing}")
            if unexpected:
                detail.append(f"unexpected={unexpected}")
            raise ValueError("features must match the frozen 17-feature schema (" + ", ".join(detail) + ")")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("state timestamp must include a timezone")
        return value


class RemoteSourceActivityPoint(BaseModel):
    """One authenticated, metadata-only source activity row.

    These fields are source intelligence, never model features.  The source
    identity is deliberately scoped to the enclosing sensor telemetry batch.
    """

    model_config = ConfigDict(extra="forbid")

    source_ip: IPvAnyAddress
    capture_day: date
    interval_start: datetime
    interval_end: datetime
    flow_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    byte_count: FiniteFloat = Field(ge=0)
    unique_destinations: int = Field(ge=0)
    unique_destination_ports: int = Field(ge=0)
    mean_packet_size: FiniteFloat = Field(ge=0)
    mean_iat: FiniteFloat = Field(ge=0)
    syn_count: int = Field(ge=0)
    ack_count: int = Field(ge=0)
    rst_count: int = Field(ge=0)
    packet_rate: FiniteFloat = Field(ge=0)
    byte_rate: FiniteFloat = Field(ge=0)

    @field_validator("interval_start", "interval_end")
    @classmethod
    def interval_timestamps_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source activity interval timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_interval(self) -> "RemoteSourceActivityPoint":
        if self.interval_start.date() != self.capture_day or self.interval_end.date() != self.capture_day:
            raise ValueError("source activity interval must belong to capture_day")
        if self.interval_end - self.interval_start != timedelta(seconds=10):
            raise ValueError("source activity intervals must be exactly 10 seconds")
        if self.interval_start.second % 10 or self.interval_start.microsecond:
            raise ValueError("source activity interval_start must be aligned to 10 seconds")
        if self.flow_count < 0 or self.packet_count < 0:
            raise ValueError("source activity counts must be non-negative")
        if self.syn_count > self.packet_count or self.ack_count > self.packet_count or self.rst_count > self.packet_count:
            raise ValueError("TCP flag counts cannot exceed packet_count")
        return self


class RemoteTelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    sensor_id: str = Field(min_length=8, max_length=64, pattern=r"^sensor-[a-f0-9]{16}$")
    sequence: int = Field(ge=1)
    sent_at: datetime
    states: list[RemoteStatePoint] = Field(min_length=1, max_length=MAX_REMOTE_STATES_PER_BATCH)
    source_schema_version: Literal["1"] | None = None
    source_activity: list[RemoteSourceActivityPoint] = Field(
        default_factory=list, max_length=MAX_REMOTE_SOURCE_ACTIVITY_PER_BATCH
    )

    @field_validator("sent_at")
    @classmethod
    def sent_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("sent_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_source_activity(self) -> "RemoteTelemetryBatch":
        if self.source_activity and self.source_schema_version != "1":
            raise ValueError("source_schema_version='1' is required when source_activity is present")
        keys = [(str(row.source_ip), row.interval_start) for row in self.source_activity]
        if len(keys) != len(set(keys)):
            raise ValueError("source_activity contains duplicate source/window rows")
        windows: dict[datetime, set[str]] = {}
        for source_ip, interval_start in keys:
            windows.setdefault(interval_start, set()).add(source_ip)
        if any(len(sources) > MAX_REMOTE_SOURCES_PER_WINDOW for sources in windows.values()):
            raise ValueError(
                f"source_activity exceeds {MAX_REMOTE_SOURCES_PER_WINDOW} sources in one 10-second window"
            )
        return self
