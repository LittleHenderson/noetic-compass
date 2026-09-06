"""Cold source/archive validation; model/provider imports remain blocked."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
source_sha = '9f562c761c7cb84c767673b2fab735cdd031b499'
archive_sha = '3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd'
output = HERE / 'cold_check_receipt.json'
if output.exists():
    raise RuntimeError('NEW_COLD_CHECK_RECEIPT_REQUIRED')
spec = importlib.util.spec_from_file_location('ablation_cold_launch', ROOT / 'aws/launch_ablation_v4.py')
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)
preimport_files = launch.verify_cli_source_before_helper_import(source_sha)
plan = json.loads(launch.PLAN_FILE.read_bytes())
launch.validate_approval('400.00', plan)
manifest = launch.validate_archive(HERE / 'source.zip', archive_sha, source_sha, plan)
identity = launch.verify_launcher_identity(manifest)
ledger = launch.budget.read_ledger()
record = {'schema': 'cas-meta2-ablation-cold-source-check/0.1', 'completed': True,
    'source_sha': source_sha, 'archive_sha256': archive_sha,
    'source_files_checked_against_git_and_disk': len(identity),
    'protected_baseline_files': manifest['protected_baseline_files'],
    'preimport_files': preimport_files, 'experiment': manifest['experiment'],
    'remaining_unreserved_usd': ledger['remaining_unreserved_usd'],
    'checker_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    'reservation_created': False, 'provider_calls': 0, 'neural_execution_performed': False}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps(record, sort_keys=True))
