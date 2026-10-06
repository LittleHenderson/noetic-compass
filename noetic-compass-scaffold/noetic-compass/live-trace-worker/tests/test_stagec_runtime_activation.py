from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import inspect
import json
import pickle
import threading
from typing import Any

import pytest

from app.runtime import stagec_runtime_activation as gate


_A = "A" * 64
_B = "B" * 64
_C = "C" * 64
_D = "D" * 64
_E = "E" * 64
_F = "F" * 64


def _artifact_identity(
    artifact_id: str,
    digest: str,
    byte_length: int,
    media_type: str,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": digest,
        "byte_length": byte_length,
        "media_type": media_type,
    }


def _capture_ids() -> dict[str, str]:
    return {
        name: f"stagec-{name.replace('_', '-')}-001"
        for name in gate.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    }


def _envelope_kwargs() -> dict[str, Any]:
    return {
        "request_artifact_identity": _artifact_identity(
            "stagec-request-001",
            _A,
            100,
            gate.REQUEST_MEDIA_TYPE,
        ),
        "authorization_projection_artifact_identity": _artifact_identity(
            "stagec-authorization-001",
            _B,
            200,
            gate.AUTHORIZATION_PROJECTION_MEDIA_TYPE,
        ),
        "capture_artifact_ids": _capture_ids(),
        "tenant_id": "tenant-001",
        "worker_id": "worker-001",
        "lease_generation": 7,
        "attempt_subject_sha256": _C,
        "case_id": "stagec-case-001",
        "case_execution_ordinal": 1,
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_revision": "a" * 40,
        "model_config_sha256": _D,
        "weights_sha256": _E,
        "tokenizer_json_sha256": _F,
        "tokenizer_config_sha256": _A,
        "chat_template_sha256": _B,
        "capture_profile_sha256": _C,
        "phase_activation_id": "stagec-phase-activation-001",
        "ledger_generation": 11,
    }


def _envelope(**changes: Any) -> gate.StageCRuntimeActivationEnvelope:
    values = _envelope_kwargs()
    values.update(changes)
    return gate.build_stagec_runtime_activation_envelope(**values)


