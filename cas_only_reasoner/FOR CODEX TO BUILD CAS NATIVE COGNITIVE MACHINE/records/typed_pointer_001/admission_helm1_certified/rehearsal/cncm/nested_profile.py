"""Pinned source and authority policy for native nested planning0.3."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .canonical import digest
from .model import ContractError
from .native_profile import SOURCE_FILES as BASE_SOURCE_FILES
from .procedural_qualification import policy_document

PROFILE_SCHEMA = "cncm.nested-source-profile/0.3"
MAX_JOURNAL_BYTES = 32 * 1024 * 1024
MAX_JOURNAL_EVENTS = 1024
MAX_EPISODES = 16
NESTED_WORK_COSTS = {
    "SELECT_PROCEDURE": (144,24), "INSTALL_PROCEDURE": (60,10),
    "BIND_EQUATION": (12,0), "APPLY_EQUATION": (18,2),
}
NESTED_AUTHORITIES = {
    "REQUEST_EQUATION": ("equation_controller","request_equation"),
    "DECOMPOSE_EQUATION": ("equation_controller","discover_dependencies"),
    "PUSH_DEPENDENCY": ("rpm_controller","suspend_for_dependency"),
    "RETURN_DEPENDENCY": ("rpm_controller","resume_checked_dependency"),
    "BIND_EQUATION": ("equation_controller","bind_checked_dependencies"),
    "PUSH_PROCEDURE": ("rpm_controller","suspend_for_nested_procedure"),
    "SELECT_PROCEDURE": ("procedure_controller","select_nested_candidate"),
    "INSTALL_PROCEDURE": ("procedure_controller","install_nested_procedure"),
    "RETURN_PROCEDURE": ("rpm_controller","resume_nested_procedure"),
    "APPLY_EQUATION": ("equation_controller","apply_checked_equation"),
    "FAIL_CALL": ("rpm_controller","record_nested_failure"),
    "ROLLBACK_PROCEDURE": ("procedure_controller","rollback_nested_procedure"),
}
SOURCE_FILES = BASE_SOURCE_FILES + (
    "spec/CNCM_NESTED_PLANNING_v0.3.md",
    "authority/nested_planning_v0.3/manifest.json",
    "cncm/nested_model.py","cncm/nested_verification.py","cncm/nested_profile.py",
    "cncm/nested_kernel.py","cncm/nested_engine.py","cncm/nested_recovery.py",
    "schemas/nested_v0_3/contracts.schema.json","schemas/nested_v0_3/problem.schema.json",
    "schemas/nested_v0_3/state.schema.json","schemas/nested_v0_3/proof.schema.json",
    "schemas/nested_v0_3/accepted_intent.schema.json","schemas/nested_v0_3/trace.schema.json",
    "schemas/nested_v0_3/journal.schema.json","schemas/nested_v0_3/evidence.schema.json",
    "schemas/nested_v0_3/source_profile.schema.json",
)
def authority_policy():
    return {"runtime_version":"0.3.0","capability":"cncm.solve-linear/0.1",
        "authorities":{key:list(pair) for key,pair in NESTED_AUTHORITIES.items()},
        "work_allocations":{key:{"instructions":pair[0],"checker_calls":pair[1]}
            for key,pair in NESTED_WORK_COSTS.items()},
        "qualification_policy":policy_document()["policy_sha256"],
        "max_equations":16,"max_terms":4,"max_frames":8,"max_json_integer_bits":512,
        "failed_checks_charged":True,"allocation_refunds":False,
        "native_batch_limit":1,"max_journal_bytes":MAX_JOURNAL_BYTES,
        "max_journal_events":MAX_JOURNAL_EVENTS,"max_episodes":MAX_EPISODES,
        "external_actions":False,"constitutional_learning":False,
        "neural_learning":False,"caller_supplied_execution_order":False}

@dataclass(frozen=True,slots=True)
class NestedProfile:
    source_files: tuple[tuple[str,int,str],...]
    policy_digest: str

    def __post_init__(self):
        if type(self.source_files) is not tuple:
            raise ContractError("nested profile shape invalid")
        for row in self.source_files:
            if (type(row) is not tuple or len(row)!=3 or type(row[0]) is not str
                or type(row[1]) is not int or row[1]<1 or type(row[2]) is not str
                or len(row[2])!=64 or any(c not in "0123456789abcdef" for c in row[2])):
                raise ContractError("nested source identity invalid")
        if (tuple(row[0] for row in self.source_files)!=SOURCE_FILES
            or type(self.policy_digest) is not str
            or self.policy_digest!=digest(authority_policy())):
            raise ContractError("nested profile source/policy mismatch")

    def to_dict(self):
        return {"schema_version":PROFILE_SCHEMA,"policy_digest":self.policy_digest,
            "source_files":[{"path":p,"bytes":size,"sha256":sha} for p,size,sha in self.source_files]}

    @property
    def profile_digest(self):
        return digest(self.to_dict())

def load_nested_profile():
    root=Path(__file__).resolve().parents[1]
    identities=[]
    for name in SOURCE_FILES:
        raw=(root/name).read_bytes()
        identities.append((name,len(raw),sha256(raw).hexdigest()))
    return NestedProfile(tuple(identities),digest(authority_policy()))
