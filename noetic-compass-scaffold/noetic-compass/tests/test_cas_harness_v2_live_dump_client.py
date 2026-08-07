from __future__ import annotations

import asyncio
import hashlib
from dataclasses import FrozenInstanceError

import httpx
import pytest

from api.services.cas_harness_v2_live_dump_client import (
    MAX_JOINED_REQUEST_BYTES,
    MAX_JOINED_RESPONSE_BYTES,
    LiveWorkerDumpPostSendIndeterminate,
    LiveWorkerDumpPreSendFailure,
    StrictLiveWorkerDumpClient,
    StrictLiveWorkerDumpClientConfig,
)
from api.services.cas_harness_v2_joined_executor import (
    JoinedLiveDumpPostSendIndeterminate,
    JoinedLiveDumpPreSendFailure,
)


AUTHORIZATION_SHA256 = "A" * 64
RUN_ID = "prospective-run-01"
INVOCATION_ID = "invocation-00000001"
TOKEN = "worker-token-that-must-never-leak"
REQUEST_RAW = b'{\n  "prompt": "preserve exact bytes"\n}'
RESPONSE_RAW = b'{ "events": [], "joined_execution_binding": {} }\n'


class _FailingResponseStream(httpx.AsyncByteStream):
    def __init__(self, failure_kind: str) -> None:
        self._failure_kind = failure_kind

    async def __aiter__(self):
        if self._failure_kind == "read-network":
            raise httpx.ReadError("remote read detail")
        if self._failure_kind == "read-cancel":
            raise asyncio.CancelledError("remote read cancellation detail")
        yield RESPONSE_RAW

    async def aclose(self) -> None:
        if self._failure_kind == "close-network":
            raise httpx.ReadError("remote close detail")
        if self._failure_kind == "close-cancel":
            raise asyncio.CancelledError("remote close cancellation detail")


def _config(
    *,
    worker_base_url: str = "http://127.0.0.1:8080",
    worker_token: str = TOKEN,
    timeout_seconds: float = 5.0,
) -> StrictLiveWorkerDumpClientConfig:
    return StrictLiveWorkerDumpClientConfig(
        worker_base_url=worker_base_url,
        worker_token=worker_token,
        timeout_seconds=timeout_seconds,
    )


def _response(
    status_code: int = 200,
    *,
    body: bytes = RESPONSE_RAW,
    content_type: str = "application/json",
    content_length: str | None = None,
    headers: list[tuple[str, str]] | None = None,
) -> httpx.Response:
    if headers is None:
        headers = [
            ("Content-Type", content_type),
            (
                "Content-Length",
                str(len(body)) if content_length is None else content_length,
            ),
        ]
    return httpx.Response(
        status_code,
        headers=headers,
        stream=httpx.ByteStream(body),
    )


async def _invoke(
    handler,
    *,
    config: StrictLiveWorkerDumpClientConfig | None = None,
    request_raw: bytes = REQUEST_RAW,
    authorization_sha256: str = AUTHORIZATION_SHA256,
    prospective_run_id: str = RUN_ID,
    invocation_id: str = INVOCATION_ID,
) -> bytes:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StrictLiveWorkerDumpClient(config or _config(), http_client=http)
        return await client.invoke_once(
            request_raw=request_raw,
            authorization_sha256=authorization_sha256,
            prospective_run_id=prospective_run_id,
            invocation_id=invocation_id,
        )


@pytest.mark.asyncio
async def test_invoke_once_sends_exact_carrier_headers_path_and_returns_raw_bytes():
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "POST"
        assert request.url == "http://127.0.0.1:8080/sessions/dump"
        assert await request.aread() == REQUEST_RAW
        assert request.headers.get_list("content-type") == ["application/json"]
        assert request.headers.get_list("x-atlas-worker-token") == [TOKEN]
        assert request.headers.get_list("x-cas-joined-request-sha256") == [
            hashlib.sha256(REQUEST_RAW).hexdigest().upper()
        ]
        assert request.headers.get_list("x-cas-joined-request-byte-length") == [
            str(len(REQUEST_RAW))
        ]
        assert request.headers.get_list("x-cas-joined-authorization-sha256") == [
            AUTHORIZATION_SHA256
        ]
        assert request.headers.get_list("x-cas-joined-run-id") == [RUN_ID]
        assert request.headers.get_list("x-cas-joined-invocation-id") == [
            INVOCATION_ID
        ]
        assert request.headers.get_list("accept-encoding") == ["identity"]
        return _response(content_type="application/json; charset=UTF-8")

    result = await _invoke(handler)

    assert result == RESPONSE_RAW
    assert len(seen) == 1


