"""Lightweight local receipt download/extraction inspection; no test execution."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
archive = HERE / 'run001-results.tar.gz'
destination = HERE / 'run001'
destination.mkdir(exist_ok=True)
prefix = 'records/helm_stage2_checker_20260923/'
with tarfile.open(archive, 'r:gz') as tar:
    for member in tar.getmembers():
        if member.isdir():
            continue
        if not member.isfile() or not member.name.startswith(prefix):
            raise RuntimeError('UNEXPECTED_ARCHIVE_MEMBER:' + member.name)
        relative = member.name[len(prefix):]
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise RuntimeError('UNSAFE_ARCHIVE_PATH')
        raw = tar.extractfile(member).read()
        if target.exists() and target.read_bytes() != raw:
            raise RuntimeError('EXISTING_RECEIPT_DIFFERS:' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

xml = ET.parse(destination / 'builder_tests.xml')
cases = list(xml.iter('testcase'))
functions = {row.attrib['classname'] + '::' + row.attrib['name'].split('[')[0] for row in cases}
new = [row for row in cases if row.attrib['classname'].endswith('test_stage2_checker')]
old = [row for row in cases if row not in new]
repo = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
tracked = subprocess.check_output(['git', 'ls-files', '*.py'], cwd=repo, text=True).splitlines()
test_files = [p for p in tracked if re.match(r'(test_.*|.*_test)\.py$', Path(p).name)]
counts = {
    'scope': 'two selected files; filename census is not repository-wide pytest collection',
    'test_functions': len(functions), 'test_cases': len(cases),
    'passed': sum(not any(row.find(tag) is not None for tag in ('failure','error','skipped')) for row in cases),
    'failed': sum(row.find('failure') is not None for row in cases),
    'errors': sum(row.find('error') is not None for row in cases),
    'skipped': sum(row.find('skipped') is not None for row in cases),
    'new_functions': len({r.attrib['name'].split('[')[0] for r in new}), 'new_cases': len(new),
    'existing_functions': len({r.attrib['name'].split('[')[0] for r in old}), 'existing_cases': len(old),
    'loaded_test_files': sorted({r.attrib['classname'] for r in cases}),
    'tracked_test_filename_count': len(test_files), 'unloaded_test_filename_count': len(test_files)-2,
}
compat = json.loads((destination / 'compatibility.json').read_bytes())
custody = json.loads((HERE / 'HISTORICAL_INPUT_CUSTODY.json').read_bytes())
counts['frozen_profile_matches_both_original_anchors'] = all(
    r['original_checker_profile_digest'] == compat['frozen_profile']['profile_digest'] for r in custody['anchors'])
counts['accepted_answer_records'] = compat['target_records']
counts['slot_plans'] = compat['slot_plans']
counts['historical_prediction_checks'] = compat['predictions']
counts['compatibility_status'] = compat['status']
(HERE / 'TEST_ACCOUNTING.json').write_text(json.dumps(counts, indent=2)+'\n', encoding='utf-8')
print(json.dumps(counts))
