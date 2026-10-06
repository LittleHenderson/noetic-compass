"""Structural assessment for isolated Ring-4 CAS Core v8 research.

Self-hashed receipts and action descriptors detect corruption; they do not
authenticate callers and they never grant authorization.  A structural pass is
available only after this process freshly replays the bound legacy source and
exact compiler bytes, then assesses a complete action descriptor against that
replayed compilation.

Every decision remains Ring 4 / OPEN / NOT LICENSED.  There is no claim-bearing,
external-side-effect, licensing, publication, or authorization path here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .compatibility import (
    CAS_V77_COMPILER_CANONICAL_LF_SHA256,
    CAS_V77_COMPILER_RAW_CRLF_SHA256,
    CAS_V77_COMPILER_SOURCE_ID,
    CAS_V77_SEMANTIC_PROFILE,
    CAS_V77_SYNTAX_PROFILE,
    PYTHON_ONLY_ENGINE_PROFILE,
    CompatibilityError,
    CompatibilityCompilation,
    replay_compatibility_compilation,
)
from .identity import (
    CanonicalizationError,
    canonical_json_bytes,
    canonical_json_sha256,
    require_ascii_identifier,
    require_canonical_text,
    require_sha256,
)
from .registry import RecordRegistry, RegistryError
from .semantics import ResearchBoundary, is_exact_ring4_open


COMPILER_RECEIPT_VERSION = "cas_core_v8.compiler_validation.v0.3"
ACTION_DESCRIPTOR_VERSION = "cas_core_v8.runtime_action_descriptor.v0.1"
COMPILATION_ASSESSMENT_VERSION = "cas_core_v8.compilation_assessment.v0.1"
RECEIPT_SELF_HASH_SCOPE = "CORRUPTION_DETECTION_ONLY_NOT_AUTHENTICATION"
NO_MODEL_IDENTITY_SHA256 = canonical_json_sha256(
    {
        "identity_kind": "NO_MODEL",
        "reason": "deterministic frozen compiler path contains no model invocation",
    }
)


def _runtime_text(value: Any, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    try:
        return require_canonical_text(value, field=field_name)
    except CanonicalizationError as exc:
        raise ValueError(str(exc)) from exc


def _runtime_sha(value: Any, *, field_name: str) -> str:
    try:
        return require_sha256(value, field=field_name)
    except CanonicalizationError as exc:
        raise ValueError(str(exc)) from exc


class RuntimeOperation(str, Enum):
    LEGACY_COMPATIBILITY_EVALUATION = "LEGACY_COMPATIBILITY_EVALUATION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    PUBLISH_CLAIM = "PUBLISH_CLAIM"


class RuntimeTarget(str, Enum):
    LOCAL_RING4_RESEARCH_ARTIFACT = "LOCAL_RING4_RESEARCH_ARTIFACT"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"
    PUBLIC_CLAIM_SURFACE = "PUBLIC_CLAIM_SURFACE"


class RuntimeEffectClass(str, Enum):
    PURE_LOCAL_COMPUTE = "PURE_LOCAL_COMPUTE"
    CLAIM_BEARING = "CLAIM_BEARING"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"


@dataclass(frozen=True, slots=True)
class RuntimeActionDescriptor:
    """Complete typed action identity; still an assertion, not authority."""

    descriptor_version: str
    operation: RuntimeOperation
    target: RuntimeTarget
    effect_class: RuntimeEffectClass
    source_sha256: str
    compilation_result_sha256: str
    model_identity_sha256: str
    environment_identity_sha256: str
    claim_id: str | None
    claim_version: str | None
    action_sha256: str
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not RuntimeActionDescriptor:
            raise ValueError("RuntimeActionDescriptor subclasses are not accepted")
        if self.descriptor_version != ACTION_DESCRIPTOR_VERSION:
            raise ValueError("unknown runtime action descriptor version")
        if type(self.operation) is not RuntimeOperation:
            raise ValueError("operation must be a RuntimeOperation")
        if type(self.target) is not RuntimeTarget:
            raise ValueError("target must be a RuntimeTarget")
        if type(self.effect_class) is not RuntimeEffectClass:
            raise ValueError("effect_class must be a RuntimeEffectClass")
        for field_name in (
            "source_sha256",
            "compilation_result_sha256",
            "model_identity_sha256",
            "environment_identity_sha256",
            "action_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _runtime_sha(getattr(self, field_name), field_name=field_name),
            )
        if (self.claim_id is None) != (self.claim_version is None):
            raise ValueError("claim_id and claim_version must be supplied together")
        for field_name in ("claim_id", "claim_version"):
            value = getattr(self, field_name)
            if value is not None:
                _runtime_text(value, field_name=field_name)
        if self.claim_id is not None:
            try:
                require_ascii_identifier(self.claim_id, field="claim_id")
            except CanonicalizationError as exc:
                raise ValueError(str(exc)) from exc
        if self.effect_class is RuntimeEffectClass.PURE_LOCAL_COMPUTE and self.claim_id is not None:
            raise ValueError("pure local compute cannot carry claim metadata")
        if self.effect_class is RuntimeEffectClass.CLAIM_BEARING and self.claim_id is None:
            raise ValueError("claim-bearing actions require exact claim metadata")
        if not is_exact_ring4_open(self.boundary):
            raise ValueError("actions must remain Ring 4 / OPEN / NOT LICENSED")
        if canonical_json_sha256(self.payload_without_digest()) != self.action_sha256:
            raise ValueError("runtime action descriptor digest mismatch")

    @classmethod
    def bind(
        cls,
        compilation: CompatibilityCompilation,
        *,
        operation: RuntimeOperation = RuntimeOperation.LEGACY_COMPATIBILITY_EVALUATION,
        target: RuntimeTarget = RuntimeTarget.LOCAL_RING4_RESEARCH_ARTIFACT,
        effect_class: RuntimeEffectClass = RuntimeEffectClass.PURE_LOCAL_COMPUTE,
        model_identity_sha256: str = NO_MODEL_IDENTITY_SHA256,
        claim_id: str | None = None,
        claim_version: str | None = None,
    ) -> "RuntimeActionDescriptor":
        if type(compilation) is not CompatibilityCompilation:
            raise TypeError("a CompatibilityCompilation is required")
        payload = {
            "descriptor_version": ACTION_DESCRIPTOR_VERSION,
            "operation": operation.value if type(operation) is RuntimeOperation else operation,
            "target": target.value if type(target) is RuntimeTarget else target,
            "effect_class": (
                effect_class.value
                if type(effect_class) is RuntimeEffectClass
                else effect_class
            ),
            "source_sha256": compilation.source_sha256,
            "compilation_result_sha256": compilation.legacy_artifact_sha256,
            "model_identity_sha256": model_identity_sha256,
            "environment_identity_sha256": compilation.execution_profile_sha256,
            "claim_id": claim_id,
            "claim_version": claim_version,
            "boundary": compilation.boundary.to_dict(),
        }
        return cls(
            descriptor_version=ACTION_DESCRIPTOR_VERSION,
            operation=operation,
            target=target,
            effect_class=effect_class,
            source_sha256=compilation.source_sha256,
            compilation_result_sha256=compilation.legacy_artifact_sha256,
            model_identity_sha256=model_identity_sha256,
            environment_identity_sha256=compilation.execution_profile_sha256,
            claim_id=claim_id,
            claim_version=claim_version,
            action_sha256=canonical_json_sha256(payload),
            boundary=compilation.boundary,
        )

    def payload_without_digest(self) -> dict[str, Any]:
        return {
            "descriptor_version": self.descriptor_version,
            "operation": self.operation.value,
            "target": self.target.value,
            "effect_class": self.effect_class.value,
            "source_sha256": self.source_sha256,
            "compilation_result_sha256": self.compilation_result_sha256,
            "model_identity_sha256": self.model_identity_sha256,
            "environment_identity_sha256": self.environment_identity_sha256,
            "claim_id": self.claim_id,
            "claim_version": self.claim_version,
            "boundary": self.boundary.to_dict(),
        }

    def verify_self_digest(self) -> bool:
        return canonical_json_sha256(self.payload_without_digest()) == self.action_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload_without_digest(), "action_sha256": self.action_sha256}


def _runtime_actions_match(left: Any, right: Any) -> bool:
    return (
        type(left) is RuntimeActionDescriptor
        and type(right) is RuntimeActionDescriptor
        and type(left.operation) is RuntimeOperation
        and type(right.operation) is RuntimeOperation
        and type(left.target) is RuntimeTarget
        and type(right.target) is RuntimeTarget
        and type(left.effect_class) is RuntimeEffectClass
        and type(right.effect_class) is RuntimeEffectClass
        and all(
            type(getattr(value, field_name)) is str
            for value in (left, right)
            for field_name in (
                "descriptor_version",
                "source_sha256",
                "compilation_result_sha256",
                "model_identity_sha256",
                "environment_identity_sha256",
                "action_sha256",
            )
        )
        and all(
            getattr(value, field_name) is None
            or type(getattr(value, field_name)) is str
            for value in (left, right)
            for field_name in ("claim_id", "claim_version")
        )
        and is_exact_ring4_open(left.boundary)
        and is_exact_ring4_open(right.boundary)
        and canonical_json_bytes(RuntimeActionDescriptor.to_dict(left))
        == canonical_json_bytes(RuntimeActionDescriptor.to_dict(right))
    )


@dataclass(frozen=True, slots=True)
class CompilerValidationReceipt:
    """Structural compilation receipt; never a bearer authorization token."""

    receipt_version: str
    valid: bool
    source_sha256: str
    compiler_raw_sha256: str
    compiler_canonical_lf_sha256: str
    compiler_source_id: str
    compilation_result_sha256: str
    execution_profile_sha256: str
    python_executable_sha256: str
    worker_sha256: str
    semantic_profile: str
    syntax_profile: str
    engine_profile: str
    runtime_profile: str
    isolated_mode: bool
    ignore_environment: bool
    fresh_process: bool
    parent_sys_modules_inherited: bool
    os_sandboxed: bool
    host_os_dependencies_content_addressed: bool
    legacy_only: bool
    self_hash_scope: str
    receipt_sha256: str
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not CompilerValidationReceipt:
            raise ValueError("CompilerValidationReceipt subclasses are not accepted")
        if self.receipt_version != COMPILER_RECEIPT_VERSION:
            raise ValueError("unknown compiler validation receipt version")
        for field_name in (
            "valid",
            "isolated_mode",
            "ignore_environment",
            "fresh_process",
            "parent_sys_modules_inherited",
            "os_sandboxed",
            "host_os_dependencies_content_addressed",
            "legacy_only",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be boolean")
        for field_name in (
            "source_sha256",
            "compiler_raw_sha256",
            "compiler_canonical_lf_sha256",
            "compilation_result_sha256",
            "execution_profile_sha256",
            "python_executable_sha256",
            "worker_sha256",
            "receipt_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _runtime_sha(getattr(self, field_name), field_name=field_name),
            )
        for field_name in (
            "compiler_source_id",
            "semantic_profile",
            "syntax_profile",
            "engine_profile",
            "runtime_profile",
            "self_hash_scope",
        ):
            _runtime_text(getattr(self, field_name), field_name=field_name)
        if not is_exact_ring4_open(self.boundary):
            raise ValueError("compiler receipts must remain Ring 4 / OPEN / NOT LICENSED")

    @classmethod
    def from_compatibility(
        cls, result: CompatibilityCompilation
    ) -> "CompilerValidationReceipt":
        if type(result) is not CompatibilityCompilation:
            raise TypeError("a CompatibilityCompilation is required")
        profile = result.execution_profile
        payload = {
            "receipt_version": COMPILER_RECEIPT_VERSION,
            "valid": result.legacy_artifact.get("valid") is True,
            "source_sha256": result.source_sha256,
            "compiler_raw_sha256": result.compiler_identity.raw_sha256,
            "compiler_canonical_lf_sha256": result.compiler_identity.canonical_lf_sha256,
            "compiler_source_id": result.compiler_source_id,
            "compilation_result_sha256": result.legacy_artifact_sha256,
            "execution_profile_sha256": result.execution_profile_sha256,
            "python_executable_sha256": profile.executable_identity.raw_sha256,
            "worker_sha256": profile.worker_identity.raw_sha256,
            "semantic_profile": CAS_V77_SEMANTIC_PROFILE,
            "syntax_profile": CAS_V77_SYNTAX_PROFILE,
            "engine_profile": result.engine_profile,
            "runtime_profile": profile.runtime_profile,
            "isolated_mode": profile.isolated_mode,
            "ignore_environment": profile.ignore_environment,
            "fresh_process": profile.fresh_process,
            "parent_sys_modules_inherited": profile.parent_sys_modules_inherited,
            "os_sandboxed": profile.os_sandboxed,
            "host_os_dependencies_content_addressed": (
                profile.host_os_dependencies_content_addressed
            ),
            "legacy_only": True,
            "self_hash_scope": RECEIPT_SELF_HASH_SCOPE,
            "boundary": result.boundary.to_dict(),
        }
        return cls(
            receipt_sha256=canonical_json_sha256(payload),
            boundary=result.boundary,
            **{key: value for key, value in payload.items() if key != "boundary"},
        )

    @property
    def dependency_closure_sha256(self) -> str:
        """Compatibility alias; this now names the complete execution profile."""

        return self.execution_profile_sha256

    def payload_without_digest(self) -> dict[str, Any]:
        return {
            "receipt_version": self.receipt_version,
            "valid": self.valid,
            "source_sha256": self.source_sha256,
            "compiler_raw_sha256": self.compiler_raw_sha256,
            "compiler_canonical_lf_sha256": self.compiler_canonical_lf_sha256,
            "compiler_source_id": self.compiler_source_id,
            "compilation_result_sha256": self.compilation_result_sha256,
            "execution_profile_sha256": self.execution_profile_sha256,
            "python_executable_sha256": self.python_executable_sha256,
            "worker_sha256": self.worker_sha256,
            "semantic_profile": self.semantic_profile,
            "syntax_profile": self.syntax_profile,
            "engine_profile": self.engine_profile,
            "runtime_profile": self.runtime_profile,
            "isolated_mode": self.isolated_mode,
            "ignore_environment": self.ignore_environment,
            "fresh_process": self.fresh_process,
            "parent_sys_modules_inherited": self.parent_sys_modules_inherited,
            "os_sandboxed": self.os_sandboxed,
            "host_os_dependencies_content_addressed": (
                self.host_os_dependencies_content_addressed
            ),
            "legacy_only": self.legacy_only,
            "self_hash_scope": self.self_hash_scope,
            "boundary": self.boundary.to_dict(),
        }

    def verify_self_digest(self) -> bool:
        """Detect corruption only; a matching digest is not authentication."""

        return canonical_json_sha256(self.payload_without_digest()) == self.receipt_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload_without_digest(), "receipt_sha256": self.receipt_sha256}


def _compiler_receipts_match(left: Any, right: Any) -> bool:
    return (
        type(left) is CompilerValidationReceipt
        and type(right) is CompilerValidationReceipt
        and all(
            type(getattr(value, field_name)) is bool
            for value in (left, right)
            for field_name in (
                "valid",
                "isolated_mode",
                "ignore_environment",
                "fresh_process",
                "parent_sys_modules_inherited",
                "os_sandboxed",
                "host_os_dependencies_content_addressed",
                "legacy_only",
            )
        )
        and all(
            type(getattr(value, field_name)) is str
            for value in (left, right)
            for field_name in (
                "receipt_version",
                "source_sha256",
                "compiler_raw_sha256",
                "compiler_canonical_lf_sha256",
                "compiler_source_id",
                "compilation_result_sha256",
                "execution_profile_sha256",
                "python_executable_sha256",
                "worker_sha256",
                "semantic_profile",
                "syntax_profile",
                "engine_profile",
                "runtime_profile",
                "self_hash_scope",
                "receipt_sha256",
            )
        )
        and is_exact_ring4_open(left.boundary)
        and is_exact_ring4_open(right.boundary)
        and canonical_json_bytes(CompilerValidationReceipt.to_dict(left))
        == canonical_json_bytes(CompilerValidationReceipt.to_dict(right))
    )


def _assessment_findings(
    receipt: CompilerValidationReceipt, action: RuntimeActionDescriptor
) -> tuple[str, ...]:
    codes: list[str] = []
    if not CompilerValidationReceipt.verify_self_digest(receipt):
        codes.append("DENY_CORRUPT_COMPILER_VALIDATION")
    if not receipt.valid:
        codes.append("DENY_COMPILER_RESULT_INVALID")
    if receipt.compiler_raw_sha256 not in (
        CAS_V77_COMPILER_RAW_CRLF_SHA256,
        CAS_V77_COMPILER_CANONICAL_LF_SHA256,
    ):
        codes.append("DENY_UNKNOWN_COMPILER_RAW_IDENTITY")
    if receipt.compiler_canonical_lf_sha256 != CAS_V77_COMPILER_CANONICAL_LF_SHA256:
        codes.append("DENY_UNKNOWN_COMPILER_CONTENT_IDENTITY")
    if receipt.compiler_source_id != CAS_V77_COMPILER_SOURCE_ID:
        codes.append("DENY_UNKNOWN_COMPILER_SOURCE_AUTHORITY")
    if receipt.semantic_profile != CAS_V77_SEMANTIC_PROFILE:
        codes.append("DENY_UNKNOWN_SEMANTIC_PROFILE")
    if receipt.syntax_profile != CAS_V77_SYNTAX_PROFILE:
        codes.append("DENY_UNKNOWN_SYNTAX_PROFILE")
    if receipt.engine_profile != PYTHON_ONLY_ENGINE_PROFILE:
        codes.append("DENY_NON_PYTHON_ENGINE_PROFILE")
    if (
        not receipt.isolated_mode
        or not receipt.ignore_environment
        or not receipt.fresh_process
        or receipt.parent_sys_modules_inherited
    ):
        codes.append("DENY_NONISOLATED_PYTHON_PROCESS")
    if receipt.os_sandboxed or receipt.host_os_dependencies_content_addressed:
        codes.append("DENY_FALSE_OS_ISOLATION_CLAIM")
    if not receipt.legacy_only:
        codes.append("DENY_NONLEGACY_RECEIPT")
    if receipt.self_hash_scope != RECEIPT_SELF_HASH_SCOPE:
        codes.append("DENY_MISSTATED_RECEIPT_INTEGRITY_SCOPE")
    if not RuntimeActionDescriptor.verify_self_digest(action):
        codes.append("DENY_CORRUPT_ACTION_DESCRIPTOR")
    if action.source_sha256 != receipt.source_sha256:
        codes.append("DENY_ACTION_SOURCE_MISMATCH")
    if action.compilation_result_sha256 != receipt.compilation_result_sha256:
        codes.append("DENY_ACTION_RESULT_MISMATCH")
    if action.environment_identity_sha256 != receipt.execution_profile_sha256:
        codes.append("DENY_ACTION_ENVIRONMENT_MISMATCH")
    if action.model_identity_sha256 != NO_MODEL_IDENTITY_SHA256:
        codes.append("DENY_UNBOUND_OR_UNEXPECTED_MODEL_IDENTITY")
    if action.operation is not RuntimeOperation.LEGACY_COMPATIBILITY_EVALUATION:
        codes.append("DENY_UNSUPPORTED_RUNTIME_OPERATION")
    if action.target is not RuntimeTarget.LOCAL_RING4_RESEARCH_ARTIFACT:
        codes.append("DENY_UNSUPPORTED_RUNTIME_TARGET")
    if action.effect_class is RuntimeEffectClass.CLAIM_BEARING:
        codes.append("DENY_CLAIM_BEARING_ACTION_NOT_AUTHORIZED")
    elif action.effect_class is RuntimeEffectClass.EXTERNAL_SIDE_EFFECT:
        codes.append("DENY_EXTERNAL_SIDE_EFFECT_NOT_AUTHORIZED")
    elif action.effect_class is not RuntimeEffectClass.PURE_LOCAL_COMPUTE:
        codes.append("DENY_UNKNOWN_EFFECT_CLASS")
    return tuple(dict.fromkeys(codes))


def _expected_assessment_codes(
    receipt: CompilerValidationReceipt, action: RuntimeActionDescriptor
) -> tuple[bool, tuple[str, ...]]:
    denials = _assessment_findings(receipt, action)
    if denials:
        return False, denials
    return True, (
        "STRUCTURAL_PASS_RING4_PURE_LOCAL_COMPUTE",
        "LIMITATION_NO_OS_SANDBOX",
        "LIMITATION_HOST_OS_DEPENDENCIES_NOT_CONTENT_ADDRESSED",
    )


@dataclass(frozen=True, slots=True)
class CompilationAssessment:
    """Replay-backed structural comparison, never authorization."""

    assessment_version: str
    structurally_admissible: bool
    assessment_codes: tuple[str, ...]
    receipt: CompilerValidationReceipt
    action: RuntimeActionDescriptor
    compilation: CompatibilityCompilation = field(repr=False)
    compilation_evidence_sha256: str
    assessment_sha256: str
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not CompilationAssessment:
            raise ValueError("CompilationAssessment subclasses are not accepted")
        if self.assessment_version != COMPILATION_ASSESSMENT_VERSION:
            raise ValueError("unknown compilation assessment version")
        if type(self.structurally_admissible) is not bool:
            raise ValueError("structurally_admissible must be boolean")
        if type(self.assessment_codes) is not tuple or not self.assessment_codes:
            raise ValueError("assessment_codes must be a nonempty tuple")
        for code in self.assessment_codes:
            _runtime_text(code, field_name="assessment code")
        if type(self.receipt) is not CompilerValidationReceipt:
            raise ValueError("assessment requires a typed compiler receipt")
        if type(self.action) is not RuntimeActionDescriptor:
            raise ValueError("assessment requires a typed action descriptor")
        if type(self.compilation) is not CompatibilityCompilation:
            raise ValueError("assessment requires a bound CompatibilityCompilation")
        object.__setattr__(
            self,
            "compilation_evidence_sha256",
            _runtime_sha(
                self.compilation_evidence_sha256,
                field_name="compilation_evidence_sha256",
            ),
        )
        object.__setattr__(
            self,
            "assessment_sha256",
            _runtime_sha(self.assessment_sha256, field_name="assessment_sha256"),
        )
        if not is_exact_ring4_open(self.boundary):
            raise ValueError("assessments must remain Ring 4 / OPEN / NOT LICENSED")
        if not self.verify_self_digest():
            raise ValueError("compilation assessment digest mismatch")

    def payload_without_digest(self) -> dict[str, Any]:
        return {
            "assessment_version": self.assessment_version,
            "structurally_admissible": self.structurally_admissible,
            "assessment_codes": list(self.assessment_codes),
            "receipt": self.receipt.to_dict(),
            "action": self.action.to_dict(),
            "compilation_evidence_sha256": self.compilation_evidence_sha256,
            "boundary": self.boundary.to_dict(),
        }

    def verify_self_digest(self) -> bool:
        return canonical_json_sha256(self.payload_without_digest()) == self.assessment_sha256

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.payload_without_digest(),
            "assessment_sha256": self.assessment_sha256,
        }


def assess_compilation_for_action(
    compilation: CompatibilityCompilation,
    action: RuntimeActionDescriptor,
) -> CompilationAssessment:
    """Freshly replay the exact compilation before calculating structure."""

    if type(compilation) is not CompatibilityCompilation:
        raise TypeError("a CompatibilityCompilation is required")
    if type(action) is not RuntimeActionDescriptor:
        raise TypeError("a RuntimeActionDescriptor is required")
    replay = replay_compatibility_compilation(compilation)
    receipt = CompilerValidationReceipt.from_compatibility(replay)
    structurally_admissible, codes = _expected_assessment_codes(receipt, action)
    compilation_evidence_sha256 = canonical_json_sha256(
        CompatibilityCompilation.to_dict(replay)
    )
    payload = {
        "assessment_version": COMPILATION_ASSESSMENT_VERSION,
        "structurally_admissible": structurally_admissible,
        "assessment_codes": list(codes),
        "receipt": receipt.to_dict(),
        "action": action.to_dict(),
        "compilation_evidence_sha256": compilation_evidence_sha256,
        "boundary": replay.boundary.to_dict(),
    }
    assessment = CompilationAssessment(
        assessment_version=COMPILATION_ASSESSMENT_VERSION,
        structurally_admissible=structurally_admissible,
        assessment_codes=codes,
        receipt=receipt,
        action=action,
        compilation=replay,
        compilation_evidence_sha256=compilation_evidence_sha256,
        assessment_sha256=canonical_json_sha256(payload),
        boundary=replay.boundary,
    )
    return assessment


@dataclass(frozen=True, slots=True)
class GateDecision:
    structurally_admissible: bool
    authorization_granted: bool
    codes: tuple[str, ...]
    action_sha256: str | None
    validation_receipt_sha256: str | None
    compilation_assessment_sha256: str | None
    registry_raw_sha256: str | None
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not GateDecision:
            raise ValueError("GateDecision subclasses are not accepted")
        if type(self.structurally_admissible) is not bool:
            raise ValueError("structurally_admissible must be boolean")
        if self.authorization_granted is not False:
            raise ValueError("CAS Core v8 structural gate cannot grant authorization")
        if type(self.codes) is not tuple or not self.codes:
            raise ValueError("decision codes must be a nonempty tuple")
        has_denial = any(code.startswith("DENY_") for code in self.codes)
        if self.structurally_admissible and has_denial:
            raise ValueError("a structural pass cannot carry denial codes")
        if self.structurally_admissible and not any(
            code.startswith("STRUCTURAL_PASS_") for code in self.codes
        ):
            raise ValueError("a structural pass needs an explicit structural code")
        if not self.structurally_admissible and not has_denial:
            raise ValueError("a structural failure needs an explicit denial code")
        if any(code.startswith("ALLOW") for code in self.codes):
            raise ValueError("authorization-style ALLOW codes are forbidden")
        for field_name in (
            "action_sha256",
            "validation_receipt_sha256",
            "compilation_assessment_sha256",
            "registry_raw_sha256",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, _runtime_sha(value, field_name=field_name)
                )
        if not is_exact_ring4_open(self.boundary):
            raise ValueError("gate decisions must remain Ring 4 / OPEN / NOT LICENSED")

    @property
    def allowed(self) -> bool:
        """Backward-compatible spelling that is intentionally always false."""

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "structurally_admissible": self.structurally_admissible,
            "authorization_granted": self.authorization_granted,
            "codes": list(self.codes),
            "action_sha256": self.action_sha256,
            "validation_receipt_sha256": self.validation_receipt_sha256,
            "compilation_assessment_sha256": self.compilation_assessment_sha256,
            "registry_raw_sha256": self.registry_raw_sha256,
            "boundary": self.boundary.to_dict(),
        }


def evaluate_runtime_gate(
    evidence: CompilationAssessment | CompilerValidationReceipt | None,
    action: RuntimeActionDescriptor | None = None,
    *,
    claim_registry: RecordRegistry | None = None,
) -> GateDecision:
    """Evaluate structural evidence while categorically withholding authority."""

    selected_action: RuntimeActionDescriptor | None = None
    receipt_sha256: str | None = None
    assessment_sha256: str | None = None
    codes: tuple[str, ...]
    structurally_admissible = False

    if type(evidence) is CompilationAssessment:
        selected_action = (
            evidence.action
            if type(evidence.action) is RuntimeActionDescriptor
            else None
        )
        receipt_sha256 = (
            evidence.receipt.receipt_sha256
            if type(evidence.receipt) is CompilerValidationReceipt
            else None
        )
        assessment_sha256 = evidence.assessment_sha256
        if not (
            type(evidence.receipt) is CompilerValidationReceipt
            and type(evidence.action) is RuntimeActionDescriptor
            and type(evidence.compilation) is CompatibilityCompilation
            and type(evidence.assessment_version) is str
            and type(evidence.structurally_admissible) is bool
            and type(evidence.assessment_codes) is tuple
            and all(type(code) is str for code in evidence.assessment_codes)
            and type(evidence.compilation_evidence_sha256) is str
            and type(evidence.assessment_sha256) is str
            and is_exact_ring4_open(evidence.boundary)
            and _compiler_receipts_match(evidence.receipt, evidence.receipt)
            and _runtime_actions_match(evidence.action, evidence.action)
        ):
            codes = ("DENY_ASSESSMENT_TYPE_MISMATCH",)
        elif not CompilationAssessment.verify_self_digest(evidence):
            codes = ("DENY_CORRUPT_COMPILATION_ASSESSMENT",)
        elif action is not None and not _runtime_actions_match(action, evidence.action):
            codes = ("DENY_ACTION_ASSESSMENT_MISMATCH",)
        else:
            try:
                replay = replay_compatibility_compilation(evidence.compilation)
                replay_receipt = CompilerValidationReceipt.from_compatibility(replay)
                replay_evidence_sha256 = canonical_json_sha256(
                    CompatibilityCompilation.to_dict(replay)
                )
            except (CompatibilityError, OSError, TypeError, ValueError):
                codes = ("DENY_COMPILATION_REPLAY_FAILED",)
            else:
                expected_state, expected_codes = _expected_assessment_codes(
                    replay_receipt, evidence.action
                )
                if not _compiler_receipts_match(evidence.receipt, replay_receipt):
                    codes = ("DENY_RECEIPT_REPLAY_MISMATCH",)
                elif evidence.compilation_evidence_sha256 != replay_evidence_sha256:
                    codes = ("DENY_COMPILATION_EVIDENCE_MISMATCH",)
                elif (
                    type(evidence.structurally_admissible) is not bool
                    or evidence.structurally_admissible != expected_state
                    or type(evidence.assessment_codes) is not tuple
                    or evidence.assessment_codes != expected_codes
                ):
                    codes = ("DENY_ASSESSMENT_STATE_MISMATCH",)
                else:
                    structurally_admissible = expected_state
                    codes = expected_codes
    elif type(evidence) is CompilerValidationReceipt:
        receipt_sha256 = evidence.receipt_sha256
        selected_action = action if type(action) is RuntimeActionDescriptor else None
        receipt_codes = ["DENY_STRUCTURAL_RECEIPT_NOT_AUTHORIZATION"]
        if not CompilerValidationReceipt.verify_self_digest(evidence):
            receipt_codes.append("DENY_CORRUPT_COMPILER_VALIDATION")
        codes = tuple(receipt_codes)
    elif evidence is None:
        selected_action = action if type(action) is RuntimeActionDescriptor else None
        codes = ("DENY_MISSING_COMPILATION_ASSESSMENT",)
    else:
        selected_action = action if type(action) is RuntimeActionDescriptor else None
        codes = ("DENY_UNKNOWN_STRUCTURAL_EVIDENCE",)

    if action is not None and type(action) is not RuntimeActionDescriptor:
        codes = tuple(dict.fromkeys((*codes, "DENY_UNKNOWN_ACTION_DESCRIPTOR")))
        structurally_admissible = False
    registry_verified = False
    if claim_registry is not None:
        if type(claim_registry) is not RecordRegistry:
            codes = tuple(dict.fromkeys((*codes, "DENY_UNKNOWN_CLAIM_REGISTRY")))
            structurally_admissible = False
        else:
            try:
                RecordRegistry.verify_raw_bindings(claim_registry)
            except RegistryError:
                codes = tuple(
                    dict.fromkeys((*codes, "DENY_CLAIM_REGISTRY_RAW_BINDING"))
                )
                structurally_admissible = False
            else:
                registry_verified = True

    codes = tuple(
        dict.fromkeys((*codes, "AUTHORIZATION_NOT_GRANTED_RING4_RESEARCH"))
    )
    return GateDecision(
        structurally_admissible=structurally_admissible,
        authorization_granted=False,
        codes=codes,
        action_sha256=(selected_action.action_sha256 if selected_action is not None else None),
        validation_receipt_sha256=receipt_sha256,
        compilation_assessment_sha256=assessment_sha256,
        registry_raw_sha256=(
            claim_registry.identity.raw_sha256
            if registry_verified
            else None
        ),
        boundary=ResearchBoundary.ring4_open(),
    )
