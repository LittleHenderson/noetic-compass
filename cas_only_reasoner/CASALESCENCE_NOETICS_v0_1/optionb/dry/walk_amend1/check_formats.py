"""[MADE-UP DATA WALK, NOT A RESULT] Compare the files the tools wrote in the scratch project with FILE_FORMATS.md.

The field lists below were typed from the tables of FILE_FORMATS.md (sections 2 to 12 and 15) by the walker.
For each file: the three header fields, the schema name, the exact set of top-level fields, the exact set of
fields of each row, UTF-8, LF only, no byte-order mark, one LF at the end, and no decimal number.
It prints one line per file: OK, or what differs. It reads only files under optionb/dry/walk_amend1/.

Usage: python -B check_formats.py <project folder name> [part of a path ...]
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
S = 'casalescence/optionb/'
HEAD = ['schema', 'made_by', 'inputs']
CALL = ['utc', 'set', 'pass', 'model', 'model_in_reply', 'wave', 'batch', 'attempt', 'http_status', 'passage_ids', 'prompt_sha256', 'reply_sha256',
        'ok', 'error', 'usage', 'prompt', 'reply']
QUESTION = ['question_id', 'form', 'question', 'right', 'wrong', 'anchors']
TASK = ['task_id', 'passage_id', 'question_id', 'family', 'type', 'form', 'question', 'right', 'wrong', 'anchors', 'anchors_matched',
        'right_is_single_longest', 'right_is_single_shortest']

# name pattern -> (schema, top-level fields besides the header, {path of a list: exact fields of its rows})
JSON_FILES = {
    'elig/exclusions.json': (S + 'exclusions/v1', ['count', 'by_kind', 'passages'], {'passages': ['id', 'kind', 'reasons']}),
    'elig/eligibility.json': (S + 'eligibility/v1', ['practice_settings', 'reserve_settings_in_order', 'counts', 'counts_match_plan', 'passages'],
                              {'passages': ['id', 'kind', 'setting', 'text', 'setting_role', 'writer_asks', 'excluded', 'barred', 'eligible', 'agreed', 'only_a',
                                            'only_b', 'open_forms', 'open_types', 'max_role_step_tasks', 'leftover_on_type', 'any_leftover_2_to_9', 'entries']}),
    'notes_role/role_notes.json': (S + 'role_notes/v1', ['canon', 'passages'],
                                   {'passages': ['id', 'entries', 'role_text', 'mixed_text', 'quotes_only_text', 'frame_blanked', 'size', 'left_out'],
                                    'passages.entries': ['noetic', 'name', 'mixed_noetic', 'mixed_name', 'label', 'mind', 'relative_to', 'supporting_quote',
                                                         'same_as_label', 'offset', 'a_index', 'b_index']}),
    'notes_role/owner_sample_20.json': (S + 'owner_role_note_sample/v1', ['seed', 'passages'], {'passages': ['id', 'text', 'role_text', 'left_out']}),
    'questions/writer_state_': (S + 'writer_state/v1', ['set', 'pass', 'model', 'seed', 'waves', 'cap_stops_utc', 'complete'],
                                {'waves': ['wave', 'settings', 'batches'], 'waves.batches': ['batch', 'passage_ids', 'status', 'attempts']}),
    'questions/raw_questions_': (S + 'raw_questions/v1', ['set', 'pass', 'model', 'passages'],
                                 {'passages': ['passage_id', 'wave', 'batch', 'status', 'what_follows', 'plain_fact', 'extra_dropped'],
                                  'passages.what_follows': QUESTION}),
    'checks/form_check_': (S + 'form_check/v1', ['set', 'rows', 'counts'], {'rows': ['question_id', 'family', 'passed', 'reasons']}),
    'checks/anchor_check_': (S + 'anchor_check/v1', ['set', 'rows', 'counts'], {'rows': ['question_id', 'passed', 'reason', 'matched'],
                                                                                'rows.matched': ['anchor', 'noetic', 'agreed_index', 'field']}),
    'checks/option_check_': (S + 'option_check/v1', ['set', 'rows', 'counts'], {'rows': ['question_id', 'passed', 'hits'],
                                                                                'rows.hits': ['option_index', 'option', 'noetic', 'team', 'entry_index', 'field']}),
    'checks/candidates_': (S + 'candidates/v1', ['set', 'candidates', 'counts'],
                           {'candidates': ['question_id', 'passage_id', 'family', 'form', 'pass', 'passage', 'question', 'right', 'wrong', 'anchors']}),
    'solve/solver_items_': (S + 'solver_items/v1', ['set', 'items'], {'items': ['item_id', 'solver', 'mode', 'sheet', 'question_id', 'shown', 'right_letter']}),
    'solve/solver_answers_': (S + 'solver_answers/v1', ['set', 'answers'],
                              {'answers': ['item_id', 'solver', 'mode', 'question_id', 'raw', 'readable', 'picked_option_index', 'flag', 'source_sha256', 'model_in_reply']}),
    'solve/key_check_': (S + 'key_check/v1', ['set', 'rows', 'counts'],
                         {'rows': ['question_id', 'family', 'with_passage', 'key_check_passed', 'no_passage', 'no_passage_passed', 'survives']}),
    'select/selection_practice': (S + 'selection/v1', ['set', 'practice_setting_count', 'tasks', 'dropped', 'counts', 'floor', 'reserve'],
                                  {'tasks': TASK, 'dropped': ['question_id', 'reason']}),
    'select/selection_final': (S + 'selection/v1', ['set', 'practice_setting_count', 'tasks', 'dropped', 'counts'], {'tasks': TASK, 'dropped': ['question_id', 'reason']}),
    'select/split_fixed.json': (S + 'split_fixed/v1', ['practice_setting_count', 'practice_settings', 'final_settings', 'history', 'reserve_target_met',
                                                       'floor_met', 'final_writer_passage_ids'],
                                {'history': ['practice_setting_count', 'practice_role_step_tasks', 'practice_plain_fact_tasks', 'target_met']}),
}
JSONL_FILES = {
    'questions/writer_calls_': CALL,
    'solve/deepseek_calls_': ['utc', 'item_id', 'mode', 'question_id', 'model', 'model_in_reply', 'usage', 'http_status', 'ok', 'error', 'prompt_sha256',
                              'reply_sha256', 'prompt', 'reply'],
}
MORE = HERE / 'check_formats_more.json'
if MORE.exists():
    extra = json.loads(MORE.read_text(encoding='utf-8'))
    JSON_FILES.update({k: tuple(v) for k, v in extra.get('json', {}).items()})
    JSONL_FILES.update(extra.get('jsonl', {}))


def has_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(has_float(v) for v in value.values())
    if isinstance(value, list):
        return any(has_float(v) for v in value)
    return False


def rows_at(doc, path):
    nodes = [doc]
    for part in path.split('.'):
        nxt = []
        for node in nodes:
            value = node.get(part) if isinstance(node, dict) else None
            if isinstance(value, list):
                nxt += [v for v in value if isinstance(v, dict)]
            elif isinstance(value, dict):
                nxt.append(value)
        nodes = nxt
    return nodes


def check_bytes(data):
    out = []
    if b'\r' in data:
        out.append('holds a CR')
    if data.startswith(b'\xef\xbb\xbf'):
        out.append('has a byte-order mark')
    if not data.endswith(b'\n') or data.endswith(b'\n\n'):
        out.append('does not end with exactly one LF')
    return out


def main():
    project = HERE / sys.argv[1] / 'optionb'
    wanted = sys.argv[2:]
    seen, bad = 0, 0
    for path in sorted(p for p in project.rglob('*') if p.is_file()):
        relative = path.relative_to(project).as_posix()
        if relative.startswith(('job/', 'dry/')) or (wanted and not any(w in relative for w in wanted)):
            continue
        data = path.read_bytes()
        problems = check_bytes(data)
        spec = next((v for k, v in JSON_FILES.items() if relative.startswith(k)), None)
        log = next((v for k, v in JSONL_FILES.items() if relative.startswith(k)), None)
        if spec:
            doc = json.loads(data.decode('utf-8'))
            schema, top, lists = spec
            if list(doc)[:3] != HEAD:
                problems.append('does not start with schema, made_by, inputs: %s' % list(doc)[:3])
            if doc.get('schema') != schema:
                problems.append('schema is %r, the formats file says %r' % (doc.get('schema'), schema))
            if sorted(doc.get('made_by', {})) != ['program', 'sha256', 'utc'] or not isinstance(doc.get('inputs'), list):
                problems.append('made_by or inputs does not have the form of section 0')
            have = [k for k in doc if k not in HEAD]
            if sorted(have) != sorted(top):
                problems.append('top-level fields: extra %s, missing %s' % (sorted(set(have) - set(top)), sorted(set(top) - set(have))))
            for where, fields in lists.items():
                rows = rows_at(doc, where)
                odd = {tuple(sorted(set(r) ^ set(fields))) for r in rows if set(r) != set(fields)}
                if odd:
                    problems.append('rows of %s: fields that differ from the formats file: %s' % (where, sorted(odd)[:3]))
            if has_float(doc):
                problems.append('holds a decimal number')
        elif log:
            rows = [json.loads(line) for line in data.decode('utf-8').split('\n') if line.strip()]
            odd = {tuple(sorted(set(r) ^ set(log))) for r in rows if set(r) != set(log)}
            if odd:
                problems.append('lines with fields that differ from the formats file: %s' % sorted(odd)[:3])
            order = [list(r) for r in rows if list(r) != log]
            if not odd and order:
                problems.append('field order differs from the formats file in %d lines (first: %s)' % (len(order), order[0]))
        elif relative.endswith(('.json', '.jsonl')) and relative != 'PLAN_CONSTANTS.json':
            problems.append('NO FORMAT TYPED IN FOR THIS FILE (checked bytes only)')
        seen += 1
        bad += bool(problems)
        print('%-52s %8d bytes  %s' % (relative, len(data), 'OK' if not problems else 'DIFFERS: ' + ' | '.join(problems)))
    print('files looked at: %d; with a difference: %d' % (seen, bad))


if __name__ == '__main__':
    main()
