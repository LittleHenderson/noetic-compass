"""Reconcile audit parse failures, archive source families and authored variants."""
from a import *
from cas_meta2.graph_teaching import lessons, cube_node, final_panel
history=read(OUT/'history.json'); supply=read(OUT/'supply.json')
candidate={r['topology'] for r in supply['rows'] if r['candidate_pool']}
known={r['sha256'] for r in supply['archives']}
current_tree=ast.parse((ROOT/'cas_meta2/graph_teaching/lessons.py').read_bytes())
current_fn=next(n for n in current_tree.body if isinstance(n,ast.FunctionDef) and n.name=='whole_part_family')
family_ast=sha256(ast.dump(current_fn).encode()).hexdigest()
archive_rows=[]; template_union=set(); bundles={}
for archive in history['archives']:
    if not archive.get('relevant_source_members'):continue
    entry={'path':archive['path'],'sha256':archive['sha256'],'in_exact_exclusion_rebuild':archive['sha256'] in known}
    with ZipFile(ROOT/archive['path']) as z:
        lesson=next((n for n in z.namelist() if n.endswith('/graph_teaching/lessons.py')),None)
        if lesson:
            tree=ast.parse(z.read(lesson))
            declaration=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='WHOLE_PART_TEMPLATES' for t in n.targets))
            shapes=ast.literal_eval(declaration.value)
            keys={shape_key(s) for s in shapes};template_union|=keys
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='whole_part_family')
            entry['whole_part_family_ast_sha256']=sha256(ast.dump(fn).encode()).hexdigest()
            entry['whole_part_family_ast_matches_current']=entry['whole_part_family_ast_sha256']==family_ast
            entry['declared_lesson_topologies']=sorted(keys)
            entry['candidate_overlap']=sorted(keys&candidate)
        bundle=next((n for n in z.namelist() if n.endswith('/Cube_Node_Example_v0.1.json')),None)
        if bundle:
            raw=z.read(bundle); identity=sha256(raw).hexdigest()
            if identity not in bundles:
                data=json.loads(raw); cube_node.validate_bundle(data)
                graphs=[cube_node.containment_graph(data,v['view_id']).to_record() for v in data['views']]
                bundles[identity]={'view_node_counts':[len(g['nodes']) for g in graphs],
                    'topologies':sorted({graph_key(g) for g in graphs}),'current_validator_passed':True,
                    'scope':'Exact archived authored bundle views, pure structural check; not replay of historical learner input.'}
            entry['cube_bundle_sha256']=identity
        archive_rows.append(entry)
assert not template_union&candidate
assert all(r.get('whole_part_family_ast_matches_current',True) for r in archive_rows)
assert not candidate&{k for b in bundles.values() for k in b['topologies']}
smokes=[]
for row in history['parse_failures']:
    raw=(ROOT/row['path']).read_text(encoding='utf-8')
    document,end=json.JSONDecoder().raw_decode(raw)
    suffix=raw[end:].strip()
    assert suffix=='SMOKE ONLY - not a measurement, not claim-bearing, local GPU.'
    selected={k:document[k] for k in ('boundary','updates_per_condition','probe_questions','records','probe_items_measured','conditions','package','result_sha256') if k in document}
    smokes.append({**row,'json_object_recovered':True,'trailing_text':suffix,'metadata':selected,
      'exposure_interpretation':'Actual local GPU smoke counts as neural exposure despite not being a claim-bearing experiment; old cube or CFC source family only.'})
allocation={r['topology']:r['current_allocation'] for r in supply['rows']}
occ=[]
for r in history['candidate_occurrences']:
    counts=Counter(allocation[x['topology']] for x in r['matches'])
    entry={k:r[k] for k in ('path','sha256','schema')}
    entry['classification']='AUTHORED_PREPARATION_NOT_OBSERVED_NEURAL_EXPOSURE'
    entry['occurrences_by_allocation']=dict(counts)
    entry['topologies_by_allocation']={s:sorted({v['topology'] for v in r['matches'] if allocation[v['topology']]==s}) for s in set(allocation.values())}
    if 'perspective' in r['path']:
        entry['final_variant_development_overlap']=[v for v in r['matches'] if allocation[v['topology']]=='development']
    occ.append(entry)
probe=ROOT/'records/ordered_encoder_001/receipt_cas-meta2-orderedencoder-20260916064137-e47349be/collected/results/artifacts/encoder_probe.json'
probe_doc=read(probe); envelope=read(OUT/'envelope.json')
assert probe_doc['ordered_profile']['tokenizer_sha256']==envelope['rows'][1]['tokenizer_sha256']
missing=[]
for row in supply['rows']:
    if row['candidate_pool'] and not row['supports_all_three_reach_classes']:
        shape=next(s for s in final_panel.enumerate_patterns().values() if shape_key(s)==row['topology'])
        family=final_panel._family(shape,7)
        missing.append({'topology':row['topology'],'unsupported_reach_classes':[v for v in ('direct','via','absent') if final_panel._reach_case(family,v) is None]})
write('reconcile.json',{'schema':'cas.learning-panel-history-reconciliation/0.1','archives':archive_rows,
  'old_lesson_template_topologies':sorted(template_union),'archived_cube_bundles':bundles,'smoke_recovery':smokes,
  'candidate_occurrences':occ,'unsupported_candidates':missing,'ordered_tokenizer_match':{'probe':pin(probe),'matched_tokenizer_sha256':envelope['rows'][1]['tokenizer_sha256']},
  'scope':'Retained source-family and record evidence; authoring separated from actual local/remote neural use. Does not certify unretained global history or a new experiment.',
  'inputs':[pin(OUT/n) for n in ('a.py','b.py','supply.json','envelope.json','history.json')],
  'perspective_preparation_pins':[pin(ROOT/'records/perspective_resonance_001'/n) for n in ('DESIGN_TASK_BINDINGS.md','prepared/preparation_receipt.json','prepared/unsigned_worker_config.json','prepared/unsigned_costed_request.json')],
  'source_pins':modules(),'actual_neural_presentations':0,'actual_optimizer_updates':0,'actual_provider_calls':0})