class _TrustedTestBackend:
    def __init__(
        self,
        *,
        fixed_claim_id: str | None = None,
        fail_authenticate: bool = False,
        fail_terminalize: bool = False,
        bad_terminal: bool = False,
        mutate_terminal_inputs: bool = False,
        claim_mutation: tuple[str, Any] | None = None,
        fail_ambiguous_terminalize: bool = False,
        ambiguous_terminal_mutation: tuple[str, Any] | None = None,
        mutate_authenticate_envelope: bool = False,
    ) -> None:
        self.fixed_claim_id = fixed_claim_id
        self.fail_authenticate = fail_authenticate
        self.fail_terminalize = fail_terminalize
        self.bad_terminal = bad_terminal
        self.mutate_terminal_inputs = mutate_terminal_inputs
        self.claim_mutation = claim_mutation
        self.fail_ambiguous_terminalize = fail_ambiguous_terminalize
        self.ambiguous_terminal_mutation = ambiguous_terminal_mutation
        self.mutate_authenticate_envelope = mutate_authenticate_envelope
        self.authenticate_calls = 0
        self.terminalize_calls = 0
        self.redemption_calls = 0
        self.invalidation_calls = 0
        self.ambiguous_terminalize_calls = 0
        self.ambiguous_reasons: list[str] = []
        self.terminal_states: list[str] = []
        self.last_claim_observation: (
            gate.StageCRuntimeActivationLedgerObservation | None
        ) = None
        self.current_trust: dict[str, Any] = {
            "trusted_time_in_window": True,
            "storage_version": "object-version-001",
            "storage_checksum": _A,
            "retention_sufficient": True,
            "worker_lease_active": True,
            "authorization_revoked": False,
            "ledger_generation": 11,
        }

    def authenticate_and_claim_stagec_runtime_activation(
        self,
        *,
        envelope: gate.StageCRuntimeActivationEnvelope,
        claim_operation_id: str,
    ) -> gate.StageCRuntimeActivationLedgerObservation:
        self.authenticate_calls += 1
        if self.fail_authenticate:
            raise RuntimeError("test backend rejected")
        payload = gate.replay_stagec_runtime_activation_envelope(envelope)
        claim_id = self.fixed_claim_id or f"test-claim-{self.authenticate_calls}"
        observation = gate.StageCRuntimeActivationLedgerObservation(
            schema_version=gate.STAGEC_RUNTIME_LEDGER_OBSERVATION_SCHEMA,
            envelope_sha256=envelope.sha256,
            logical_row_claim_sha256=gate._logical_row_claim_sha256(payload),
            claim_operation_id=claim_operation_id,
            backend_claim_id=claim_id,
            ledger_observation_sha256=_D,
            phase_activation_id=payload["runtime_authorization"][
                "phase_activation_id"
            ],
            case_id=payload["attempt"]["case_id"],
            case_execution_ordinal=payload["attempt"][
                "case_execution_ordinal"
            ],
            ledger_generation=payload["runtime_authorization"][
                "ledger_generation"
            ],
            prior_claim_state="UNCLAIMED",
            claim_state="AUTHENTICATED_AND_CLAIMED_FOR_ONE_MODEL_CALL",
            claimed_now=True,
        )
        if self.claim_mutation is not None:
            object.__setattr__(observation, *self.claim_mutation)
        if self.mutate_authenticate_envelope:
            object.__setattr__(envelope, "sha256", "0" * 64)
        self.last_claim_observation = observation
        return observation

    def _terminal_observation(
        self,
        *,
        envelope: gate.StageCRuntimeActivationEnvelope,
        observation: gate.StageCRuntimeActivationLedgerObservation,
        terminal_state: str,
    ) -> gate.StageCRuntimeActivationTerminalObservation:
        self.terminalize_calls += 1
        self.terminal_states.append(terminal_state)
        if self.fail_terminalize:
            raise RuntimeError("test terminal ledger unavailable")
        state = "INVALIDATED_REJECTED_PRE_MODEL_CALL" if self.bad_terminal else terminal_state
        envelope_sha256 = envelope.sha256
        backend_claim_id = observation.backend_claim_id
        ledger_observation_sha256 = observation.ledger_observation_sha256
        phase_activation_id = observation.phase_activation_id
        ledger_generation = observation.ledger_generation
        if self.mutate_terminal_inputs:
            object.__setattr__(envelope, "sha256", "0" * 64)
            object.__setattr__(observation, "backend_claim_id", "mutated-backend-claim")
        terminal_digest = sha256(
            f"{backend_claim_id}:{state}".encode("ascii")
        ).hexdigest().upper()
        fresh_digest = sha256(
            json.dumps(
                self.current_trust,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            + f":{self.terminalize_calls}".encode("ascii")
        ).hexdigest().upper()
        return gate.StageCRuntimeActivationTerminalObservation(
            schema_version=gate.STAGEC_RUNTIME_TERMINAL_OBSERVATION_SCHEMA,
            envelope_sha256=envelope_sha256,
            backend_claim_id=backend_claim_id,
            ledger_observation_sha256=ledger_observation_sha256,
            fresh_trust_observation_sha256=fresh_digest,
            terminal_observation_sha256=terminal_digest,
            phase_activation_id=phase_activation_id,
            ledger_generation=ledger_generation + 1,
            terminal_state=state,
        )

    def reauthenticate_and_redeem_stagec_runtime_activation_claim(
        self,
        *,
        envelope: gate.StageCRuntimeActivationEnvelope,
        observation: gate.StageCRuntimeActivationLedgerObservation,
        terminal_state: str,
    ) -> gate.StageCRuntimeActivationTerminalObservation:
        self.redemption_calls += 1
        if (
            self.current_trust["trusted_time_in_window"] is not True
            or self.current_trust["storage_version"] != "object-version-001"
            or self.current_trust["storage_checksum"] != _A
            or self.current_trust["retention_sufficient"] is not True
            or self.current_trust["worker_lease_active"] is not True
            or self.current_trust["authorization_revoked"] is not False
            or self.current_trust["ledger_generation"]
            != observation.ledger_generation
        ):
            raise RuntimeError("fresh redemption trust recheck rejected")
        return self._terminal_observation(
            envelope=envelope,
            observation=observation,
            terminal_state=terminal_state,
        )

    def terminalize_stagec_runtime_activation_claim(
        self,
        *,
        envelope: gate.StageCRuntimeActivationEnvelope,
        observation: gate.StageCRuntimeActivationLedgerObservation,
        terminal_state: str,
    ) -> gate.StageCRuntimeActivationTerminalObservation:
        self.invalidation_calls += 1
        return self._terminal_observation(
            envelope=envelope,
            observation=observation,
            terminal_state=terminal_state,
        )

    def terminalize_ambiguous_stagec_runtime_activation_claim(
        self,
        *,
        envelope_sha256: str,
        logical_row_claim_key: tuple[str, str, str],
        logical_row_claim_sha256: str,
        claim_operation_id: str,
        tenant_id: str,
        phase_activation_id: str,
        attempt_subject_sha256: str,
        case_id: str,
        case_execution_ordinal: int,
        prior_ledger_generation: int,
        ambiguity_reason: str,
        terminal_state: str,
    ) -> gate.StageCRuntimeActivationAmbiguousTerminalObservation:
        self.ambiguous_terminalize_calls += 1
        self.ambiguous_reasons.append(ambiguity_reason)
        if self.fail_ambiguous_terminalize:
            raise RuntimeError("test ambiguous terminal ledger unavailable")
        assert logical_row_claim_key == (
            tenant_id,
            phase_activation_id,
            attempt_subject_sha256,
        )
        terminal_digest = sha256(
            (
                f"{envelope_sha256}:{logical_row_claim_sha256}:"
                f"{claim_operation_id}:{ambiguity_reason}:"
                f"{prior_ledger_generation + 1}"
            ).encode("ascii")
        ).hexdigest().upper()
        terminal = gate.StageCRuntimeActivationAmbiguousTerminalObservation(
            schema_version=(
                gate.STAGEC_RUNTIME_AMBIGUOUS_TERMINAL_OBSERVATION_SCHEMA
            ),
            envelope_sha256=envelope_sha256,
            logical_row_claim_sha256=logical_row_claim_sha256,
            claim_operation_id=claim_operation_id,
            terminal_observation_sha256=terminal_digest,
            tenant_id=tenant_id,
            phase_activation_id=phase_activation_id,
            attempt_subject_sha256=attempt_subject_sha256,
            case_id=case_id,
            case_execution_ordinal=case_execution_ordinal,
            prior_ledger_generation=prior_ledger_generation,
            ledger_generation=prior_ledger_generation + 1,
            ambiguity_reason=ambiguity_reason,
            terminal_state=terminal_state,
            tombstoned_now=True,
        )
        if self.ambiguous_terminal_mutation is not None:
            object.__setattr__(terminal, *self.ambiguous_terminal_mutation)
        return terminal


class _ArbitrarySpyBackend:
    def __init__(self) -> None:
        self.calls = 0

    def authenticate_and_claim_stagec_runtime_activation(self, **_kwargs: Any) -> Any:
        self.calls += 1
        raise AssertionError("an unregistered backend must not be called")

    def terminalize_stagec_runtime_activation_claim(self, **_kwargs: Any) -> Any:
        self.calls += 1
        raise AssertionError("an unregistered backend must not be called")

    def reauthenticate_and_redeem_stagec_runtime_activation_claim(
        self, **_kwargs: Any
    ) -> Any:
        self.calls += 1
        raise AssertionError("an unregistered backend must not be called")


@pytest.fixture(autouse=True)
def _isolated_private_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    with gate._PERMIT_LOCK:
        gate._PERMIT_RECORDS.clear()
        gate._BACKEND_CLAIMS.clear()
        gate._ENVELOPE_CLAIMS.clear()
        gate._LOGICAL_ROW_CLAIMS.clear()
        gate._ATTEMPT_SUBJECT_CLAIMS.clear()
        gate._AMBIGUOUS_TERMINALS.clear()
    monkeypatch.setattr(gate, "_REGISTERED_WORKER_TRUST_BACKEND_TYPES", ())
    monkeypatch.setattr(gate, "_WORKER_TRUST_BACKEND", gate._UNAVAILABLE_TRUST_BACKEND)
    yield
    with gate._PERMIT_LOCK:
        gate._PERMIT_RECORDS.clear()
        gate._BACKEND_CLAIMS.clear()
        gate._ENVELOPE_CLAIMS.clear()
        gate._LOGICAL_ROW_CLAIMS.clear()
        gate._ATTEMPT_SUBJECT_CLAIMS.clear()
        gate._AMBIGUOUS_TERMINALS.clear()


def _install_backend(
    monkeypatch: pytest.MonkeyPatch,
    backend: _TrustedTestBackend,
) -> None:
    monkeypatch.setattr(
        gate,
        "_REGISTERED_WORKER_TRUST_BACKEND_TYPES",
        (_TrustedTestBackend,),
    )
    monkeypatch.setattr(gate, "_WORKER_TRUST_BACKEND", backend)


def _assert_code(
    exc_info: pytest.ExceptionInfo[gate.StageCRuntimeActivationError],
    code: gate.StageCRuntimeActivationErrorCode,
) -> None:
    assert exc_info.value.code == code.value
    assert str(exc_info.value) == code.value


def test_default_backend_is_unavailable_before_any_external_side_effect() -> None:
    envelope = _envelope()
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=envelope,
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.BACKEND_UNAVAILABLE)
    assert gate._REGISTERED_WORKER_TRUST_BACKEND_TYPES == ()


