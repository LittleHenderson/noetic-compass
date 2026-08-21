"""Tests for the live launch driver.

Nothing here touches the network or spends anything. The decisive test is the
same discipline as the bridge: the `authorize` subcommand's document must be
ACCEPTED by the launcher's own `_load_authorization` — the validator that will
judge it at launch time.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import create_provider_launch_receipt as launcher
import launch_canary_pod as driver

COMMIT = "7c338f6dfc3446bd3ff55c7565eefc18fd24ae1d"


def _write_public_key(tmp_path: Path) -> Path:
    key = tmp_path / "runpod_cas.pub"
    key.write_text(
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGZha2V0ZXN0a2V5Zm9ydGVzdHM test-key\n",
        encoding="utf-8",
    )
    return key


def _common(tmp_path: Path) -> list[str]:
    return [
        "--authorization", str(tmp_path / "authorization.json"),
        "--source-commit", COMMIT,
        "--state-directory", str(tmp_path / "state"),
        "--public-key-path", str(_write_public_key(tmp_path)),
    ]


# -- authorize -------------------------------------------------------------


def test_authorize_document_is_accepted_by_the_launchers_own_loader(tmp_path):
    assert driver.main(["authorize", *_common(tmp_path)]) == 0
    path = tmp_path / "authorization.json"
    raw = path.read_bytes()
    value = json.loads(raw)
    configuration = launcher.LaunchConfiguration(
        pod_name=value["pod_name"],
        source_commit_sha256=COMMIT,
        oci_image_digest=driver.OCI_IMAGE_DIGEST,
        image_name=driver.IMAGE_NAME,
        public_key="ssh-ed25519 AAAA test",
        authorization_path=path,
        expected_authorization_sha256=launcher.sha256_bytes(raw),
        state_directory=tmp_path / "state",
        provider_receipt_path=tmp_path / "state" / "r.json",
        failure_evidence_path=tmp_path / "state" / "f.json",
        public_key_path=tmp_path / "runpod_cas.pub",
    )
    accepted = launcher._load_authorization(
        configuration,
        request_sha=value["request_body_sha256"],
        now=datetime.now(timezone.utc),
    )
    assert accepted["operation"] == "CREATE_EXACTLY_ONE_NEW_RUNPOD_POD"
    assert accepted["one_use"] is True
    assert accepted["maximum_spend_usd"] == "0.50"
    assert accepted["maximum_wall_seconds"] == 1800


def test_authorize_request_hash_matches_the_request_the_launch_will_build(tmp_path):
    driver.main(["authorize", *_common(tmp_path)])
    value = json.loads((tmp_path / "authorization.json").read_bytes())
    configuration = driver._configuration(
        type("A", (), {
            "authorization": str(tmp_path / "authorization.json"),
            "authorization_sha256": "",
            "source_commit": COMMIT,
            "state_directory": str(tmp_path / "state"),
            "public_key_path": str(tmp_path / "runpod_cas.pub"),
            "observed_hourly_rate": "0.44",
        })(),
        value["pod_name"],
    )
    rebuilt = launcher.canonical_json_bytes(
        launcher.build_create_request(configuration)
    )
    assert launcher.sha256_bytes(rebuilt) == value["request_body_sha256"]


def test_authorize_never_overwrites_an_existing_authorization(tmp_path):
    argv = ["authorize", *_common(tmp_path)]
    assert driver.main(argv) == 0
    assert driver.main(argv) == 3  # FileExistsError -> fail closed


def test_authorize_expiry_is_fifteen_minutes(tmp_path):
    driver.main(["authorize", *_common(tmp_path)])
    value = json.loads((tmp_path / "authorization.json").read_bytes())
    issued = launcher.parse_utc(value["issued_at_utc"])
    expires = launcher.parse_utc(value["expires_at_utc"])
    assert (expires - issued).total_seconds() == 900


# -- launch refusals -------------------------------------------------------


def test_launch_refuses_without_the_confirmation_flag(tmp_path):
    driver.main(["authorize", *_common(tmp_path)])
    code = driver.main(["launch", *_common(tmp_path)])
    assert code == 4


def test_launch_refuses_without_the_authorization_hash(tmp_path):
    driver.main(["authorize", *_common(tmp_path)])
    code = driver.main(
        ["launch", *_common(tmp_path), "--i-confirm-one-paid-create"]
    )
    assert code == 4


def test_launch_never_reaches_the_transport_without_a_credential(tmp_path, monkeypatch):
    """With confirmation and hash present but no credential, the driver must
    fail closed at the environment check, before any transport exists."""
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    driver.main(["authorize", *_common(tmp_path)])
    raw = (tmp_path / "authorization.json").read_bytes()
    with pytest.raises(SystemExit) as caught:
        driver.main([
            "launch",
            "--authorization", str(tmp_path / "authorization.json"),
            "--authorization-sha256", launcher.sha256_bytes(raw),
            "--source-commit", COMMIT,
            "--state-directory", str(tmp_path / "state"),
            "--public-key-path", str(tmp_path / "runpod_cas.pub"),
            "--i-confirm-one-paid-create",
        ])
    assert "MISSING_REQUIRED_ENVIRONMENT_RUNPOD_API_KEY" in str(caught.value)


# -- authority boundary ----------------------------------------------------


def test_driver_is_the_only_spender_and_uses_only_frozen_collaborators():
    text = Path(driver.__file__).read_text(encoding="utf-8")
    # every collaborator is the frozen library's or the tested bridge's
    for required in (
        "RunPodHttpsTransport",
        "BridgeGuardian",
        "RunnerAndWatchdogValidator",
        "SecretGuard",
        "execute_create_once",
    ):
        assert required in text
    # no ad-hoc HTTP anywhere in the driver
    for forbidden in ("urlopen", "requests.", "http.client"):
        assert forbidden not in text
