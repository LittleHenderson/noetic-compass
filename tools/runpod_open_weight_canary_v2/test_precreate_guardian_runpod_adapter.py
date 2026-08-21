"""Tests for the live RunPod guardian adapter.

These are offline: every test injects a fake opener, so no network call is made
and no credential is required. The point of the suite is the AUTHORITY
BOUNDARY -- that the adapter cannot create, cannot delete, cannot start, and
cannot stop a protected Pod -- not merely that the happy path parses.
"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from precreate_guardian_offline import PROTECTED_POD_IDS
import precreate_guardian_runpod_adapter as adapter_module
from precreate_guardian_runpod_adapter import (
    GuardianTransportError,
    RunPodGuardianAdapter,
)

POD_A = "vernmyfb3ck9po"
POD_FREE = "abc123def456"


class _Response(io.BytesIO):
    def __init__(self, payload: bytes, status: int = 200) -> None:
        super().__init__(payload)
        self.status = status

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _opener(payload: Any, status: int = 200, *, record: list | None = None):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def open_it(request, timeout=None):  # noqa: ANN001 - test double
        if record is not None:
            record.append((request.get_method(), request.full_url, dict(request.headers)))
        return _Response(body, status)

    return open_it


def _adapter(payload: Any, status: int = 200, record: list | None = None):
    return RunPodGuardianAdapter(
        api_key="test-key-not-a-real-credential",
        opener=_opener(payload, status, record=record),
    )


# -- authority boundary ---------------------------------------------------


def test_adapter_exposes_only_inventory_get_and_stop():
    public = {
        name
        for name in dir(RunPodGuardianAdapter)
        if not name.startswith("_")
    }
    assert public == {"list_pods", "get_pod", "stop_pod"}


def test_adapter_has_no_create_delete_or_start_method():
    for forbidden in ("create_pod", "create", "delete_pod", "delete", "start_pod", "start", "resume"):
        assert not hasattr(RunPodGuardianAdapter, forbidden)


def test_source_contains_no_create_or_delete_verb():
    source = adapter_module.__file__
    with open(source, "r", encoding="utf-8") as handle:
        text = handle.read()
    # The only HTTP verbs that may appear as request methods are GET and POST,
    # and POST only for the stop path.
    assert '"DELETE"' not in text
    assert '"PUT"' not in text
    assert '"PATCH"' not in text
    assert text.count('"POST"') == 2  # allowlist entry + the stop call


def test_every_allowlisted_operation_is_read_only_or_stop():
    for method, template in adapter_module._ALLOWED:
        assert method in {"GET", "POST"}
        if method == "POST":
            assert template.endswith("/stop")


def test_non_allowlisted_operation_is_refused_before_any_socket():
    calls: list = []
    a = _adapter({}, record=calls)
    with pytest.raises(GuardianTransportError, match="OPERATION_NOT_ON_GUARDIAN_ALLOWLIST"):
        a._request("DELETE", "/pods/{id}", path="/pods/abc123def456")
    assert calls == []  # nothing was ever opened


# -- protected pods -------------------------------------------------------


@pytest.mark.parametrize("protected", sorted(PROTECTED_POD_IDS))
def test_stop_refuses_every_protected_pod_before_building_a_request(protected):
    calls: list = []
    a = _adapter({}, record=calls)
    with pytest.raises(GuardianTransportError, match="PROTECTED_POD_STOP_REFUSED"):
        a.stop_pod(protected)
    assert calls == []


def test_protected_set_is_shared_with_the_state_machine_not_copied():
    assert adapter_module.PROTECTED_POD_IDS is PROTECTED_POD_IDS
    assert POD_A in PROTECTED_POD_IDS


def test_stop_allows_a_non_protected_pod():
    calls: list = []
    a = _adapter(b"", status=200, record=calls)
    assert a.stop_pod(POD_FREE) == 200
    assert len(calls) == 1
    method, url, _headers = calls[0]
    assert method == "POST"
    assert url.endswith(f"/pods/{POD_FREE}/stop")


# -- identity binding -----------------------------------------------------


def test_get_pod_refuses_a_response_describing_a_different_pod():
    a = _adapter({"id": "someotherpod", "desiredStatus": "RUNNING"})
    with pytest.raises(GuardianTransportError, match="PROVIDER_POD_IDENTITY_MISMATCH"):
        a.get_pod(POD_FREE)


def test_get_pod_accepts_the_exact_pod():
    a = _adapter({"id": POD_FREE, "desiredStatus": "RUNNING"})
    assert a.get_pod(POD_FREE)["id"] == POD_FREE


@pytest.mark.parametrize("bad", ["", "UPPER123", "has space", "x" * 64, "sh", "a/b"])
def test_malformed_pod_ids_are_refused(bad):
    calls: list = []
    a = _adapter({}, record=calls)
    with pytest.raises(GuardianTransportError, match="POD_ID_MALFORMED"):
        a.get_pod(bad)
    with pytest.raises(GuardianTransportError, match="POD_ID_MALFORMED"):
        a.stop_pod(bad)
    assert calls == []


# -- credential handling --------------------------------------------------

def test_absent_credential_fails_closed(monkeypatch):
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    with pytest.raises(GuardianTransportError, match="PROVIDER_CREDENTIAL_ABSENT"):
        RunPodGuardianAdapter()


def test_credential_is_sent_as_a_header_and_never_in_the_url():
    calls: list = []
    a = _adapter([], record=calls)
    a.list_pods()
    _method, url, headers = calls[0]
    assert "test-key-not-a-real-credential" not in url
    assert headers.get("Authorization") == "Bearer test-key-not-a-real-credential"


def test_transport_errors_never_carry_the_credential():
    key = "super-secret-value-abc"

    def boom(request, timeout=None):  # noqa: ANN001 - test double
        raise OSError(f"connection failed for {key}")

    a = RunPodGuardianAdapter(api_key=key, opener=boom)
    with pytest.raises(GuardianTransportError) as caught:
        a.list_pods()
    assert key not in str(caught.value)


# -- hostile responses ----------------------------------------------------


def test_inventory_rejects_a_non_list_body():
    a = _adapter({"unexpected": "shape"})
    with pytest.raises(GuardianTransportError, match="PROVIDER_INVENTORY_SHAPE_INVALID"):
        a.list_pods()


def test_inventory_rejects_non_object_entries():
    a = _adapter(["not-an-object"])
    with pytest.raises(GuardianTransportError, match="PROVIDER_INVENTORY_ENTRY_INVALID"):
        a.list_pods()


def test_inventory_accepts_a_wrapped_collection():
    a = _adapter({"pods": [{"id": POD_FREE, "name": "x"}]})
    assert a.list_pods() == [{"id": POD_FREE, "name": "x"}]


def test_non_json_body_is_refused():
    a = _adapter(b"<html>gateway error</html>")
    with pytest.raises(GuardianTransportError, match="PROVIDER_RESPONSE_NOT_JSON"):
        a.list_pods()


def test_oversized_body_is_refused():
    payload = b"[" + b"0," * adapter_module.MAX_RESPONSE_BYTES + b"0]"
    a = _adapter(payload)
    with pytest.raises(GuardianTransportError, match="PROVIDER_RESPONSE_TOO_LARGE"):
        a.list_pods()


def test_invalid_timeout_is_refused():
    for bad in (0, -1, "30"):
        with pytest.raises(GuardianTransportError, match="TIMEOUT_INVALID"):
            RunPodGuardianAdapter(api_key="k", timeout_seconds=bad, opener=_opener([]))
