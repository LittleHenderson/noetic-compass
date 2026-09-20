"""Read-only atlas projection after complete caller-anchored compound replay.

Navigation and evidence paging are pure. Recovery is imported only by the main
entry point and may repeat bounded construction; display budgets do not limit
that independent verification cost. Source attestations never become world
truth. Registry eligibility and next-action hints grant no execution authority.
"""
from __future__ import annotations

import json

from .canonical import canonical_json, content_id, digest
from .model import ContractError, TerminalStatus
from .rpa_model import AtlasContext, AtlasNode, AtlasLink, AtlasSnapshot, LinkType, NodeKind, NodeStatus

VIEW_SCHEMA = 'cncm.rpa-compound-view/0.1'
CATALOG_SCHEMA = 'cncm.rpa-compound-evidence/0.1'
CURSOR_SCHEMA = 'cncm.rpa-compound-cursor/0.1'
PAGE_SCHEMA = 'cncm.rpa-compound-page/0.1'
MAX_VIEW_BYTES = 32 * 1024 * 1024
MAX_PAGE_SIZE = 20
PRIMITIVE_CAPABILITY = 'cncm.solve-linear/0.1'


def _require(condition, reason):
    if not condition:
        raise ContractError(reason)


def _keys(value, keys, label):
    _require(type(value) is dict and set(value) == set(keys), label + ' fields invalid')


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _bounded(value):
    pending, nodes, text = [(value, 0)], 0, 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _require(nodes <= 1000000 and depth <= 50, 'compound atlas JSON structure limit exceeded')
        if type(item) is dict:
            _require(len(item) <= 4096 and all(type(k) is str for k in item), 'compound atlas JSON object invalid')
            text += sum(len(k) for k in item)
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            _require(len(item) <= 4096, 'compound atlas JSON list limit exceeded')
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            text += len(item)
        elif type(item) is int:
            _require(item.bit_length() <= 512, 'compound atlas JSON integer limit exceeded')
        else:
            _require(item is None or type(item) is bool, 'compound atlas requires exact JSON primitives')
        _require(text <= MAX_VIEW_BYTES, 'compound atlas display size limit exceeded')
    encoded = canonical_json(value)
    _require(len(encoded.encode()) <= MAX_VIEW_BYTES, 'compound atlas display size limit exceeded')
    return encoded


def _copy(value):
    return json.loads(canonical_json(value))


def _record_digest(row, body):
    return digest({'schema_version': row['schema_version'], 'kind': row['kind'], 'body': body})


def validate_evidence_catalog(catalog):
    """Validate immutable content identity, not historical or caller authority."""
    _bounded(catalog)
    _keys(catalog, ('schema_version', 'records', 'reports', 'catalog_digest'), 'evidence catalog')
    _require(catalog['schema_version'] == CATALOG_SCHEMA and _sha(catalog['catalog_digest']), 'evidence catalog version/digest invalid')
    _require(type(catalog['records']) is list and len(catalog['records']) <= 2560
             and type(catalog['reports']) is list and len(catalog['reports']) <= 2560, 'evidence catalog collections invalid')
    reports = {}
    for row in catalog['reports']:
        _keys(row, ('report_digest', 'digest_field', 'body'), 'catalog report')
        key, field, body = row['report_digest'], row['digest_field'], row['body']
        _require(_sha(key) and field in ('report_digest', 'report_sha256', 'receipt_digest')
                 and type(body) is dict and body.get(field) == key, 'catalog report identity invalid')
        _require(key == digest({k: v for k, v in body.items() if k != field}), 'catalog report seal mismatch')
        _require(key not in reports, 'duplicate catalog report')
        reports[key] = body
    seen = set()
    for row in catalog['records']:
        _keys(row, ('record_digest', 'schema_version', 'kind', 'body', 'report_refs'), 'catalog record')
        _require(_sha(row['record_digest']) and row['record_digest'] not in seen
                 and type(row['body']) is dict and type(row['report_refs']) is list and len(row['report_refs']) <= 2,
                 'catalog record identity invalid')
        _require(row['schema_version'] in ('cncm.compound-record/0.5', 'cncm.semantic-record/0.4', 'cncm.nested-record/0.3')
                 and type(row['kind']) is str, 'catalog record version/kind invalid')
        body = dict(row['body'])
        for binding in row['report_refs']:
            _keys(binding, ('field', 'report_digest'), 'catalog report reference')
            field, key = binding['field'], binding['report_digest']
            _require(field in ('report', 'receipt') and field not in body and key in reports, 'catalog report reference invalid')
            body[field] = reports[key]
        _require(_record_digest(row, body) == row['record_digest'], 'catalog original record digest mismatch')
        seen.add(row['record_digest'])
    _require([row['record_digest'] for row in catalog['records']] == sorted(seen)
             and [row['report_digest'] for row in catalog['reports']] == sorted(reports), 'catalog order invalid')
    _require(catalog['catalog_digest'] == digest({k: v for k, v in catalog.items() if k != 'catalog_digest'}), 'catalog digest mismatch')
    return _copy(catalog)


