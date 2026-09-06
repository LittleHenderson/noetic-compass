"""Independent audit of a committed prefix, never a fabricated completed run."""
from hashlib import sha256
import sqlite3
import struct


def audit_prefix(packet,folder,public,action,identity,engine,validator,c):
    require,digest=c.require,c.digest
    database=folder+'/native.db'
    names={name[len(folder)+1:] for name in packet.inventory if name.startswith(folder+'/')}
    require(names=={'native.db','failure.json'},'PREFIX_UNEXPECTED_OR_UNCLOSED_FILES')
    require(packet.json(folder+'/failure.json')=={'status':'INFRASTRUCTURE_FAILURE',
        'type':'RuntimeContractError','message':c.MESSAGE},'PREFIX_ERROR_IDENTITY')
    before={name:packet.inventory[folder+'/'+name]['sha256'] for name in names}
    con=sqlite3.connect(packet.path(database).as_uri()+'?mode=ro&immutable=1',uri=True)
    con.row_factory=sqlite3.Row
    observations={row['slot']:{'sha':sha256(struct.pack('<8f',*row['values'])).hexdigest(),'tag':row['tag']}
                  for row in public['observations']}
    def document(table,key,*,field='record_id'):
        require(table in {'model_versions','state_versions','commit_receipts','causes','published_effects',
                           'candidate_effects','verifier_receipts'},'PREFIX_TABLE_NOT_ALLOWED')
        row=con.execute('SELECT * FROM '+table+' WHERE '+field+'=?',(key,)).fetchone()
        require(row is not None,'PREFIX_DOCUMENT_MISSING')
        raw=row['payload_json'];value=c.decode(raw)
        require(c.canonical(value).decode()==raw and sha256(raw.encode()).hexdigest()==row['payload_sha256'],
                'PREFIX_DOCUMENT_HASH')
        return value,row
    def artifact(ref):
        row=con.execute('SELECT * FROM artifacts WHERE artifact_id=?',(ref['artifact_id'],)).fetchone()
        require(row is not None,'PREFIX_ARTIFACT_MISSING')
        metadata=c.decode(row['metadata_json']);raw=bytes(row['payload'])
        header={'encoding':row['encoding'],'kind':row['kind'],'media_type':row['media_type'],
                'metadata':metadata,'payload_byte_length':len(raw)}
        checksum=sha256(c.canonical(header)+b'\n'+raw).hexdigest()
        require(c.canonical(metadata).decode()==row['metadata_json'] and row['sha256']==checksum
                and row['artifact_id']=='artifact-'+checksum[:24] and ref['sha256']==checksum
                and ref['encoding']==row['encoding'] and ref['byte_length']==len(raw), 'PREFIX_ARTIFACT_BINDING')
        return sha256(raw).hexdigest()
    def units(plan):
        def total(value):
            if type(value) is list:return sum(total(item) for item in value)
            require(type(value) is int and value>=0,'PREFIX_PLAN_INTEGER');return value
        result=sum(total(plan[name]) for name in ('route_quanta','reasoning_step_quanta','branch_quanta',
                                                 'memory_read_quanta','diagnostic_probe_quanta'))
        require(result>0,'PREFIX_ZERO_PLAN');return result
    try:
        con.execute('PRAGMA query_only=ON')
        require([tuple(r) for r in con.execute('PRAGMA integrity_check')]==[('ok',)],'PREFIX_SQLITE_INTEGRITY')
        require(tuple(con.execute('SELECT value FROM store_metadata WHERE key=?',('schema_version',)).fetchone())
            ==('cas.neural-cjt.sqlite-store/0.2',),'PREFIX_STORE_SCHEMA')
        model_digest=identity['model']['model_digest']
        model,model_row=document('model_versions',model_digest,field='model_digest')
        require(model['model_digest']==model_digest==identity['stored_model_digest']
                and model['model_artifact_ref']['sha256']==model_digest and model['network']==identity['topology']
                and artifact(model['model_artifact_ref'])==identity['model']['parameter_bytes_sha256'],
                'PREFIX_FIXED_MODEL_IDENTITY')
        rows,traces,effects,previous,previous_state=[],[],{},None,None
        committed_units=0
        for index,row in enumerate(con.execute('SELECT * FROM trace_events ORDER BY sequence')):
            trace=c.decode(row['payload_json']);validator.validate(trace)
            body={k:v for k,v in trace.items() if k not in ('trace_digest','trace_id')}
            trace_id='trace-'+digest(body)[:24]
            require(row['sequence']==index+1 and type(trace['tick']) is int and trace['tick']==index+1
                    and sha256(row['payload_json'].encode()).hexdigest()==row['payload_sha256']
                    and trace['trace_id']==trace_id and trace['trace_digest']==digest({**body,'trace_id':trace_id})
                    and trace['previous_trace_digest']==previous
                    and (previous_state is None or previous_state==trace['pre_state_digest'])
                    and all(row[k]==trace[k] for k in ('trace_id','trace_digest','previous_trace_digest',
                                                     'pre_state_digest','post_state_digest')),'PREFIX_TRACE_CHAIN')
            require(trace['sealed'] is True and trace['pre_model_digest']==trace['post_model_digest']==model_digest
                    and trace['software_digest']==identity['software_digest']
                    and [p.get('phase',p.get('name')) for p in trace['phases']]==
                        ['READ','CANDIDATE','READINESS','ROUTE','EXECUTE','OBSERVE','VERIFY','DIAGNOSE','EMIT','COMMIT','TRACE'],
                    'PREFIX_TRACE_SOURCE_IDENTITY')
            receipt,rr=document('commit_receipts',trace['commit_receipt_id'],field='receipt_id')
            require(receipt['receipt_digest']==digest({k:v for k,v in receipt.items() if k!='receipt_digest'})
                    and receipt['receipt_id']=='commit-'+rr['request_digest'][:24]
                    and all(receipt[k]==rr[k] for k in ('receipt_id','batch_id','pre_state_digest','post_state_digest','rollback_of_receipt_id'))
                    and all(receipt[k]==trace[k] for k in ('trace_id','tick','pre_state_digest','post_state_digest','pre_model_digest','post_model_digest'))
                    and rr['trace_digest']==trace['trace_digest'] and receipt['authorized'] is True
                    and receipt['atomic'] is True and receipt['disposition']=='COMMITTED','PREFIX_COMMIT_RECEIPT')
            software={'runtime_id':trace['runtime_id'],'authority_contract_id':receipt['authority_contract_id'],
                      'topology':identity['topology'],'operation_contracts':identity['contracts'],'decoders':identity['decoders']}
            require(digest(software)==identity['software_digest'],'PREFIX_SOFTWARE_IDENTITY')
            ids=trace['published_effect_ids'];require(len(ids)==1 and ids==receipt['published_effect_ids']
                and ids[0] not in effects,'PREFIX_EFFECT_COUNT')
            effect,er=document('published_effects',ids[0])
            require(er['commit_receipt_id']==receipt['receipt_id']==effect['commit_receipt_id']
                    and effect['published_effect_id']==ids[0] and effect['tick']==trace['tick']
                    and effect['authoritative'] is True
                    and effect['publication_digest']==digest({k:v for k,v in effect.items() if k!='publication_digest'}),
                    'PREFIX_EFFECT_PUBLICATION')
            cause,cr=document('causes',trace['cause_id'])
            require(cr['commit_receipt_id']==receipt['receipt_id'] and cause==trace['cause']
                    and cause['tick']==trace['tick'],'PREFIX_CAUSE_BINDING')
            parent=cause['parent_effect_id'];input_sha=artifact(cause['content_ref'])
            if parent is None:
                slot=cause['content']['binding_slot']
                require(slot==action['binding'] and slot in observations and cause['content']['public_digest']==digest(public)
                        and cause['content']['binding_tag']==observations[slot]['tag']
                        and cause['content']['task']=='cas-meta2-observation' and input_sha==observations[slot]['sha'],
                        'PREFIX_OBSERVATION_BINDING')
                input_node=-1
            else:
                require(parent in effects and input_sha==effects[parent]['sha']
                        and cause['originating_cjt_id']==effects[parent]['cjt'],'PREFIX_EARLIER_EFFECT_BINDING')
                input_node=effects[parent]['index']
            require(len(trace['verifier_receipts'])==1 and trace['verifier_receipts'][0]['disposition']=='ACCEPT'
                    and trace['verifier_receipts'][0]['repair_required'] is False,'PREFIX_ACCEPT_REQUIRED')
            verifier,vr=document('verifier_receipts',trace['verifier_receipts'][0]['receipt_id'])
            require(verifier==trace['verifier_receipts'][0] and vr['commit_receipt_id']==receipt['receipt_id']
                    and verifier['independent'] is True and verifier['cause_id']==cause['cause_id'],'PREFIX_VERIFIER_BINDING')
            output_sha=artifact(effect['content_ref'])
            cjt=effect['producer_cjt_id']
            effects[ids[0]]={'sha':output_sha,'cjt':cjt,'index':index}
            row_summary={'cjt_id':cjt,'input_node':input_node,'input_sha256':input_sha,'output_sha256':output_sha}
            rows.append(row_summary);traces.append(trace);committed_units+=units(trace['compute_plan'])
            for state_name,column in (('state_before','pre_state_digest'),('state_after','post_state_digest')):
                state,sr=document('state_versions',trace[column],field='state_digest')
                require(state==trace[state_name] and digest({k:v for k,v in state.items() if k!='state_digest'})==trace[column]
                        and state['model_digest']==model_digest,'PREFIX_STATE_IDENTITY')
            previous,previous_state=trace['trace_digest'],trace['post_state_digest']
        count=len(rows)
        require(con.execute('SELECT COUNT(*) FROM model_versions').fetchone()[0]==1
            and con.execute('SELECT COUNT(*) FROM state_versions').fetchone()[0]==count+1,
            'PREFIX_EXTRA_MODEL_OR_STATE_VERSION')
        require(con.execute('SELECT COUNT(*) FROM commit_receipts').fetchone()[0]==count
                and con.execute('SELECT COUNT(*) FROM published_effects').fetchone()[0]==count,'PREFIX_UNACCOUNTED_COMMITS')
        heads=list(con.execute('SELECT * FROM active_head'));require(len(heads)==1,'PREFIX_HEAD_COUNT')
        head=heads[0]
        require(head['state_version']==count and head['model_digest']==model_digest and head['trace_digest']==previous,
                'PREFIX_FINAL_HEAD')
        final_state,_=document('state_versions',head['state_digest'],field='state_digest')
        require(final_state['state_digest']==head['state_digest']
            and digest({k:v for k,v in final_state.items() if k!='state_digest'})==head['state_digest']
            and final_state['state_version']==count and final_state['model_digest']==model_digest,
            'PREFIX_HEAD_STATE_DOCUMENT')
        if count==0:
            require(head['commit_receipt_id'] is None and final_state['previous_state_digest'] is None,
                    'PREFIX_INITIAL_HEAD')
        if count:require(head['state_digest']==previous_state and head['commit_receipt_id']==traces[-1]['commit_receipt_id'],
                         'PREFIX_FINAL_HEAD')
        plan=engine.check_native_topology(action['program'])
        expected=[{k:r[k] for k in ('cjt_id','input_node')} for r in plan['runs']]
        actual=[{k:r[k] for k in ('cjt_id','input_node')} for r in rows]
        require(count<len(expected) and actual==expected[:count],'PREFIX_SEALED_PROGRAM_MISMATCH')
        next_run=plan['runs'][count]
        # With this frozen four-node topology, A and B have no distinct return
        # path. Do not infer the missing tick's candidate symbol or neural cause.
        require(next_run['cjt_id'] in ('A','B'),'PREFIX_UNSUPPORTED_ERROR_TARGET')
        require(committed_units<=32768 and count<384,'PREFIX_POLICY_BOUND')
    finally:con.close()
    require({name:c.file_hash(packet.path(folder+'/'+name)) for name in names}==before,'PREFIX_CHANGED_DURING_AUDIT')
    return {'committed_native_runs':count,'committed_reserved_policy_units':committed_units,
        'failed_tick_compute':None,'compute_complete':False,'database_sha256':before['native.db'],
        'evidence_sha256':before,'rows':rows,'next_sealed_run':next_run,
        'published_trace_schema_checked':True,'committed_prefix_documents_checked':True,
        'document_tables_checked':['trace_events','commit_receipts','published_effects','causes',
                                   'verifier_receipts','model_versions','state_versions','artifacts','active_head'],
        'sealed_program_prefix_checked':True,'complete_execution_trace':False,
        'missing_failed_tick_candidate_and_verifier_receipt':True,
        'boundary':'Stored committed prefix and sealed-program mapping only; no failed-tick tensor decoding, '
                   'no full call-tree export, no final output, and no independently replayed neural execution.'}