def test_arbitrary_backend_is_rejected_without_method_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _ArbitrarySpyBackend()
    monkeypatch.setattr(gate, "_WORKER_TRUST_BACKEND", spy)
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(),
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.BACKEND_NOT_REGISTERED)
    assert spy.calls == 0


def test_no_caller_selected_backend_clock_or_trust_argument() -> None:
    parameters = inspect.signature(gate.acquire_stagec_model_call_permit).parameters
    assert tuple(parameters) == ("runtime_activation_envelope",)
    with pytest.raises(TypeError):
        gate.acquire_stagec_model_call_permit(  # type: ignore[call-arg]
            runtime_activation_envelope=_envelope(),
            backend=object(),
        )
    assert all("clock" not in name and "trust" not in name for name in parameters)


@pytest.mark.parametrize("as_mapping", [False, True])
def test_test_only_trusted_backend_happy_path_is_one_use_and_exact(
    monkeypatch: pytest.MonkeyPatch,
    as_mapping: bool,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    values = _envelope_kwargs()
    if not as_mapping:
        capture_ids = values["capture_artifact_ids"]
        values["capture_artifact_ids"] = tuple(
            capture_ids[name] for name in gate.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
        )
    envelope = gate.build_stagec_runtime_activation_envelope(**values)
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )

    assert type(permit) is gate.StageCModelCallPermit
    assert repr(permit) == "<StageCModelCallPermit opaque process-local capability>"
    gate.validate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )
    gate.validate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )
    assert backend.authenticate_calls == 1
    assert backend.terminalize_calls == 0
    record = gate._PERMIT_RECORDS[id(permit)]
    assert record.observation.claim_operation_id == gate._claim_operation_id(
        envelope,
        gate.replay_stagec_runtime_activation_envelope(envelope),
    )

    gate.redeem_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )
    assert backend.terminalize_calls == 1
    assert backend.terminal_states == ["CALL_STARTED"]
    assert backend.redemption_calls == 1
    assert backend.invalidation_calls == 0
    for operation in (
        gate.validate_stagec_model_call_permit,
        gate.redeem_stagec_model_call_permit,
        gate.invalidate_stagec_model_call_permit,
    ):
        with pytest.raises(gate.StageCRuntimeActivationError):
            operation(permit=permit, runtime_activation_envelope=envelope)
    assert backend.terminalize_calls == 1