def record_body_from_catalog(catalog, record_digest):
    catalog = validate_evidence_catalog(catalog)
    row = next((r for r in catalog['records'] if r['record_digest'] == record_digest), None)
    _require(row is not None, 'catalog record not found')
    reports = {r['report_digest']: r['body'] for r in catalog['reports']}
    body = row['body']
    for binding in row['report_refs']:
        body[binding['field']] = reports[binding['report_digest']]
    return body


def _catalog(records):
    catalog_records, reports = {}, {}
    for record in records:
        wire, body = record.to_dict(), record.body_dict()
        refs = []
        for field in ('report', 'receipt'):
            report = body.get(field)
            if type(report) is not dict:
                continue
            seals = [name for name in ('report_digest', 'report_sha256', 'receipt_digest') if name in report]
            _require(len(seals) == 1, 'source report has no unique content seal')
            key, seal = report[seals[0]], seals[0]
            entry = {'report_digest': key, 'digest_field': seal, 'body': report}
            _require(key not in reports or reports[key] == entry, 'source reports disagree at same digest')
            reports[key] = entry
            refs.append({'field': field, 'report_digest': key})
            del body[field]
        row = {'record_digest': record.record_digest, 'schema_version': wire['schema_version'],
               'kind': record.kind, 'body': body, 'report_refs': refs}
        _require(record.record_digest not in catalog_records or catalog_records[record.record_digest] == row, 'source records disagree')
        catalog_records[record.record_digest] = row
    result = {'schema_version': CATALOG_SCHEMA, 'records': [catalog_records[k] for k in sorted(catalog_records)],
              'reports': [reports[k] for k in sorted(reports)]}
    result['catalog_digest'] = digest(result)
    return validate_evidence_catalog(result)


def _cursor(view, record_digest, report_digest, start, count, total):
    body = {'schema_version': CURSOR_SCHEMA, 'journal_digest': view['native']['journal_digest'],
            'catalog_digest': view['native']['evidence_catalog']['catalog_digest'], 'record_digest': record_digest,
            'report_digest': report_digest, 'start': start, 'count': count, 'total': total}
    return body | {'cursor_digest': digest(body)}


