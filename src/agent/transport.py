"""Small standard-library JSON transport for the remote sensor agent."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


class TransportError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(_url(base_url, path), data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise TransportError(f"server returned HTTP {exc.code}: {detail}", status_code=exc.code) from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise TransportError("sensor transport failed") from exc
    if not isinstance(result, dict):
        raise TransportError("server returned a non-object JSON response")
    return result
