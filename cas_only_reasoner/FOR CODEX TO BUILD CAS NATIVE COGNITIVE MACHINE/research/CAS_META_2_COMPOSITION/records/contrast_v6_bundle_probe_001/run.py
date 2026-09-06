"""Recorded pure export and fresh-process loading of the exposed unit fixture."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2.contrast_v6 import curriculum as c, data as d

CONFIG = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
                  validation_pairs_per_cell=2, test_triplets=3)
KW = {'seed': 926603, 'config': CONFIG, 'excluded': frozenset()}


def child(pin):
    opened = []
    def audit(event, args):
        if event == 'open' and isinstance(args[0], str):
            if Path(args[0]).name == 'test_private.json':
                raise RuntimeError('PRIVATE_TEST_READ_FORBIDDEN')
            opened.append(args[0])
    sys.addaudithook(audit)
    def no_parser(*args, **kwargs):
        raise RuntimeError('SYMBOLIC_TEST_ANSWER_PARSING_FORBIDDEN')
    c.parse_problem = no_parser
    c.generate = no_parser
    loaded = d.load_training_bundle(HERE/'trainer_input', expected_sha256=pin, **KW)
    print(json.dumps({'receipt': loaded['receipt'], 'opened_files': opened,
                      'private_read_attempts_permitted': False, 'symbolic_parser_permitted': False}))


def parent():
    if (HERE/'receipt.json').exists() or (HERE/'dataset').exists() or (HERE/'trainer_input').exists():
        raise ValueError('NEW_PROBE_REQUIRED')
    sources = {name: sha256((ROOT/name).read_bytes()).hexdigest() for name in
               ('cas_meta2/contrast_v6/curriculum.py', 'cas_meta2/contrast_v6/data.py')}
    c.write(HERE/'dataset', **KW)
    pin = sha256((HERE/'dataset/manifest.json').read_bytes()).hexdigest()
    prepared = d.prepare_training_bundle(HERE/'dataset', HERE/'trainer_input', expected_sha256=pin, **KW)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', pin]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
    for name, raw in (('stdout.txt', result.stdout), ('stderr.txt', result.stderr)):
        with (HERE/name).open('xb') as stream:
            stream.write(raw)
    after = {name: sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    receipt = {'completed': result.returncode == 0 and sources == after,
               'command': command, 'returncode': result.returncode,
               'source_sha256': sources, 'sources_unchanged': sources == after,
               'manifest_sha256': pin, 'parent': prepared,
               'stdout_sha256': sha256(result.stdout).hexdigest(),
               'stderr_sha256': sha256(result.stderr).hexdigest(),
               'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
               'fixture_seed': 926603, 'fresh_evaluation': False, 'training_performed': False,
               'boundary': 'Previously exposed unit fixture. Separate-process data loading only; no model or provider.'}
    with (HERE/'receipt.json').open('xb') as stream:
        stream.write(c.canonical(receipt)+b'\n')
    print(json.dumps({'completed': receipt['completed'], 'returncode': result.returncode,
                      'manifest_sha256': pin, 'training_performed': False}))
    if not receipt['completed']:
        raise RuntimeError('BUNDLE_PROBE_FAILED')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        child(sys.argv[2])
    else:
        parent()
