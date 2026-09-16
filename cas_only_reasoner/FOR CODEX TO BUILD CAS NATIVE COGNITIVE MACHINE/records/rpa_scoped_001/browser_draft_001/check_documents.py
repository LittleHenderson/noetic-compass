"""Independent Python graph/reference and exact evidence comparison after real UI clicks."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback
from scoped_browser_helper import ROOT,FOLDER,check_page,checksum
from cncm.canonical import canonical_json,digest
from cncm.rpa_compound_adapter import record_body_from_catalog
from cncm.rpa_scoped_compound import validate_scoped,ScopePath,local_scope,start_scope,enter_scope,return_scope
from tools.render_scoped_rpa_view import render_scoped_rpa

def encoded_hash(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify(document,proof):
    atlas=validate_scoped(document);nodes=atlas.node_map();wire=atlas.to_dict()
    expected=[]
    def descend(cursor):
        local=local_scope(atlas,cursor);ids=[n['node_id'] for n in local['nodes'][1:]]
        expected.append({'path':list(cursor.path),'children':ids,'pages':[ids[i:i+8] for i in range(0,len(ids),8)] or [[]]})
        for child in ids:
            if any(e['source_id']==child and e['relation']=='contains_part' for e in wire['links']) and child not in cursor.path:
                entered=enter_scope(atlas,cursor,child)
                assert return_scope(atlas,entered,len(cursor.path)-1)==cursor
                descend(entered)
    descend(start_scope(atlas))
    catalog=document['source']['native']['evidence_catalog']
    record_keys={r['record_digest'] for r in catalog['records']}
    fallback='Content identity / source reference. No additional record body is supplied in this evidence catalog.'
    summary=[]
    for view in proof['views']:
        assert canonical_json(view['scopes'])==canonical_json(expected),'reachable scopes differ from Python reference'
        assert view['fixed']['current_state_id']==atlas.current_state_id
        assert view['fixed']['current_state_hash']==document['current_state_hash']
        assert view['fixed']['document_digest']==document['document_digest']
        assert view['fixed']['snapshot_digest']==digest(wire)
        assert view['geometry']==document['geometry']
        for row in view['inspections']:
            assert row['node_sha256']==encoded_hash(nodes[row['id']].to_dict()),'displayed record differs from Python source'
            links=[e for e in wire['links'] if e['relation']=='contains_part' and e['source_id']==row['scope'] and (e['target_id']==row['id'] or row['id']==row['scope'])]
            assert canonical_json(row['relationships'])==canonical_json(links)
            assert row['evidence_keys']==list(nodes[row['id']].evidence_refs)
        for key,value in view['evidence_records'].items():
            body=canonical_json(record_body_from_catalog(catalog,key)) if key in record_keys else fallback
            assert value==sha256(body.encode()).hexdigest(),'displayed exact evidence text differs from catalog'
        summary.append({'viewport':view['viewport'],'scope_paths':len(view['scopes']),'inspections':len(view['inspections']),
                        'leaf_count':view['leaf_count'],'evidence_refs':len(view['evidence_records']),
                        'min_font_px':min(r['font'] for r in view['bounds']),'max_scroll_width':max(r['width'] for r in view['bounds']),
                        'card_overlap_count':sum(r['overlaps'] for r in view['bounds'])})
    assert not proof['requests'] and not proof['errors'] and proof['page_unchanged']
    return summary

def main():
    source=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve();destination.mkdir()
    sources=[p for p in sorted(source.glob('*.json')) if json.loads(p.read_bytes()).get('schema_version')=='cncm.rpa-scoped-compound-view/0.1']
    bound=[ROOT/'cncm/rpa_scoped_compound.py',ROOT/'tools/render_scoped_rpa_view.py',FOLDER/'scoped_browser_helper.py',FOLDER/'check_scoped_browser.mjs',Path(__file__),*sources]
    before={str(p.relative_to(ROOT)):checksum(p) for p in bound}
    (destination/'inputs.json').write_text(json.dumps(before,indent=2),encoding='utf-8',newline='\n')
    rows=[]
    try:
        for source_file in sources:
            document=json.loads(source_file.read_bytes());folder=destination/source_file.stem;folder.mkdir()
            page=folder/'view.html';page.write_text(render_scoped_rpa(document),encoding='utf-8',newline='\n')
            proof=check_page(page,folder)
            (folder/'browser_result.json').write_text(json.dumps(proof,separators=(',',':')),encoding='utf-8',newline='\n')
            checks=verify(document,proof)
            row={'name':source_file.stem,'source_sha256':checksum(source_file),'page_sha256':checksum(page),'browser_proof_sha256':checksum(folder/'browser_result.json'),
                 'independent_reference_match':True,'exact_records_match':True,'exact_evidence_bodies_match':True,'fixed_source_state_unchanged':True,
                 'requests':0,'errors':0,'geometry':document['geometry'],'views':checks,
                 'screenshots':{p.name:checksum(p) for p in sorted(folder.glob('*.png'))}}
            rows.append(row);print(json.dumps(row),flush=True)
        after={str(p.relative_to(ROOT)):checksum(p) for p in bound};assert before==after,'bound input changed'
        receipt={'status':'PASS','inputs':before,'inputs_unchanged':True,'document_count':len(rows),'pages':rows}
        (destination/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8',newline='\n')
    except BaseException:
        (destination/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');raise

if __name__=='__main__':main()
