"""Structured JSON logging with request correlation and secret-safe fields."""

from __future__ import annotations

import contextvars
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
from typing import Any


REQUEST_ID = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": REQUEST_ID.get(),
        }
        for key in (
            "endpoint",
            "event_type",
            "duration_ms",
            "error_type",
            "model_version",
            "sensor_id",
            "sequence",
            "state_count",
            "status_code",
            "buffered_item_count",
            "retry_delay_seconds",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=True, allow_nan=False)


def configure_logging(
    level: str = "INFO",
    *,
    log_path: str | Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved = path.resolve()
        if not any(
            isinstance(handler, RotatingFileHandler)
            and Path(getattr(handler, "baseFilename", "")).resolve() == resolved
            for handler in root.handlers
        ):
            file_handler = RotatingFileHandler(
                path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(JsonFormatter())
            root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str) -> contextvars.Token[str]:
    return REQUEST_ID.set(request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    REQUEST_ID.reset(token)


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    safe_fields = {key: value for key, value in fields.items() if key not in {"token", "password", "secret", "payload"}}
    logger.info(message, extra=safe_fields)
