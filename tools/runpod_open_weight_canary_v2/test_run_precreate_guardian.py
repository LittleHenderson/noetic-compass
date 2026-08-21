"""Tests for the GitHub-hosted pre-create guardian driver.

Offline: a fake ProviderAdapter is injected by monkeypatching the adapter class,
so no network call is made and no credential is needed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import run_precreate_guardian as driver

POD_NAME = "cas-open-weight-canary-v2-testrun-" + "a" * 32
# The guardian requires GITHUB_SHA to EQUAL the guarded source commit, so the
# workflow cannot arm for one commit while running another. One constant serves
# both, which is what a real run looks like.
SOURCE_COMMIT = "b" * 40
FREE_POD = "abc123def456"


class FakeAdapter:
    """Only the three guardian methods exist, mirroring the real boundary."""

    def __init__(self, pods=None, *, stopped=None):
        self._pods = pods if pods is not None else []
        self.stopped = stopped if stopped is not None else []

    def list_pods(self):
        return list(self._pods)

    def get_pod(self, pod_id):
        for pod in self._pods:
            if pod["id"] == pod_id:
                return dict(pod)
        raise KeyError(pod_id)

    def stop_pod(self, pod_id):
        self.stopped.append(pod_id)
        return 200


def _create_request_bytes(pod_name: str = POD_NAME) -> bytes:
    """The guardian binds the arm to the exact create bytes, and refuses unless
    those bytes actually name the Pod being guarded. A fixture that omitted the
    name was correctly rejected with "exact create request does not contain the
    bound Pod name" -- that refusal is a feature, so the fixture is realistic."""
    return json.dumps({"cloudType": "SECURE", "name": pod_name}).encode()


def _env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "1234567890")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", SOURCE_COMMIT)


def _arm_argv(tmp_path: Path, request_file: Path) -> list[str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    # The guardian enforces armed <= window_start < window_end < deadline: it must
    # arm BEFORE the creation window opens, so a Pod cannot be created during a
    # period nothing was watching. The window therefore opens in the future.
    opens = now + timedelta(seconds=60)
    return [
        "--phase", "arm",
        "--pod-name", POD_NAME,
        "--exact-create-request", str(request_file),
        "--exact-create-request-sha256",
        hashlib.sha256(request_file.read_bytes()).hexdigest(),
        "--source-commit", SOURCE_COMMIT,
        "--oci-image-digest", "sha256:" + "c" * 64,
        "--creation-window-start-utc", fmt(opens),
        "--creation-window-end-utc", fmt(opens + timedelta(seconds=240)),
        "--hard-stop-deadline-utc", fmt(opens + timedelta(seconds=1500)),
        "--arm-receipt", str(tmp_path / "arm.json"),
    ]


def test_driver_exposes_no_create_or_delete_path():
    text = Path(driver.__file__).read_text(encoding="utf-8")
    for forbidden in ("create_pod", "delete_pod", "POST /v1/pods\"", "requests.post"):
        assert forbidden not in text


def test_driver_only_imports_the_bounded_adapter():
    text = Path(driver.__file__).read_text(encoding="utf-8")
    assert "RunPodGuardianAdapter" in text
    # No other provider transport may be imported here.
    assert "create_provider_launch_receipt" not in text


def test_arm_requires_the_full_spec(tmp_path, monkeypatch):
    _env(monkeypatch)
    code = driver.main(["--phase", "arm", "--arm-receipt", str(tmp_path / "a.json")])
    assert code == 2
    assert not (tmp_path / "a.json").exists()


def test_arm_fails_closed_without_github_identity(tmp_path, monkeypatch):
    for name in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(driver, "RunPodGuardianAdapter", lambda: FakeAdapter())
    request_file = tmp_path / "request.json"
    request_file.write_bytes(_create_request_bytes())
    with pytest.raises(SystemExit) as caught:
        driver.main(_arm_argv(tmp_path, request_file))
    assert "MISSING_REQUIRED_ENVIRONMENT" in str(caught.value)


def test_arm_writes_a_receipt_and_refuses_to_overwrite_it(tmp_path, monkeypatch):
    _env(monkeypatch)
    monkeypatch.setattr(driver, "RunPodGuardianAdapter", lambda: FakeAdapter())
    request_file = tmp_path / "request.json"
    request_file.write_bytes(_create_request_bytes())
    argv = _arm_argv(tmp_path, request_file)

    assert driver.main(argv) == 0
    receipt = json.loads((tmp_path / "arm.json").read_bytes())
    assert receipt["schema_version"] == "cas_runpod_precreate_guardian_arm.v1"
    assert receipt["pod_name"] == POD_NAME
    assert receipt["delete_attempted"] is False
    assert "vernmyfb3ck9po" in receipt["protected_pod_ids"]

    # Second run must not silently replace the durable receipt.
    with pytest.raises(SystemExit) as caught:
        driver.main(argv)
    assert "REFUSING_OVERWRITE" in str(caught.value)


def test_arm_refuses_when_the_bound_name_already_exists(tmp_path, monkeypatch):
    _env(monkeypatch)
    existing = [{"id": FREE_POD, "name": POD_NAME, "desiredStatus": "RUNNING"}]
    monkeypatch.setattr(driver, "RunPodGuardianAdapter", lambda: FakeAdapter(existing))
    request_file = tmp_path / "request.json"
    request_file.write_bytes(_create_request_bytes())
    code = driver.main(_arm_argv(tmp_path, request_file))
    assert code == 3  # fail closed
    assert not (tmp_path / "arm.json").exists()


def test_transport_failure_fails_closed_without_leaking(tmp_path, monkeypatch):
    _env(monkeypatch)

    def boom():
        raise driver.GuardianTransportError("PROVIDER_UNREACHABLE")

    monkeypatch.setattr(driver, "RunPodGuardianAdapter", boom)
    request_file = tmp_path / "request.json"
    request_file.write_bytes(_create_request_bytes())
    assert driver.main(_arm_argv(tmp_path, request_file)) == 3
    assert not (tmp_path / "arm.json").exists()


def test_supervise_requires_both_output_paths(tmp_path, monkeypatch):
    _env(monkeypatch)
    arm = tmp_path / "arm.json"
    arm.write_bytes(b"{}")
    code = driver.main(["--phase", "supervise", "--arm-receipt", str(arm)])
    assert code == 2


def test_supervise_rejects_a_non_object_arm_receipt(tmp_path, monkeypatch):
    _env(monkeypatch)
    arm = tmp_path / "arm.json"
    arm.write_bytes(b"[]")
    with pytest.raises(SystemExit) as caught:
        driver.main([
            "--phase", "supervise",
            "--arm-receipt", str(arm),
            "--binding-receipt", str(tmp_path / "b.json"),
            "--terminal-receipt", str(tmp_path / "t.json"),
        ])
    assert "INPUT_RECEIPT_NOT_AN_OBJECT" in str(caught.value)
