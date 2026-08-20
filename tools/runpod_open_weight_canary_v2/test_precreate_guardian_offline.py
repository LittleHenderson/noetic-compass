from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import pytest


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import precreate_guardian_offline as guardian


class FakeClock:
    def __init__(self, now: datetime):
        self.current = now

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class FakeProvider:
    def __init__(self, inventories: list[list[dict[str, object]]]):
        self.inventories = inventories
        self.inventory_index = 0
        self.pods: dict[str, dict[str, object]] = {}
        self.stop_calls: list[tuple[str, datetime | None]] = []
        self.clock: FakeClock | None = None
        for inventory in inventories:
            for pod in inventory:
                self.pods[str(pod["id"])] = dict(pod)

    def list_pods(self) -> list[dict[str, object]]:
        index = min(self.inventory_index, len(self.inventories) - 1)
        self.inventory_index += 1
        return [dict(item) for item in self.inventories[index]]

    def get_pod(self, pod_id: str) -> dict[str, object]:
        return dict(self.pods[pod_id])

    def stop_pod(self, pod_id: str) -> int:
        self.stop_calls.append((pod_id, self.clock.now() if self.clock else None))
        self.pods[pod_id]["desiredStatus"] = "EXITED"
        return 200


def make_fixture(now: datetime):
    name = guardian.generate_pod_name(now, entropy_hex="ab" * 16)
    request = guardian.canonical_json_bytes(
        {
            "cloudType": "SECURE",
            "gpuCount": 1,
            "gpuTypeIds": ["NVIDIA A40"],
            "name": name,
        }
    )
    start = now + timedelta(seconds=1)
    end = start + timedelta(minutes=2)
    deadline = now + timedelta(minutes=30)
    spec = guardian.ArmSpec(
        pod_name=name,
        exact_create_request_sha256=hashlib.sha256(request).hexdigest(),
        source_commit_sha="a" * 40,
        oci_image_digest="sha256:" + "b" * 64,
        creation_window_start_utc=start.isoformat(),
        creation_window_end_utc=end.isoformat(),
        hard_stop_deadline_utc=deadline.isoformat(),
        github_repository="LittleHenderson/noetic-compass",
        github_run_id="123456",
        github_run_attempt="1",
        github_sha="a" * 40,
    )
    return spec, request, start, end, deadline


def arm(now: datetime, provider: FakeProvider):
    spec, request, start, end, deadline = make_fixture(now)
    receipt = guardian.arm_guardian(
        spec,
        exact_create_request_bytes=request,
        provider=provider,
        armed_at=now,
    )
    return receipt, spec, start, end, deadline


def test_crash_after_create_is_recovered_and_stopped_by_deadline():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, _request, start, _end, deadline = make_fixture(now)
    created = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": (start + timedelta(seconds=5)).isoformat(),
        "desiredStatus": "RUNNING",
    }
    provider = FakeProvider([[], [], [created]])
    clock = FakeClock(now)
    provider.clock = clock
    arm_receipt = guardian.arm_guardian(
        spec,
        exact_create_request_bytes=_request,
        provider=provider,
        armed_at=now,
    )

    result = guardian.supervise_after_arm(
        arm_receipt,
        provider=provider,
        clock=clock,
        poll_seconds=30,
        stop_lead_seconds=90,
    )

    assert result.binding_receipt is not None
    assert result.binding_receipt["pod_id"] == "newpod1234"
    assert result.terminal_receipt["observed_terminal_status"] == "EXITED"
    assert provider.stop_calls[0][0] == "newpod1234"
    assert provider.stop_calls[0][1] == deadline - timedelta(seconds=90)
    assert provider.stop_calls[0][1] <= deadline


def test_arm_rejects_name_already_present_before_create():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, request, start, _end, _deadline = make_fixture(now)
    provider = FakeProvider(
        [[{"id": "oldpod1234", "name": spec.pod_name, "createdAt": start.isoformat()}]]
    )
    with pytest.raises(guardian.AmbiguousTargetError, match="before guardian arm"):
        guardian.arm_guardian(
            spec,
            exact_create_request_bytes=request,
            provider=provider,
            armed_at=now,
        )


