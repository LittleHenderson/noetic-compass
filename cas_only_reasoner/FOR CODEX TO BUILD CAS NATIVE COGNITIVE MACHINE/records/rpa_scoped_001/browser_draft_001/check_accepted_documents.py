"""QA accepted HTML bytes directly; this runner never rerenders a page."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback
from scoped_browser_helper import ROOT,FOLDER,check_page,checksum
from check_documents import verify

STATUS='SCOPED_PROJECTION_AND_NAVIGATION_PASS_BROWSER_CHECK_SEPARATE'

def verify_package(source,expected):
    assert checksum(source/'receipt.json')==expected,'acceptance receipt changed'
    receipt=json.loads((source/'receipt.json').read_bytes())
    assert receipt['status']==STATUS
    for row in receipt['files']:
        path=(source/row['path']).resolve()
        assert path.is_relative_to(source) and path.is_file()
        assert path.stat().st_size==row['bytes'] and checksum(path)==row['sha256']
    for row in receipt['sources']:
        path=(ROOT/row['path']).resolve()
        assert path.is_relative_to(ROOT) and path.is_file()
        assert path.stat().st_size==row['bytes'] and checksum(path)==row['sha256']
    return receipt

def main():
    source=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve();expected=sys.argv[3]
    assert len(expected)==64 and all(c in '0123456789abcdef' for c in expected)
    receipt=verify_package(source,expected);destination.mkdir()
    helpers=[FOLDER/name for name in ('check_accepted_documents.py','check_documents.py','scoped_browser_helper.py','check_scoped_browser.mjs')]
    helpers.append(ROOT/'tests/test_rpa_view.py')
    before={str(p.relative_to(ROOT)):checksum(p) for p in helpers}
    (destination/'inputs.json').write_text(json.dumps({'receipt_sha256':expected,'helpers':before},indent=2),encoding='utf-8',newline='\n')
    rows=[]
    try:
        names=[r['name'] for r in receipt['examples']];assert len(names)==10 and len(set(names))==10
        for name in names:
            document_path=source/(name+'.json');page=source/(name+'.html')
            document=json.loads(document_path.read_bytes());folder=destination/name;folder.mkdir()
            proof=check_page(page,folder)
            (folder/'browser_result.json').write_text(json.dumps(proof,separators=(',',':')),encoding='utf-8',newline='\n')
            checks=verify(document,proof)
            rows.append({'name':name,'accepted_document_sha256':checksum(document_path),'accepted_html_sha256':checksum(page),
                'browser_proof_sha256':checksum(folder/'browser_result.json'),'accepted_html_opened_without_rerender':True,
                'independent_reference_match':True,'exact_record_and_evidence_match':True,'fixed_source_state_unchanged':True,
                'requests':len(proof['requests']),'errors':len(proof['errors']),'geometry':document['geometry'],'views':checks,
                'screenshots':{p.name:checksum(p) for p in sorted(folder.glob('*.png'))}})
            print(json.dumps({'checked':name,'views':checks}),flush=True)
        verify_package(source,expected)
        assert before=={str(p.relative_to(ROOT)):checksum(p) for p in helpers},'browser helper changed during checks'
        result={'status':'PASS','accepted_receipt_sha256':expected,'accepted_directory':source.relative_to(ROOT).as_posix(),
                'accepted_html_rerendered':False,'accepted_package_and_sources_unchanged':True,'helper_inputs':before,
                'helper_inputs_unchanged':True,'document_count':len(rows),'pages':rows}
        (destination/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
        print(json.dumps({'status':'PASS','receipt_sha256':checksum(destination/'receipt.json')}),flush=True)
    except BaseException:
        (destination/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');raise

if __name__=='__main__':main()