def test_config_is_frozen_and_repr_redacts_worker_token():
    config = _config()

    assert TOKEN not in repr(config)
    with pytest.raises(FrozenInstanceError):
        config.worker_token = "replacement"  # type: ignore[misc]


def test_client_failures_are_executor_failure_contracts():
    pre_send = LiveWorkerDumpPreSendFailure("safe generic failure")
    post_send = LiveWorkerDumpPostSendIndeterminate("safe generic failure")

    assert isinstance(pre_send, JoinedLiveDumpPreSendFailure)
    assert isinstance(post_send, JoinedLiveDumpPostSendIndeterminate)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "local_url",
    [
        "http://localhost:8080",
        "http://127.9.8.7:8080/",
        "http://[::1]:8080",
    ],
)
async def test_plaintext_http_is_allowed_only_for_explicit_loopback_hosts(local_url):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response()

    assert await _invoke(handler, config=_config(worker_base_url=local_url)) == RESPONSE_RAW
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nonlocal_url",
    [
        "http://worker.example",
        "http://10.0.0.8:8080",
        "http://0.0.0.0:8080",
    ],
)
async def test_plaintext_http_is_rejected_for_nonloopback_hosts_before_send(
    nonlocal_url,
):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response()

    with pytest.raises(LiveWorkerDumpPreSendFailure) as captured:
        await _invoke(handler, config=_config(worker_base_url=nonlocal_url))

    assert calls == 0
    assert str(captured.value) == "live-worker dump request failed before transport"


