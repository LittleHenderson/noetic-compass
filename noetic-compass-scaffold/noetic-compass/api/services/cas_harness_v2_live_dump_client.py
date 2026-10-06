"""Strict one-shot transport for a joined CAS Harness live-worker dump.

This module deliberately owns only the HTTP carrier boundary.  It snapshots
and binds the exact request bytes before transport, invokes the worker exactly
once, and returns the exact response bytes.  The joined response binder owns
JSON and domain-schema validation after this boundary.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx

from api.services.cas_harness_v2_joined_executor import (
    JoinedLiveDumpPostSendIndeterminate,
    JoinedLiveDumpPreSendFailure,
)


JOINED_DUMP_PATH = "/sessions/dump"
MAX_JOINED_REQUEST_BYTES = 2_000_000
MAX_JOINED_RESPONSE_BYTES = 2_000_000

_REQUEST_SHA256_HEADER = "X-CAS-Joined-Request-SHA256"
_REQUEST_BYTE_LENGTH_HEADER = "X-CAS-Joined-Request-Byte-Length"
_AUTHORIZATION_SHA256_HEADER = "X-CAS-Joined-Authorization-SHA256"
_RUN_ID_HEADER = "X-CAS-Joined-Run-ID"
_INVOCATION_ID_HEADER = "X-CAS-Joined-Invocation-ID"
_WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"

_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_INVOCATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
_CANONICAL_LENGTH_RE = re.compile(r"^(?:0|[1-9][0-9]{0,7})$")
_DNS_NAME_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?$"
)

_PRE_SEND_MESSAGE = "live-worker dump request failed before transport"
_POST_SEND_MESSAGE = "live-worker dump execution disposition is indeterminate"


class LiveWorkerDumpClientError(RuntimeError):
    """Base error for the strict joined dump transport."""


class LiveWorkerDumpPreSendFailure(
    JoinedLiveDumpPreSendFailure,
    LiveWorkerDumpClientError,
):
    """The request was rejected before the transport boundary was entered."""

    transport_entered = False


class LiveWorkerDumpPostSendIndeterminate(
    JoinedLiveDumpPostSendIndeterminate,
    LiveWorkerDumpClientError,
):
    """The worker may have executed; callers must reconcile and never retry."""

    transport_entered = True
    retry_allowed = False
    reconcile_only = True


@dataclass(frozen=True, slots=True)
class StrictLiveWorkerDumpClientConfig:
    """Immutable live-worker endpoint configuration.

    Validation is performed again at invocation time so all configuration and
    carrier failures remain on the pre-send side of the execution boundary.
    The worker token is intentionally absent from ``repr`` output.
    """

    worker_base_url: str
    worker_token: str = field(repr=False)
    timeout_seconds: float = 60.0


class StrictLiveWorkerDumpClient:
    """POST one exact joined request and never retry it."""

    __slots__ = ("_config", "_http_client")

    def __init__(
        self,
        config: StrictLiveWorkerDumpClientConfig,
        *,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._http_client = http_client

    async def invoke_once(
        self,
        *,
        request_raw: bytes,
        authorization_sha256: str,
        prospective_run_id: str,
        invocation_id: str,
    ) -> bytes:
        """Invoke ``/sessions/dump`` once and return its exact raw bytes.

        Any failure after ``AsyncClient.send`` is entered is deliberately
        collapsed to a non-retryable, reconcile-only indeterminate result.  No
        remote detail or bound identifier is exposed through the exception.
        """

        try:
            endpoint, token, timeout = _validated_config_snapshot(
                self._config,
                http_client=self._http_client,
            )
            body = _validated_request_snapshot(request_raw)
            authorization = _validated_authorization_sha256(
                authorization_sha256
            )
            run_id = _validated_machine_id(prospective_run_id)
            invocation = _validated_invocation_id(invocation_id)
            request_sha256 = hashlib.sha256(body).hexdigest().upper()
            request = self._http_client.build_request(
                "POST",
                endpoint,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    _WORKER_TOKEN_HEADER: token,
                    _REQUEST_SHA256_HEADER: request_sha256,
                    _REQUEST_BYTE_LENGTH_HEADER: str(len(body)),
                    _AUTHORIZATION_SHA256_HEADER: authorization,
                    _RUN_ID_HEADER: run_id,
                    _INVOCATION_ID_HEADER: invocation,
                },
                timeout=httpx.Timeout(timeout),
            )
        except LiveWorkerDumpPreSendFailure:
            raise
        except Exception:
            raise LiveWorkerDumpPreSendFailure(_PRE_SEND_MESSAGE) from None

        # Crossing into ``send`` is the point after which execution may have
        # occurred.  Every exit other than one fully validated 200 response is
        # therefore indeterminate and must not be retried.
        response: httpx.Response | None = None
        try:
            response = await self._http_client.send(
                request,
                stream=True,
                follow_redirects=False,
            )
            if response.status_code != 200:
                raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)

            declared_length = _validated_response_headers(response)
            raw = bytearray()
            async for chunk in response.aiter_raw():
                raw.extend(chunk)
                if len(raw) > MAX_JOINED_RESPONSE_BYTES:
                    raise LiveWorkerDumpPostSendIndeterminate(
                        _POST_SEND_MESSAGE
                    )
            if not raw or len(raw) != declared_length:
                raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)
            return bytes(raw)
        except LiveWorkerDumpPostSendIndeterminate:
            raise
        except asyncio.CancelledError:
            raise LiveWorkerDumpPostSendIndeterminate(
                _POST_SEND_MESSAGE
            ) from None
        except Exception:
            raise LiveWorkerDumpPostSendIndeterminate(
                _POST_SEND_MESSAGE
            ) from None
        finally:
            if response is not None:
                try:
                    await response.aclose()
                except asyncio.CancelledError:
                    raise LiveWorkerDumpPostSendIndeterminate(
                        _POST_SEND_MESSAGE
                    ) from None
                except Exception:
                    # A close failure is still post-send.  Replacing any prior
                    # error with the same generic disposition is intentional:
                    # neither case is retryable and no transport detail escapes.
                    raise LiveWorkerDumpPostSendIndeterminate(
                        _POST_SEND_MESSAGE
                    ) from None


def _fail_pre_send() -> None:
    raise LiveWorkerDumpPreSendFailure(_PRE_SEND_MESSAGE)


def _validated_config_snapshot(
    config: StrictLiveWorkerDumpClientConfig,
    *,
    http_client: httpx.AsyncClient,
) -> tuple[str, str, float]:
    if not isinstance(config, StrictLiveWorkerDumpClientConfig):
        _fail_pre_send()
    if not isinstance(http_client, httpx.AsyncClient) or http_client.is_closed:
        _fail_pre_send()

    base = config.worker_base_url
    token = config.worker_token
    timeout = config.timeout_seconds
    if not isinstance(base, str) or not base or len(base) > 2_048:
        _fail_pre_send()
    if base != base.strip() or any(ord(char) < 0x20 for char in base):
        _fail_pre_send()
    if (
        not isinstance(token, str)
        or not 1 <= len(token) <= 4_096
        or any(not 0x21 <= ord(char) <= 0x7E for char in token)
    ):
        _fail_pre_send()
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or not 0 < float(timeout) <= 300
    ):
        _fail_pre_send()

    try:
        parsed = urlsplit(base)
        port = parsed.port
    except (TypeError, ValueError):
        _fail_pre_send()
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        _fail_pre_send()
    if port is not None and not 1 <= port <= 65_535:
        _fail_pre_send()
    hostname = parsed.hostname
    if not _valid_hostname(hostname):
        _fail_pre_send()
    if parsed.scheme == "http" and not _is_loopback_host(hostname):
        _fail_pre_send()

    endpoint = urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=JOINED_DUMP_PATH,
            query="",
            fragment="",
        )
    )
    return endpoint, token, float(timeout)


def _valid_hostname(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return _DNS_NAME_RE.fullmatch(hostname) is not None
    return True


def _is_loopback_host(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validated_request_snapshot(request_raw: bytes) -> bytes:
    if type(request_raw) is not bytes or not 1 <= len(request_raw) <= MAX_JOINED_REQUEST_BYTES:
        _fail_pre_send()

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise ValueError("non-finite number")

    try:
        parsed = json.loads(
            request_raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        _fail_pre_send()
    if not isinstance(parsed, dict):
        _fail_pre_send()
    return bytes(request_raw)


def _validated_authorization_sha256(value: str) -> str:
    if not isinstance(value, str) or _UPPER_SHA256_RE.fullmatch(value) is None:
        _fail_pre_send()
    return value


def _validated_machine_id(value: str) -> str:
    if not isinstance(value, str) or _MACHINE_ID_RE.fullmatch(value) is None:
        _fail_pre_send()
    return value


def _validated_invocation_id(value: str) -> str:
    if not isinstance(value, str) or _INVOCATION_ID_RE.fullmatch(value) is None:
        _fail_pre_send()
    return value


def _validated_response_headers(response: httpx.Response) -> int:
    content_types = response.headers.get_list("content-type")
    content_lengths = response.headers.get_list("content-length")
    if len(content_types) != 1 or len(content_lengths) != 1:
        raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)
    if not _is_json_content_type(content_types[0]):
        raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)

    length_text = content_lengths[0]
    if _CANONICAL_LENGTH_RE.fullmatch(length_text) is None:
        raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)
    declared_length = int(length_text)
    if not 1 <= declared_length <= MAX_JOINED_RESPONSE_BYTES:
        raise LiveWorkerDumpPostSendIndeterminate(_POST_SEND_MESSAGE)
    return declared_length


def _is_json_content_type(value: str) -> bool:
    parts = [part.strip() for part in value.split(";")]
    if not parts or parts[0].casefold() != "application/json":
        return False
    if len(parts) == 1:
        return True
    if len(parts) != 2 or "=" not in parts[1]:
        return False
    name, charset = (item.strip() for item in parts[1].split("=", 1))
    return name.casefold() == "charset" and charset.casefold() in {
        "utf-8",
        '"utf-8"',
    }


__all__ = [
    "JOINED_DUMP_PATH",
    "MAX_JOINED_REQUEST_BYTES",
    "MAX_JOINED_RESPONSE_BYTES",
    "LiveWorkerDumpClientError",
    "LiveWorkerDumpPreSendFailure",
    "LiveWorkerDumpPostSendIndeterminate",
    "StrictLiveWorkerDumpClientConfig",
    "StrictLiveWorkerDumpClient",
]
