"""Structured JSON logging with request correlation and secret-safe fields."""

from __future__ import annotations

import contextvars
import json
import logging
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
        for key in ("endpoint", "event_type", "duration_ms", "error_type", "model_version"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=True, allow_nan=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str) -> contextvars.Token[str]:
    return REQUEST_ID.set(request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    REQUEST_ID.reset(token)


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    safe_fields = {key: value for key, value in fields.items() if key not in {"token", "password", "secret", "payload"}}
    logger.info(message, extra=safe_fields)