def test_arm_rejects_request_hash_or_name_drift():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, request, _start, _end, _deadline = make_fixture(now)
    provider = FakeProvider([[]])
    with pytest.raises(ValueError, match="bound SHA-256"):
        guardian.arm_guardian(
            spec,
            exact_create_request_bytes=request + b" ",
            provider=provider,
            armed_at=now,
        )
    wrong_request = json.dumps({"name": spec.pod_name + "x"}).encode()
    wrong_spec = guardian.ArmSpec(
        **{
            **spec.__dict__,
            "exact_create_request_sha256": hashlib.sha256(wrong_request).hexdigest(),
        }
    )
    with pytest.raises(ValueError, match="bound Pod name"):
        guardian.arm_guardian(
            wrong_spec,
            exact_create_request_bytes=wrong_request,
            provider=provider,
            armed_at=now,
        )


def test_discovery_rejects_two_exact_name_matches_without_stopping():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, _end, _deadline = arm(now, provider)
    duplicates = [
        {
            "id": "newpod1234",
            "name": spec.pod_name,
            "createdAt": start.isoformat(),
            "desiredStatus": "RUNNING",
        },
        {
            "id": "newpod5678",
            "name": spec.pod_name,
            "createdAt": start.isoformat(),
            "desiredStatus": "RUNNING",
        },
    ]
    with pytest.raises(guardian.AmbiguousTargetError, match="not unique"):
        guardian.discover_candidate(
            receipt, inventory=duplicates, observed_at=start + timedelta(seconds=1)
        )
    assert provider.stop_calls == []


def test_discovery_rejects_protected_or_preexisting_id():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider(
        [[{"id": "oldpod1234", "name": "unrelated", "desiredStatus": "EXITED"}]]
    )
    receipt, spec, start, _end, _deadline = arm(now, provider)
    with pytest.raises(guardian.AmbiguousTargetError, match="pre-arm"):
        guardian.discover_candidate(
            receipt,
            inventory=[
                {
                    "id": "oldpod1234",
                    "name": spec.pod_name,
                    "createdAt": start.isoformat(),
                    "desiredStatus": "RUNNING",
                }
            ],
            observed_at=start,
        )
    with pytest.raises(guardian.ProtectedTargetError, match="protected"):
        guardian.discover_candidate(
            receipt,
            inventory=[
                {
                    "id": "q2oqlooejhin7s",
                    "name": spec.pod_name,
                    "createdAt": start.isoformat(),
                    "desiredStatus": "RUNNING",
                }
            ],
            observed_at=start,
        )


def test_discovery_rejects_candidate_created_outside_window():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, end, _deadline = arm(now, provider)
    for created_at in (start - timedelta(microseconds=1), end + timedelta(microseconds=1)):
        with pytest.raises(guardian.AmbiguousTargetError, match="bound window"):
            guardian.discover_candidate(
                receipt,
                inventory=[
                    {
                        "id": "newpod1234",
                        "name": spec.pod_name,
                        "createdAt": created_at.isoformat(),
                        "desiredStatus": "RUNNING",
                    }
                ],
                observed_at=start,
            )


def test_last_started_at_can_supply_missing_created_at():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, _end, _deadline = arm(now, provider)
    binding = guardian.discover_candidate(
        receipt,
        inventory=[
            {
                "id": "newpod1234",
                "name": spec.pod_name,
                "lastStartedAt": start.isoformat(),
                "desiredStatus": "RUNNING",
            }
        ],
        observed_at=start,
    )
    assert binding is not None
    assert binding["provider_birth_times_utc"] == {
        "lastStartedAt": start.isoformat()
    }


def test_legacy_runpod_last_started_at_is_admitted_in_window():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, _end, _deadline = arm(now, provider)
    legacy = start.strftime("%Y-%m-%d %H:%M:%S.000 +0000 UTC")
    binding = guardian.discover_candidate(
        receipt,
        inventory=[
            {
                "id": "newpod1234",
                "name": spec.pod_name,
                "lastStartedAt": legacy,
                "desiredStatus": "RUNNING",
            }
        ],
        observed_at=start,
    )
    assert binding is not None
    assert binding["provider_birth_times_utc"] == {"lastStartedAt": legacy}


