"""Live RunPod transport for the pre-create guardian's ProviderAdapter.

This module supplies the missing piece named in the package README: an adapter
the pre-create guardian can use to observe and contain a Pod. It implements
exactly the three methods of `precreate_guardian_offline.ProviderAdapter` and
nothing else.

Deliberate authority boundary, enforced structurally rather than by convention:

  * There is NO create method, NO delete method, and NO start/resume method.
    The guardian's authority is inventory, exact GET, and STOP. The
    create-capable launcher is a separate trust domain and must stay that way.
  * Only three request shapes can ever be produced -- `GET /v1/pods`,
    `GET /v1/pods/{id}`, and `POST /v1/pods/{id}/stop` -- and `_request` refuses
    any method/path pair outside that allowlist before a socket is opened.
  * Protected Pod ids are refused for STOP before any request is built. The set
    is imported from the guardian state machine so the two cannot drift apart.

The credential is read from the environment and is never logged, never returned,
never placed in a URL, and never included in any exception message.
"""

from __future__ import annotations

import json
import os
from typing import Any, Final
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from precreate_guardian_offline import PROTECTED_POD_IDS, POD_ID_PATTERN

API_ROOT: Final[str] = "https://rest.runpod.io/v1"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
MAX_RESPONSE_BYTES: Final[int] = 4_000_000
CREDENTIAL_ENVIRONMENT_VARIABLE: Final[str] = "RUNPOD_API_KEY"

# The complete set of operations this adapter may ever perform. Anything else
# is refused before a request object is constructed.
_ALLOWED: Final[frozenset[tuple[str, str]]] = frozenset(
    {("GET", "/pods"), ("GET", "/pods/{id}"), ("POST", "/pods/{id}/stop")}
)


class GuardianTransportError(RuntimeError):
    """Transport failure. Never carries credential material."""


def _require_credential() -> str:
    value = os.environ.get(CREDENTIAL_ENVIRONMENT_VARIABLE, "")
    if not isinstance(value, str) or not value.strip():
        raise GuardianTransportError("PROVIDER_CREDENTIAL_ABSENT")
    return value.strip()


def _require_pod_id(pod_id: str) -> str:
    if not isinstance(pod_id, str) or not POD_ID_PATTERN.fullmatch(pod_id):
        raise GuardianTransportError("POD_ID_MALFORMED")
    return pod_id


class RunPodGuardianAdapter:
    """Inventory / exact GET / STOP only. It cannot create, delete, or start."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Any | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else _require_credential()
        if not self._api_key:
            raise GuardianTransportError("PROVIDER_CREDENTIAL_ABSENT")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise GuardianTransportError("TIMEOUT_INVALID")
        self._timeout = float(timeout_seconds)
        self._opener = opener if opener is not None else urlopen

    # -- internal ---------------------------------------------------------

    def _request(
        self, method: str, template: str, *, path: str
    ) -> tuple[int, dict[str, Any] | list[Any] | None]:
        if (method, template) not in _ALLOWED:
            # Structural refusal: reached before any URL or socket exists.
            raise GuardianTransportError("OPERATION_NOT_ON_GUARDIAN_ALLOWLIST")
        request = Request(
            f"{API_ROOT}{path}",
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = int(getattr(response, "status", 0) or 0)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:  # noqa: PERF203 - explicit mapping wanted
            # Deliberately does not echo the response body: an upstream error
            # page must never be able to smuggle text into guardian evidence.
            raise GuardianTransportError(
                f"PROVIDER_HTTP_STATUS_{int(error.code)}"
            ) from None
        except URLError:
            raise GuardianTransportError("PROVIDER_UNREACHABLE") from None
        except Exception:
            raise GuardianTransportError("PROVIDER_TRANSPORT_FAILED") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise GuardianTransportError("PROVIDER_RESPONSE_TOO_LARGE")
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except Exception:
            raise GuardianTransportError("PROVIDER_RESPONSE_NOT_JSON") from None

    # -- ProviderAdapter --------------------------------------------------

    def list_pods(self) -> list[dict[str, Any]]:
        _status, body = self._request("GET", "/pods", path="/pods")
        if isinstance(body, dict):
            # Some deployments wrap the collection; accept only an exact key.
            body = body.get("pods")
        if not isinstance(body, list):
            raise GuardianTransportError("PROVIDER_INVENTORY_SHAPE_INVALID")
        pods: list[dict[str, Any]] = []
        for item in body:
            if not isinstance(item, dict):
                raise GuardianTransportError("PROVIDER_INVENTORY_ENTRY_INVALID")
            pods.append(item)
        return pods

    def get_pod(self, pod_id: str) -> dict[str, Any]:
        pod_id = _require_pod_id(pod_id)
        _status, body = self._request(
            "GET", "/pods/{id}", path=f"/pods/{quote(pod_id, safe='')}"
        )
        if not isinstance(body, dict):
            raise GuardianTransportError("PROVIDER_POD_SHAPE_INVALID")
        observed = body.get("id")
        if observed != pod_id:
            # Refuses a response describing a different Pod than the one asked
            # for, so a mis-routed reply can never bind to the wrong target.
            raise GuardianTransportError("PROVIDER_POD_IDENTITY_MISMATCH")
        return body

    def stop_pod(self, pod_id: str) -> int:
        pod_id = _require_pod_id(pod_id)
        if pod_id in PROTECTED_POD_IDS:
            # Checked before the request is built, so a protected Pod can never
            # have a stop request constructed for it, let alone sent.
            raise GuardianTransportError("PROTECTED_POD_STOP_REFUSED")
        status, _body = self._request(
            "POST", "/pods/{id}/stop", path=f"/pods/{quote(pod_id, safe='')}/stop"
        )
        return int(status)