@pytest.mark.parametrize(
    "disposition",
    [
        gate.StageCModelCallInvalidationDisposition.REJECTED,
        gate.StageCModelCallInvalidationDisposition.INDETERMINATE,
    ],
)
def test_pre_call_invalidation_is_durable_and_prevents_retry(
    monkeypatch: pytest.MonkeyPatch,
    disposition: gate.StageCModelCallInvalidationDisposition,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    gate.validate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )
    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
        disposition=disposition,
    )
    assert backend.terminal_states == [disposition.value]
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.PERMIT_INVALIDATED)
    assert backend.terminalize_calls == 1


def test_invalidation_disposition_is_closed_and_does_not_burn_on_bad_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.invalidate_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
            disposition="REJECTED",  # type: ignore[arg-type]
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.INVALID_INVALIDATION_DISPOSITION,
    )
    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )


_BINDING_DRIFTS: tuple[tuple[str, Any], ...] = (
    ("request.artifact_id", "stagec-request-drift"),
    ("request.sha256", _B),
    ("request.byte_length", 101),
    ("authorization.artifact_id", "stagec-authorization-drift"),
    ("authorization.sha256", _C),
    ("authorization.byte_length", 201),
    *tuple(
        (f"capture.{name}", f"stagec-{name.replace('_', '-')}-drift")
        for name in gate.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    ),
    ("tenant_id", "tenant-drift"),
    ("worker_id", "worker-drift"),
    ("lease_generation", 8),
    ("attempt_subject_sha256", _D),
    ("case_id", "stagec-case-drift"),
    ("case_execution_ordinal", 2),
    ("model_id", "Qwen/Qwen2.5-0.5B-Instruct-drift"),
    ("model_revision", "b" * 40),
    ("model_config_sha256", _E),
    ("weights_sha256", _F),
    ("tokenizer_json_sha256", _A),
    ("tokenizer_config_sha256", _B),
    ("chat_template_sha256", _C),
    ("capture_profile_sha256", _D),
    ("phase_activation_id", "stagec-phase-activation-drift"),
    ("ledger_generation", 12),
)


def _drifted_envelope(path: str, replacement: Any) -> gate.StageCRuntimeActivationEnvelope:
    values = _envelope_kwargs()
    if path.startswith("request."):
        values["request_artifact_identity"][path.split(".", 1)[1]] = replacement
    elif path.startswith("authorization."):
        values["authorization_projection_artifact_identity"][
            path.split(".", 1)[1]
        ] = replacement
    elif path.startswith("capture."):
        values["capture_artifact_ids"][path.split(".", 1)[1]] = replacement
    else:
        values[path] = replacement
    return gate.build_stagec_runtime_activation_envelope(**values)


