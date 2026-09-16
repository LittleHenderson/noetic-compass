"""Retain complete final-suite output, status and the source identity tested."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

RECORD = Path(__file__).resolve().parent
ROOT = RECORD.parents[1]
sys.path.insert(0, str(ROOT))
from cncm.compound_profile import load_compound_profile

expected = json.loads((RECORD / 'source_freeze_final.json').read_bytes())['source_profile_digest']
assert load_compound_profile().profile_digest == expected
targets = [RECORD / name for name in ('final_full_suite_tests.xml', 'final_full_suite_output.log', 'final_validation_summary.json')]
assert not any(p.exists() for p in targets), 'use a new evidence run; never overwrite results'
command = [sys.executable, '-B', '-m', 'pytest', '-q', '--junitxml=records/compound_procedure_001/final_full_suite_tests.xml', '--tb=short']
start = time.monotonic()
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
elapsed = time.monotonic() - start
raw = (result.stdout + result.stderr).replace('\r\n', '\n').encode('utf-8')
targets[1].write_bytes(raw)
suite = ET.fromstring(targets[0].read_bytes()).find('testsuite')
assert suite is not None
passed = re.search(r'(\d+) passed', result.stdout)
subtests = re.search(r'(\d+) subtests passed', result.stdout)
summary = {
    'command': command, 'pytest_exit_code': result.returncode,
    'tests_passed': int(passed[1]) if passed else 0,
    'subtests_passed': int(subtests[1]) if subtests else 0,
    'xml_cases': int(suite.attrib['tests']),
    'errors': int(suite.attrib['errors']), 'failures': int(suite.attrib['failures']),
    'skipped': int(suite.attrib['skipped']), 'duration_seconds': elapsed,
    'source_profile_digest': expected,
    'source_unchanged': load_compound_profile().profile_digest == expected,
    'xml_sha256': sha256(targets[0].read_bytes()).hexdigest(),
}
targets[2].write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(result.stdout[-5000:])
print(json.dumps(summary))
assert result.returncode == 0 and summary['source_unchanged']
assert all(summary[k] == 0 for k in ('errors', 'failures', 'skipped'))
assert summary['xml_cases'] == summary['tests_passed'] + summary['subtests_passed']
