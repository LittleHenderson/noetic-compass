"""Bind this additive package to its exact bytes; does not certify behavior."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
files=[]
for path in sorted(root.rglob('*')):
    if path.is_file() and path.name!='PACKAGE_MANIFEST.json':
        raw=path.read_bytes()
        files.append({'path':path.relative_to(root).as_posix(),'bytes':len(raw),
                      'sha256_raw':hashlib.sha256(raw).hexdigest()})
(root/'PACKAGE_MANIFEST.json').write_text(json.dumps({
    'schema':'cas.audit-reconciliation-package/0.1',
    'subject_commit':'eb9985566bd11a89f485d627186ef0efa7177f02',
    'peer_audit_commit':'65ad300835c06f9feff154170cb8b103d5d13ffa',
    'scope':'Integrity manifest of additive evidence reconciliation, not product or model acceptance.',
    'files':files},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'files_bound':len(files),'manifest_sha256':hashlib.sha256((root/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()}))
