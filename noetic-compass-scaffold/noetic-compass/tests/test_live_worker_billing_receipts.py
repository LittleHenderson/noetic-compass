from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from api.services.billing_entitlements import BillingEntitlementStore
from api.services.billing_reconciliation import (
    BillingReconciliationConflict,
    BillingReconciliationStore,
)
from api.services.live_worker_billing_receipts import (
    LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION,
    LiveWorkerBillingReceiptError,
    LiveWorkerMeasurementReceiptVerifier,
)
from api.services.production.state_substrate import InMemoryStateStore
from tests.billing_test_support import install_verified_stripe_subscription


HMAC_KEY = "live-worker-billing-key-0123456789-ABCDEFG"
KEY_ID = "worker-billing-2026-07"
ISSUER = "atlas-live-worker"
PROVIDER_ID = "runpod-us-ca-2"
WORKER_ID = "m2-real-pythia"


def _worker_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "live-trace-worker"
        / "app"
        / "runtime"
        / "billing_receipt.py"
    )
    spec = importlib.util.spec_from_file_location("worker_billing_receipt", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _CudaModel:
    def parameters(self):
        yield SimpleNamespace(device=SimpleNamespace(type="cuda"))


def _signed_receipt(monkeypatch, *, context=None, elapsed_ms: int = 900):
    module = _worker_module()
    monkeypatch.setattr(module, "_synchronize_cuda", lambda _device: None)
    # Cross one exact whole-second boundary deterministically so the durable
    # Meter Event timestamp contract is exercised without wall-clock flakiness.
    started = datetime.now(UTC).replace(microsecond=500_000) - timedelta(seconds=2)
    clock = module.CudaMeasurementClock(
        started_at=started,
        started_monotonic_ns=1_000_000_000,
        accelerator_count=1,
    )
    monkeypatch.setattr(
        module.time,
        "monotonic_ns",
        lambda: 1_000_000_000 + (elapsed_ms * 1_000_000),
    )
    loaded = SimpleNamespace(
        is_real=True,
        model=_CudaModel(),
        manifest=SimpleNamespace(model_id="EleutherAI/pythia-160m"),
    )
    config = module.WorkerBillingReceiptConfig(
        hmac_key=HMAC_KEY.encode(),
        key_id=KEY_ID,
        issuer=ISSUER,
        provider_id=PROVIDER_ID,
        worker_id=WORKER_ID,
    )
    return module.finish_cuda_measurement_receipt(
        clock,
        loaded_model=loaded,
        context=context
        or {
            "tenant_id": "tenant-a",
            "billing_account_id": "acct-a",
            "run_id": "attempt-a",
        },
        config=config,
    )


def _verifier(**overrides):
    values = {
        "hmac_key": HMAC_KEY,
        "key_id": KEY_ID,
        "issuer": ISSUER,
        "provider_id": PROVIDER_ID,
        "worker_id": WORKER_ID,
        "max_age_seconds": 300,
    }
    values.update(overrides)
    return LiveWorkerMeasurementReceiptVerifier(**values)


def _verify(verifier, receipt, **overrides):
    values = {
        "expected_tenant_id": "tenant-a",
        "expected_billing_account_id": "acct-a",
        "expected_run_id": "attempt-a",
        "expected_model_id": "EleutherAI/pythia-160m",
    }
    values.update(overrides)
    return verifier.verify(receipt, **values)


def _resign(receipt: dict[str, object], **changes: object) -> dict[str, object]:
    unsigned = {
        key: value
        for key, value in {**receipt, **changes}.items()
        if key not in {"payload_sha256", "signature"}
    }
    encoded = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    signed = {**unsigned, "payload_sha256": digest}
    signed_bytes = json.dumps(
        signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    signature = hmac.new(HMAC_KEY.encode(), signed_bytes, hashlib.sha256).hexdigest()
    return {**signed, "signature": f"hmac-sha256:{signature}"}


def _store() -> BillingReconciliationStore:
    backend = InMemoryStateStore()
    entitlements = BillingEntitlementStore(backend)
    now = datetime.now(UTC)
    install_verified_stripe_subscription(
        entitlements,
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        customer_id="cus_CustomerA",
        subscription_id="sub_SubscriptionA",
        event_id="evt_SubscriptionA",
        event_created=1,
        livemode=False,
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=30),
    )
    return BillingReconciliationStore(
        backend,
        entitlements,
        provider_reference_hash_key="provider-reference-key-0123456789-ABCDE",
        usage_price_id="price_UsageMilliseconds",
        meter_event_name="cas.accelerator_milliseconds",
        meter_event_version="cas_meter.v1",
        currency="usd",
        livemode=False,
        customer_receipt_allowed_hosts=("receipts.stripe.test",),
    )


def test_worker_signer_and_api_verifier_share_one_exact_contract(monkeypatch) -> None:
    receipt = _signed_receipt(monkeypatch)
    result = _verify(_verifier(), receipt)

    assert receipt["schema_version"] == LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION
    assert result.measurement.accelerator_milliseconds == 900
    assert result.measurement.accelerator_count == 1
    assert result.measurement.tenant_id == "tenant-a"
    assert result.measurement.billing_account_id == "acct-a"
    assert result.measurement.run_id == "attempt-a"
    assert result.measurement.worker_id == WORKER_ID
    assert result.measurement.worker_provider_id == PROVIDER_ID
    assert result.measurement.model_id == "EleutherAI/pythia-160m"
    assert result.provider_id == PROVIDER_ID
    assert result.model_id == "EleutherAI/pythia-160m"
    assert result.measurement.receipt_size_bytes <= 16_384


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("tenant_id", "tenant-b", "billing context"),
        ("billing_account_id", "acct-b", "billing context"),
        ("run_id", "attempt-b", "billing context"),
        ("worker_id", "attacker-worker", "source"),
        ("provider_id", "attacker-provider", "source"),
        ("model_id", "EleutherAI/pythia-410m", "billing context"),
        ("accelerator_type", "cpu", "CUDA"),
    ),
)
def test_validly_resigned_identity_substitution_is_refused(
    monkeypatch, field: str, value: object, message: str
) -> None:
    receipt = _resign(_signed_receipt(monkeypatch), **{field: value})
    with pytest.raises(LiveWorkerBillingReceiptError, match=message):
        _verify(_verifier(), receipt)


