"""Small standard-library client used by Streamlit to call the backend."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def post_json(path: str, payload: dict[str, Any] | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
    base_url = os.getenv("SIH_API_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("SIH_API_TOKEN")
    body = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"backend returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"backend unavailable: {exc.reason}") from exc


def get_json(path: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """Read a backend status resource using the configured bearer token."""

    base_url = os.getenv("SIH_API_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("SIH_API_TOKEN")
    request = urllib.request.Request(
        f"{base_url}{path}",
        headers={**({"Authorization": f"Bearer {token}"} if token else {})},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"backend returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"backend unavailable: {exc.reason}") from exc
