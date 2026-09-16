"""Retained final-page browser verification driver; no runtime execution."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cncm.canonical import canonical_json
from tests.test_rpa_compound_view import run_browser_check

OUTPUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'records/rpa_compound_001/acceptance_002'
NAMES = ('missing_primitive','constructed_not_installed','installed_waiting_return',
         'checked_solution','source_correction','budget_exhausted','search_exhausted',
         'corrected_reuse','compound_rollback','primitive_rollback')
SCREENSHOTS = {'missing_primitive','checked_solution','source_correction','primitive_rollback'}
RENDERER = '904a7f4d91b121e966998ee6791e3ec172d07b587158f4da0005cebc5945a2bc'
HELPER = '53280ec9e59acc109f3a9f7a5e3e7c0db85b2aff0f56668adb70a5763dae6a86'

def checksum(path):
    return sha256(path.read_bytes()).hexdigest()

def write(path, value):
    assert not path.exists(), str(path)
    path.write_text(canonical_json(value)+'\n', encoding='utf-8', newline='\n')

def ready(path):
    end = time.monotonic()+2400
    while not path.exists():
        if (SOURCE/'failure.txt').exists():
            raise RuntimeError('Source acceptance recorded a concrete failure')
        if time.monotonic() >= end:
            raise TimeoutError('Wait expired for '+str(path))
        time.sleep(1)

def main():
    assert checksum(ROOT/'tools/render_compound_rpa_view.py') == RENDERER
    assert checksum(ROOT/'tests/test_rpa_compound_view.py') == HELPER
    proofs=[]
    for name in NAMES:
        page=SOURCE/(name+'.html')
        ready(page)
        # The producer writes before announcing a page. Require byte stability
        # before opening it, then re-check against the final source receipt.
        original=checksum(page)
        time.sleep(.5)
        assert original == checksum(page)
        proof=run_browser_check(page,OUTPUT/(name+'.png') if name in SCREENSHOTS else None)
        assert proof['page_sha256'] == original == checksum(page)
        proof.update(name=name,renderer_sha256=RENDERER,test_helper_sha256=HELPER)
        write(OUTPUT/(name+'_proof.json'),proof)
        proofs.append(proof)
        print(canonical_json({'checked':name,'candidate_rows':proof['candidate_rows_checked'],
                              'external_requests':proof['external_requests'],'source_unchanged':proof['source_unchanged']}),flush=True)
    ready(SOURCE/'receipt.json')
    receipt=json.loads((SOURCE/'receipt.json').read_text(encoding='utf-8'))
    assert receipt['all_retained_cuts']==75 and len(receipt['examples'])==10
    for row in receipt['files']:
        assert checksum(SOURCE/row['path']) == row['sha256']
    by_name={row['path']:row for row in receipt['files']}
    for proof in proofs:
        assert proof['page_sha256']==by_name[proof['name']+'.html']['sha256']
    assert checksum(ROOT/'tools/render_compound_rpa_view.py')==RENDERER
    assert checksum(ROOT/'tests/test_rpa_compound_view.py')==HELPER
    write(OUTPUT/'checks.json',{'status':'PASS','source_acceptance_receipt_sha256':checksum(SOURCE/'receipt.json'),
          'renderer_sha256':RENDERER,'test_helper_sha256':HELPER,'pages':proofs,
          'checked_pages':len(proofs),'visual_review':'separate receipt after image inspection'})

if __name__ == '__main__':
    try:
        main()
    except Exception:
        (OUTPUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n')
        raise
