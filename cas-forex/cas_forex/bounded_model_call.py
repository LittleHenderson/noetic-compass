"""True wall-clock and single-flight boundary for runtime model decisions.

Provider HTTP timeouts are necessary but are not a scheduler guarantee: a local
model can keep generating after its client-side timeout, or a provider adapter
can ignore optional timeout arguments.  Trading-loop callers use this module so
one slow inference cannot stop broker reconciliation or position protection.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping


LOCAL_MODEL_WALL_TIMEOUT_SECONDS = 15.0


@dataclass
class _ModelCall:
    call_id: str
    started_monotonic: float
    request_kind: str
    request_fingerprint: str
    done: threading.Event = field(default_factory=threading.Event)
    result: dict[str, Any] | None = None
    completed_monotonic: float | None = None


_calls_lock = threading.RLock()
_calls: dict[str, _ModelCall] = {}


def _provider_status(provider: Any) -> dict[str, Any]:
    try:
        value = provider.status()
    except Exception:
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _failure(
    *,
    code: str,
    message: str,
    status: Mapping[str, Any],
    call: _ModelCall,
    wall_timeout_seconds: float,
) -> dict[str, Any]:
    return {
        "ok": False,
        "text": "",
        "provider": status.get("active_provider"),
        "provider_label": status.get("active_provider_label"),
        "model_ref": None,
        "model_backend": None,
        "paid": bool(status.get("active_is_paid")),
        "failover": False,
        "error": f"{code}: {message}",
        "error_code": code,
        "model_call_id": call.call_id,
        "model_request_kind": call.request_kind,
        "model_request_fingerprint": call.request_fingerprint,
        "wall_timeout_seconds": wall_timeout_seconds,
        "elapsed_seconds": round(max(0.0, time.monotonic() - call.started_monotonic), 3),
    }


def bounded_provider_generate(
    provider: Any,
    prompt: str,
    system: str,
    *,
    channel: str,
    wall_timeout_seconds: float,
    generate_kwargs: Mapping[str, Any] | None = None,
    request_kind: str | None = None,
) -> dict[str, Any]:
    """Run ``provider.generate`` behind a daemon worker and a true deadline.

    A channel permits only one unfinished request.  If a provider ignores the
    transport timeout, later trading cycles fail closed immediately instead of
    piling more inference work onto the runtime.
    """

    status = _provider_status(provider)
    normalized_request_kind = str(request_kind or channel).strip() or channel
    fingerprint_payload = json.dumps(
        {
            "prompt": prompt,
            "system": system,
            "generate_kwargs": dict(generate_kwargs or {}),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    request_fingerprint = hashlib.sha256(
        fingerprint_payload.encode("utf-8")
    ).hexdigest()
    requested_timeout = max(0.01, float(wall_timeout_seconds))
    effective_timeout = requested_timeout
    if str(status.get("active_provider") or "") == "local-fallback":
        effective_timeout = min(effective_timeout, LOCAL_MODEL_WALL_TIMEOUT_SECONDS)

    with _calls_lock:
        previous = _calls.get(channel)
        if previous is not None and not previous.done.is_set():
            return _failure(
                code="MODEL_CALL_IN_PROGRESS",
                message="the previous model decision is still running; this cycle stood down",
                status=status,
                call=previous,
                wall_timeout_seconds=effective_timeout,
            )
        if previous is not None:
            _calls.pop(channel, None)
            if previous.request_kind == normalized_request_kind:
                result = dict(previous.result or {})
                result.setdefault("model_call_id", previous.call_id)
                result.setdefault("model_request_kind", previous.request_kind)
                result.setdefault(
                    "model_request_fingerprint",
                    previous.request_fingerprint,
                )
                result["completed_after_wall_timeout"] = True
                result["result_age_seconds"] = round(
                    max(
                        0.0,
                        time.monotonic()
                        - (
                            previous.completed_monotonic
                            or previous.started_monotonic
                        ),
                    ),
                    3,
                )
                result.setdefault(
                    "elapsed_seconds",
                    round(
                        max(
                            0.0,
                            (previous.completed_monotonic or time.monotonic())
                            - previous.started_monotonic,
                        ),
                        3,
                    ),
                )
                result.setdefault("wall_timeout_seconds", effective_timeout)
                return result

        call = _ModelCall(
            call_id=uuid.uuid4().hex,
            started_monotonic=time.monotonic(),
            request_kind=normalized_request_kind,
            request_fingerprint=request_fingerprint,
        )
        _calls[channel] = call

    kwargs = dict(generate_kwargs or {})
    # The same decision-kind boundary that protects late-result delivery also
    # drives Flash/Pro provider routing. A provider that predates role routing
    # is still supported by the TypeError compatibility fallback below.
    kwargs.setdefault("request_kind", normalized_request_kind)

    def _worker() -> None:
        try:
            try:
                value = provider.generate(prompt, system, **kwargs)
            except TypeError as exc:
                unsupported = any(key in str(exc) for key in kwargs)
                if not unsupported:
                    raise
                value = provider.generate(prompt, system)
            if isinstance(value, Mapping):
                call.result = dict(value)
            else:
                call.result = {
                    "ok": False,
                    "text": "",
                    "error": "MODEL_RESULT_INVALID: provider returned a non-mapping result",
                    "error_code": "MODEL_RESULT_INVALID",
                }
        except Exception as exc:
            call.result = {
                "ok": False,
                "text": "",
                "provider": status.get("active_provider"),
                "provider_label": status.get("active_provider_label"),
                "paid": bool(status.get("active_is_paid")),
                "failover": False,
                "error": f"{type(exc).__name__}: {exc}",
                "error_code": "MODEL_CALL_EXCEPTION",
            }
        finally:
            call.completed_monotonic = time.monotonic()
            call.done.set()

    threading.Thread(
        target=_worker,
        name=f"cas-model-{channel}-{call.call_id[:8]}",
        daemon=True,
    ).start()

    if not call.done.wait(effective_timeout):
        return _failure(
            code="MODEL_CALL_TIMEOUT",
            message=(
                f"model decision exceeded the {effective_timeout:g}-second wall-clock budget; "
                "this cycle stood down"
            ),
            status=status,
            call=call,
            wall_timeout_seconds=effective_timeout,
        )

    result = dict(call.result or {})
    with _calls_lock:
        if _calls.get(channel) is call:
            _calls.pop(channel, None)
    result.setdefault("model_call_id", call.call_id)
    result.setdefault("model_request_kind", call.request_kind)
    result.setdefault("model_request_fingerprint", call.request_fingerprint)
    result.setdefault(
        "elapsed_seconds",
        round(max(0.0, time.monotonic() - call.started_monotonic), 3),
    )
    result.setdefault("wall_timeout_seconds", effective_timeout)
    return result


def reset_bounded_model_calls_for_tests() -> None:
    """Clear completed test channels; unfinished daemon work remains isolated."""

    with _calls_lock:
        for channel, call in list(_calls.items()):
            if call.done.is_set():
                _calls.pop(channel, None)
