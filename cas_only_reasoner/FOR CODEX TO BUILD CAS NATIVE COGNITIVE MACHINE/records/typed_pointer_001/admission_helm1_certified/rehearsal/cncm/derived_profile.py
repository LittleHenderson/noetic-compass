"""Source identity and conservative, nonrefundable 0.6 work allocations."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from .canonical import digest
from .compound_profile import SOURCE_FILES as OLD_SOURCE_FILES
from .derived_model import require

PROFILE_SCHEMA = 'cncm.derived-source-profile/0.6'
MAX_EPISODES = 16
MAX_JOURNAL_EVENTS = 2048
MAX_JOURNAL_BYTES = 96*1024*1024
DERIVED_AUTHORITIES = {
    'REGISTER_DEFINITION': ('derived_memory_controller', 'register_formal_definition'),
    'INSPECT_DERIVED': ('derived_memory_controller', 'inspect_formal_memory'),
    'PUSH_DERIVED': ('rpm_controller', 'suspend_for_formal_proof'),
    'GENERATE_DERIVED': ('derived_candidate_controller', 'propose_formal_candidate'),
    'CHECK_DERIVED': ('derived_verifier', 'check_formal_candidate'),
    'ADMIT_DERIVED': ('derived_memory_controller', 'admit_checked_formal_memory'),
    'RETURN_DERIVED': ('rpm_controller', 'resume_formal_parent'),
    'STORE_DERIVED': ('derived_memory_controller', 'store_committed_formal_result'),
    'FAIL_DERIVED': ('rpm_controller', 'record_formal_failure'),
}
DERIVED_WORK_COSTS = {
    'REGISTER_DEFINITION': (16, 1), 'INSPECT_DERIVED': (4096, 128),
    'GENERATE_DERIVED': (128, 5), 'CHECK_DERIVED': (256, 8),
    'ADMIT_DERIVED': (4096, 128), 'STORE_DERIVED': (20480, 640),
    'CHECK_DERIVED_INPUTS': (20480, 640),
}
SOURCE_FILES = OLD_SOURCE_FILES + (
    'spec/CNCM_DERIVED_MEMORY_v0.6.md', 'cncm/derived_model.py', 'cncm/derived_profile.py',
    'cncm/derived_verification.py', 'cncm/derived_kernel.py', 'cncm/derived_engine.py', 'cncm/derived_recovery.py',
    'schemas/derived_v0_6/contracts.schema.json', 'schemas/derived_v0_6/problem.schema.json',
    'schemas/derived_v0_6/state.schema.json', 'schemas/derived_v0_6/journal.schema.json',
    'schemas/derived_v0_6/source_profile.schema.json', 'schemas/derived_v0_6/verifier_receipt.schema.json',
)


def authority_policy():
    return {'runtime_version':'0.6.0', 'authorities':{k:list(v) for k,v in DERIVED_AUTHORITIES.items()},
        'work_allocations':{k:{'instructions':v[0], 'checker_calls':v[1]} for k,v in DERIVED_WORK_COSTS.items()},
        'allocation_semantics':'conservative policy units, not measured compute; failed work charged; no refunds',
        'max_support_nodes':16, 'max_support_depth':8, 'max_acquisition_depth':1,
        'memory_rational_bits':128, 'formal_parameters':'a*(b*x+c)+d=e',
        'derived_in_derived_acquisition':False, 'transitive_committed_result_support':True,
        'formal_checker':'protected check_math_step and verify_math_receipt', 'solver_regeneration_verifier':False,
        'freshness':'exact current definition and complete active scoped source sets',
        'source_authority':'external source and definition digest allowlist with ordered extensions',
        'max_episodes':MAX_EPISODES, 'max_journal_events':MAX_JOURNAL_EVENTS, 'max_journal_bytes':MAX_JOURNAL_BYTES,
        'unconditional_world_truth':False, 'external_authentication':False, 'neural_learning':False}


@dataclass(frozen=True, slots=True)
class DerivedProfile:
    source_files: tuple
    policy_digest: str

    def __post_init__(self):
        require(type(self.source_files) is tuple and tuple(r[0] for r in self.source_files) == SOURCE_FILES,
                'derived profile source list mismatch')
        for row in self.source_files:
            require(type(row) is tuple and len(row) == 3 and type(row[1]) is int and row[1] > 0
                    and type(row[2]) is str and len(row[2]) == 64 and all(c in '0123456789abcdef' for c in row[2]),
                    'derived source identity invalid')
        require(self.policy_digest == digest(authority_policy()), 'derived authority policy mismatch')

    def to_dict(self):
        return {'schema_version':PROFILE_SCHEMA, 'policy_digest':self.policy_digest,
                'source_files':[{'path':p, 'bytes':n, 'sha256':h} for p,n,h in self.source_files]}

    @property
    def profile_digest(self):
        return digest(self.to_dict())


def load_derived_profile():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for name in SOURCE_FILES:
        raw = (root/name).read_bytes()
        rows.append((name,len(raw),sha256(raw).hexdigest()))
    return DerivedProfile(tuple(rows), digest(authority_policy()))