@pytest.mark.asyncio
async def test_https_nonlocal_endpoint_is_allowed():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url == "https://worker.example/sessions/dump"
        return _response()

    assert (
        await _invoke(handler, config=_config(worker_base_url="https://worker.example"))
        == RESPONSE_RAW
    )
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "request_raw", "authorization", "run_id", "invocation"),
    [
        (
            _config(worker_base_url="worker.example"),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (
            _config(worker_base_url="https://user:pass@worker.example"),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (
            _config(worker_base_url="https://worker.example/base"),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (
            _config(worker_base_url="https://worker.example?query=1"),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (_config(worker_token=""), REQUEST_RAW, AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (
            _config(worker_token="secret\nleak"),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (
            _config(timeout_seconds=float("nan")),
            REQUEST_RAW,
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (_config(), b"", AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (_config(), b"not-json", AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (_config(), b"[]", AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (_config(), b'{"prompt":"a","prompt":"b"}', AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (_config(), b'{"gain":NaN}', AUTHORIZATION_SHA256, RUN_ID, INVOCATION_ID),
        (
            _config(),
            b"{}" * (MAX_JOINED_REQUEST_BYTES // 2 + 1),
            AUTHORIZATION_SHA256,
            RUN_ID,
            INVOCATION_ID,
        ),
        (_config(), REQUEST_RAW, "a" * 64, RUN_ID, INVOCATION_ID),
        (_config(), REQUEST_RAW, AUTHORIZATION_SHA256, "bad run id", INVOCATION_ID),
        (_config(), REQUEST_RAW, AUTHORIZATION_SHA256, RUN_ID, "too-short"),
    ],
    ids=[
        "relative-endpoint",
        "endpoint-userinfo",
        "endpoint-path",
        "endpoint-query",
        "empty-token",
        "control-in-token",
        "nan-timeout",
        "empty-body",
        "invalid-json",
        "nonobject-json",
        "duplicate-json-key",
        "nonfinite-json",
        "oversize-body",
        "lowercase-authorization",
        "invalid-run-id",
        "short-invocation-id",
    ],
)
async def test_all_malformed_config_and_carriers_fail_before_zero_requests(
    config,
    request_raw,
    authorization,
    run_id,
    invocation,
):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response()

    with pytest.raises(LiveWorkerDumpPreSendFailure) as captured:
        await _invoke(
            handler,
            config=config,
            request_raw=request_raw,
            authorization_sha256=authorization,
            prospective_run_id=run_id,
            invocation_id=invocation,
        )

    assert calls == 0
    assert captured.value.transport_entered is False
    assert TOKEN not in str(captured.value)
    assert RUN_ID not in str(captured.value)
    assert INVOCATION_ID not in str(captured.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_factory",
    [
        lambda: _response(302, headers=[("Location", "https://elsewhere.example/")]),
        lambda: _response(500, body=b"remote-secret-detail"),
        lambda: _response(headers=[("Content-Length", str(len(RESPONSE_RAW)))]),
        lambda: _response(
            headers=[
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(RESPONSE_RAW))),
            ]
        ),
        lambda: _response(
            headers=[
                ("Content-Type", "application/json, application/json"),
                ("Content-Length", str(len(RESPONSE_RAW))),
            ]
        ),
        lambda: _response(
            headers=[
                ("Content-Type", "application/json"),
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(RESPONSE_RAW))),
            ]
        ),
        lambda: _response(headers=[("Content-Type", "application/json")]),
        lambda: _response(content_length="01"),
        lambda: _response(content_length="not-a-number"),
        lambda: _response(content_length=str(len(RESPONSE_RAW) + 1)),
        lambda: _response(content_length=str(MAX_JOINED_RESPONSE_BYTES + 1)),
        lambda: _response(body=b"", content_length="0"),
        lambda: _response(
            headers=[
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(RESPONSE_RAW))),
                ("Content-Length", str(len(RESPONSE_RAW))),
            ]
        ),
    ],
)
async def test_every_invalid_response_is_post_send_indeterminate_without_retry(
    response_factory,
):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response_factory()

    with pytest.raises(LiveWorkerDumpPostSendIndeterminate) as captured:
        await _invoke(handler)

    assert calls == 1
    assert captured.value.retry_allowed is False
    assert captured.value.reconcile_only is True
    assert str(captured.value) == (
        "live-worker dump execution disposition is indeterminate"
    )
    assert TOKEN not in str(captured.value)
    assert RUN_ID not in str(captured.value)
    assert INVOCATION_ID not in str(captured.value)
    assert "remote-secret-detail" not in str(captured.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ["network", "cancel"])
async def test_transport_error_or_cancellation_is_post_send_and_never_retried(
    failure_kind,
):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if failure_kind == "cancel":
            raise asyncio.CancelledError("remote cancellation detail")
        raise httpx.ConnectError("remote network detail", request=request)

    with pytest.raises(LiveWorkerDumpPostSendIndeterminate) as captured:
        await _invoke(handler)

    assert calls == 1
    assert captured.value.retry_allowed is False
    assert captured.value.reconcile_only is True
    assert str(captured.value) == (
        "live-worker dump execution disposition is indeterminate"
    )
    assert "remote" not in str(captured.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_kind",
    ["read-network", "read-cancel", "close-network", "close-cancel"],
)
async def test_stream_or_close_failure_is_post_send_and_never_retried(
    failure_kind,
):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers=[
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(RESPONSE_RAW))),
            ],
            stream=_FailingResponseStream(failure_kind),
        )

    with pytest.raises(LiveWorkerDumpPostSendIndeterminate) as captured:
        await _invoke(handler)

    assert calls == 1
    assert captured.value.retry_allowed is False
    assert captured.value.reconcile_only is True
    assert str(captured.value) == (
        "live-worker dump execution disposition is indeterminate"
    )
    assert "remote" not in str(captured.value)


@pytest.mark.asyncio
async def test_streamed_response_above_bound_is_indeterminate_without_retry():
    calls = 0
    body = b"x" * (MAX_JOINED_RESPONSE_BYTES + 1)

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response(body=body, content_length=str(MAX_JOINED_RESPONSE_BYTES))

    with pytest.raises(LiveWorkerDumpPostSendIndeterminate) as captured:
        await _invoke(handler)

    assert calls == 1
    assert captured.value.retry_allowed is False
    assert captured.value.reconcile_only is True
