"""Reconstruct the original dataset, never train or alter the frozen generator."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HB = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports, no_links
sys.meta_path.insert(0, NoNeuralOrProviderImports())


def digest(path):
    no_links(path)
    return sha256(path.read_bytes()).hexdigest()


def frozen_sources():
    path = ROOT / 'records/aws_learning_v3_source_001/source.receipt.json'
    if digest(path) != '82bf0c0f3b6f7e93f579356c854e95e65a4bb9eaa695d82e0aea9f8ecd3138a6':
        raise RuntimeError('SOURCE_RECEIPT_CHANGED')
    record = json.loads(path.read_bytes())
    expected = record['launch_manifest']['files_sha256']
    actual = {name: digest(HB / name) for name in expected}
    if actual != expected or len(actual) != 461:
        raise RuntimeError('FROZEN_SOURCE_CHANGED')
    return actual


def main():
    if '--child' in sys.argv:
        from cas_meta2.curriculum_v3 import write_dataset, registered_development_exclusions
        write_dataset(HERE / 'dataset', seed=20260919,
                      excluded_graph_signatures=registered_development_exclusions())
        return 0
    if (HERE / 'receipt.json').exists() or (HERE / 'dataset').exists():
        raise RuntimeError('NEW_RECONSTRUCTION_REQUIRED')
    no_links(HERE)
    started = time.monotonic()
    receipt = {'schema': 'cas-meta2-retrospective-dataset-reconstruction/0.1',
        'completed': False, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'neural_execution_performed': False, 'provider_calls': 0,
        'fresh_held_out_claim_permitted': False, 'errors': []}
    stdout, stderr = b'', b''
    try:
        before = frozen_sources()
        receipt['frozen_source_files_checked'] = len(before)
        archive = ROOT / 'records/decoder_ablation_inputs_v4_001/inputs.zip'
        if digest(archive) != 'bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93':
            raise RuntimeError('INPUT_ARCHIVE_CHANGED')
        with zipfile.ZipFile(archive) as bundle:
            original_raw = bundle.read('dataset/dataset_manifest.json')
        original = json.loads(original_raw)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child']
        receipt['command'] = command
        receipt['timeout_seconds'] = 600
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=600)
        stdout, stderr = process.stdout, process.stderr
        receipt['returncode'] = process.returncode
        if process.returncode != 0:
            raise RuntimeError('RECONSTRUCTION_CHILD_FAILED')
        expected = dict(original['sha256'])
        expected['dataset_manifest.json'] = sha256(original_raw).hexdigest()
        actual = {name: digest(HERE / 'dataset' / name) for name in expected}
        receipt['expected_sha256'] = expected
        receipt['actual_sha256'] = actual
        receipt['all_five_files_match'] = actual == expected
        if actual != expected:
            raise RuntimeError('RECONSTRUCTED_DATASET_BYTES_DIFFER')
        receipt['frozen_sources_unchanged'] = frozen_sources() == before
        receipt['counts'] = original['counts']
        receipt['dataset_id'] = original['dataset_id']
        receipt['completed'] = receipt['frozen_sources_unchanged']
    except BaseException as error:
        if isinstance(error, subprocess.TimeoutExpired):
            stdout, stderr = error.stdout or b'', error.stderr or b''
        receipt['errors'].append({'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc()})
    for name, raw in [('stdout.txt', stdout), ('stderr.txt', stderr)]:
        with (HERE / name).open('xb') as stream:
            stream.write(raw)
        receipt[name + '_sha256'] = sha256(raw).hexdigest()
    receipt['builder_sha256'] = digest(Path(__file__))
    receipt['wall_seconds'] = time.monotonic() - started
    receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
    with (HERE / 'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
