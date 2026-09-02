"""Small explicit registry for telemetry source adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.telemetry.contracts import SourceType


class UnsupportedSourceError(RuntimeError):
    """The requested source is known but not enabled in this release."""


class CollectorRegistry:
    """Map source identities to factories without a source-specific pipeline."""

    def __init__(self, factories: dict[SourceType, Callable[..., Any]], unsupported: set[SourceType] | None = None) -> None:
        self._factories = dict(factories)
        self._unsupported = set(unsupported or set())

    @classmethod
    def default(cls) -> "CollectorRegistry":
        # Imports stay here so the source modules can refer to the error type
        # without creating an import cycle during package initialization.
        from src.telemetry.collectors.ipfix import IPFIXCollector
        from src.telemetry.collectors.netflow import NetFlowCollector
        from src.telemetry.collectors.scapy import ScapyCollector
        from src.telemetry.collectors.zeek import ZeekCollector
        from src.telemetry.mock import MockTelemetryAdapter
        from src.telemetry.replay import ReplayTelemetryAdapter

        return cls(
            {
                SourceType.LOCAL_PACKET_CAPTURE: ScapyCollector,
                SourceType.ZEEK: ZeekCollector,
                SourceType.REPLAY: ReplayTelemetryAdapter,
                SourceType.MOCK: MockTelemetryAdapter,
                SourceType.NETFLOW: NetFlowCollector,
                SourceType.IPFIX: IPFIXCollector,
            },
            unsupported={SourceType.NETFLOW, SourceType.IPFIX},
        )

    def create(self, source_type: SourceType | str, **kwargs: Any) -> Any:
        try:
            source = SourceType(source_type)
        except ValueError as exc:
            raise UnsupportedSourceError(f"unknown telemetry source: {source_type}") from exc
        if source in self._unsupported:
            raise UnsupportedSourceError(f"{source.value} is not supported by this release")
        factory = self._factories.get(source)
        if factory is None:
            raise UnsupportedSourceError(f"no collector registered for {source.value}")
        return factory(**kwargs)

    def supported_sources(self) -> tuple[str, ...]:
        return tuple(source.value for source in self._factories if source not in self._unsupported)

    def registered_sources(self) -> tuple[str, ...]:
        return tuple(source.value for source in self._factories)