def test_post_binding_name_drift_does_not_defeat_id_stop():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    arm_receipt, spec, start, _end, deadline = arm(now, provider)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": start.isoformat(),
        "desiredStatus": "RUNNING",
    }
    binding = guardian.discover_candidate(
        arm_receipt, inventory=[candidate], observed_at=start
    )
    assert binding is not None
    provider.pods["newpod1234"] = {**candidate, "name": "renamed-after-binding"}
    clock = FakeClock(deadline - timedelta(seconds=90))
    provider.clock = clock

    terminal = guardian.contain_bound_target(
        binding,
        arm_receipt=arm_receipt,
        provider=provider,
        clock=clock,
        poll_seconds=1,
    )

    assert provider.stop_calls[0][0] == "newpod1234"
    assert terminal["observed_terminal_status"] == "EXITED"


def test_transient_get_failures_do_not_prevent_bound_id_stop():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    arm_receipt, spec, start, _end, deadline = arm(now, provider)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": start.isoformat(),
        "desiredStatus": "RUNNING",
    }
    binding = guardian.discover_candidate(
        arm_receipt, inventory=[candidate], observed_at=start
    )
    assert binding is not None
    provider.pods["newpod1234"] = dict(candidate)
    clock = FakeClock(deadline - timedelta(seconds=100))
    provider.clock = clock
    real_get = provider.get_pod
    failures_remaining = 2

    def flaky_get(pod_id: str):
        nonlocal failures_remaining
        if failures_remaining:
            failures_remaining -= 1
            raise RuntimeError("temporary inventory outage")
        return real_get(pod_id)

    provider.get_pod = flaky_get  # type: ignore[method-assign]
    terminal = guardian.contain_bound_target(
        binding,
        arm_receipt=arm_receipt,
        provider=provider,
        clock=clock,
        poll_seconds=5,
    )
    assert provider.stop_calls == [("newpod1234", deadline - timedelta(seconds=90))]
    assert terminal["get_error_count"] == 2
    assert terminal["observed_terminal_status"] == "EXITED"


def test_binding_cannot_be_reused_with_a_different_arm_receipt():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    arm_receipt, spec, start, _end, deadline = arm(now, provider)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": start.isoformat(),
        "desiredStatus": "RUNNING",
    }
    binding = guardian.discover_candidate(
        arm_receipt, inventory=[candidate], observed_at=start
    )
    assert binding is not None
    different_arm = dict(arm_receipt)
    different_arm["receipt_sha256"] = "0" * 64
    clock = FakeClock(deadline - timedelta(seconds=90))
    with pytest.raises(ValueError, match="self-hash"):
        guardian.contain_bound_target(
            binding,
            arm_receipt=different_arm,
            provider=provider,
            clock=clock,
        )
    assert provider.stop_calls == []


def test_same_process_helper_cannot_publish_live_launch_authority():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, request, start, _end, _deadline = make_fixture(now)
    provider = FakeProvider([[]])
    clock = FakeClock(now)
    provider.clock = clock
    published: list[str] = []

    def publish(receipt: dict[str, object]) -> None:
        published.append(str(receipt["receipt_sha256"]))
        raise AssertionError("offline reference must not publish a live arm receipt")

    with pytest.raises(
        guardian.GuardianError,
        match="OFFLINE_REFERENCE_CANNOT_AUTHORIZE_LIVE_CREATE",
    ):
        guardian.arm_and_supervise_offline(
            spec,
            exact_create_request_bytes=request,
            provider=provider,
            clock=clock,
            publish_arm_receipt=publish,
            poll_seconds=30,
        )
    assert published == []
    assert provider.stop_calls == []


def test_arm_deadline_cannot_exceed_thirty_minutes_from_window_start():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, request, start, end, _deadline = make_fixture(now)
    overlong = guardian.ArmSpec(
        **{
            **spec.__dict__,
            "hard_stop_deadline_utc": (
                start + timedelta(seconds=guardian.MAX_POD_RUN_SECONDS, microseconds=1)
            ).isoformat(),
        }
    )
    with pytest.raises(ValueError, match="30 minutes from window start"):
        guardian.arm_guardian(
            overlong,
            exact_create_request_bytes=request,
            provider=FakeProvider([[]]),
            armed_at=now,
        )


