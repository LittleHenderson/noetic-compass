from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

import pytest


APP_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = APP_ROOT / "scripts" / "collect_hosted_runtime_worm_evidence.py"
SPEC = importlib.util.spec_from_file_location("hosted_runtime_worm", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

runtime = module.runtime
NOW = datetime(2026, 7, 15, 20, 10, tzinfo=UTC)
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-d9bntki8qa3s73ac90a0"
DEPLOYED_AT = "2026-07-15T20:00:00Z"
IDENTITY_NONCE = "0123456789abcdef01234567"
RUNTIME_NONCE = "89abcdef0123456701234567"
PLATFORM_SECRET = "platform-secret-private"
BILLING_SECRET = "billing-secret-private"
RENDER_KEY = "render-key-private"
ACCOUNT_ID = "acct-" + "b" * 32
PROVISIONING_ID = "tenantprov-" + "c" * 32
RECEIPT_ID = "tenantprovrct-" + "d" * 32
BEARER = "private-account-bearer"


def _body(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _result(status: int, value: Mapping[str, Any] | None = None) -> Any:
    return runtime.HttpResult(
        status=status,
        headers={} if value is None else {"content-type": "application/json"},
        body=b"" if value is None else _body(value),
    )


class FakeTransport:
    def __init__(
        self,
        *,
        render_changes: Mapping[str, Any] | None = None,
        logout_status: int = 204,
        network_once_path: str | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.render_changes = dict(render_changes or {})
        self.logout_status = logout_status
        self.network_once_path = network_once_path
        self.network_failed = False

    def __call__(self, **request: Any) -> Any:
        self.calls.append(dict(request))
        path = request["path"]
        if path == self.network_once_path and not self.network_failed:
            self.network_failed = True
            raise runtime.RuntimeWormFailure("network", "simulated transport loss")
        if request["base_url"] == runtime.RENDER_API_ORIGIN:
            payload = {
                "id": DEPLOY_ID,
                "status": "live",
                "trigger": "new_commit",
                "createdAt": "2026-07-15T19:59:00Z",
                "finishedAt": DEPLOYED_AT,
                "commit": {"id": MASTER_SHA},
            }
            payload.update(self.render_changes)
            return _result(200, payload)
        if path == "/platform/tenants":
            submitted = request["payload"]
            return _result(
                200,
                {
                    "owner": {
                        "account_id": ACCOUNT_ID,
                        "tenant_id": submitted["tenant_id"],
                        "email_or_username": submitted["email_or_username"],
                        "role": "owner",
                        "status": "active",
                    },
                    "provisioning_id": PROVISIONING_ID,
                    "receipt_id": RECEIPT_ID,
                    "completed_at": NOW.isoformat(),
                },
            )
        if path == "/platform/billing/manual-comped-subscription":
            submitted = request["payload"]
            return _result(
                200,
                {
                    "tenant_id": submitted["tenant_id"],
                    "plan_id": "beta_comped",
                    "status": "active",
                    "source": "manual_comped",
                    "expires_at": submitted["expires_at"],
                },
            )
        if path == "/auth/token":
            return _result(200, {"token": BEARER})
        if path == "/auth/logout":
            return _result(self.logout_status)
        raise AssertionError(f"unexpected request: {request}")


class FakeRuntimeFactory:
    def __init__(
        self,
        call_order: list[str],
        *,
        failure: Exception | None = None,
        unsafe_value: str | None = None,
    ) -> None:
        self.call_order = call_order
        self.failure = failure
        self.unsafe_value = unsafe_value
        self.kwargs: dict[str, Any] | None = None

    def __call__(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        parent = self

        class Instance:
            def collect(self) -> tuple[dict[str, Any], dict[str, Any]]:
                parent.call_order.append("runtime")
                if parent.failure is not None:
                    raise parent.failure
                evidence = {
                    "gate": "runtime_worm",
                    "artifact_sha256": "e" * 64,
                    "safe": parent.unsafe_value or "present",
                }
                artifact = {
                    "gate": "runtime_worm",
                    "authority_published": False,
                    "customer_production_status": "OPEN",
                }
                return evidence, artifact

        return Instance()


def _environment(**changes: str) -> dict[str, str]:
    value = {
        "RENDER_SERVICE_ID": runtime.PRODUCTION_SERVICE_ID,
        "RENDER_GIT_COMMIT": MASTER_SHA,
    }
    value.update(changes)
    return value


def _collector(
    transport: FakeTransport,
    factory: FakeRuntimeFactory,
    *,
    environment: Mapping[str, str] | None = None,
    platform_secret: str = PLATFORM_SECRET,
) -> Any:
    return module.HostedRuntimeWormCollector(
        base_url=runtime.PRODUCTION_API_ORIGIN,
        platform_secret=platform_secret,
        billing_secret=BILLING_SECRET,
        render_api_key=RENDER_KEY,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        deployed_at_utc=DEPLOYED_AT,
        runtime_environment=environment or _environment(),
        transport=transport,
        clock=lambda: NOW,
        identity_nonce=IDENTITY_NONCE,
        runtime_nonce=RUNTIME_NONCE,
        runtime_collector_factory=factory,
    )


def test_happy_path_preflights_before_mutation_and_logs_out_before_return() -> None:
    order: list[str] = []

    class OrderedTransport(FakeTransport):
        def __call__(self, **request: Any) -> Any:
            path = request["path"]
            order.append("render" if request["base_url"] == runtime.RENDER_API_ORIGIN else path)
            return super().__call__(**request)

    transport = OrderedTransport()
    factory = FakeRuntimeFactory(order)
    collector = _collector(transport, factory)

    evidence, artifact, logout_status = collector.collect()

    assert order == [
        "render",
        "/platform/tenants",
        "/platform/billing/manual-comped-subscription",
        "/auth/token",
        "runtime",
        "/auth/logout",
    ]
    assert logout_status == 204
    assert evidence["gate"] == artifact["gate"] == "runtime_worm"
    assert factory.kwargs is not None
    assert factory.kwargs["bearer_token"] == BEARER
    assert factory.kwargs["render_api_key"] == RENDER_KEY
    assert factory.kwargs["nonce"] == RUNTIME_NONCE
    assert module.runtime.API_TOKEN_ENV not in collector.runtime_environment


@pytest.mark.parametrize(
    ("environment", "error_fragment"),
    [
        ({"RENDER_GIT_COMMIT": MASTER_SHA}, "pinned production service"),
        (
            {
                "RENDER_SERVICE_ID": runtime.PRODUCTION_SERVICE_ID,
                "RENDER_GIT_COMMIT": "f" * 40,
            },
            "runtime commit",
        ),
        (
            {
                "RENDER_SERVICE_ID": runtime.PRODUCTION_SERVICE_ID,
                "RENDER_GIT_COMMIT": MASTER_SHA,
                runtime.API_TOKEN_ENV: "inherited",
            },
            "inherited account bearer",
        ),
    ],
)
def test_local_binding_failures_make_no_request(
    environment: Mapping[str, str], error_fragment: str
) -> None:
    transport = FakeTransport()
    with pytest.raises(runtime.RuntimeWormFailure, match=error_fragment):
        _collector(transport, FakeRuntimeFactory([]), environment=environment)
    assert transport.calls == []


@pytest.mark.parametrize(
    "render_changes",
    [
        {"status": "build_in_progress"},
        {"trigger": "service_updated"},
        {"commit": {"id": "f" * 40}},
        {"id": "dep-wrong"},
        {"finishedAt": "2026-07-15T19:59:59Z"},
    ],
)
def test_render_drift_fails_before_first_mutation(
    render_changes: Mapping[str, Any]
) -> None:
    transport = FakeTransport(render_changes=render_changes)
    with pytest.raises(runtime.RuntimeWormFailure, match="render-deployment"):
        _collector(transport, FakeRuntimeFactory([])).collect()
    assert [call["base_url"] for call in transport.calls] == [runtime.RENDER_API_ORIGIN]


def test_stale_deployment_fails_before_first_mutation() -> None:
    transport = FakeTransport()
    collector = module.HostedRuntimeWormCollector(
        base_url=runtime.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        render_api_key=RENDER_KEY,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        deployed_at_utc="2026-07-15T19:00:00Z",
        runtime_environment=_environment(),
        transport=transport,
        clock=lambda: NOW,
        identity_nonce=IDENTITY_NONCE,
        runtime_nonce=RUNTIME_NONCE,
        runtime_collector_factory=FakeRuntimeFactory([]),
    )
    with pytest.raises(runtime.RuntimeWormFailure, match="older than"):
        collector.collect()
    assert transport.calls == []


def test_render_read_crossing_freshness_boundary_fails_before_mutation() -> None:
    before = datetime(2026, 7, 15, 20, 29, 59, tzinfo=UTC)
    after = datetime(2026, 7, 15, 20, 30, 1, tzinfo=UTC)
    clock_values = iter((before, before, after))
    transport = FakeTransport()
    collector = module.HostedRuntimeWormCollector(
        base_url=runtime.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        render_api_key=RENDER_KEY,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        deployed_at_utc=DEPLOYED_AT,
        runtime_environment=_environment(),
        transport=transport,
        clock=lambda: next(clock_values),
        identity_nonce=IDENTITY_NONCE,
        runtime_nonce=RUNTIME_NONCE,
        runtime_collector_factory=FakeRuntimeFactory([]),
    )
    with pytest.raises(runtime.RuntimeWormFailure, match="older than"):
        collector.collect()
    assert [call["base_url"] for call in transport.calls] == [runtime.RENDER_API_ORIGIN]


def test_subsecond_provider_finish_cannot_match_truncated_pin() -> None:
    transport = FakeTransport(
        render_changes={"finishedAt": "2026-07-15T20:00:00.900Z"}
    )
    with pytest.raises(runtime.RuntimeWormFailure, match="finish time differs"):
        _collector(transport, FakeRuntimeFactory([])).collect()
    assert [call["base_url"] for call in transport.calls] == [runtime.RENDER_API_ORIGIN]


def test_provision_retry_reuses_exact_payload() -> None:
    transport = FakeTransport(network_once_path="/platform/tenants")
    collector = _collector(transport, FakeRuntimeFactory([]))
    collector._preflight()
    collector._provision()
    calls = [call for call in transport.calls if call["path"] == "/platform/tenants"]
    assert len(calls) == 2
    assert calls[0]["payload"] == calls[1]["payload"]


def test_ambiguous_entitlement_response_is_not_retried_or_followed_by_login() -> None:
    transport = FakeTransport(
        network_once_path="/platform/billing/manual-comped-subscription"
    )
    collector = _collector(transport, FakeRuntimeFactory([]))
    with pytest.raises(runtime.RuntimeWormFailure, match="network"):
        collector.collect()
    assert (
        sum(
            call["path"] == "/platform/billing/manual-comped-subscription"
            for call in transport.calls
        )
        == 1
    )
    assert not any(call["path"] == "/auth/token" for call in transport.calls)


def test_login_transport_ambiguity_is_not_retried() -> None:
    transport = FakeTransport(network_once_path="/auth/token")
    collector = _collector(transport, FakeRuntimeFactory([]))
    collector._preflight()
    tenant, identity, credential, account = collector._provision()
    collector._grant_comped(tenant, account)
    with pytest.raises(runtime.RuntimeWormFailure, match="network"):
        collector._login(identity, credential)
    assert sum(call["path"] == "/auth/token" for call in transport.calls) == 1


def test_valid_token_in_malformed_login_response_is_logged_out() -> None:
    class DuplicateTokenTransport(FakeTransport):
        def __call__(self, **request: Any) -> Any:
            if request["path"] == "/auth/token":
                self.calls.append(dict(request))
                return _result(200, {"token": BEARER, "duplicate": BEARER})
            return super().__call__(**request)

    transport = DuplicateTokenTransport()
    collector = _collector(transport, FakeRuntimeFactory([]))
    with pytest.raises(runtime.RuntimeWormFailure, match="duplicated"):
        collector.collect()
    assert transport.calls[-1]["path"] == "/auth/logout"
    assert collector._active_token is None


def test_runtime_failure_logs_out_and_returns_no_evidence() -> None:
    transport = FakeTransport()
    failure = runtime.RuntimeWormFailure("audit-run", "failed closed")
    collector = _collector(transport, FakeRuntimeFactory([], failure=failure))
    with pytest.raises(runtime.RuntimeWormFailure, match="audit-run"):
        collector.collect()
    assert transport.calls[-1]["path"] == "/auth/logout"
    assert collector._active_token is None


@pytest.mark.parametrize(
    "failure",
    [KeyboardInterrupt(), SystemExit(17)],
    ids=["keyboard-interrupt", "system-exit"],
)
def test_base_exception_after_login_still_logs_out_without_replacement(
    failure: BaseException,
) -> None:
    transport = FakeTransport()
    collector = _collector(transport, FakeRuntimeFactory([], failure=failure))
    with pytest.raises(type(failure)) as captured:
        collector.collect()
    assert captured.value is failure
    assert transport.calls[-1]["path"] == "/auth/logout"
    assert collector._active_token is None


@pytest.mark.parametrize(
    "failure",
    [KeyboardInterrupt(), SystemExit(17)],
    ids=["keyboard-interrupt", "system-exit"],
)
def test_base_exception_remains_primary_when_logout_also_fails(
    failure: BaseException,
) -> None:
    transport = FakeTransport(logout_status=500)
    collector = _collector(transport, FakeRuntimeFactory([], failure=failure))
    with pytest.raises(type(failure)) as captured:
        collector.collect()
    assert captured.value is failure
    assert sum(call["path"] == "/auth/logout" for call in transport.calls) == 4
    assert "probe session cleanup could not be confirmed" in tuple(
        getattr(captured.value, "__notes__", ())
    )


def test_runtime_failure_remains_primary_when_logout_also_fails() -> None:
    transport = FakeTransport(logout_status=500)
    failure = runtime.RuntimeWormFailure("audit-run", "original failure")
    collector = _collector(transport, FakeRuntimeFactory([], failure=failure))
    with pytest.raises(runtime.RuntimeWormFailure, match="audit-run") as captured:
        collector.collect()
    assert sum(call["path"] == "/auth/logout" for call in transport.calls) == 4
    assert "probe session cleanup could not be confirmed" in tuple(
        getattr(captured.value, "__notes__", ())
    )


def test_logout_failure_suppresses_successful_evidence() -> None:
    transport = FakeTransport(logout_status=500)
    collector = _collector(transport, FakeRuntimeFactory([]))
    with pytest.raises(runtime.RuntimeWormFailure, match="logout") as captured:
        collector.collect()
    # Two bounded confirmation attempts plus two best-effort revocation
    # attempts; no evidence escapes even when all four fail.
    assert sum(call["path"] == "/auth/logout" for call in transport.calls) == 4
    assert "probe session cleanup could not be confirmed" in tuple(
        getattr(captured.value, "__notes__", ())
    )


def test_wrapper_secret_scan_runs_after_logout() -> None:
    transport = FakeTransport()
    collector = _collector(
        transport, FakeRuntimeFactory([], unsafe_value=PLATFORM_SECRET)
    )
    with pytest.raises(runtime.RuntimeWormFailure, match="secret-safety"):
        collector.collect()
    assert transport.calls[-1]["path"] == "/auth/logout"
    assert collector._active_token is None


@pytest.mark.parametrize(
    "secret",
    [
        'secret-"quoted"-private-0123456789',
        "secret-\\backslash-private-0123456789",
        "sécret-non-ascii-private-0123456789",
    ],
)
def test_secret_scan_uses_decoded_json_semantics(secret: str) -> None:
    transport = FakeTransport()
    collector = _collector(
        transport,
        FakeRuntimeFactory([], unsafe_value=secret),
        platform_secret=secret,
    )
    with pytest.raises(runtime.RuntimeWormFailure, match="secret-safety"):
        collector.collect()
    assert transport.calls[-1]["path"] == "/auth/logout"
    assert runtime._semantic_contains_any(({"nested": [secret]},), (secret,))


def test_second_staged_write_failure_leaves_no_output_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence_path = tmp_path / "evidence.json"
    artifact_path = tmp_path / "artifact.json"
    original = runtime._atomic_write
    calls = 0

    def fail_second(path: Path, payload: Mapping[str, Any]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second staged write failure")
        original(path, payload)

    monkeypatch.setattr(runtime, "_atomic_write", fail_second)
    with pytest.raises(OSError, match="second staged write"):
        module._write_output_pair(
            evidence_path=evidence_path,
            evidence={"gate": "runtime_worm"},
            artifact_path=artifact_path,
            artifact={"gate": "runtime_worm"},
        )
    assert not evidence_path.exists()
    assert not artifact_path.exists()
    assert not list(tmp_path.glob("*.stage"))


def test_second_create_only_publish_failure_rolls_back_first_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence_path = tmp_path / "evidence.json"
    artifact_path = tmp_path / "artifact.json"
    original = os.link
    calls = 0

    def fail_second(source: os.PathLike[str], target: os.PathLike[str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second publish failure")
        original(source, target)

    monkeypatch.setattr(os, "link", fail_second)
    with pytest.raises(OSError, match="second publish"):
        module._write_output_pair(
            evidence_path=evidence_path,
            evidence={"gate": "runtime_worm"},
            artifact_path=artifact_path,
            artifact={"gate": "runtime_worm"},
        )
    assert not evidence_path.exists()
    assert not artifact_path.exists()
    assert not list(tmp_path.glob("*.stage"))


def test_pre_existing_output_pair_is_preserved_byte_for_byte(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    artifact_path = tmp_path / "artifact.json"
    original_evidence = b"existing evidence\n"
    original_artifact = b"existing artifact\n"
    evidence_path.write_bytes(original_evidence)
    artifact_path.write_bytes(original_artifact)

    with pytest.raises(runtime.RuntimeWormFailure, match="pre-existing output"):
        module._write_output_pair(
            evidence_path=evidence_path,
            evidence={"gate": "runtime_worm"},
            artifact_path=artifact_path,
            artifact={"gate": "runtime_worm"},
        )

    assert evidence_path.read_bytes() == original_evidence
    assert artifact_path.read_bytes() == original_artifact
    assert not list(tmp_path.glob("*.stage"))


def test_concurrent_second_target_is_preserved_when_first_target_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence_path = tmp_path / "evidence.json"
    artifact_path = tmp_path / "artifact.json"
    concurrent_evidence = b"concurrent evidence\n"
    original = os.link
    calls = 0

    def occupy_second_target(
        source: os.PathLike[str], target: os.PathLike[str]
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            Path(target).write_bytes(concurrent_evidence)
        original(source, target)

    monkeypatch.setattr(os, "link", occupy_second_target)
    with pytest.raises(FileExistsError):
        module._write_output_pair(
            evidence_path=evidence_path,
            evidence={"gate": "runtime_worm"},
            artifact_path=artifact_path,
            artifact={"gate": "runtime_worm"},
        )

    assert evidence_path.read_bytes() == concurrent_evidence
    assert not artifact_path.exists()
    assert not list(tmp_path.glob("*.stage"))


def test_run_surfaces_combined_failure_cleanup_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Runner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def collect(self) -> tuple[dict[str, Any], dict[str, Any], int]:
            failure = runtime.RuntimeWormFailure("audit-run", "original failure")
            failure.add_note("probe session cleanup could not be confirmed")
            raise failure

    monkeypatch.setattr(module, "HostedRuntimeWormCollector", Runner)
    result = module.run(
        [
            "--master-head",
            MASTER_SHA,
            "--deploy-id",
            DEPLOY_ID,
            "--deployed-at-utc",
            DEPLOYED_AT,
            "--output",
            str(tmp_path / "evidence.json"),
            "--safe-artifact-output",
            str(tmp_path / "receipt.json"),
        ]
    )
    assert result == 2
    report = json.loads(capsys.readouterr().err)
    assert report["gate"] == "audit-run"
    assert report["status"] == "OPEN"
    assert report["probe_session_cleanup_unconfirmed"] is True
    assert "cleanup could not be confirmed" in report["error"]


def test_run_surfaces_cleanup_warning_for_internal_primary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Runner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def collect(self) -> tuple[dict[str, Any], dict[str, Any], int]:
            failure = ValueError("do not expose internal detail")
            failure.add_note("probe session cleanup could not be confirmed")
            raise failure

    monkeypatch.setattr(module, "HostedRuntimeWormCollector", Runner)
    result = module.run(
        [
            "--master-head",
            MASTER_SHA,
            "--deploy-id",
            DEPLOY_ID,
            "--deployed-at-utc",
            DEPLOYED_AT,
            "--output",
            str(tmp_path / "evidence.json"),
            "--safe-artifact-output",
            str(tmp_path / "receipt.json"),
        ]
    )
    assert result == 2
    report = json.loads(capsys.readouterr().err)
    assert report["gate"] == "internal"
    assert report["probe_session_cleanup_unconfirmed"] is True
    assert "cleanup could not be confirmed" in report["error"]
    assert "do not expose internal detail" not in report["error"]


def test_run_writes_distinct_mode_0600_outputs_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = {"gate": "runtime_worm", "artifact_sha256": "e" * 64}
    artifact = {
        "gate": "runtime_worm",
        "authority_published": False,
        "customer_production_status": "OPEN",
    }

    class Runner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def collect(self) -> tuple[dict[str, Any], dict[str, Any], int]:
            return evidence, artifact, 204

    monkeypatch.setattr(module, "HostedRuntimeWormCollector", Runner)
    output = tmp_path / "evidence.json"
    receipt = tmp_path / "receipt.json"
    result = module.run(
        [
            "--master-head",
            MASTER_SHA,
            "--deploy-id",
            DEPLOY_ID,
            "--deployed-at-utc",
            DEPLOYED_AT,
            "--output",
            str(output),
            "--safe-artifact-output",
            str(receipt),
        ]
    )
    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8")) == evidence
    assert json.loads(receipt.read_text(encoding="utf-8")) == artifact
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "validated_hosted_draft"
    assert summary["authority_published"] is False
    assert summary["customer_production_status"] == "OPEN"


def test_dockerfile_keeps_explicit_bounded_script_allowlist() -> None:
    dockerfile = (APP_ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    for name in (
        "object_lock_smoke_validation.py",
        "collect_runtime_worm_evidence.py",
        "collect_hosted_runtime_worm_evidence.py",
    ):
        assert f"COPY scripts/{name} scripts/{name}" in dockerfile
    assert "COPY scripts/ scripts/" not in dockerfile


def test_runbook_uses_hidden_process_only_key_and_states_residuals() -> None:
    runbook = (
        APP_ROOT / "docs" / "runbooks" / "runtime_worm_evidence_collector.md"
    ).read_text(encoding="utf-8")
    assert "set +x" in runbook
    assert "set +o history" in runbook
    assert "read -r -s" in runbook
    assert 'RENDER_API_KEY="$RENDER_API_KEY"' in runbook
    assert "export RENDER_API_KEY" not in runbook
    assert "refuses any inherited account bearer" in runbook
    assert re.search(r"account and\s+provisioning\s+rows remain durable", runbook)
    assert "lost entitlement response" in runbook.lower()
    assert "lost login response" in runbook.lower()
    assert "normally 60 minutes" in runbook
    assert "revoke that key immediately" in runbook
