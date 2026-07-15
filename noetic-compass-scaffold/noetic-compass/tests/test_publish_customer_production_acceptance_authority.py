"""Operational publisher tests: exact bindings, CAS, and secret-safe failures."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from api.acceptance_authority_contract import acceptance_authority_url
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityInvalid,
    CustomerProductionAcceptanceAuthorityStore,
    canonicalize_acceptance_evidence,
)
from api.services.acceptance_publication_authorizations import (
    AcceptancePublicationAuthorizationStore,
)
from api.services.production.state_substrate.memory_store import InMemoryStateStore
import scripts.publish_customer_production_acceptance_authority as publisher


MASTER = "a" * 40
DEPLOY = "dep-publishertest001"
AUTHORIZATION_SHA256 = hashlib.sha256(b"test-authorization").hexdigest()
AUTHORIZATION_URI = (
    f"{publisher.PRODUCTION_API_ORIGIN}/internal/acceptance-authorizations/"
    f"{AUTHORIZATION_SHA256}"
)


@pytest.fixture(autouse=True)
def _isolate_existing_publisher_tests_from_the_new_record_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        AcceptancePublicationAuthorizationStore,
        "assert_matches",
        lambda self, **kwargs: None,
    )


def _authority_auth(action: str) -> dict[str, str]:
    return {
        "authorization_artifact_uri": AUTHORIZATION_URI,
        "authorization_artifact_sha256": AUTHORIZATION_SHA256,
        "operation_reason": (
            "authorized_publication"
            if action == "publish"
            else "operator_safety_action"
        ),
    }


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _legal_evidence(now: datetime) -> dict[str, object]:
    stamp = _utc(now)
    return {
        "schema_version": "cas_harness_customer_production_gate_evidence.v2",
        "gate": "legal_publication_approval",
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
        "artifact_uri": acceptance_authority_url("legal_publication_approval"),
        "artifact_sha256": _sha("independent-legal-artifact"),
        "public_base_url": "https://cascompass.ai",
        "documents": [
            {
                "kind": kind,
                "url": f"https://cascompass.ai/{kind}",
                "http_status": 200,
                "content_sha256": _sha(f"document-{kind}"),
                "published_at_utc": stamp,
                "verified_at_utc": stamp,
            }
            for kind in ("legal", "privacy", "terms")
        ],
        "approvals": [
            {
                "role": role,
                "approval_artifact_uri": (
                    f"{publisher.PRODUCTION_API_ORIGIN}/"
                    f"internal/approvals/{role}"
                ),
                "approval_sha256": _sha(f"approval-{role}"),
                "approved_at_utc": stamp,
            }
            for role in ("legal_counsel", "privacy_owner", "product_owner")
        ],
        "claim_status_vocabulary": [
            "ACCEPT",
            "FLAG_FOR_HUMAN_REVIEW",
            "LICENSED",
            "NOT LICENSED",
            "OPEN",
            "present",
            "unavailable",
        ],
    }


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return path


def _validate_args(path: Path, digest: str | None = None) -> list[str]:
    args = [
        "validate",
        "--gate",
        "legal_publication_approval",
        "--evidence",
        str(path),
        "--expected-master-head",
        MASTER,
        "--expected-deploy-id",
        DEPLOY,
    ]
    if digest is not None:
        args.extend(["--expected-evidence-sha256", digest])
    return args


def _publish_args(
    path: Path,
    digest: str,
    head_version: int = 0,
    previous_digest: str | None = None,
) -> list[str]:
    args = [
        "publish",
        "--gate",
        "legal_publication_approval",
        "--evidence",
        str(path),
        "--expected-master-head",
        MASTER,
        "--expected-deploy-id",
        DEPLOY,
        "--expected-evidence-sha256",
        digest,
        "--expected-head-version",
        str(head_version),
        "--authorization-artifact-uri",
        AUTHORIZATION_URI,
        "--authorization-artifact-sha256",
        AUTHORIZATION_SHA256,
        "--operation-reason",
        "authorized_publication",
    ]
    if previous_digest is not None:
        args.extend(["--expected-previous-evidence-sha256", previous_digest])
    return args


def _render_environ() -> dict[str, str]:
    return {
        "IS_PULL_REQUEST": "false",
        "RENDER": "true",
        "RENDER_EXTERNAL_URL": publisher.PRODUCTION_API_ORIGIN,
        "RENDER_GIT_BRANCH": "master",
        "RENDER_GIT_COMMIT": MASTER,
        "RENDER_GIT_REPO_SLUG": publisher.REPOSITORY,
        "RENDER_SERVICE_ID": publisher.PRODUCTION_SERVICE_ID,
        "RENDER_SERVICE_NAME": publisher.PRODUCTION_SERVICE_NAME,
        "RENDER_SERVICE_TYPE": "web",
    }


def test_direct_script_invocation_bootstraps_application_imports(
    tmp_path: Path,
) -> None:
    script = Path(publisher.__file__).resolve()
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "{validate,head,publish,deactivate}" in result.stdout


def test_validate_hashes_exact_canonical_bytes_without_opening_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    expected = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=now
        )
    ).hexdigest()

    def forbidden(**_: object):
        raise AssertionError("validate must not open production state")

    monkeypatch.setattr(publisher, "_production_authority", forbidden)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _validate_args(path, expected), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "evidence_sha256": expected,
        "gate": "legal_publication_approval",
        "status": "valid",
    }


def test_validate_rejects_duplicate_json_keys_before_binding_checks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"master_head_sha":"' + MASTER + '","gate":"a","gate":"b"}',
        encoding="utf-8",
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _validate_args(path), stdout=stdout, stderr=stderr
    )

    assert result == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["code"] == "duplicate_json_key"


def test_validate_reports_out_of_range_url_port_as_evidence_invalid(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    approvals = evidence["approvals"]
    assert isinstance(approvals, list)
    approvals[0]["approval_artifact_uri"] = (  # type: ignore[index]
        f"{publisher.PRODUCTION_API_ORIGIN}:99999/internal/approval"
    )
    path = _write(tmp_path / "bad-port.json", evidence)
    stdout, stderr = io.StringIO(), io.StringIO()

    result = publisher.run(
        _validate_args(path), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["code"] == "evidence_invalid"


def test_publish_uses_expected_head_and_verifies_exact_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    canonical = canonicalize_acceptance_evidence(
        "legal_publication_approval", evidence, now=now
    )
    digest = hashlib.sha256(canonical).hexdigest()
    authority = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())

    @contextmanager
    def fake_production_authority(**_: object):
        yield authority

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, digest), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 0
    assert stderr.getvalue() == ""
    output = json.loads(stdout.getvalue())
    head = authority.current_head("legal_publication_approval")
    assert head is not None
    assert output == {
        "evidence_sha256": digest,
        "gate": "legal_publication_approval",
        "head_version": 1,
        "operation_record_id": head.operation_record_id,
        "operation_sha256": head.operation_sha256,
        "readback_verified": True,
        "status": "published",
        "storage_mode": "state_store",
    }
    assert authority.load("legal_publication_approval", now=now).body == canonical


def test_head_returns_version_hash_and_active_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    authority = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    published = authority.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_authority_auth("publish"),
        now=now,
    )

    @contextmanager
    def fake_production_authority(**_: object):
        yield authority

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "head",
            "--gate",
            "legal_publication_approval",
            "--expected-master-head",
            MASTER,
        ],
        now=now,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "active": True,
        "evidence_sha256": published.sha256,
        "gate": "legal_publication_approval",
        "head_version": 1,
        "operation_record_id": published.operation_record_id,
        "operation_sha256": published.operation_sha256,
        "status": "observed",
    }


def test_deactivate_tombstones_exact_hash_and_verifies_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    authority = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    published = authority.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_authority_auth("publish"),
        now=now,
    )

    @contextmanager
    def fake_production_authority(**_: object):
        yield authority

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "deactivate",
            "--gate",
            "legal_publication_approval",
            "--expected-master-head",
            MASTER,
            "--expected-evidence-sha256",
            published.sha256,
            "--expected-head-version",
            "1",
            "--authorization-artifact-uri",
            AUTHORIZATION_URI,
            "--authorization-artifact-sha256",
            AUTHORIZATION_SHA256,
            "--operation-reason",
            "operator_safety_action",
        ],
        now=now,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 0
    assert stderr.getvalue() == ""
    output = json.loads(stdout.getvalue())
    head = authority.current_head("legal_publication_approval")
    assert head is not None
    assert output == {
        "already_inactive": False,
        "evidence_sha256": published.sha256,
        "gate": "legal_publication_approval",
        "head_version": 2,
        "operation_record_id": head.operation_record_id,
        "operation_sha256": head.operation_sha256,
        "readback_verified": True,
        "status": "inactive",
    }
    head = authority.current_head("legal_publication_approval")
    assert head is not None and head.active is False


def test_replacement_requires_previous_hash_before_opening_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=now
        )
    ).hexdigest()

    def forbidden(**_: object):
        raise AssertionError("missing previous hash must fail before production")

    monkeypatch.setattr(publisher, "_production_authority", forbidden)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, digest, head_version=1),
        now=now,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 2
    assert stdout.getvalue() == ""
    assert (
        json.loads(stderr.getvalue())["code"]
        == "expected_previous_evidence_sha256_required"
    )


def test_wrong_expected_hash_fails_before_production_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    path = _write(tmp_path / "legal.json", _legal_evidence(now))

    def forbidden(**_: object):
        raise AssertionError("hash mismatch must fail before production")

    monkeypatch.setattr(publisher, "_production_authority", forbidden)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, "0" * 64), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["code"] == "evidence_sha256_mismatch"


def test_post_mutation_readback_failure_reports_unknown_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    canonical = canonicalize_acceptance_evidence(
        "legal_publication_approval", evidence, now=now
    )
    digest = hashlib.sha256(canonical).hexdigest()
    base = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())

    class FailingReadback:
        def assert_publication_authorized(self, **kwargs):  # type: ignore[no-untyped-def]
            return base.assert_publication_authorized(**kwargs)

        def publish(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return base.publish(*args, **kwargs)

        def load(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise publisher.AcceptanceAuthorityUnavailable("driver secret")

    @contextmanager
    def fake_production_authority(**_: object):
        yield FailingReadback()

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, digest), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 4
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "code": "mutation_readback_failed",
        "detail": "mutation may have committed; recover by reading the exact head",
        "publication_state": "unknown",
        "status": "error",
    }
    assert base.current_head_version("legal_publication_approval") == 1


def test_publish_commit_then_disconnect_reports_unknown_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    canonical = canonicalize_acceptance_evidence(
        "legal_publication_approval", evidence, now=now
    )
    digest = hashlib.sha256(canonical).hexdigest()
    base = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())

    class CommitThenDisconnect:
        def assert_publication_authorized(self, **kwargs):  # type: ignore[no-untyped-def]
            return base.assert_publication_authorized(**kwargs)

        def publish(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            base.publish(*args, **kwargs)
            raise publisher.AcceptanceAuthorityUnavailable("driver secret")

    @contextmanager
    def fake_production_authority(**_: object):
        yield CommitThenDisconnect()

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, digest), now=now, stdout=stdout, stderr=stderr
    )

    assert result == 4
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["publication_state"] == "unknown"
    assert base.current_head_version("legal_publication_approval") == 1


def test_deactivate_commit_then_disconnect_reports_unknown_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    base = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    published = base.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_authority_auth("publish"),
        now=now,
    )

    class CommitThenDisconnect:
        def deactivate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            base.deactivate(*args, **kwargs)
            raise publisher.AcceptanceAuthorityUnavailable("driver secret")

    @contextmanager
    def fake_production_authority(**_: object):
        yield CommitThenDisconnect()

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "deactivate",
            "--gate",
            "legal_publication_approval",
            "--expected-master-head",
            MASTER,
            "--expected-evidence-sha256",
            published.sha256,
            "--expected-head-version",
            "1",
            "--authorization-artifact-uri",
            AUTHORIZATION_URI,
            "--authorization-artifact-sha256",
            AUTHORIZATION_SHA256,
            "--operation-reason",
            "operator_safety_action",
        ],
        now=now,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 4
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["publication_state"] == "unknown"
    head = base.current_head("legal_publication_approval")
    assert head is not None and head.active is False


def test_stale_head_fails_closed_without_replacing_active_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = _legal_evidence(now)
    path = _write(tmp_path / "legal.json", evidence)
    canonical = canonicalize_acceptance_evidence(
        "legal_publication_approval", evidence, now=now
    )
    digest = hashlib.sha256(canonical).hexdigest()
    authority = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    authority.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_authority_auth("publish"),
        now=now,
    )

    @contextmanager
    def fake_production_authority(**_: object):
        yield authority

    monkeypatch.setattr(
        publisher, "_production_authority", fake_production_authority
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        _publish_args(path, digest, head_version=0),
        now=now,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 3
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["code"] == "head_version_conflict"
    assert authority.current_head_version("legal_publication_approval") == 1


@pytest.mark.parametrize(
    ("settings", "environ", "code"),
    [
        (
            SimpleNamespace(
                debug=True,
                state_ledger_enabled=True,
                database_url="postgresql://redacted",
            ),
            {"RENDER_SERVICE_ID": publisher.PRODUCTION_SERVICE_ID, "RENDER_GIT_COMMIT": MASTER},
            "debug_runtime_forbidden",
        ),
        (
            SimpleNamespace(
                debug=False,
                state_ledger_enabled=False,
                database_url="postgresql://redacted",
            ),
            {"RENDER_SERVICE_ID": publisher.PRODUCTION_SERVICE_ID, "RENDER_GIT_COMMIT": MASTER},
            "state_ledger_disabled",
        ),
        (
            SimpleNamespace(
                debug=False, state_ledger_enabled=True, database_url="sqlite:///local.db"
            ),
            {"RENDER_SERVICE_ID": publisher.PRODUCTION_SERVICE_ID, "RENDER_GIT_COMMIT": MASTER},
            "shared_postgres_required",
        ),
        (
            SimpleNamespace(
                debug=False,
                state_ledger_enabled=True,
                database_url="postgresql://redacted",
            ),
            {"RENDER_SERVICE_ID": "srv-wrong", "RENDER_GIT_COMMIT": MASTER},
            "render_service_mismatch",
        ),
        (
            SimpleNamespace(
                debug=False,
                state_ledger_enabled=True,
                database_url="postgresql://redacted",
            ),
            {"RENDER_SERVICE_ID": publisher.PRODUCTION_SERVICE_ID, "RENDER_GIT_COMMIT": "b" * 40},
            "runtime_commit_mismatch",
        ),
    ],
)
def test_production_binding_rejects_wrong_runtime(
    settings: SimpleNamespace, environ: dict[str, str], code: str
) -> None:
    with pytest.raises(publisher.PublisherInputError) as raised:
        publisher._assert_production_binding(
            settings, expected_master_head=MASTER, environ=environ
        )
    assert raised.value.code == code


def test_production_binding_accepts_the_complete_exact_render_identity() -> None:
    settings = SimpleNamespace(
        debug=False,
        state_ledger_enabled=True,
        database_url="postgresql://redacted",
    )
    publisher._assert_production_binding(
        settings, expected_master_head=MASTER, environ=_render_environ()
    )


def test_head_and_deactivate_authority_setup_does_not_touch_s3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api import config as config_module
    from api import state_ledger_bootstrap
    from api.services import cas_harness_evidence_object_store

    calls = {"s3": 0}

    class Settings:
        evidence_packet_object_store_enabled = True
        accounts_bootstrap_tenant_id = "primary"

        def validate_object_lock_receipt_attestation(self) -> None:
            calls["s3"] += 1
            raise RuntimeError("S3 attestation unavailable")

    class StateStore(InMemoryStateStore):
        closed = False

        def close(self) -> None:
            self.closed = True

    state_store = StateStore()

    def unavailable_s3(_state_store: object) -> object:
        calls["s3"] += 1
        raise RuntimeError("S3 unavailable")

    monkeypatch.setattr(config_module, "Settings", Settings)
    monkeypatch.setattr(
        state_ledger_bootstrap, "_build_state_store", lambda _settings: state_store
    )
    monkeypatch.setattr(
        cas_harness_evidence_object_store,
        "build_s3_evidence_packet_repository",
        unavailable_s3,
    )
    monkeypatch.setattr(
        publisher, "_assert_production_binding", lambda *_args, **_kwargs: None
    )

    with publisher._production_authority(
        expected_master_head=MASTER,
        environ=_render_environ(),
        include_immutable_backend=False,
    ) as authority:
        assert authority.current_head("legal_publication_approval") is None
        from api.services.human_attestations import HumanAttestationStore

        assert isinstance(authority._human_attestations, HumanAttestationStore)
        now = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
        with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
            authority.assert_human_attestations(
                "legal_publication_approval", _legal_evidence(now), now=now
            )

    assert calls == {"s3": 0}
    assert state_store.closed is True


@pytest.mark.parametrize(
    "field",
    [
        "IS_PULL_REQUEST",
        "RENDER",
        "RENDER_EXTERNAL_URL",
        "RENDER_GIT_BRANCH",
        "RENDER_GIT_REPO_SLUG",
        "RENDER_SERVICE_NAME",
        "RENDER_SERVICE_TYPE",
    ],
)
def test_production_binding_rejects_every_secondary_identity_mismatch(
    field: str,
) -> None:
    settings = SimpleNamespace(
        debug=False,
        state_ledger_enabled=True,
        database_url="postgresql://redacted",
    )
    environ = _render_environ()
    environ[field] = "wrong"
    with pytest.raises(publisher.PublisherInputError) as raised:
        publisher._assert_production_binding(
            settings, expected_master_head=MASTER, environ=environ
        )
    assert raised.value.code == "render_runtime_identity_mismatch"


def test_unexpected_backend_failure_never_prints_exception_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "postgresql://operator:do-not-print@db.example/prod"

    @contextmanager
    def failed_authority(**_: object):
        raise RuntimeError(secret)
        yield  # pragma: no cover

    monkeypatch.setattr(publisher, "_production_authority", failed_authority)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "head",
            "--gate",
            "legal_publication_approval",
            "--expected-master-head",
            MASTER,
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 5
    assert stdout.getvalue() == ""
    assert secret not in stderr.getvalue()
    assert json.loads(stderr.getvalue()) == {
        "code": "unexpected_failure",
        "error_type": "RuntimeError",
        "status": "error",
    }
