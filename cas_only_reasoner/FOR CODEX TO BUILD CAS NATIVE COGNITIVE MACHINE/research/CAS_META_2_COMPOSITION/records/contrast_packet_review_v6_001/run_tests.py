"""Receipt a local synthetic checker test run; no GPU or provider operations."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT/'records/aws_contrast_v6_source_001'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_bytes():
    with zipfile.ZipFile(SOURCE) as archive:
        manifest = json.loads(archive.read('launch_manifest.json'))
    for name, checksum in manifest['files_sha256'].items():
        if digest(ROOT.parents[1]/name) != checksum:
            raise ValueError('FROZEN_SOURCE_CHANGED:'+name)
    return {'source_sha': manifest['source_sha'], 'source_archive_sha256': digest(SOURCE),
            'files_verified': len(manifest['files_sha256']), 'protected_baseline_files': manifest['protected_baseline_files']}


class CountedResult(unittest.TextTestResult):
    subtests = 0

    def addSubTest(self, test, subtest, err):
        self.subtests += 1
        super().addSubTest(test, subtest, err)


if __name__ == '__main__':
    receipt_path, stdout_path = HERE/'pure_test_receipt.json', HERE/'pure_test_output.txt'
    if receipt_path.exists() or stdout_path.exists():
        raise ValueError('NEW_TEST_RECEIPT_REQUIRED')
    before = source_bytes()
    started = time.monotonic()
    spec = importlib.util.spec_from_file_location('synthetic_review_tests', HERE/'test_review.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CountedResult).run(
        unittest.defaultTestLoader.loadTestsFromModule(module))
    after = source_bytes()
    if before != after:
        raise ValueError('SOURCE_CHANGED_DURING_TESTS')
    raw = stream.getvalue().encode('utf-8')
    with stdout_path.open('xb') as output:
        output.write(raw)
    receipt = {'schema': 'cas-meta2-contrast-review-pure-tests/6', 'completed': result.wasSuccessful(),
        'test_methods': result.testsRun, 'subtests': result.subtests, 'failures': len(result.failures),
        'errors': len(result.errors), 'skips': len(result.skipped), 'command': [sys.executable, '-B', str(Path(__file__))],
        'source_before_and_after': before, 'test_sources_sha256': {name: digest(HERE/name) for name in
            ('review.py', 'test_review.py', 'run_tests.py')}, 'raw_output_sha256': sha256(raw).hexdigest(),
        'wall_seconds': time.monotonic()-started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'neural_execution': False, 'provider_calls': False, 'registered_seed_generated': False,
        'current_campaign_result_read': False,
        'boundary': 'Synthetic checker tests and existing seed-926603 development fixture only; not a model or native runtime result.'}
    with receipt_path.open('x', encoding='utf-8') as output:
        json.dump(receipt, output, sort_keys=True, indent=2)
        output.write('\n')
    print(raw.decode(), end='')
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
