"""Tests for the bridge guardian.

The decisive test is compatibility: the bridge's receipt must pass the
launcher's OWN `_validate_guardian_receipt` — the exact check that exposed the
23-vs-22-key schema incompatibility. Everything is offline: a fake adapter and
a recording dispatcher are injected; no network, no credential, no gh call.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import create_provider_launch_receipt as launcher
from create_provider_launch_receipt import ArmContext, ProtocolFailure
from precreate_guardian_bridge import GUARDIAN_ID, STOP_WORKFLOW, BridgeGuardian

POD_NAME = "cas-open-weight-canary-v2-bridge-" + "a" * 32
REPO = "LittleHenderson/noetic-compass"


class FakeAdapter:
    def __init__(self, pods=None):
        self._pods = pods if pods is not None else []
        self.calls = 0

    def list_pods(self):
        self.calls += 1
        return list(self._pods)

    def get_pod(self, pod_id):  # pragma: no cover - unused by the bridge
        raise KeyError(pod_id)

    def stop_pod(self, pod_id):  # pragma: no cover - must never be called
        raise AssertionError("bridge must never stop a pod")


def _intent(pod_name: str = POD_NAME) -> dict[str, object]:
    """Build an intent exactly the way execute_create_once builds one."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = launcher._format_utc
    request_raw = launcher.canonical_json_bytes(
        {"cloudType": "SECURE", "name": pod_name}
    )
    return launcher._self_hashed(
        {
            "authorization_id": "auth-" + "1" * 28,
            "authorization_sha256": launcher.sha256_bytes(b"authorization"),
            "claim_boundary": launcher.INTENT_CLAIM,
            "creation_window_end_utc": fmt(now + timedelta(minutes=5)),
            "creation_window_start_utc": fmt(now),
            "maximum_hard_stop_deadline_utc": fmt(now + timedelta(seconds=1800)),
            "oci_image_digest": "sha256:" + "c" * 64,
            "pod_name": pod_name,
            "prepared_at_utc": fmt(now),
            "request_body_base64": base64.b64encode(request_raw).decode("ascii"),
            "request_body_byte_count": len(request_raw),
            "request_body_sha256": launcher.sha256_bytes(request_raw),
            "schema_version": launcher.INTENT_SCHEMA,
            "source_commit_sha256": "b" * 40,
            "status": "PREPARED_CREATE_NOT_SENT",
        },
        "intent_sha256",
    )


