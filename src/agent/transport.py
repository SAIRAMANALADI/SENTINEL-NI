"""Small standard-library JSON transport for the remote sensor agent."""

from __future__ import annotations

import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any
from urllib.parse import urlsplit


class TransportError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def build_tls_context(
    *,
    ca_path: str | None = None,
    client_cert_path: str | None = None,
    client_key_path: str | None = None,
    verify_tls: bool = True,
) -> ssl.SSLContext:
    """Build the HTTPS context used by the agent.

    Certificate verification and hostname checking are enabled by default.
    The insecure branch exists only for an explicitly configured development
    endpoint; production configuration rejects it before any request runs.
    The client certificate/key parameters are an mTLS-ready interface.  They
    load a caller-provided identity but do not implement a CA or PKI.
    """

    context = ssl.create_default_context(cafile=ca_path)
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    if (client_cert_path is None) != (client_key_path is None):
        raise ValueError("client certificate and key must be configured together")
    if client_cert_path and client_key_path:
        context.load_cert_chain(client_cert_path, client_key_path)
    return context


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    ca_path: str | None = None,
    client_cert_path: str | None = None,
    client_key_path: str | None = None,
    verify_tls: bool = True,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(_url(base_url, path), data=body, headers=request_headers, method=method)
    try:
        scheme = urlsplit(request.full_url).scheme.lower()
        context = None
        if scheme == "https":
            context = build_tls_context(
                ca_path=ca_path,
                client_cert_path=client_cert_path,
                client_key_path=client_key_path,
                verify_tls=verify_tls,
            )
        with urlopen(request, timeout=timeout, context=context) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Do not relay arbitrary server response bodies into agent logs or
        # operator CLI output.  The status remains available for retry policy.
        exc.read(512)
        raise TransportError("central service rejected the request", status_code=exc.code) from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise TransportError("sensor transport failed") from exc
    if not isinstance(result, dict):
        raise TransportError("server returned a non-object JSON response")
    return result
