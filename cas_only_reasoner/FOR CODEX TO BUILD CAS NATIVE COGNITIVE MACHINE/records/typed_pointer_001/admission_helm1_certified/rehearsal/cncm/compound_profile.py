"""Transitive runtime identity and conservative work policy for construction0.5."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from .canonical import digest
from .model import ContractError
from .semantic_profile import SOURCE_FILES as SEMANTIC_SOURCE_FILES

PROFILE_SCHEMA='cncm.compound-source-profile/0.5'
MAX_JOURNAL_BYTES=64*1024*1024
MAX_JOURNAL_EVENTS=1024
MAX_EPISODES=16
COMPOUND_AUTHORITIES={
 'REQUEST_COMPOUND':('compound_controller','request_compound_call'),
 'PUSH_COMPOUND_ACQUISITION':('rpm_controller','suspend_for_compound'),
 'PUSH_PRIMITIVE_ACQUISITION':('rpm_controller','suspend_for_primitive'),
 'SELECT_PRIMITIVE':('procedure_controller','select_compound_primitive'),
 'INSTALL_PRIMITIVE':('procedure_controller','install_compound_primitive'),
 'RETURN_PRIMITIVE':('rpm_controller','resume_compound_construction'),
 'CONSTRUCT_COMPOUND':('compound_controller','construct_bounded_call_program'),
 'INSTALL_COMPOUND':('procedure_controller','install_checked_call_program'),
 'RETURN_COMPOUND':('rpm_controller','resume_compound_caller'),
 'APPLY_COMPOUND':('compound_controller','apply_checked_call_program'),
 'FAIL_COMPOUND':('rpm_controller','record_compound_failure'),
 'ROLLBACK_COMPOUND':('procedure_controller','rollback_call_program'),
 'ROLLBACK_PRIMITIVE':('procedure_controller','rollback_compound_primitive'),
}
COMPOUND_WORK_COSTS={
 'SELECT_PRIMITIVE':(144,24),'INSTALL_PRIMITIVE':(60,10),
 'CONSTRUCT_COMPOUND':(40320,1680),'INSTALL_COMPOUND':(288,12),'APPLY_COMPOUND':(24,1),
}
SOURCE_FILES=SEMANTIC_SOURCE_FILES+(
 'spec/CNCM_COMPOUND_CONSTRUCTION_v0.5.md','authority/compound_construction_v0.5/manifest.json',
 'cncm/compound_program.py','cncm/compound_verification.py','cncm/compound_model.py',
 'cncm/compound_profile.py','cncm/compound_kernel.py','cncm/compound_engine.py','cncm/compound_recovery.py',
 'schemas/compound_v0_5/contracts.schema.json','schemas/compound_v0_5/problem.schema.json',
 'schemas/compound_v0_5/state.schema.json','schemas/compound_v0_5/journal.schema.json',
 'schemas/compound_v0_5/source_profile.schema.json','schemas/compound_v0_5/verifier_receipt.schema.json',
)

def authority_policy():
 return {'runtime_version':'0.5.0','authorities':{k:list(v) for k,v in COMPOUND_AUTHORITIES.items()},
  'work_allocations':{k:{'instructions':v[0],'checker_calls':v[1]} for k,v in COMPOUND_WORK_COSTS.items()},
  'construction_prefix_allocation':{'instructions_per_candidate':96,'checker_calls_per_candidate':4},
  'candidate_grammar_size':420,'development_cases':4,'qualification_cases':12,
  'expression_family':'a*(b*x+c)+d=e','maximum_calls':2,'input_bits':128,'intermediate_bits':512,
  'primitive_capability':'cncm.solve-linear/0.1','compound_capability':'cncm.solve-nested-affine/0.1',
  'primitive_head_required_at_every_dispatch':True,'failed_checks_charged':True,'allocation_refunds':False,
  'max_journal_bytes':MAX_JOURNAL_BYTES,'max_journal_events':MAX_JOURNAL_EVENTS,'max_episodes':MAX_EPISODES,
  'source_custody':'external initial statement digests and quiescent ordered extensions',
  'conditional_arithmetic_only':True,'external_actions':False,'neural_learning':False,
  'fixture_custody':'disjoint public engineering panels, not secret held-out evaluation'}

@dataclass(frozen=True,slots=True)
class CompoundProfile:
 source_files:tuple[tuple[str,int,str],...]
 policy_digest:str
 def __post_init__(self):
  if type(self.source_files) is not tuple:raise ContractError('compound profile shape invalid')
  for row in self.source_files:
   if (type(row) is not tuple or len(row)!=3 or type(row[0]) is not str or type(row[1]) is not int
    or row[1]<1 or type(row[2]) is not str or len(row[2])!=64 or any(c not in '0123456789abcdef' for c in row[2])):
    raise ContractError('compound source identity invalid')
  if tuple(r[0] for r in self.source_files)!=SOURCE_FILES or self.policy_digest!=digest(authority_policy()):
   raise ContractError('compound source/policy mismatch')
 def to_dict(self):
  return {'schema_version':PROFILE_SCHEMA,'policy_digest':self.policy_digest,
   'source_files':[{'path':p,'bytes':n,'sha256':h} for p,n,h in self.source_files]}
 @property
 def profile_digest(self):return digest(self.to_dict())

def load_compound_profile():
 root=Path(__file__).resolve().parents[1]
 rows=[]
 for name in SOURCE_FILES:
  raw=(root/name).read_bytes();rows.append((name,len(raw),sha256(raw).hexdigest()))
 return CompoundProfile(tuple(rows),digest(authority_policy()))