def candidate_page(view, record_digest, *, start=None, count=None, cursor=None):
    """Pure, digest-bound display slice. Deferred candidates are not negatives."""
    _require(type(view) is dict and view.get('schema_version') == VIEW_SCHEMA, 'compound view required for paging')
    _require((start is None or type(start) is int) and (count is None or type(count) is int), 'candidate display page raw type invalid')
    _require(type(view.get('native')) is dict and 'evidence_catalog' in view['native'], 'candidate page native binding missing')
    _require(_sha(view['native'].get('journal_digest')), 'candidate page journal identity invalid')
    body = record_body_from_catalog(view['native']['evidence_catalog'], record_digest)
    report = body.get('report')
    _require(type(report) is dict and report.get('schema_version') == 'cncm.compound-construction/0.1', 'record is not a construction report')
    candidates, report_digest = report['candidates'], report['report_digest']
    _require(type(candidates) is list and type(report['candidate_count']) is int
             and len(candidates) == report['candidate_count'] and 1 <= len(candidates) <= 420, 'candidate report count mismatch')
    total = len(candidates)
    if cursor is not None:
        _keys(cursor, ('schema_version', 'journal_digest', 'catalog_digest', 'record_digest', 'report_digest',
                       'start', 'count', 'total', 'cursor_digest'), 'candidate cursor')
        _require(type(cursor['schema_version']) is str and cursor['schema_version'] == CURSOR_SCHEMA
                 and all(_sha(cursor[key]) for key in ('journal_digest', 'catalog_digest', 'record_digest', 'report_digest', 'cursor_digest')),
                 'candidate cursor identity fields invalid')
        _require(all(type(cursor[key]) is int for key in ('start', 'count', 'total'))
                 and 0 <= cursor['start'] <= total and 1 <= cursor['count'] <= MAX_PAGE_SIZE and cursor['total'] == total,
                 'candidate cursor numeric fields invalid')
        _require((start is None or start == cursor['start']) and (count is None or count == cursor['count']), 'cursor and requested page disagree')
        start, count = cursor['start'], cursor['count']
        _require(cursor == _cursor(view, record_digest, report_digest, start, count, total), 'candidate cursor is stale or foreign')
    start, count = (0 if start is None else start), (MAX_PAGE_SIZE if count is None else count)
    _require(type(start) is int and 0 <= start <= total and type(count) is int and 1 <= count <= MAX_PAGE_SIZE, 'candidate display page bound invalid')
    stop = min(start + count, total)
    return {'schema_version': PAGE_SCHEMA, 'journal_digest': view['native']['journal_digest'],
        'catalog_digest': view['native']['evidence_catalog']['catalog_digest'], 'record_digest': record_digest,
        'report_digest': report_digest, 'start': start, 'count': count, 'returned': stop - start, 'total': total,
        'items': [{'index': index, 'candidate': _copy(candidates[index])} for index in range(start, stop)],
        'deferred': {'before': [0, start], 'after': [stop, total]},
        'next_cursor': _cursor(view, record_digest, report_digest, stop, count, total) if stop < total else None}


def _actual(report):
    result = {'primitive_instructions': 0, 'original_checks': 0, 'linear_checks': 0}
    if type(report) is not dict:
        return result
    if 'actual_work' in report:
        result.update(report['actual_work'])
    elif type(report.get('cost')) is dict:
        result['primitive_instructions'] = report['cost'].get('instructions_executed', 0)
        result['linear_checks'] = report['cost'].get('checker_calls', 0)
    return result


def work_from_catalog(catalog, work_record_digests, event):
    """Pure exact event-work join; a later stale proposal cannot reuse a debit."""
    checked = validate_evidence_catalog(catalog)
    _require(type(event) is dict and type(event.get('run_id')) is str
             and type(event.get('logical_tick')) is int and event['logical_tick'] >= 1
             and type(event.get('proposed_intents')) is list, 'work event binding invalid')
    _require(all(type(row) is dict and type(row.get('intent_id')) is str for row in event['proposed_intents']), 'work event intents invalid')
    ids = {row['intent_id'] for row in event['proposed_intents']}
    selected = {row['record_digest']: row for row in checked['records'] if row['kind'] == 'WORK_RESERVATION'
                and row['body'].get('run_id') == event['run_id']
                and row['body'].get('tick') == event['logical_tick'] - 1 and row['body'].get('intent_id') in ids}
    _require(type(work_record_digests) is list and work_record_digests == sorted(selected), 'work records do not exactly bind this event')
    reports = {row['report_digest']: row['body'] for row in checked['reports']}
    result = {'instructions_allocated': 0, 'checker_calls_allocated': 0,
              'primitive_instructions': 0, 'original_checks': 0, 'linear_checks': 0, 'basis': 'conservative_policy_units'}
    for row in selected.values():
        body = row['body']
        for key in ('instructions_allocated', 'checker_calls_allocated'):
            _require(type(body.get(key)) is int and body[key] >= 0, 'work allocation invalid')
            result[key] += body[key]
        report = next((reports[binding['report_digest']] for binding in row['report_refs'] if binding['field'] in ('report', 'receipt')), None)
        for key, value in _actual(report).items():
            _require(type(value) is int and value >= 0, 'actual work count invalid')
            result[key] += value
    return result


