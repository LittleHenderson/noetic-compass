"""Load the bound pure replay engine and published schema, without any model."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from tools import inspect_ablation_packet_v5 as inspector
from tools import audit_ablation_stored_v4 as auditor

output = HERE / 'receipt.json'
if output.exists():
    raise RuntimeError('FRESH_PREFLIGHT_RECEIPT_REQUIRED')
source = '9f562c761c7cb84c767673b2fab735cdd031b499'
archive = ROOT / 'records/aws_ablation_v4_source_002/source.zip'
archive_sha = '3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd'
helper, manifest, _, _ = inspector.load_helpers(archive, source, archive_sha)
engine = auditor.load_engine(manifest, helper)
validator, schema = engine.protected_schema()
checked = auditor.check_source(manifest)
record = {'schema': 'cas-meta2-retrospective-replay-preflight/0.1', 'completed': True,
    'source_sha': source, 'archive_sha256': archive_sha, 'source_files_checked': len(checked),
    'published_schema': schema, 'neural_execution_performed': False, 'provider_calls': 0,
    'stored_outcome_audit_performed': False, 'learning_accepted': False,
    'auditor_sha256': sha256((ROOT / 'tools/audit_ablation_stored_v4.py').read_bytes()).hexdigest(),
    'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps(record))