@pytest.mark.parametrize(("path", "replacement"), _BINDING_DRIFTS)
def test_every_row_binding_drift_rejects_and_terminalizes_the_claim(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    replacement: Any,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    original = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=original,
    )
    drifted = _drifted_envelope(path, replacement)

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.validate_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=drifted,
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.PERMIT_BINDING_MISMATCH,
    )
    assert backend.terminal_states == [
        gate.StageCModelCallInvalidationDisposition.REJECTED.value
    ]
    with pytest.raises(gate.StageCRuntimeActivationError):
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=original,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("request_artifact_identity", {"media_type": "wrong"}),
        ("capture_artifact_ids", ("too-short",)),
        ("model_revision", "not-a-revision"),
        ("attempt_subject_sha256", "a" * 64),
        ("case_execution_ordinal", 0),
        ("case_execution_ordinal", 481),
        ("ledger_generation", True),
    ],
)
def test_illegal_binding_types_and_literals_fail_before_backend(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: Any,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    values = _envelope_kwargs()
    values[field] = replacement
    with pytest.raises(gate.StageCRuntimeActivationError):
        gate.build_stagec_runtime_activation_envelope(**values)
    assert backend.authenticate_calls == 0
    assert backend.terminalize_calls == 0


def test_forged_or_mutated_envelope_fails_before_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    object.__setattr__(envelope, "sha256", "0" * 64)
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=envelope,
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    assert backend.authenticate_calls == 0


def test_post_acquire_caller_envelope_rebinding_cannot_change_retained_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    caller_envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=caller_envelope,
    )
    original = gate.StageCRuntimeActivationEnvelope(
        raw_bytes=caller_envelope.raw_bytes,
        sha256=caller_envelope.sha256,
    )
    substituted = _envelope(case_execution_ordinal=2)
    object.__setattr__(caller_envelope, "raw_bytes", substituted.raw_bytes)
    object.__setattr__(caller_envelope, "sha256", substituted.sha256)

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=caller_envelope,
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.PERMIT_BINDING_MISMATCH,
    )
    assert backend.redemption_calls == 0
    assert backend.invalidation_calls == 1
    with pytest.raises(gate.StageCRuntimeActivationError) as second:
        gate.validate_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=original,
        )
    _assert_code(second, gate.StageCRuntimeActivationErrorCode.PERMIT_INVALIDATED)
    assert backend.authenticate_calls == 1


def test_backend_rejection_and_protocol_violation_mint_no_permit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rejecting = _TrustedTestBackend(fail_authenticate=True)
    _install_backend(monkeypatch, rejecting)
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(),
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.BACKEND_REJECTED)
    assert not gate._PERMIT_RECORDS
    assert rejecting.ambiguous_terminalize_calls == 1
    assert rejecting.ambiguous_reasons == [
        gate.StageCRuntimeActivationAmbiguityReason.AUTHENTICATE_EXCEPTION.value
    ]
    assert len(gate._AMBIGUOUS_TERMINALS) == 1

    class _BadProtocolBackend(_TrustedTestBackend):
        def authenticate_and_claim_stagec_runtime_activation(
            self,
            *,
            envelope: gate.StageCRuntimeActivationEnvelope,
            claim_operation_id: str,
        ) -> object:
            del claim_operation_id
            self.authenticate_calls += 1
            return object()

        def terminalize_ambiguous_stagec_runtime_activation_claim(
            self,
            **kwargs: Any,
        ) -> gate.StageCRuntimeActivationAmbiguousTerminalObservation:
            return _TrustedTestBackend.terminalize_ambiguous_stagec_runtime_activation_claim(
                self,
                **kwargs,
            )

    bad = _BadProtocolBackend()
    monkeypatch.setattr(
        gate,
        "_REGISTERED_WORKER_TRUST_BACKEND_TYPES",
        (_BadProtocolBackend,),
    )
    monkeypatch.setattr(gate, "_WORKER_TRUST_BACKEND", bad)
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(
                attempt_subject_sha256=_D,
                case_execution_ordinal=2,
            ),
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION,
    )
    assert not gate._PERMIT_RECORDS
    assert bad.ambiguous_terminalize_calls == 1
    assert bad.ambiguous_reasons == [
        gate.StageCRuntimeActivationAmbiguityReason.MALFORMED_LEDGER_OBSERVATION.value
    ]
    assert len(gate._AMBIGUOUS_TERMINALS) == 2


def test_backend_envelope_mutation_is_durably_tombstoned_from_control_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(mutate_authenticate_envelope=True)
    _install_backend(monkeypatch, backend)
    envelope = _envelope()

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=envelope,
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION,
    )
    assert not gate._PERMIT_RECORDS
    assert backend.ambiguous_terminalize_calls == 1
    assert backend.ambiguous_reasons == [
        gate.StageCRuntimeActivationAmbiguityReason.BACKEND_ENVELOPE_MUTATION.value
    ]
    receipt = next(iter(gate._AMBIGUOUS_TERMINALS.values()))
    assert receipt.envelope_sha256 == envelope.sha256
    assert receipt.logical_row_claim_sha256 == gate._logical_row_claim_sha256(
        gate.replay_stagec_runtime_activation_envelope(envelope)
    )
    assert receipt.ledger_generation == receipt.prior_ledger_generation + 1


