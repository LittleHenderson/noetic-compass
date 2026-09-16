"""Versioned scoped-view reproduction over separately pinned compound evidence.

Navigation never runs a procedure. One journal is replayed to check the runtime
adapter; the ten display inputs are bound to the earlier acceptance receipt.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FORBIDDEN = frozenset({'torch','numpy','transformers','tensorflow','jax','boto3','botocore','requests','httpx','openai'})
class DenyCompute:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise RuntimeError('Prohibited compute/provider import: '+fullname)
sys.meta_path.insert(0, DenyCompute())
from cncm.canonical import canonical_json, digest
from cncm.compound_model import CompoundProblem
from cncm.compound_engine import CompoundMachine
from cncm.compound_recovery import recover_compound_journal
from cncm.model import ContractError
from cncm.rpa_model import LinkType
from cncm.rpa_scoped_compound import (scoped_projection, scoped_from_journal,
    validate_scoped, start_scope, enter_scope, return_scope, local_scope, children)
from tools.render_scoped_rpa_view import render_scoped_rpa

BASE = ROOT/'records/rpa_compound_001/acceptance_002'
BASE_RECEIPT = '73bcedec7a2cdd3a761dcc55cef59049bf643645c1ad8dd810ea503fd264cd55'
RUNTIME = ROOT/'records/compound_procedure_001/acceptance_001'
RUNTIME_RECEIPT = '3f3ca9e9f3016df527ddbf218f7c0d26a41cc7d9baf01ca99f8d7632f6fcf66b'
OWN_INPUTS = ('cncm/rpa_scoped_compound.py','tools/render_scoped_rpa_view.py',
    'tools/reproduce_scoped_rpa.py','tests/test_rpa_scoped_compound.py')

def read(path):
    return json.loads(path.read_bytes())

def identity(path, base=ROOT):
    raw=path.read_bytes()
    return {'path':path.relative_to(base).as_posix(),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}

def put(path, value):
    raw=value.encode() if type(value) is str else (canonical_json(value)+'\n').encode()
    with path.open('xb') as stream:stream.write(raw)

def project_imports():
    paths=set()
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.suffix=='.py' and path.is_relative_to(ROOT):paths.add(path)
    return sorted(paths)

def require(condition, message):
    if not condition:raise AssertionError(message)

def verify_package(base, expected):
    require(identity(base/'receipt.json')['sha256']==expected,'Prior acceptance receipt changed')
    receipt=read(base/'receipt.json')
    for row in receipt['files']:
        path=(base/row['path']).resolve()
        require(path.is_relative_to(base.resolve()) and identity(path,base)==row,'Prior package file changed: '+row['path'])
    return receipt

def verify_navigation(document):
    atlas=validate_scoped(document)
    initial=start_scope(atlas)
    before=canonical_json(document)
    results=[]
    stack=[initial]
    while stack:
        cursor=stack.pop()
        local=local_scope(atlas,cursor)
        expected=children(atlas,cursor.path[-1])
        require(local['current_state_id']==atlas.current_state_id,'Navigation changed current state')
        require({row['node_id'] for row in local['nodes']}=={cursor.path[-1],*expected},'Scope contains unrelated nodes')
        expected_links={edge.link_id for edge in atlas.links if edge.source_id==cursor.path[-1]
                        and edge.relation is LinkType.CONTAINS_PART and edge.target_id in expected}
        require({edge['link_id'] for edge in local['links']}==expected_links,'Scope differs from declared dependency graph')
        require(return_scope(atlas,cursor,0)==initial,'Breadcrumb did not return to root')
        results.append({'path':list(cursor.path),'children':list(expected),
                        'current_state_id':local['current_state_id'],'snapshot_digest':local['snapshot_digest']})
        for key in expected:
            if children(atlas,key):
                stack.append(enter_scope(atlas,cursor,key))
            else:
                try:enter_scope(atlas,cursor,key)
                except ContractError:pass
                else:raise AssertionError('Leaf acquired invented internal structure')
    require(before==canonical_json(document),'Navigation mutated its document')
    return results

def index(examples):
    links=''.join('<li><a href="'+escape(row['name'])+'.html">'+escape(row['name'].replace('_',' '))+'</a></li>' for row in examples)
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; connect-src \'none\'"><title>CAS declared structure</title><style>body{font:18px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 24px;color:#18302c;background:#f2f5ef}a{color:#17614e}li{margin:12px 0}code{overflow-wrap:anywhere}</style><h1>Enter the declared structure</h1><p>Choose a saved episode. Select a retained compound program, then <strong>Enter structure</strong>. Enter a call to see its input bindings, or enter its primitive to see its instructions. Use the breadcrumbs to return.</p><p>The current execution state stays fixed. Evidence records show what was retained. An empty interior stays empty; navigation does not execute or install anything.</p><ul>'+links+'</ul><p>Version 0.1 · compound runtime 0.5 evidence · no assigned profile40 measurements or overlap certificates in these ten inputs. This navigation extension does not establish recursive reasoning, learning, geometry, or a performance advantage.</p></html>'

def main():
    if sys.flags.optimize:raise RuntimeError('Unoptimized Python required for evidence checks')
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    options=parser.parse_args()
    output=options.output.resolve()
    require(output.parent==(ROOT/'records/rpa_scoped_001').resolve() and not output.exists(),'New direct output directory required')
    output.mkdir()
    try:
        baseline=verify_package(BASE,BASE_RECEIPT)
        runtime=verify_package(RUNTIME,RUNTIME_RECEIPT)
        names=({row['path'] for row in baseline['sources']}|set(OWN_INPUTS)
               |{path.relative_to(ROOT).as_posix() for path in project_imports()})
        before=[identity(ROOT/name) for name in sorted(names)]
        for row in baseline['sources']:
            require(identity(ROOT/row['path'])==row,'Frozen source changed: '+row['path'])
        put(output/'sources_before.json',before)
        examples=[]
        for item in baseline['examples']:
            name=item['name'];source=read(BASE/(name+'.json'))
            saved=canonical_json(source)
            document=scoped_projection(source)
            paths=verify_navigation(document)
            require(canonical_json(source)==saved,'Projection mutated source')
            require(document['source']==source,'Projection replaced source data')
            put(output/(name+'.json'),document)
            put(output/(name+'.html'),render_scoped_rpa(document))
            put(output/(name+'_navigation.json'),{'paths':paths,'state_unchanged':True,'declared_graph_parity':True})
            examples.append({'name':name,'source':identity(BASE/(name+'.json')),
                'document_digest':document['document_digest'],'current_state_hash':document['current_state_hash'],
                'current_state_id':document['atlas']['current_state_id'],'scopes':len(paths),
                'max_depth':max(len(row['path'])-1 for row in paths),'geometry':document['geometry']})
            print(json.dumps({'projected':name,'scopes':len(paths)}),flush=True)
        journal=read(RUNTIME/'baseline_journal.json')
        genesis=CompoundProblem.from_dict(read(RUNTIME/'genesis.json'))
        custody=read(RUNTIME/'external_ingress.json')
        anchor=read(RUNTIME/'baseline_anchor.json')['journal_digest']
        original=canonical_json(journal)
        arguments=dict(trusted_genesis=genesis,trusted_ingress=tuple(custody['initial_statement_digests']),expected_journal_digest=anchor)
        replayed=scoped_from_journal(journal,**arguments)
        checked=read(output/'checked_solution.json')
        require(replayed==checked,'Runtime adapter differs from the separately pinned checked-solution document')
        wrong=dict(arguments,expected_journal_digest='0'*64)
        try:scoped_from_journal(journal,**wrong)
        except ContractError:pass
        else:raise AssertionError('Runtime adapter accepted a wrong external journal digest')
        require(canonical_json(journal)==original,'Adapter mutated journal')
        put(output/'runtime_adapter.json',{'journal':identity(RUNTIME/'baseline_journal.json'),
            'custody':identity(RUNTIME/'external_ingress.json'),'anchor':identity(RUNTIME/'baseline_anchor.json'),
            'exact_checked_projection':True,'wrong_anchor_refused':True,'current_state_unchanged':True})
        put(output/'index.html',index(examples))
        require(before==[identity(ROOT/name) for name in sorted(names)],'Scoped input changed during reproduction')
        verify_package(BASE,BASE_RECEIPT);verify_package(RUNTIME,RUNTIME_RECEIPT)
        imports=[]
        for module in tuple(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if filename:
                path=Path(filename).resolve()
                if path.suffix=='.py' and path.is_relative_to(ROOT):
                    row=identity(path)
                    require(row in before,'Unpinned imported source: '+row['path'])
                    imports.append(row)
        put(output/'actual_imports.json',sorted(imports,key=lambda row:row['path']))
        put(output/'receipt.json',{'schema_version':'cncm.scoped-rpa-receipt/0.1',
            'status':'SCOPED_PROJECTION_AND_NAVIGATION_PASS_BROWSER_CHECK_SEPARATE',
            'baseline_receipt_sha256':BASE_RECEIPT,'runtime_receipt_sha256':RUNTIME_RECEIPT,
            'old_files_verified':len(baseline['files'])+len(runtime['files']),
            'examples':examples,'sources':before,
            'files':[identity(path,output) for path in sorted(output.iterdir()) if path.is_file()],
            'interpreter':sys.version,'forbidden_imports':sorted(FORBIDDEN),
            'recursive_reasoning_or_learning_proven':False,'measured_geometry':False,
            'runtime_writes_from_navigation':0,'full_vision_complete':False})
    except BaseException as error:
        put(output/'failure.json',{'type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()})
        raise

if __name__=='__main__':main()
