"""A real failed experiment must not enter stored-outcome acceptance."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from tools.audit_ablation_stored_v4 import audit

path = ROOT / 'records/aws_ablation_v5_failure_crosscheck_001/inspection_receipt.json'
before = sha256(path.read_bytes()).hexdigest()
output = HERE / 'must_not_be_created'
receipt_path = HERE / 'receipt.json'
if output.exists() or receipt_path.exists():
    raise RuntimeError('FRESH_CHECK_PATHS_REQUIRED')
try:
    audit(path, inspection_sha256=before,
        source_archive=ROOT / 'records/aws_ablation_v4_source_001/source.zip',
        source_sha256='e680545e231d7f9f7fca0dd4f84e3fe4988b3d7c129c83a0bfe313ea809fdbc2',
        source_sha='3da01c577c47978e595caaff1ebbe9b30c3a87b6',
        job='cas-meta2-20260906025939-e933c868',
        packet_sha256='53b5be708b4e12206f8f35357977fd020a34d8426db616eb09a068682c743642',
        output=output)
except ValueError as error:
    if str(error) != 'SUCCESSFUL_RETROSPECTIVE_INSPECTION_REQUIRED':
        raise
else:
    raise RuntimeError('FAILED_RUN_WAS_NOT_REFUSED')
if output.exists() or sha256(path.read_bytes()).hexdigest() != before:
    raise RuntimeError('FAILED_CHECK_WROTE_OR_CHANGED_INPUT')
record = {'status': 'FAILED_EXPERIMENT_REFUSED_FOR_STORED_AUDIT', 'completed': True,
    'inspection_receipt_sha256': before, 'stored_outcome_audit_performed': False,
    'neural_execution_performed': False, 'provider_calls': 0,
    'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    'auditor_sha256': sha256((ROOT / 'tools/audit_ablation_stored_v4.py').read_bytes()).hexdigest()}
with receipt_path.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps(record))