def test_ambiguous_terminalization_failure_overrides_claim_error_and_forbids_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(
        fail_authenticate=True,
        fail_ambiguous_terminalize=True,
    )
    _install_backend(monkeypatch, backend)
    envelope = _envelope()

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=envelope,
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_AMBIGUOUS_TERMINALIZATION_FAILED,
    )
    assert backend.authenticate_calls == 1
    assert backend.ambiguous_terminalize_calls == 1
    assert not gate._PERMIT_RECORDS
    assert not gate._AMBIGUOUS_TERMINALS
    with pytest.raises(gate.StageCRuntimeActivationError) as retry:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        retry,
        gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM,
    )
    assert backend.authenticate_calls == 1


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("envelope_sha256", "0" * 64),
        ("logical_row_claim_sha256", "0" * 64),
        ("claim_operation_id", "0" * 64),
        ("ledger_generation", 11),
        (
            "ambiguity_reason",
            gate.StageCRuntimeActivationAmbiguityReason.MALFORMED_LEDGER_OBSERVATION.value,
        ),
        (
            "ambiguity_reason",
            gate.StageCRuntimeActivationAmbiguityReason.AUTHENTICATE_EXCEPTION,
        ),
        ("terminal_state", "CALL_STARTED"),
        (
            "terminal_state",
            gate.StageCModelCallInvalidationDisposition.INDETERMINATE,
        ),
        ("tombstoned_now", False),
        ("tombstoned_now", 1),
    ],
)
def test_bad_ambiguous_terminal_receipt_is_never_accepted(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: Any,
) -> None:
    backend = _TrustedTestBackend(
        fail_authenticate=True,
        ambiguous_terminal_mutation=(field, replacement),
    )
    _install_backend(monkeypatch, backend)

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(),
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_AMBIGUOUS_TERMINALIZATION_FAILED,
    )
    assert backend.ambiguous_terminalize_calls == 1
    assert not gate._PERMIT_RECORDS
    assert not gate._AMBIGUOUS_TERMINALS


def test_duplicate_backend_claim_never_returns_a_second_permit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(fixed_claim_id="duplicate-test-claim")
    _install_backend(monkeypatch, backend)
    first_envelope = _envelope()
    first = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=first_envelope,
    )
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(
                attempt_subject_sha256=_D,
                case_execution_ordinal=2,
            ),
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM,
    )
    assert len(gate._PERMIT_RECORDS) == 1
    assert backend.ambiguous_terminalize_calls == 1
    assert backend.ambiguous_reasons == [
        gate.StageCRuntimeActivationAmbiguityReason.DUPLICATE_RETURNED_CLAIM_ID.value
    ]
    gate.invalidate_stagec_model_call_permit(
        permit=first,
        runtime_activation_envelope=first_envelope,
    )


def test_same_exact_envelope_is_reserved_before_backend_and_never_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    first = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=gate.StageCRuntimeActivationEnvelope(
                raw_bytes=envelope.raw_bytes,
                sha256=envelope.sha256,
            ),
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM,
    )
    assert backend.authenticate_calls == 1
    assert len(gate._PERMIT_RECORDS) == 1
    gate.invalidate_stagec_model_call_permit(
        permit=first,
        runtime_activation_envelope=envelope,
    )


def test_variant_envelope_for_same_logical_row_is_rejected_before_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    original = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=original,
    )
    variant_ids = _capture_ids()
    variant_ids["target_vector"] = "stagec-target-vector-variant"
    variant = _envelope(capture_artifact_ids=variant_ids)
    assert variant.sha256 != original.sha256

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=variant,
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM,
    )
    assert backend.authenticate_calls == 1
    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=original,
    )


@pytest.mark.parametrize(
    "variant",
    [
        {"case_id": "stagec-case-drift"},
        {"case_execution_ordinal": 2},
        {"phase_activation_id": "stagec-phase-activation-drift"},
    ],
)
def test_same_attempt_subject_cannot_replay_under_drifted_row_pairing(
    monkeypatch: pytest.MonkeyPatch,
    variant: dict[str, Any],
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    original = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=original,
    )

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(**variant),
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM,
    )
    assert backend.authenticate_calls == 1
    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=original,
    )


def test_concurrent_same_envelope_acquisition_has_exactly_one_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    barrier = threading.Barrier(12)

    def attempt() -> tuple[str, gate.StageCModelCallPermit | None]:
        barrier.wait()
        try:
            permit = gate.acquire_stagec_model_call_permit(
                runtime_activation_envelope=envelope,
            )
        except gate.StageCRuntimeActivationError as exc:
            return exc.code, None
        return "SUCCESS", permit

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _index: attempt(), range(12)))

    assert sum(code == "SUCCESS" for code, _permit in results) == 1
    assert sum(
        code == gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM.value
        for code, _permit in results
    ) == 11
    assert backend.authenticate_calls == 1
    assert len(gate._PERMIT_RECORDS) == 1
    winner = next(permit for code, permit in results if code == "SUCCESS")
    assert winner is not None
    gate.invalidate_stagec_model_call_permit(
        permit=winner,
        runtime_activation_envelope=envelope,
    )