def _dispatch(state):
    primitive_head = dict(state.procedure_heads).get(PRIMITIVE_CAPABILITY)
    program = next((row for row in state.compound_artifacts if row.program_digest == state.compound_head), None)
    pinned = program.primitive_sha256 if program else None
    present = any(row.artifact_sha256 == pinned for row in state.procedural_artifacts)
    blockers = []
    if state.compound_head is None: blockers.append('NO_ACTIVE_COMPOUND_HEAD')
    elif program is None: blockers.append('ACTIVE_COMPOUND_ARTIFACT_MISSING')
    if primitive_head is None: blockers.append('NO_ACTIVE_PRIMITIVE_HEAD')
    if program and not present: blockers.append('PINNED_PRIMITIVE_ARTIFACT_MISSING')
    if program and primitive_head != pinned: blockers.append('PINNED_PRIMITIVE_NOT_AUTHORIZED')
    return {'compound_head': state.compound_head, 'primitive_head': primitive_head, 'program_present': program is not None,
        'pinned_primitive_sha256': pinned, 'primitive_present': present, 'pin_matches_current_head': pinned is not None and pinned == primitive_head,
        'eligible': not blockers, 'blockers': blockers}


def proposed_next_actions(machine):
    """Read coordinator proposals, never advance or publish a state mutation."""
    from .compound_profile import COMPOUND_WORK_COSTS
    from .semantic_profile import SEMANTIC_WORK_COSTS
    state = machine.state
    before = canonical_json(machine.journal())
    blockers, proposal = [], None
    if state.halt_status is not TerminalStatus.RUNNING:
        action = 'START_NEW_EPISODE'
        blockers = ['UNRESOLVED_ACQUISITION_FRAME'] if state.rpm_stack else ['SEPARATE_TRUSTED_HOST_OPERATION']
    elif state.memory_failure is not None:
        action = 'HALT'
        blockers = [state.memory_failure]
    elif state.commitment_state.decision_status == 'COMMITTED':
        action = 'HALT'
    else:
        proposal = machine.coordinator.next_intent()
        if proposal is not None:
            action = proposal.intent_type.value
            if action == 'FAIL_COMPOUND': blockers.append(proposal.mutation_dict()['reason'])
        else:
            action = 'HALT' if state.compound_call and state.compound_call.status == 'FAILED' else 'ORDINARY_REASONING_AND_COMMITMENT_GATES'
            if state.compound_call and state.compound_call.failure: blockers.append(state.compound_call.failure)
    cost = COMPOUND_WORK_COSTS.get(action, SEMANTIC_WORK_COSTS.get(action, (0, 0)))
    if action == 'CONSTRUCT_COMPOUND': cost = (machine.problem.construction_limit * 96, machine.problem.construction_limit * 4)
    if state.native_budget.instructions_remaining < cost[0]: blockers.append('INSUFFICIENT_INSTRUCTION_ALLOCATION')
    if state.native_budget.checker_calls_remaining < cost[1]: blockers.append('INSUFFICIENT_CHECKER_ALLOCATION')
    if state.budget.ticks_remaining <= 1 and action not in ('HALT', 'START_NEW_EPISODE'): blockers.append('LAST_TICK_RESERVED_FOR_HALT')
    _require(canonical_json(machine.journal()) == before, 'next-action projection mutated recovered journal')
    return [{'action': action, 'readiness': 'blocked' if blockers else 'necessary_conditions_present',
        'blockers': blockers, 'authority': 'PROPOSAL_ONLY', 'proposal': proposal.to_dict() if proposal else None,
        'policy_cost': {'instructions': cost[0], 'checker_calls': cost[1]}}]


