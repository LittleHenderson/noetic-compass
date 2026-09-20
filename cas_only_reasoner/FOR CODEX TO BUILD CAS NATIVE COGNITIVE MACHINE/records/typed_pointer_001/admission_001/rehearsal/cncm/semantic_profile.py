"""Frozen transitive source and policy identity for sourced memory0.4."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .canonical import digest
from .model import ContractError
from .nested_profile import SOURCE_FILES as NESTED_SOURCE_FILES

PROFILE_SCHEMA = "cncm.semantic-source-profile/0.4"
MAX_JOURNAL_BYTES = 48 * 1024 * 1024
MAX_JOURNAL_EVENTS = 1024
MAX_EPISODES = 16
SEMANTIC_AUTHORITIES = {
    "STORE_SOURCE": ("semantic_memory_controller", "store_anchored_source"),
    "RECALL_MEMORY": ("semantic_memory_controller", "recall_scoped_source"),
    "CHECK_MEMORY_RESOLUTION": ("semantic_memory_controller", "check_memory_resolution"),
}
SEMANTIC_WORK_COSTS = {"STORE_SOURCE": (12, 1), "RECALL_MEMORY": (12, 1),
                       "CHECK_MEMORY_RESOLUTION": (16, 1)}
SOURCE_FILES = NESTED_SOURCE_FILES + (
    "spec/CNCM_SEMANTIC_MEMORY_v0.4.md", "authority/semantic_memory_v0.4/manifest.json",
    "cncm/semantic_model.py", "cncm/semantic_verification.py", "cncm/semantic_profile.py",
    "cncm/semantic_kernel.py", "cncm/semantic_engine.py", "cncm/semantic_recovery.py",
    "schemas/semantic_v0_4/contracts.schema.json", "schemas/semantic_v0_4/problem.schema.json",
    "schemas/semantic_v0_4/state.schema.json", "schemas/semantic_v0_4/journal.schema.json",
    "schemas/semantic_v0_4/source_profile.schema.json", "schemas/semantic_v0_4/verifier_receipt.schema.json",
)


def authority_policy():
    return {"runtime_version": "0.4.0", "authorities": {k:list(v) for k,v in SEMANTIC_AUTHORITIES.items()},
        "work_allocations": {k:{"instructions":v[0],"checker_calls":v[1]} for k,v in SEMANTIC_WORK_COSTS.items()},
        "max_statements":256, "max_references":48, "max_semantic_records":1024,
        "max_journal_bytes":MAX_JOURNAL_BYTES,"max_journal_events":MAX_JOURNAL_EVENTS,"max_episodes":MAX_EPISODES,
        "trusted_ingress":"exact externally supplied statement digests with quiescent append-only host extensions",
        "ingress_recovery":"externally supplied initial set and ordered extension schedule",
        "source_statuses":["USER_ATTESTED","TEST_FIXTURE"],
        "factual_verification":False,"conditional_arithmetic_only":True,
        "source_head_key":["scope","key","source_id"],
        "source_mutation_window":"before first equation call",
        "independent_resolution_check":True,"failed_checks_charged":True,"allocation_refunds":False,
        "unreachable_equations":"retained in original problem; excluded from resolved problem",
        "external_actions":False,"constitutional_learning":False,"neural_learning":False}


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    source_files: tuple[tuple[str,int,str], ...]
    policy_digest: str

    def __post_init__(self):
        if type(self.source_files) is not tuple:
            raise ContractError("semantic source profile shape invalid")
        for row in self.source_files:
            if (type(row) is not tuple or len(row)!=3 or type(row[0]) is not str
                    or type(row[1]) is not int or row[1]<1 or type(row[2]) is not str
                    or len(row[2])!=64 or any(c not in "0123456789abcdef" for c in row[2])):
                raise ContractError("semantic source identity invalid")
        if tuple(row[0] for row in self.source_files)!=SOURCE_FILES or self.policy_digest!=digest(authority_policy()):
            raise ContractError("semantic source/policy mismatch")

    def to_dict(self):
        return {"schema_version":PROFILE_SCHEMA,"policy_digest":self.policy_digest,
            "source_files":[{"path":p,"bytes":size,"sha256":sha} for p,size,sha in self.source_files]}

    @property
    def profile_digest(self):
        return digest(self.to_dict())


def load_semantic_profile():
    root=Path(__file__).resolve().parents[1]
    identities=[]
    for name in SOURCE_FILES:
        raw=(root/name).read_bytes()
        identities.append((name,len(raw),sha256(raw).hexdigest()))
    return SemanticProfile(tuple(identities),digest(authority_policy()))