def test_concurrent_variant_envelopes_for_one_logical_row_have_one_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelopes: list[gate.StageCRuntimeActivationEnvelope] = []
    for index in range(12):
        artifact_ids = _capture_ids()
        artifact_ids["target_vector"] = f"stagec-target-vector-variant-{index}"
        envelopes.append(_envelope(capture_artifact_ids=artifact_ids))
    assert len({item.sha256 for item in envelopes}) == len(envelopes)
    barrier = threading.Barrier(len(envelopes))

    def attempt(
        envelope: gate.StageCRuntimeActivationEnvelope,
    ) -> tuple[str, gate.StageCModelCallPermit | None]:
        barrier.wait()
        try:
            permit = gate.acquire_stagec_model_call_permit(
                runtime_activation_envelope=envelope,
            )
        except gate.StageCRuntimeActivationError as exc:
            return exc.code, None
        return "SUCCESS", permit

    with ThreadPoolExecutor(max_workers=len(envelopes)) as pool:
        results = list(pool.map(attempt, envelopes))

    assert sum(code == "SUCCESS" for code, _permit in results) == 1
    assert sum(
        code == gate.StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM.value
        for code, _permit in results
    ) == len(envelopes) - 1
    assert backend.authenticate_calls == 1
    winner_index = next(
        index for index, (code, _permit) in enumerate(results) if code == "SUCCESS"
    )
    winner = results[winner_index][1]
    assert winner is not None
    gate.invalidate_stagec_model_call_permit(
        permit=winner,
        runtime_activation_envelope=envelopes[winner_index],
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("logical_row_claim_sha256", _A),
        ("claim_operation_id", _A),
        ("case_id", "stagec-case-drift"),
        ("case_execution_ordinal", 2),
        ("case_execution_ordinal", True),
        ("prior_claim_state", "ALREADY_CLAIMED"),
        ("claim_state", "UNCLAIMED"),
        ("claimed_now", False),
        ("claimed_now", 1),
        ("ledger_generation", True),
    ],
)
def test_claim_observation_requires_exact_newly_won_cas_evidence(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: Any,
) -> None:
    backend = _TrustedTestBackend(claim_mutation=(field, replacement))
    _install_backend(monkeypatch, backend)

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.acquire_stagec_model_call_permit(
            runtime_activation_envelope=_envelope(),
        )

    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION,
    )
    assert not gate._PERMIT_RECORDS
    assert backend.ambiguous_terminalize_calls == 1
    assert backend.ambiguous_reasons == [
        gate.StageCRuntimeActivationAmbiguityReason.MALFORMED_LEDGER_OBSERVATION.value
    ]


def test_backend_owned_observation_and_terminal_inputs_are_detached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(mutate_terminal_inputs=True)
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    returned = backend.last_claim_observation
    assert returned is not None
    record = gate._PERMIT_RECORDS[id(permit)]
    assert record.observation is not returned
    object.__setattr__(returned, "backend_claim_id", "post-return-mutation")
    object.__setattr__(returned, "claimed_now", False)

    gate.redeem_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )

    assert record.state == "CALL_STARTED"
    assert record.envelope.sha256 == envelope.sha256
    assert record.observation.backend_claim_id == "test-claim-1"
    assert record.observation.claimed_now is True
    assert record.observation_seal == gate._ledger_observation_values(
        record.observation
    )


def test_permit_constructor_subclass_copy_replace_and_serialization_are_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )

    with pytest.raises(TypeError):
        gate.StageCModelCallPermit()
    with pytest.raises(TypeError):
        exec("class ForgedPermit(gate.StageCModelCallPermit):\n    pass", {"gate": gate})
    with pytest.raises(TypeError):
        copy.copy(permit)
    with pytest.raises(TypeError):
        copy.deepcopy(permit)
    with pytest.raises(TypeError):
        replace(permit)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        pickle.dumps(permit)
    with pytest.raises(TypeError):
        json.dumps(permit)
    with pytest.raises(AttributeError):
        _ = permit._StageCModelCallPermit__nonce  # type: ignore[attr-defined]

    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )


def test_object_forgery_even_with_copied_hidden_slots_is_not_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    forged = object.__new__(gate.StageCModelCallPermit)
    object.__setattr__(
        forged,
        "_StageCModelCallPermit__nonce",
        object.__getattribute__(permit, "_StageCModelCallPermit__nonce"),
    )
    object.__setattr__(
        forged,
        "_StageCModelCallPermit__process_seal",
        object.__getattribute__(permit, "_StageCModelCallPermit__process_seal"),
    )
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.validate_stagec_model_call_permit(
            permit=forged,
            runtime_activation_envelope=envelope,
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    assert backend.terminalize_calls == 0
    gate.invalidate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )


