"""Observe the four exact accepted cube views without importing a learner."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'records/rpa_cube_001/acceptance_001'
raw=(BASE/'receipt.json').read_bytes()
expected='b0550845a0e64653910bf8c17a5bd45011ca7068897c59608227b7ce6f50fe7c'
assert sha256(raw).hexdigest()==expected
manifest={row['path']:row for row in json.loads(raw)['artifacts']}
rows=[]
for name in ('view_formal','view_context','view_analogy','hypothesis'):
    relative=name+'.document.json'
    raw=(BASE/relative).read_bytes();document=json.loads(raw)
    row=manifest[relative]
    assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256']
    atlas=document['atlas']
    rows.append({'source':row,'nodes':len(atlas['nodes']),
        'profile40_assigned':sum(node['profile40'] is not None for node in atlas['nodes']),
        'overlap_certificates':len(atlas['overlap_certificates'])})
assert all(row['profile40_assigned']==row['overlap_certificates']==0 for row in rows)
with (Path(__file__).parent/'cube_geometry_001.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'receipt_sha256':expected,'observations':rows,
        'boundary':'These exact four accepted cube documents only. No geometry or learning performance established.'},stream,sort_keys=True,separators=(',',':'))
    stream.write('\n')
print(json.dumps(rows))
