"""Fingerprint completed source and acceptance artifacts; no test execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
manifest = HERE / 'OUTPUT_MANIFEST.json'


def pin(p):
    raw = p.read_bytes()
    return {'path': str(p.resolve()), 'relative_path': p.relative_to(ROOT).as_posix(),
            'bytes': len(raw), 'sha256_raw': hashlib.sha256(raw).hexdigest()}


files = sorted(p for p in HERE.rglob('*') if p.is_file() and p != manifest and not p.name.endswith('.tar.gz'))
package = ROOT / 'research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching'
sources = [package / p for p in ['checker_v2.py', 'answers_v2.py', 'slots_v2.py',
                               'checker.py', 'answers.py', 'slots.py', 'source.py', 'pointer_inputs.py']]
sources.append(ROOT / 'research/CAS_META_2_COMPOSITION/tests/test_stage2_checker.py')
body = {'schema': 'helm.stage2-completed-evidence/1', 'sealed_utc': datetime.now(timezone.utc).isoformat(),
        'implementation_commit': '45828c45', 'tested_source_commit': 'b87fcc150e5818a7b1a4efd11f56b764fa15c219',
        'prior_checkpoint': 'd206b42aa1b68d24f65ab01ec58cc82aad432859',
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
        'source_files': [pin(p) for p in sources], 'records': [pin(p) for p in files],
        'transport_archives_local_only': [pin(HERE / n) for n in ['input_bundle.tar.gz', 'run001-results.tar.gz']],
        'independent_acceptance': 'OPEN_CLAUDE_OWNED',
        'scope': 'Builder CPU checks and AWS cleanup only. No neural model execution or new learning result.'}
manifest.write_text(json.dumps(body, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'source_files': len(sources), 'records': len(files),
                  'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}))