def test_registered_permit_bypass_mutation_is_irreversibly_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    object.__setattr__(permit, "_StageCModelCallPermit__nonce", object())
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.validate_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(exc_info, gate.StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    with pytest.raises(gate.StageCRuntimeActivationError):
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )


def test_concurrent_redemption_has_exactly_one_winner_and_one_backend_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    barrier = threading.Barrier(12)

    def attempt() -> str:
        barrier.wait()
        try:
            gate.redeem_stagec_model_call_permit(
                permit=permit,
                runtime_activation_envelope=envelope,
            )
        except gate.StageCRuntimeActivationError as exc:
            return exc.code
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _index: attempt(), range(12)))
    assert results.count("SUCCESS") == 1
    assert results.count(
        gate.StageCRuntimeActivationErrorCode.PERMIT_ALREADY_REDEEMED.value
    ) == 11
    assert backend.terminalize_calls == 1


def test_backend_terminalization_failure_burns_locally_and_model_must_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(fail_terminalize=True)
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    model_calls = 0
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_REDEEM_REAUTHENTICATION_FAILED,
    )
    with pytest.raises(gate.StageCRuntimeActivationError) as second:
        gate.validate_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        second,
        gate.StageCRuntimeActivationErrorCode.PERMIT_TERMINALIZATION_INDETERMINATE,
    )
    assert backend.terminalize_calls == 1
    assert model_calls == 0


@pytest.mark.parametrize(
    ("trust_field", "drifted_value"),
    [
        ("trusted_time_in_window", False),
        ("storage_version", "object-version-stale"),
        ("storage_checksum", _B),
        ("retention_sufficient", False),
        ("worker_lease_active", False),
        ("authorization_revoked", True),
        ("ledger_generation", 12),
    ],
)
def test_redeem_freshly_reauthenticates_and_rejects_changed_trust_state(
    monkeypatch: pytest.MonkeyPatch,
    trust_field: str,
    drifted_value: Any,
) -> None:
    backend = _TrustedTestBackend()
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    gate.validate_stagec_model_call_permit(
        permit=permit,
        runtime_activation_envelope=envelope,
    )
    backend.current_trust[trust_field] = drifted_value
    model_calls = 0

    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_REDEEM_REAUTHENTICATION_FAILED,
    )
    assert backend.authenticate_calls == 1
    assert backend.redemption_calls == 1
    assert backend.terminalize_calls == 0
    assert model_calls == 0
    with pytest.raises(gate.StageCRuntimeActivationError) as second:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        second,
        gate.StageCRuntimeActivationErrorCode.PERMIT_TERMINALIZATION_INDETERMINATE,
    )


def test_wrong_terminal_ack_burns_locally_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _TrustedTestBackend(bad_terminal=True)
    _install_backend(monkeypatch, backend)
    envelope = _envelope()
    permit = gate.acquire_stagec_model_call_permit(
        runtime_activation_envelope=envelope,
    )
    with pytest.raises(gate.StageCRuntimeActivationError) as exc_info:
        gate.redeem_stagec_model_call_permit(
            permit=permit,
            runtime_activation_envelope=envelope,
        )
    _assert_code(
        exc_info,
        gate.StageCRuntimeActivationErrorCode.BACKEND_REDEEM_REAUTHENTICATION_FAILED,
    )
    assert backend.terminalize_calls == 1


def test_fixed_statuses_forbid_canary_and_never_promote_project_authority() -> None:
    payload = gate.replay_stagec_runtime_activation_envelope(_envelope())
    assert payload["scope"] == {
        "row_model_call_count": 1,
        "canary_count": 0,
        "pre_row_model_forward_count": 0,
        "corpus_access": "EXACT_BOUND_ROW_ONLY",
        "outcome_access_before_model_call": "FORBIDDEN",
    }
    assert payload["project_boundary"] == {
        "capability_status": "PROCESS_LOCAL_ONE_USE_MODEL_CALL_CHOKEPOINT_ONLY",
        "authority_boundary": (
            "NO_SCIENTIFIC_PRODUCT_EVIDENCE_PACKET_LICENSE_OR_DISCLOSURE_AUTHORITY"
        ),
        "gate5_status": "OPEN / KEEP_OPEN",
        "stagec_design_status": "DESIGN_ONLY",
        "stagec_authorization_status": "UNAUTHORIZED",
        "stagec_execution_status": "NOT_STARTED",
        "license_status": "NOT LICENSED",
        "governance_status": "HELD",
        "freeze_status": "NOT FROZEN",
    }
    assert not any("canary" in name.lower() for name in gate.__all__)
    source = inspect.getsource(gate)
    assert "import cas_harness_v2" not in source
    assert "from cas_harness_v2" not in source