def compound_atlas_from_journal(journal, *, trusted_genesis, trusted_ingress, expected_journal_digest,
                                trusted_ingress_extensions=(), profile=None):
    from .compound_recovery import recover_compound_journal
    machine = recover_compound_journal(journal, trusted_genesis=trusted_genesis, trusted_ingress=trusted_ingress,
        expected_journal_digest=expected_journal_digest, trusted_ingress_extensions=trusted_ingress_extensions, profile=profile)
    verified, state, problem = machine.journal(), machine.state, machine.problem
    records = (*state.native_records, *state.semantic_records, *state.compound_records)
    catalog = _catalog(records)
    nodes, links, timeline = {}, {}, []

    def context(run, tick, observation):
        return AtlasContext(run, VIEW_SCHEMA, 'observation-' + observation, 'logical-tick:' + str(tick), tick)

    current_context = context(state.run_id, state.logical_tick, state.state_hash)

    def node(key, label, *, fields=None, ctx=current_context, kind='idea_context', status='observed', evidence=(), idea=None, members=None, expansion=None):
        value = AtlasNode(key, idea or key, label, ctx, NodeStatus(status),
            fields=tuple(sorted((k, v if type(v) is str else canonical_json(v)) for k, v in (fields or {}).items())),
            members=members, kind=NodeKind(kind), evidence_refs=tuple(sorted(set(evidence))), expansion_ref=expansion)
        _require(key not in nodes or nodes[key] == value, 'atlas node identity collision')
        nodes[key] = value
        _require(len(nodes) <= 512, 'compound atlas node display limit exceeded; source is not truncated')
        return key

    def link(source, target, relation='contains_part', *, projection='evidence projection', evidence=(), action=None, transition=None):
        identity = dict(source=source, target=target, relation=relation, action=action)
        row = AtlasLink(content_id('rpa-link', identity), source, target, LinkType(relation),
            projection=projection if relation == 'contains_part' else None, action_id=action,
            evidence_refs=tuple(sorted(set(evidence))), transition_status=transition)
        links[row.link_id] = row
        _require(len(links) <= 2048, 'compound atlas link display limit exceeded; source is not truncated')

    state_id = lambda value: 'state-' + value
    work_rows = [(row, row.body_dict()) for row in records if row.kind == 'WORK_RESERVATION']
    previous = None
    for episode_index, episode in enumerate(verified['episodes']):
        run = episode['final_state']['run_id']; initial = episode['initial_state_hash']
        node(state_id(initial), 'Episode genesis', ctx=context(run, 0, initial), kind='state',
             fields={'state_hash': initial, 'run_id': run, 'episode_index': episode_index}, evidence=(expected_journal_digest,))
        if previous: link(state_id(previous), state_id(initial), 'reachable_via', action='START_NEW_EPISODE', transition='observed', evidence=(expected_journal_digest,))
        for event, batch in zip(episode['trace'], episode['proposal_batches'], strict=True):
            ids = {row['intent_id'] for row in event['proposed_intents']}
            charged = {row.record_digest: body for row, body in work_rows
                       if body['run_id'] == run and body['tick'] == event['logical_tick'] - 1 and body['intent_id'] in ids}
            work = {'instructions_allocated': 0, 'checker_calls_allocated': 0, 'primitive_instructions': 0,
                    'original_checks': 0, 'linear_checks': 0, 'basis': 'conservative_policy_units'}
            for body in charged.values():
                for key in ('instructions_allocated', 'checker_calls_allocated'): work[key] += body[key]
                for key, count in _actual(body.get('report', body.get('receipt'))).items(): work[key] += count
            action = '+'.join(row['intent_type'] for row in event['proposed_intents']) or 'EMPTY_BATCH'
            outcome = 'PARTIALLY_ACCEPTED' if event['authorized_intent_ids'] and event['rejected_intents'] else ('REJECTED' if event['rejected_intents'] else 'ACCEPTED')
            target = node(state_id(event['post_state_hash']), 'Tick ' + str(event['logical_tick']) + ': ' + action[:350],
                ctx=context(run, event['logical_tick'], event['post_state_hash']), kind='state',
                fields={'state_hash': event['post_state_hash'], 'run_id': run, 'event_hash': event['event_hash'], 'outcome': outcome, 'work': work}, evidence=(event['event_hash'],))
            link(state_id(event['pre_state_hash']), target, 'reachable_via', action=content_id('action', action),
                 transition='rejected' if outcome == 'REJECTED' else 'observed', evidence=(event['event_hash'],))
            timeline.append({'episode_index': episode_index, 'event': _copy(event), 'proposal_batch': _copy(batch),
                             'work_record_digests': sorted(charged), 'work': work})
        previous = episode['final_state']['state_hash']
    current_id = state_id(state.state_hash)
    call = state.compound_call
    call_fields = {'variable': problem.variable, 'goal_id': problem.reasoning.goal_id, 'branch_id': 'branch-main',
        'input_hash': problem.input_hash, 'stage': call.status if call else 'NOT_REQUESTED', 'family': 'a*(b*x+c)+d=e'}
    call_node = node('current-call', 'Original compound caller', fields=call_fields, members=('bound-call',), evidence=(expected_journal_digest,))
    link(current_id, call_node, projection='compound problem and current caller')
    detail = node('current-call-detail', 'Bound caller inputs and result', fields=call_fields | {
        'call': call.to_dict() if call else None, 'memory_resolution_digest': state.memory_resolution_digest,
        'source_profile_digest': machine.profile.profile_digest}, members=('bound-call',), idea='current-call', evidence=(expected_journal_digest,))
    link(call_node, detail, 'refines_state', evidence=(expected_journal_digest,))
    for key, value in problem.parameters:
        reference = hasattr(value, 'to_dict')
        target = node('parameter-' + key, 'Original parameter ' + key, fields={'name': key, 'value': value.to_dict() if hasattr(value, 'to_dict') else value,
            'evidence_boundary': 'reference or original literal; source attestation is not factual verification'}, evidence=(problem.input_hash,),
            idea=content_id('source-idea', {'scope': value.scope, 'key': value.key}) if reference else None)
        link(call_node, target, projection='original parameter:' + key)
    source_heads = {}
    for statement in state.memory_statements:
        source_heads[(statement.scope, statement.key, statement.source_id)] = statement
        target = node('source-' + statement.statement_digest, 'Source ' + statement.action.lower() + ': ' + statement.key,
            kind='evidence', fields=statement.to_dict() | {'statement_digest': statement.statement_digest, 'factual_status': 'NOT_INDEPENDENTLY_VERIFIED'},
            evidence=(statement.statement_digest,), idea=content_id('source-idea', {'scope': statement.scope, 'key': statement.key}))
        link(current_id, target, projection='retained admitted source statement')
        if statement.previous_digest:
            link('source-' + statement.previous_digest, target, 'reachable_via', action='RETRACT_SOURCE' if statement.action == 'RETRACT' else 'CORRECT_SOURCE',
                 transition='observed', evidence=(statement.statement_digest,))
    for index, binding in enumerate(state.memory_bindings):
        target = node('binding-' + str(index), 'Scoped source recall: ' + binding.ref.key, kind='evidence', fields=binding.to_dict(),
                      evidence=(binding.receipt_digest,), idea=content_id('source-idea', {'scope': binding.ref.scope, 'key': binding.ref.key}))
        link(call_node, target, projection='current recall binding')
        for key, value in problem.parameters:
            if value == binding.ref:
                link('parameter-' + key, target, 'references_same_idea', evidence=(binding.receipt_digest,))
        for source_digest in binding.statement_digests:
            link(target, 'source-' + source_digest, 'references_same_idea', evidence=(binding.receipt_digest, source_digest))
    dispatch = _dispatch(state)
    program_nodes = {}
    for program in state.compound_artifacts:
        key = node('program-' + program.program_digest, 'Retained compound call program', kind='evidence',
            fields={'program_digest': program.program_digest, 'primitive_sha256': program.primitive_sha256,
                    'active_head': program.program_digest == state.compound_head, 'historical_installation_is_not_dispatch': True}, evidence=(program.program_digest,))
        program_nodes[program.program_digest] = key
        link(current_id, key, projection='retained compound registry artifact')
        if call is not None and call.artifact_sha256 == program.program_digest:
            link(call_node, key, projection='current caller exact program pin', evidence=(program.program_digest, call.inputs_digest))
        for index, step in enumerate(program.steps):
            target = node(content_id('step', {'program': program.program_digest, 'index': index}), 'Primitive call step ' + str(index),
                fields={'index': index, **step.to_dict(), 'primitive_sha256': program.primitive_sha256}, evidence=(program.program_digest,))
            link(key, target, projection='program call step:' + str(index))
    for primitive in state.procedural_artifacts:
        target = node('primitive-' + primitive.artifact_sha256, 'Retained primitive dependency', kind='evidence',
            fields={'artifact': primitive.to_dict(), 'active_head': primitive.artifact_sha256 == dispatch['primitive_head']}, evidence=(primitive.artifact_sha256,))
        link(current_id, target, projection='retained primitive artifact')
        for program in state.compound_artifacts:
            if program.primitive_sha256 == primitive.artifact_sha256:
                link(program_nodes[program.program_digest], target, projection='exact pinned primitive dependency', evidence=(program.program_digest, primitive.artifact_sha256))
    for index, frame in enumerate(state.rpm_stack):
        target = node('frame-' + frame.frame_id, 'Saved acquisition frame ' + str(index + 1), fields=frame.to_dict(), evidence=(frame.parent_call_digest, frame.parent_branch_digest))
        link(current_id, target, projection='saved continuation:' + str(index))
    for row in catalog['records']:
        target = node('record-' + row['record_digest'], row['kind'].replace('_', ' ').title(), kind='evidence',
            fields={'record_digest': row['record_digest'], 'kind': row['kind'], 'run_id': row['body']['run_id'],
                    'tick': row['body']['tick'], 'catalog_digest': catalog['catalog_digest'], 'report_refs': row['report_refs']},
            evidence=(row['record_digest'],), expansion='evidence-catalog:' + row['record_digest'])
        link(current_id, target, projection='immutable history record', evidence=(row['record_digest'],))
    reports = {row['report_digest']: row['body'] for row in catalog['reports']}
    candidate_reports = []
    for key, report in sorted(reports.items()):
        if report.get('schema_version') == 'cncm.compound-construction/0.1':
            refs = [row['record_digest'] for row in catalog['records'] if any(item['report_digest'] == key for item in row['report_refs'])]
            candidate_reports.append({'report_digest': key, 'record_digests': refs, 'total': len(report['candidates']), 'page_size': MAX_PAGE_SIZE})
    current_work = [row['work'] for row in timeline if row['event']['run_id'] == state.run_id]
    budget = {'episode_limits': problem.budget.to_dict(), 'remaining': state.native_budget.to_dict(),
        'ordinary_ticks_remaining': state.budget.ticks_remaining,
        'allocated_this_episode': {'instructions': sum(w['instructions_allocated'] for w in current_work), 'checker_calls': sum(w['checker_calls_allocated'] for w in current_work)},
        'actual_work_observed': {key: sum(w[key] for w in current_work) for key in ('primitive_instructions', 'original_checks', 'linear_checks')},
        'units': 'CONSERVATIVE_POLICY_UNITS_NOT_FLOPS'}
    for key, label, fields in [('current-budget', 'Remaining and spent work', budget), ('current-dispatch', 'Current dependency eligibility', dispatch)]:
        link(current_id, node(key, label, fields=fields, evidence=(expected_journal_digest,)), projection=key)
    hints = proposed_next_actions(machine)
    for index, hint in enumerate(hints):
        target = node('proposal-' + str(index), hint['action'], status='hypothetical', fields=hint)
        link(current_id, target, 'reachable_via', action=hint['action'], transition='candidate')
    atlas = AtlasSnapshot(tuple(nodes.values()), tuple(links.values()), current_id, current_id,
                          'proposal-0' if hints else None)
    native = {'runtime_version': state.runtime_version, 'source_profile_digest': machine.profile.profile_digest,
        'journal_digest': expected_journal_digest, 'ingress_digest': state.ingress_digest, 'current_state_hash': state.state_hash,
        'terminal_status': state.halt_status.value, 'conditional_output': call.output if call else None,
        'claim_status': 'CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS', 'authority': 'DISPLAY_ONLY',
        'current_call': call.to_dict() if call else None, 'frames': [row.to_dict() for row in state.rpm_stack],
        'current_program': next((row.to_dict() for row in state.compound_artifacts if row.program_digest == state.compound_head), None),
        'parameters': problem.to_dict()['parameters'], 'source_bindings': [row.to_dict() for row in state.memory_bindings],
        'dispatch': dispatch, 'budget': budget,
        'source_heads': [row.to_dict() | {'statement_digest': row.statement_digest} for _, row in sorted(source_heads.items())],
        'evidence_catalog': catalog, 'candidate_reports': candidate_reports,
        'scope': 'Read-only replayed evidence. Source statements are attestations; arithmetic is conditional. No general synthesis, independent factual verification, measured CAS profile, probability, native neural flow or write authority is supplied.'}
    result = {'schema_version': VIEW_SCHEMA, 'atlas': atlas.to_dict(), 'native': native, 'timeline': timeline, 'next_actions': hints}
    _bounded(result)
    return result
