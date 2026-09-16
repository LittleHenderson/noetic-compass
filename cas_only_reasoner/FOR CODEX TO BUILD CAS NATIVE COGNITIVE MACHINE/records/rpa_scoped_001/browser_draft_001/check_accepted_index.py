"""Inspect accepted static index bytes and bind every relative target to its package."""
import json
from pathlib import Path
import sys
import traceback
from check_accepted_documents import verify_package
from scoped_browser_helper import ROOT,FOLDER,check_page,checksum

def main():
    source=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve();expected=sys.argv[3]
    receipt=verify_package(source,expected);destination.mkdir()
    helpers=[FOLDER/name for name in ('check_accepted_index.py','check_scoped_index.mjs','check_accepted_documents.py','scoped_browser_helper.py')]
    before={str(p.relative_to(ROOT)):checksum(p) for p in helpers}
    try:
        proof=check_page(source/'index.html',destination,'check_scoped_index.mjs')
        targets=[];expected_names={row['name']+'.html' for row in receipt['examples']}
        assert [r['href'] for r in proof['views'][0]['links']]==[r['href'] for r in proof['views'][1]['links']]
        actual=[r['href'] for r in proof['views'][0]['links']]
        assert len(actual)==len(set(actual))==10 and set(actual)==expected_names
        for name in actual:
            target=(source/name).resolve();assert target.is_relative_to(source) and target.is_file()
            targets.append({'relative_href':name,'exists_in_accepted_directory':True,'sha256':checksum(target)})
        verify_package(source,expected)
        assert before=={str(p.relative_to(ROOT)):checksum(p) for p in helpers}
        result={'status':'PASS','accepted_receipt_sha256':expected,'index_sha256':checksum(source/'index.html'),
                'accepted_package_unchanged':True,'helper_inputs':before,'browser':proof,'targets':targets,
                'screenshots':{p.name:checksum(p) for p in destination.glob('*.png')}}
        (destination/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
        print(json.dumps({'status':'PASS','receipt_sha256':checksum(destination/'receipt.json')}),flush=True)
    except BaseException:
        (destination/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');raise

if __name__=='__main__':main()
