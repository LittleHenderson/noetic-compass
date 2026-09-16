"""Host-side source pinning for the opt-in native procedure runtime.

Reading source files belongs to the trusted host boundary. The coordinator
receives this immutable profile and never reads files or accesses providers.
Profile digests establish identity, not authenticated ownership of a journal.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .canonical import digest
from .model import ContractError
from .procedural_qualification import policy_document

PROFILE_SCHEMA = "cncm.native-source-profile/0.2"
NATIVE_WORK_COSTS = {
    "SELECT_PROCEDURE": (144, 24),
    "INSTALL_PROCEDURE": (60, 10),
    "APPLY_PROCEDURE": (6, 1),
}
NATIVE_AUTHORITIES = {
    "REQUEST_PROCEDURE_CALL": ("procedure_controller", "request_typed_procedure_call"),
    "PUSH_ACQUISITION": ("rpm_controller", "suspend_for_procedure_acquisition"),
    "SELECT_PROCEDURE": ("procedure_controller", "select_finite_candidate"),
    "INSTALL_PROCEDURE": ("procedure_controller", "install_checked_procedure"),
    "RETURN_ACQUISITION": ("rpm_controller", "resume_exact_procedure_caller"),
    "APPLY_PROCEDURE": ("procedure_controller", "apply_checked_procedure"),
    "ROLLBACK_PROCEDURE": ("procedure_controller", "rollback_procedure_head"),
}
SOURCE_FILES = (
    "cas_reasoner.txt", "AUTHORITY_MANIFEST.yaml", "spec/CNCM_NATIVE_PROCEDURES_v0.2.md",
    "cncm/canonical.py", "cncm/model.py", "cncm/kernel.py", "cncm/engine.py",
    "cncm/semantics.py", "cncm/math_model.py", "cncm/math_parser.py",
    "cncm/math_normalize.py", "cncm/math_kernel.py", "cncm/procedural_substrate.py",
    "cncm/procedural_qualification.py", "cncm/native_model.py", "cncm/native_profile.py",
    "cncm/native_kernel.py", "cncm/native_engine.py", "cncm/native_recovery.py",
    "authority/native_procedures_v0.2/manifest.json",
    "schemas/native_v0_2/contracts.schema.json", "schemas/native_v0_2/problem.schema.json",
    "schemas/native_v0_2/state.schema.json", "schemas/native_v0_2/proof.schema.json",
    "schemas/native_v0_2/accepted_intent.schema.json", "schemas/native_v0_2/trace.schema.json",
    "schemas/native_v0_2/journal.schema.json", "schemas/native_v0_2/evidence.schema.json",
    "schemas/native_v0_2/source_profile.schema.json",
    "schemas/branch_frame.schema.json", "schemas/intent.schema.json",
    "schemas/machine_state.schema.json", "schemas/math_claim.schema.json",
    "schemas/problem_packet.schema.json", "schemas/procedure_substrate_artifact.schema.json",
    "schemas/procedure_substrate_execution.schema.json", "schemas/proof_step.schema.json",
    "schemas/proposition.schema.json", "schemas/rpm_frame.schema.json",
    "schemas/rule.schema.json", "schemas/trace_event.schema.json",
)
MAX_JOURNAL_BYTES = 32 * 1024 * 1024
MAX_JOURNAL_EVENTS = 1024
MAX_EPISODES = 8


def authority_policy():
    return {
        "runtime_version": "0.2.0",
        "capability": "cncm.solve-linear/0.1",
        "authorities": {key: list(value) for key, value in NATIVE_AUTHORITIES.items()},
        "work_allocations": {key: {"instructions": value[0], "checker_calls": value[1]}
                             for key, value in NATIVE_WORK_COSTS.items()},
        "qualification_policy": policy_document()["policy_sha256"],
        "failed_checks_charged": True, "allocation_refunds": False,
        "native_batch_limit": 1, "max_journal_bytes": MAX_JOURNAL_BYTES,
        "max_journal_events": MAX_JOURNAL_EVENTS, "max_episodes": MAX_EPISODES,
        "constitutional_learning": False, "external_actions": False,
        "neural_learning": False,
    }


@dataclass(frozen=True, slots=True)
class NativeProfile:
    source_files: tuple[tuple[str, int, str], ...]
    policy_digest: str

    def __post_init__(self):
        if type(self.source_files) is not tuple:
            raise ContractError("native profile shape/policy mismatch")
        for row in self.source_files:
            if (type(row) is not tuple or len(row) != 3 or type(row[1]) is not int
                    or row[1] < 1 or type(row[2]) is not str or len(row[2]) != 64
                    or any(c not in "0123456789abcdef" for c in row[2])):
                raise ContractError("native profile source identity is invalid")
        if (tuple(row[0] for row in self.source_files) != SOURCE_FILES
                or type(self.policy_digest) is not str
                or self.policy_digest != digest(authority_policy())):
            raise ContractError("native profile shape/policy mismatch")

    def to_dict(self):
        return {"schema_version": PROFILE_SCHEMA, "policy_digest": self.policy_digest,
                "source_files": [{"path": p, "bytes": size, "sha256": sha}
                                 for p, size, sha in self.source_files]}

    @property
    def profile_digest(self):
        return digest(self.to_dict())


def load_native_profile():
    """Read the current pinned source set at the host boundary, before execution."""
    root = Path(__file__).resolve().parents[1]
    identities = []
    for name in SOURCE_FILES:
        raw = (root / name).read_bytes()
        identities.append((name, len(raw), sha256(raw).hexdigest()))
    return NativeProfile(tuple(identities), digest(authority_policy()))