def _bridge(tmp_path: Path, pods=None, dispatcher=None):
    calls: list[list[str]] = []

    def record(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    guardian = BridgeGuardian(
        state_directory=tmp_path / "state",
        repository=REPO,
        adapter=FakeAdapter(pods),
        dispatcher=dispatcher if dispatcher is not None else record,
    )
    return guardian, calls


# -- the decisive test -----------------------------------------------------


def test_bridge_receipt_passes_the_launchers_own_validator(tmp_path):
    guardian, _ = _bridge(
        tmp_path,
        pods=[
            {"id": "vernmyfb3ck9po", "name": "old-evidence-pod"},
            {"id": "q2oqlooejhin7s", "name": "heavy_moccasin_gerbil"},
        ],
    )
    intent = _intent()
    raw = guardian.consume_authorization_and_arm_precreate(intent)
    receipt = launcher._validate_guardian_receipt(raw, intent)
    assert receipt["guardian_id"] == GUARDIAN_ID
    assert receipt["guardian_consumption_generation"] == 1
    assert receipt["pre_arm_inventory_count"] == 2
    assert receipt["status"] == "ARMED_FOR_EXACT_NAME_RECONCILIATION"


def test_receipt_schema_is_the_launchers_not_the_offline_guardians(tmp_path):
    guardian, _ = _bridge(tmp_path)
    raw = guardian.consume_authorization_and_arm_precreate(_intent())
    value = json.loads(raw)
    assert value["schema_version"] == "cas_runpod_precreate_guardian_receipt.v1"
    assert len(value) == 22


# -- one-time consumption --------------------------------------------------


def test_second_consumption_of_the_same_authorization_refuses(tmp_path):
    guardian, _ = _bridge(tmp_path)
    intent = _intent()
    guardian.consume_authorization_and_arm_precreate(intent)
    with pytest.raises(ProtocolFailure, match="BRIDGE_AUTHORIZATION_ALREADY_CONSUMED"):
        guardian.consume_authorization_and_arm_precreate(intent)


def test_consumption_survives_a_new_guardian_instance(tmp_path):
    intent = _intent()
    guardian, _ = _bridge(tmp_path)
    guardian.consume_authorization_and_arm_precreate(intent)
    # Fresh instance over the same state directory: durable, not in-memory.
    reborn = BridgeGuardian(
        state_directory=tmp_path / "state",
        repository=REPO,
        adapter=FakeAdapter(),
        dispatcher=lambda argv: 0,
    )
    with pytest.raises(ProtocolFailure, match="BRIDGE_AUTHORIZATION_ALREADY_CONSUMED"):
        reborn.consume_authorization_and_arm_precreate(intent)


def test_marker_is_written_before_the_inventory_is_taken(tmp_path):
    order: list[str] = []

    class OrderedAdapter(FakeAdapter):
        def list_pods(self):
            order.append("inventory")
            state = tmp_path / "state"
            assert any(p.name.startswith("consumed-") for p in state.iterdir()), (
                "the durable consumption marker must exist before the inventory"
            )
            return []

    guardian = BridgeGuardian(
        state_directory=tmp_path / "state",
        repository=REPO,
        adapter=OrderedAdapter(),
        dispatcher=lambda argv: 0,
    )
    guardian.consume_authorization_and_arm_precreate(_intent())
    assert order == ["inventory"]


# -- validator interplay ---------------------------------------------------


def test_a_pod_already_carrying_the_bound_name_is_rejected_by_the_validator(tmp_path):
    guardian, _ = _bridge(tmp_path, pods=[{"id": "abc123def456", "name": POD_NAME}])
    intent = _intent()
    raw = guardian.consume_authorization_and_arm_precreate(intent)
    with pytest.raises(ProtocolFailure, match="PRECREATE_GUARDIAN_NAME_ALREADY_PRESENT"):
        launcher._validate_guardian_receipt(raw, intent)


def test_hostile_inventory_entry_is_refused(tmp_path):
    guardian, _ = _bridge(tmp_path, pods=[{"id": None, "name": "x"}])
    with pytest.raises(ProtocolFailure, match="BRIDGE_INVENTORY_ENTRY_INVALID"):
        guardian.consume_authorization_and_arm_precreate(_intent())


# -- bind_exact_pod --------------------------------------------------------


def _context() -> ArmContext:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = launcher._format_utc
    return ArmContext(
        authorization_id="auth-" + "1" * 28,
        pod_id="abc123def456",
        pod_name=POD_NAME,
        provider_started_at_utc=fmt(now),
        hard_stop_deadline_utc=fmt(now + timedelta(seconds=1500)),
        source_commit_sha256="b" * 40,
        oci_image_digest="sha256:" + "c" * 64,
        image_name="runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
        provider_receipt_path=Path("provider.json"),
        provider_receipt_sha256=hashlib.sha256(b"receipt").hexdigest(),
    )


def test_bind_dispatches_the_stop_supervisor_for_the_exact_pod(tmp_path):
    guardian, calls = _bridge(tmp_path)
    context = _context()
    guardian.bind_exact_pod(context)
    assert len(calls) == 1
    argv = calls[0]
    assert argv[:4] == ["gh", "workflow", "run", STOP_WORKFLOW]
    assert f"pod_id={context.pod_id}" in argv
    assert f"pod_name={context.pod_name}" in argv
    assert f"hard_stop_deadline_utc={context.hard_stop_deadline_utc}" in argv
    binding = json.loads(
        (tmp_path / "state" / f"binding-{context.pod_id}.json").read_bytes()
    )
    assert binding["pod_id"] == context.pod_id
    assert binding["stop_workflow"] == STOP_WORKFLOW


def test_bind_fails_when_the_dispatch_fails(tmp_path):
    guardian, _ = _bridge(tmp_path, dispatcher=lambda argv: 1)
    with pytest.raises(ProtocolFailure, match="BRIDGE_GITHUB_STOP_DISPATCH_FAILED"):
        guardian.bind_exact_pod(_context())


def test_bind_refuses_a_second_binding_for_the_same_pod(tmp_path):
    guardian, _ = _bridge(tmp_path)
    context = _context()
    guardian.bind_exact_pod(context)
    with pytest.raises(ProtocolFailure, match="BRIDGE_POD_ALREADY_BOUND"):
        guardian.bind_exact_pod(context)


# -- authority boundary ----------------------------------------------------


def test_bridge_never_calls_stop_create_or_delete(tmp_path):
    text = Path(
        __file__
    ).parent.joinpath("precreate_guardian_bridge.py").read_text(encoding="utf-8")
    for forbidden in ("stop_pod", "create_pod", "delete_pod", "requests.post", "urlopen"):
        assert forbidden not in text


def test_invalid_repository_is_refused(tmp_path):
    with pytest.raises(ProtocolFailure, match="BRIDGE_REPOSITORY_INVALID"):
        BridgeGuardian(
            state_directory=tmp_path,
            repository="not-owner-slash-name",
            adapter=FakeAdapter(),
            dispatcher=lambda argv: 0,
        )
