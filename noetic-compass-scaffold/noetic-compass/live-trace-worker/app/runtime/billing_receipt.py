"""Create a canonical HMAC receipt for one real CUDA worker interval."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from typing import Mapping


SCHEMA_VERSION = "cas_harness_live_worker_measurement_receipt.v1"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,200}$")
_PREDICTABLE_KEY_MARKERS = (
    "change-me",
    "changeme",
    "default",
    "example",
    "not-a-secret",
    "placeholder",
    "sample-secret",
    "test-secret",
)


class WorkerBillingReceiptError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WorkerBillingReceiptConfig:
    hmac_key: bytes = field(repr=False)
    key_id: str
    issuer: str
    provider_id: str
    worker_id: str

    @classmethod
    def from_environment(cls) -> "WorkerBillingReceiptConfig":
        raw_key = os.environ.get("CAS_BILLING_WORKER_RECEIPT_HMAC_KEY", "")
        key = _validated_hmac_key(raw_key)
        return cls(
            hmac_key=key,
            key_id=_safe_id(
                os.environ.get("CAS_BILLING_WORKER_RECEIPT_KEY_ID", ""), "key_id"
            ),
            issuer=_safe_id(
                os.environ.get("CAS_BILLING_WORKER_RECEIPT_ISSUER", ""), "issuer"
            ),
            provider_id=_safe_id(
                os.environ.get("CAS_BILLING_WORKER_PROVIDER_ID", ""), "provider_id"
            ),
            worker_id=_safe_id(
                os.environ.get("CAS_BILLING_WORKER_ID", ""), "worker_id"
            ),
        )


@dataclass(frozen=True, slots=True)
class CudaMeasurementClock:
    started_at: datetime
    started_monotonic_ns: int
    accelerator_count: int


def begin_cuda_measurement(loaded_model: object) -> CudaMeasurementClock:
    """Start only when the loaded model is genuinely resident on CUDA."""

    model = getattr(loaded_model, "model", None)
    if not bool(getattr(loaded_model, "is_real", False)) or model is None:
        raise WorkerBillingReceiptError(
            "billable measurement requires real model weights"
        )
    try:
        parameter = next(model.parameters())
        device = parameter.device
    except (AttributeError, StopIteration, TypeError) as exc:
        raise WorkerBillingReceiptError(
            "billable measurement cannot determine the model accelerator"
        ) from exc
    if str(getattr(device, "type", "")) != "cuda":
        raise WorkerBillingReceiptError(
            "billable measurement requires a CUDA-resident model"
        )
    _synchronize_cuda(device)
    return CudaMeasurementClock(
        started_at=datetime.now(UTC),
        started_monotonic_ns=time.monotonic_ns(),
        accelerator_count=1,
    )


def finish_cuda_measurement_receipt(
    clock: CudaMeasurementClock,
    *,
    loaded_model: object,
    context: Mapping[str, object],
    config: WorkerBillingReceiptConfig,
) -> dict[str, object]:
    try:
        parameter = next(getattr(loaded_model, "model").parameters())
        device = parameter.device
    except (AttributeError, StopIteration, TypeError) as exc:
        raise WorkerBillingReceiptError(
            "billable measurement lost its model accelerator"
        ) from exc
    if str(getattr(device, "type", "")) != "cuda":
        raise WorkerBillingReceiptError(
            "billable measurement lost its CUDA-resident model"
        )
    _synchronize_cuda(device)
    elapsed_ns = time.monotonic_ns() - clock.started_monotonic_ns
    if elapsed_ns < 1_000_000:
        raise WorkerBillingReceiptError(
            "billable CUDA measurement interval was shorter than one millisecond"
        )
    elapsed_microseconds = elapsed_ns // 1_000
    ended_at = clock.started_at + timedelta(microseconds=elapsed_microseconds)
    quantity = (elapsed_ns // 1_000_000) * clock.accelerator_count
    model_id = _model_id(getattr(getattr(loaded_model, "manifest", None), "model_id", None))

    unsigned: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "key_id": config.key_id,
        "issuer": config.issuer,
        "tenant_id": _safe_id(context.get("tenant_id"), "tenant_id"),
        "billing_account_id": _safe_id(
            context.get("billing_account_id"), "billing_account_id"
        ),
        "run_id": _safe_id(context.get("run_id"), "run_id"),
        "worker_id": config.worker_id,
        "provider_id": config.provider_id,
        "model_id": model_id,
        "accelerator_type": "cuda",
        "accelerator_count": clock.accelerator_count,
        "accelerator_milliseconds": quantity,
        "measurement_started_at": clock.started_at.isoformat(),
        "measurement_ended_at": ended_at.isoformat(),
        "issued_at": datetime.now(UTC).isoformat(),
        "nonce": secrets.token_urlsafe(24),
    }
    payload_sha256 = hashlib.sha256(_canonical_json(unsigned)).hexdigest()
    signed_payload = {**unsigned, "payload_sha256": payload_sha256}
    signature = hmac.new(
        config.hmac_key, _canonical_json(signed_payload), hashlib.sha256
    ).hexdigest()
    return {**signed_payload, "signature": f"hmac-sha256:{signature}"}


def _synchronize_cuda(device: object) -> None:
    try:
        import torch

        torch.cuda.synchronize(device)
    except Exception as exc:
        raise WorkerBillingReceiptError(
            "billable measurement could not synchronize the CUDA accelerator"
        ) from exc


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _safe_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _SAFE_ID_RE.fullmatch(value) is None:
        raise WorkerBillingReceiptError(f"{field} is not a canonical identifier")
    return value


def _model_id(value: object) -> str:
    if not isinstance(value, str) or _MODEL_ID_RE.fullmatch(value) is None:
        raise WorkerBillingReceiptError("model_id is not canonical")
    return value


def _validated_hmac_key(value: object) -> bytes:
    if not isinstance(value, str) or value != value.strip():
        raise WorkerBillingReceiptError(
            "CAS_BILLING_WORKER_RECEIPT_HMAC_KEY must be an exact string"
        )
    encoded = value.encode("utf-8")
    if not (32 <= len(encoded) <= 4096):
        raise WorkerBillingReceiptError(
            "CAS_BILLING_WORKER_RECEIPT_HMAC_KEY must contain 32 to 4096 bytes"
        )
    lowered = value.casefold()
    if any(marker in lowered for marker in _PREDICTABLE_KEY_MARKERS) or len(set(value)) < 8:
        raise WorkerBillingReceiptError(
            "CAS_BILLING_WORKER_RECEIPT_HMAC_KEY is predictable"
        )
    return encoded


__all__ = [
    "CudaMeasurementClock",
    "SCHEMA_VERSION",
    "WorkerBillingReceiptConfig",
    "WorkerBillingReceiptError",
    "begin_cuda_measurement",
    "finish_cuda_measurement_receipt",
]
