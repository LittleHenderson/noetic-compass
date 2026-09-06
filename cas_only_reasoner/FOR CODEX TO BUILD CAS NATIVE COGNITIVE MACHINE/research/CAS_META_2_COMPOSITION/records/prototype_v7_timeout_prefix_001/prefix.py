"""Verify a committed timeout prefix, without inventing a runtime-failure receipt.

The checks follow the frozen recovery partial.py document/trace primitives.
This separate entry accepts a read-only derived connection, not a fake packet,
and has no RuntimeContractError or failure.json precondition or fabricated result.
"""
from hashlib import sha256
import struct


def verify_prefix(con, public, action, identity, engine, validator, c):
    require, digest = c.require, c.digest
    require(con.execute('PRAGMA query_only').fetchone()[0] == 1, 'TIMEOUT_QUERY_ONLY_REQUIRED')
    require([tuple(r) for r in con.execute('PRAGMA integrity_check')] == [('ok',)], 'TIMEOUT_SQLITE_INTEGRITY')
    require(tuple(con.execute('SELECT value FROM store_metadata WHERE key=?', ('schema_version',)).fetchone())
        == ('cas.neural-cjt.sqlite-store/0.2',), 'TIMEOUT_STORE_SCHEMA')
    observations = {row['slot']: {'sha': sha256(struct.pack('<8f', *row['values'])).hexdigest(), 'tag': row['tag']}
        for row in public['observations']}
    artifacts_seen = set()
    def document(table, key, *, field='record_id'):
        require(table in {'model_versions', 'state_versions', 'commit_receipts', 'causes',
            'published_effects', 'candidate_effects', 'verifier_receipts'}, 'TIMEOUT_TABLE_NOT_ALLOWED')
        row = con.execute('SELECT * FROM '+table+' WHERE '+field+'=?', (key,)).fetchone()
        require(row is not None, 'TIMEOUT_DOCUMENT_MISSING')
        raw = row['payload_json']; value = c.decode(raw)
        require(c.canonical(value).decode() == raw and sha256(raw.encode()).hexdigest() == row['payload_sha256'],
            'TIMEOUT_DOCUMENT_HASH')
        return value, row
    def artifact(ref):
        row = con.execute('SELECT * FROM artifacts WHERE artifact_id=?', (ref['artifact_id'],)).fetchone()
        require(row is not None, 'TIMEOUT_ARTIFACT_MISSING')
        metadata = c.decode(row['metadata_json']); raw = bytes(row['payload'])
        header = {'encoding': row['encoding'], 'kind': row['kind'], 'media_type': row['media_type'],
            'metadata': metadata, 'payload_byte_length': len(raw)}
        checksum = sha256(c.canonical(header)+b'\n'+raw).hexdigest()
        require(c.canonical(metadata).decode() == row['metadata_json'] and row['sha256'] == checksum
            and row['artifact_id'] == 'artifact-'+checksum[:24] and ref['sha256'] == checksum
            and ref['encoding'] == row['encoding'] and ref['byte_length'] == len(raw), 'TIMEOUT_ARTIFACT_BINDING')
        artifacts_seen.add(row['artifact_id'])
        return sha256(raw).hexdigest()
    def units(plan):
        def total(value):
            if type(value) is list: return sum(total(item) for item in value)
            require(type(value) is int and value >= 0, 'TIMEOUT_PLAN_INTEGER')
            return value
        result = sum(total(plan[name]) for name in ('route_quanta', 'reasoning_step_quanta', 'branch_quanta',
            'memory_read_quanta', 'diagnostic_probe_quanta'))
        require(result > 0, 'TIMEOUT_ZERO_PLAN')
        return result
    model_digest = identity['model']['model_digest']
    model, _ = document('model_versions', model_digest, field='model_digest')
    require(model['model_digest'] == model_digest == identity['stored_model_digest']
        and model['model_artifact_ref']['sha256'] == model_digest and model['network'] == identity['topology']
        and artifact(model['model_artifact_ref']) == identity['model']['parameter_bytes_sha256'],
        'TIMEOUT_FIXED_MODEL_IDENTITY')
    rows, traces, effects, previous, previous_state = [], [], {}, None, None
    committed_units = 0
    for index, row in enumerate(con.execute('SELECT * FROM trace_events ORDER BY sequence')):
        trace = c.decode(row['payload_json']); validator.validate(trace)
        body = {k: v for k, v in trace.items() if k not in ('trace_digest', 'trace_id')}
        trace_id = 'trace-'+digest(body)[:24]
        require(row['sequence'] == index+1 and type(trace['tick']) is int and trace['tick'] == index+1
            and c.canonical(trace).decode() == row['payload_json']
            and sha256(row['payload_json'].encode()).hexdigest() == row['payload_sha256']
            and trace['trace_id'] == trace_id and trace['trace_digest'] == digest({**body, 'trace_id': trace_id})
            and trace['previous_trace_digest'] == previous
            and (previous_state is None or previous_state == trace['pre_state_digest'])
            and all(row[k] == trace[k] for k in ('trace_id', 'trace_digest', 'previous_trace_digest',
                'pre_state_digest', 'post_state_digest')), 'TIMEOUT_TRACE_CHAIN')
        require(trace['sealed'] is True and trace['pre_model_digest'] == trace['post_model_digest'] == model_digest
            and trace['software_digest'] == identity['software_digest']
            and [p.get('phase', p.get('name')) for p in trace['phases']] ==
            ['READ','CANDIDATE','READINESS','ROUTE','EXECUTE','OBSERVE','VERIFY','DIAGNOSE','EMIT','COMMIT','TRACE'],
            'TIMEOUT_TRACE_SOURCE_IDENTITY')
        receipt, rr = document('commit_receipts', trace['commit_receipt_id'], field='receipt_id')
        require(receipt['receipt_digest'] == digest({k: v for k, v in receipt.items() if k != 'receipt_digest'})
            and receipt['receipt_id'] == 'commit-'+rr['request_digest'][:24]
            and all(receipt[k] == rr[k] for k in ('receipt_id','batch_id','pre_state_digest','post_state_digest','rollback_of_receipt_id'))
            and all(receipt[k] == trace[k] for k in ('trace_id','tick','pre_state_digest','post_state_digest','pre_model_digest','post_model_digest'))
            and rr['trace_digest'] == trace['trace_digest'] and receipt['authorized'] is True
            and receipt['atomic'] is True and receipt['disposition'] == 'COMMITTED', 'TIMEOUT_COMMIT_RECEIPT')
        software = {'runtime_id': trace['runtime_id'], 'authority_contract_id': receipt['authority_contract_id'],
            'topology': identity['topology'], 'operation_contracts': identity['contracts'], 'decoders': identity['decoders']}
        require(digest(software) == identity['software_digest'], 'TIMEOUT_SOFTWARE_IDENTITY')
        ids = trace['published_effect_ids']
        require(len(ids) == 1 and ids == receipt['published_effect_ids'] and ids[0] not in effects, 'TIMEOUT_EFFECT_COUNT')
        effect, er = document('published_effects', ids[0])
        require(er['commit_receipt_id'] == receipt['receipt_id'] == effect['commit_receipt_id']
            and effect['published_effect_id'] == ids[0] and effect['tick'] == trace['tick']
            and effect['authoritative'] is True
            and effect['publication_digest'] == digest({k: v for k, v in effect.items() if k != 'publication_digest'}),
            'TIMEOUT_EFFECT_PUBLICATION')
        cause, cr = document('causes', trace['cause_id'])
        require(cr['commit_receipt_id'] == receipt['receipt_id'] and cause == trace['cause']
            and cause['tick'] == trace['tick'], 'TIMEOUT_CAUSE_BINDING')
        parent = cause['parent_effect_id']; input_sha = artifact(cause['content_ref'])
        if parent is None:
            slot = cause['content']['binding_slot']
            require(slot == action['binding'] and slot in observations and cause['content']['public_digest'] == digest(public)
                and cause['content']['binding_tag'] == observations[slot]['tag']
                and cause['content']['task'] == 'cas-meta2-observation' and input_sha == observations[slot]['sha'],
                'TIMEOUT_OBSERVATION_BINDING')
            input_node = -1
        else:
            require(parent in effects and input_sha == effects[parent]['sha']
                and cause['originating_cjt_id'] == effects[parent]['cjt'], 'TIMEOUT_EARLIER_EFFECT_BINDING')
            input_node = effects[parent]['index']
        require(len(trace['verifier_receipts']) == 1 and trace['verifier_receipts'][0]['disposition'] == 'ACCEPT'
            and trace['verifier_receipts'][0]['repair_required'] is False, 'TIMEOUT_ACCEPTED_PREFIX_ONLY')
        verifier, vr = document('verifier_receipts', trace['verifier_receipts'][0]['receipt_id'])
        require(verifier == trace['verifier_receipts'][0] and vr['commit_receipt_id'] == receipt['receipt_id']
            and verifier['independent'] is True and verifier['cause_id'] == cause['cause_id'], 'TIMEOUT_VERIFIER_BINDING')
        output_sha = artifact(effect['content_ref']); cjt = effect['producer_cjt_id']
        effects[ids[0]] = {'sha': output_sha, 'cjt': cjt, 'index': index}
        rows.append({'cjt_id': cjt, 'input_node': input_node, 'input_sha256': input_sha, 'output_sha256': output_sha})
        traces.append(trace); committed_units += units(trace['compute_plan'])
        for state_name, column in (('state_before', 'pre_state_digest'), ('state_after', 'post_state_digest')):
            state, _ = document('state_versions', trace[column], field='state_digest')
            require(state == trace[state_name] and digest({k: v for k, v in state.items() if k != 'state_digest'}) == trace[column]
                and state['model_digest'] == model_digest, 'TIMEOUT_STATE_IDENTITY')
        previous, previous_state = trace['trace_digest'], trace['post_state_digest']
    count = len(rows)
    require(con.execute('SELECT COUNT(*) FROM model_versions').fetchone()[0] == 1
        and con.execute('SELECT COUNT(*) FROM state_versions').fetchone()[0] == count+1, 'TIMEOUT_EXTRA_MODEL_OR_STATE')
    for table in ('commit_receipts', 'published_effects', 'causes', 'verifier_receipts'):
        require(con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] == count, 'TIMEOUT_UNACCOUNTED_COMMIT_DOCUMENT')
    heads = list(con.execute('SELECT * FROM active_head')); require(len(heads) == 1, 'TIMEOUT_HEAD_COUNT')
    head = heads[0]
    require(head['state_version'] == count and head['model_digest'] == model_digest
        and head['trace_digest'] == previous, 'TIMEOUT_FINAL_HEAD')
    final_state, _ = document('state_versions', head['state_digest'], field='state_digest')
    require(final_state['state_digest'] == head['state_digest']
        and digest({k: v for k, v in final_state.items() if k != 'state_digest'}) == head['state_digest']
        and final_state['state_version'] == count and final_state['model_digest'] == model_digest,
        'TIMEOUT_HEAD_STATE_DOCUMENT')
    if count:
        require(head['state_digest'] == previous_state and head['commit_receipt_id'] == traces[-1]['commit_receipt_id'], 'TIMEOUT_FINAL_HEAD')
    else:
        require(head['commit_receipt_id'] is None and final_state['previous_state_digest'] is None, 'TIMEOUT_INITIAL_HEAD')
    plan = engine.check_native_topology(action['program'])
    expected = [{k: r[k] for k in ('cjt_id', 'input_node')} for r in plan['runs']]
    actual = [{k: r[k] for k in ('cjt_id', 'input_node')} for r in rows]
    require(count < len(expected) and actual == expected[:count], 'TIMEOUT_SEALED_PROGRAM_PREFIX_MISMATCH')
    require(committed_units <= 32768 and count < 384, 'TIMEOUT_POLICY_BOUND')
    return {'committed_native_runs': count, 'committed_traces': len(traces),
        'committed_reserved_policy_units_lower_bound': committed_units,
        'scheduled_program_native_runs': len(expected), 'next_sealed_run': plan['runs'][count],
        'rows': rows, 'published_trace_schema_checked': True, 'committed_documents_checked': True,
        'model_parameter_bytes_hashed_not_loaded': True, 'software_model_and_public_input_bound': True,
        'sealed_program_prefix_checked': True, 'complete_execution_trace': False,
        'full_task_correctness': None, 'uncommitted_tick_compute': None, 'compute_complete': False,
        'checked_artifact_count': len(artifacts_seen),
        'boundary': 'Verified committed prefix from the copied database plus WAL. No failure.json was invented, '
            'no RuntimeContractError path was called, no unfinished tick was counted, and no final answer or '
            'completed-run verifier result was inferred. Policy units are reservations, not GPU FLOPs or billed time.'}
