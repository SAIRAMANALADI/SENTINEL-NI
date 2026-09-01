"""Append-only, JSONL audit records for forecast and recommendation events."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        event_type: str,
        model_version: str,
        policy_version: str,
        forecast_warning: bool | None = None,
        candidate_source: str | None = None,
        mitigation_recommendation: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_version": str(model_version),
            "policy_version": str(policy_version),
            "event_type": str(event_type),
            "forecast_warning": forecast_warning,
            "candidate_source": candidate_source,
            "mitigation_recommendation": mitigation_recommendation,
            "simulation_only": True,
        }
        if session_id is not None:
            record["session_id"] = str(session_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
        return record