def test_tampering_unknown_fields_and_wrong_authority_fail_closed(monkeypatch) -> None:
    receipt = _signed_receipt(monkeypatch)
    tampered = dict(receipt)
    tampered["accelerator_milliseconds"] = 899
    with pytest.raises(LiveWorkerBillingReceiptError, match="digest|signature"):
        _verify(_verifier(), tampered)

    with pytest.raises(LiveWorkerBillingReceiptError, match="schema"):
        _verify(_verifier(), {**receipt, "unexpected": "field"})

    with pytest.raises(LiveWorkerBillingReceiptError, match="authority"):
        _verify(_verifier(key_id="rotated-key"), receipt)

    with pytest.raises(LiveWorkerBillingReceiptError, match="signature"):
        _verify(_verifier(hmac_key="different-live-worker-key-0123456789-XYZ"), receipt)


def test_stale_future_and_impossible_window_receipts_are_refused(monkeypatch) -> None:
    receipt = _signed_receipt(monkeypatch)
    issued = datetime.fromisoformat(str(receipt["issued_at"]))
    with pytest.raises(LiveWorkerBillingReceiptError, match="stale"):
        _verifier(max_age_seconds=30).verify(
            receipt,
            expected_tenant_id="tenant-a",
            expected_billing_account_id="acct-a",
            expected_run_id="attempt-a",
            expected_model_id="EleutherAI/pythia-160m",
            now=issued + timedelta(seconds=31),
        )

    future = _resign(
        receipt,
        measurement_started_at=(issued + timedelta(minutes=10)).isoformat(),
        measurement_ended_at=(issued + timedelta(minutes=10, seconds=1)).isoformat(),
        issued_at=(issued + timedelta(minutes=10, seconds=1)).isoformat(),
    )
    with pytest.raises(LiveWorkerBillingReceiptError, match="future"):
        _verify(_verifier(), future, now=issued)

    impossible = _resign(receipt, accelerator_milliseconds=10_000_000)
    with pytest.raises(LiveWorkerBillingReceiptError, match="exceed"):
        _verify(_verifier(), impossible)


def test_exact_replay_is_idempotent_but_new_nonce_cannot_rebill_same_window(
    monkeypatch,
) -> None:
    receipt = _signed_receipt(monkeypatch)
    first_measurement = _verify(_verifier(), receipt).measurement
    service = _store()
    first, created = service.record_fleet_measurement(first_measurement)
    replay, replay_created = service.record_fleet_measurement(first_measurement)

    assert created is True
    assert first.worker_provider_id == PROVIDER_ID
    assert first.model_id == "EleutherAI/pythia-160m"
    public = service.public_usage_projection(
        tenant_id="tenant-a", usage_id=first.usage_id
    )
    assert public is not None
    assert public["worker_provider_id"] == PROVIDER_ID
    assert public["model_id"] == "EleutherAI/pythia-160m"
    assert replay_created is False
    assert replay == first

    second_receipt = _resign(receipt, nonce="B" * 32)
    second_measurement = _verify(_verifier(), second_receipt).measurement
    with pytest.raises(BillingReconciliationConflict, match="measurement"):
        service.record_fleet_measurement(second_measurement)


def test_worker_refuses_demo_cpu_and_unusable_signing_configuration(monkeypatch) -> None:
    module = _worker_module()
    monkeypatch.setattr(module, "_synchronize_cuda", lambda _device: None)
    config = module.WorkerBillingReceiptConfig(
        hmac_key=HMAC_KEY.encode(),
        key_id=KEY_ID,
        issuer=ISSUER,
        provider_id=PROVIDER_ID,
        worker_id=WORKER_ID,
    )
    assert HMAC_KEY not in repr(config)
    with pytest.raises(module.WorkerBillingReceiptError, match="real model"):
        module.begin_cuda_measurement(SimpleNamespace(is_real=False, model=None))
    with pytest.raises(module.WorkerBillingReceiptError, match="CUDA-resident"):
        module.begin_cuda_measurement(
            SimpleNamespace(
                is_real=True,
                model=SimpleNamespace(
                    parameters=lambda: iter(
                        [SimpleNamespace(device=SimpleNamespace(type="cpu"))]
                    )
                ),
            )
        )

    monkeypatch.setenv("CAS_BILLING_WORKER_RECEIPT_HMAC_KEY", "short")
    with pytest.raises(module.WorkerBillingReceiptError, match="32 to 4096"):
        module.WorkerBillingReceiptConfig.from_environment()


def test_verifier_rejects_predictable_or_reused_style_keys() -> None:
    with pytest.raises(LiveWorkerBillingReceiptError, match="predictable"):
        _verifier(hmac_key="change-me-worker-receipt-key-0123456789")
    with pytest.raises(LiveWorkerBillingReceiptError, match="predictable"):
        _verifier(hmac_key="A" * 40)