def test_binding_deadline_is_capped_from_earliest_provider_birth():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, _end, armed_deadline = arm(now, provider)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": start.isoformat(),
        "lastStartedAt": (start + timedelta(seconds=2)).isoformat(),
        "desiredStatus": "RUNNING",
    }
    binding = guardian.discover_candidate(
        receipt, inventory=[candidate], observed_at=start + timedelta(seconds=3)
    )
    assert binding is not None
    expected = min(
        armed_deadline,
        start + timedelta(seconds=guardian.MAX_POD_RUN_SECONDS),
    )
    assert guardian._parse_utc(binding["hard_stop_deadline_utc"]) == expected


def test_candidate_cannot_bind_before_arm_window_or_provider_birth():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, spec, start, _end, _deadline = arm(now, provider)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": (start + timedelta(seconds=40)).isoformat(),
        "desiredStatus": "RUNNING",
    }
    with pytest.raises(guardian.AmbiguousTargetError, match="precedes"):
        guardian.discover_candidate(
            receipt,
            inventory=[candidate],
            observed_at=start - timedelta(seconds=2),
        )


def test_no_target_is_not_misreported_as_safe_or_contained():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, _spec, _start, _end, _deadline = arm(now, provider)
    clock = FakeClock(now)
    result = guardian.supervise_after_arm(
        receipt, provider=provider, clock=clock, poll_seconds=120
    )
    assert result.binding_receipt is None
    assert result.terminal_receipt["status"] == "UNRESOLVED_NO_UNIQUE_TARGET_BY_DEADLINE"
    assert result.terminal_receipt["containment_proven"] is False
    assert provider.stop_calls == []


def test_arm_receipt_tamper_is_rejected_before_inventory_or_stop():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, _spec, _start, _end, _deadline = arm(now, provider)
    tampered = dict(receipt)
    tampered["hard_stop_deadline_utc"] = (now + timedelta(hours=3)).isoformat()
    with pytest.raises(ValueError, match="self-hash"):
        guardian.discover_candidate(tampered, inventory=[], observed_at=now)
    assert provider.stop_calls == []


def test_rehashed_arm_receipt_cannot_extend_deadline_past_window_start_cap():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([[]])
    receipt, _spec, start, _end, _deadline = arm(now, provider)
    forged = dict(receipt)
    forged["hard_stop_deadline_utc"] = (
        start + timedelta(seconds=guardian.MAX_POD_RUN_SECONDS + 100)
    ).isoformat()
    forged.pop("receipt_sha256")
    forged = guardian._seal_receipt(forged)
    with pytest.raises(ValueError, match="30 minutes from window start"):
        guardian.supervise_after_arm(
            forged,
            provider=provider,
            clock=FakeClock(now),
            poll_seconds=60,
        )
    assert provider.stop_calls == []


def test_rehashed_arm_receipt_rejects_boolean_inventory_count():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    preexisting = {
        "id": "oldpod1234",
        "name": "unrelated",
        "desiredStatus": "EXITED",
    }
    provider = FakeProvider([[preexisting]])
    receipt, _spec, _start, _end, _deadline = arm(now, provider)
    forged = dict(receipt)
    forged["pre_arm_inventory_count"] = True
    forged.pop("receipt_sha256")
    forged = guardian._seal_receipt(forged)
    with pytest.raises(ValueError, match="inventory count"):
        guardian.supervise_after_arm(
            forged,
            provider=provider,
            clock=FakeClock(now),
            poll_seconds=60,
        )
    assert provider.stop_calls == []


def test_exact_create_request_rejects_nonfinite_json_number():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    spec, request, _start, _end, _deadline = make_fixture(now)
    name = json.loads(request)["name"]
    hostile = ('{"hostile":NaN,"name":' + json.dumps(name) + '}\n').encode("utf-8")
    hostile_spec = guardian.ArmSpec(
        **{
            **spec.__dict__,
            "exact_create_request_sha256": hashlib.sha256(hostile).hexdigest(),
        }
    )
    with pytest.raises(ValueError, match="not strict UTF-8 JSON"):
        guardian.arm_guardian(
            hostile_spec,
            exact_create_request_bytes=hostile,
            provider=FakeProvider([[]]),
            armed_at=now,
        )


def test_production_module_has_no_network_create_delete_or_model_surface():
    source = Path(guardian.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint({"urllib", "requests", "subprocess"})
    assert "def create_pod" not in source
    assert "def delete_pod" not in source
    assert "load_model" not in source
    assert set(guardian.ProviderAdapter.__dict__) >= {
        "list_pods",
        "get_pod",
        "stop_pod",
    }
