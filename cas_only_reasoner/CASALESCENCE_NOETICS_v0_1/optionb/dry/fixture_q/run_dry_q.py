"""[DRY FIXTURE, NOT A RESULT] Dry run of the four question tools on three made-up passages.

Tools walked through, with no outside call and no key:
  tools/ob_write_questions.py   tools/ob_check_questions.py
  tools/ob_solve_blind.py       tools/ob_select.py

Everything in this folder is made up: the passages and their label entries (elig/eligibility.json),
the writer replies and the DeepSeek replies (replay/), the answer sheets of the Claude sub-agent
(written by this script from the lists below) and the model names. Nothing here is a case. Nothing
here is a result.

What this script does:
  1. It removes what an earlier walk wrote in this folder (questions/, checks/, solve/, select/,
     stop_case/). It keeps elig/ and the hand-written reply files in replay/.
  2. It runs the four tools in this folder (--work), feeding the made-up replies through
     --replay-replies, in the order of a real build: practice with 8 settings, the reserve rule,
     practice with 9 settings, the split, then the final set.
  3. It checks what each tool did against what was expected, and writes dry_run_log.json.

What the walk shows for the amendments of 2026-10-05:
  A1   one writer model for both sets; a refused call (HTTP 429) stops the writer at once.
  A3   the import step needs the model name from the sub-agent transcript and stores it.
       Operator decision C3 of 2026-10-05, round 3: the import step takes a sheet only when that
       name is exactly the pinned model id. So this walk gives the pinned id, read from the plan
       constants. With another name (a made-up one) the step must stop with
       TRANSCRIPT_MODEL_NOT_THE_PINNED_ID and store nothing.
  A8   the reserve rule. With 8 practice settings the made-up practice set meets both launch floors
       and misses a reserve target. The writer must then add the wave of reserve setting 1. It reads
       the block reserve of select/selection_practice.json and not floor.met.
  A9   every call log line holds the model name asked for and the model name in the reply.
  A11  the DeepSeek token count of the key solver, on made-up call log lines.
  A13, small faults: the exit codes of FILE_FORMATS.md section 0. Only code 0 lets the next step
       start. A writer or a solver that stops early ends with code 1. A selection that says "move the
       next reserve setting" ends with code 1. A selection that says "do not launch" ends with code 3.
       Also: a tool prints in UTF-8. The import step is run as a process of its own, with its output
       sent to a pipe, on an answer sheet with a stray line that holds an arrow sign. Before this fix
       that run crashed after it had saved the answers.

Run:  python -B optionb/dry/fixture_q/run_dry_q.py
Exit code 0: every check held. Exit code 1: at least one check did not hold.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if (HERE.name, HERE.parent.name, HERE.parent.parent.name) != ('fixture_q', 'dry', 'optionb'):
    raise SystemExit('This script runs only as optionb/dry/fixture_q/run_dry_q.py.')
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import ob_check_questions as Q   # noqa: E402
import ob_select as S            # noqa: E402
import ob_solve_blind as B       # noqa: E402
import ob_write_questions as W   # noqa: E402

LF = chr(10)
TAG = ' [DRY FIXTURE, NOT A RESULT]'
MADE_FOLDERS = ['questions', 'checks', 'solve', 'select', 'stop_case', 'floor_case', 'utf8_case']
WRITER_NAME = 'MADE-UP-NAME-IN-A-WRITER-REPLY'
SOLVER_NAME = 'MADE-UP-NAME-IN-A-SOLVER-REPLY'
TRANSCRIPT_NAME = 'MADE-UP-NAME-FROM-A-TRANSCRIPT'   # operator decision C3: this is not the pinned model id, so the import step must refuse it
OVERRIDES = {
    'note': 'MADE-UP. Dry fixture only. These four floors are lowered so that three made-up passages can walk through every step. A tool reads '
            'this file only when its work folder sits under optionb/dry/. The real floors are 100, 100, 36 and 20. The two reserve targets of '
            'the reserve rule are lowered in the same way; the real reserve targets are 45 and 25. The practice role-step floor (2) is below '
            'its reserve target (3) on purpose: with 8 practice settings the made-up practice set meets both floors and misses a reserve '
            'target. That is the case of amendment A8.',
    'launch_floor': {'final_role_step_tasks_min': 1, 'final_plain_fact_tasks_min': 1, 'practice_role_step_tasks_min': 2, 'practice_plain_fact_tasks_min': 1},
    'split': {'reserve_target_practice_role_step_tasks': 3, 'reserve_target_practice_plain_fact_tasks': 1}}
# The made-up answer sheets of the Claude sub-agent, as the operator would save them. Item ids and letters fit the seeded item maps.
ANSWERS = {
    ('practice', 'with_passage', '01'): 'Here are my answers (a MADE-UP stray line; the tool must log it and go on)\nQ0004 D\nQ0005 D\nQ0006 E\n',
    ('practice', 'no_passage', '01'): 'G0004 F\nG0005 B\nG0006 A\n',
    ('practice', 'with_passage', '02'): 'Q0012 C\nQ0013 A\nQ0014 D\nQ0015 MORE_THAN_ONE\nQ0016 C\n',
    ('practice', 'no_passage', '02'): 'G0012 B\nG0013: E\nG0014 A\nG0015 D\nG0015 A\nG0016 B\n',
    ('final', 'with_passage', '01'): 'Q0004 C\nQ0005 C\nQ0006 B\n',
    ('final', 'no_passage', '01'): 'G0004 A\nG0005 A\nG0006 A\n'}
WRITER_LOG_FIELDS = ['utc', 'set', 'pass', 'model', 'model_in_reply', 'wave', 'batch', 'attempt', 'http_status', 'passage_ids', 'prompt_sha256',
                     'reply_sha256', 'ok', 'error', 'usage', 'prompt', 'reply']
SOLVER_LOG_FIELDS = ['utc', 'item_id', 'mode', 'question_id', 'model', 'model_in_reply', 'usage', 'http_status', 'ok', 'error', 'prompt_sha256',
                     'reply_sha256', 'prompt', 'reply']
LOG = {'steps': [], 'checks': []}
PINNED_ID = None   # the pinned model id of the Claude sub-agents; main() reads it from the plan constants


# ---------------------------------------------------------------- small helpers

def load(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def write_text(name, text):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline=LF) as stream:
        stream.write(text)
    return path


def lines(name):
    return [json.loads(line) for line in (HERE / name).read_text(encoding='utf-8').split(LF) if line.strip()]


def run(label, module, argv, work=None):
    """Run one tool in this folder. Returns its exit code (2 for a clean stop), its stop code and what it printed."""
    buffer, exit_code, stop = io.StringIO(), None, None
    with contextlib.redirect_stdout(buffer):
        try:
            exit_code = module.main(list(argv) + ['--work', str(work or HERE)])
        except module.Stop as halt:
            exit_code, stop = 2, {'code': halt.args[0], 'reason': halt.args[1]}
    text = buffer.getvalue().strip()
    out = json.loads(text) if text else {}
    step = {'label': label, 'tool': module.PROGRAM, 'argv': list(argv), 'exit': exit_code, 'stop': stop,
            'status': out.get('status') or out.get('decision'), 'printed': out}
    LOG['steps'].append(step)
    return step


def check(name, held, detail=''):
    LOG['checks'].append({'check': name, 'held': bool(held), 'detail': detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)})
    return held


def expect_stop(label, module, argv, code):
    step = run(label, module, argv)
    check('%s -> stops with %s' % (label, code), step['stop'] is not None and step['stop']['code'] == code, step['stop'] or step['status'] or '')
    return step


def expect_status(label, module, argv, status, work=None, exit_code=None):
    step = run(label, module, argv, work)
    held = step['status'] == status and step['stop'] is None and (exit_code is None or step['exit'] == exit_code)
    check('%s -> %s%s' % (label, status, '' if exit_code is None else ', exit %d' % exit_code), held,
          {'status': step['status'], 'exit': step['exit'], 'stop': step['stop']})
    return step


def replay(name, model):
    """A hand-written reply file of replay/, with a made-up model name added to every answered reply. Written to replay/used_<name>.json."""
    doc = json.loads((HERE / 'replay' / (name + '.json')).read_text(encoding='utf-8'))
    for entry in (doc if isinstance(doc, list) else doc.values()):
        for step in (entry if isinstance(entry, list) else [entry]):
            if step.get('http_status') == 200:
                step['model'] = model
    return str(write_text('replay/used_%s.json' % name, json.dumps(doc, indent=1, ensure_ascii=False) + LF))


def writer(label, set_name, pass_name, replay_name, status, more=()):
    argv = ['--set', set_name, '--pass', pass_name, '--max-calls', '5'] + list(more)
    if replay_name:
        argv += ['--replay-replies', replay(replay_name, WRITER_NAME)]
    # FILE_FORMATS.md section 0: only ALL_WRITTEN ends with exit code 0; every STOPPED_ status ends with 1
    return expect_status(label, W, argv, status, exit_code=0 if status == 'ALL_WRITTEN' else 1)


def solve_set(set_name, replay_name, sheet, more=()):
    """The check, both solvers and the decide step for one set, as far as its candidates stand now."""
    expect_status('check %s' % set_name, Q, ['--set', set_name] + list(more), 'CHECKED', exit_code=0)
    # a run with --max-calls 0 makes the item map and leaves every new item open: the status is a stop and the exit code is 1
    expect_status('deepseek %s, the item map only' % set_name, B, ['deepseek', '--set', set_name, '--max-calls', '0'], 'STOPPED_CALL_BUDGET', exit_code=1)
    expect_status('deepseek %s' % set_name, B, ['deepseek', '--set', set_name, '--max-calls', '50', '--workers', '1',
                                                '--replay-replies', replay(replay_name, SOLVER_NAME)], 'ALL_ANSWERED', exit_code=0)
    for mode in ('with_passage', 'no_passage'):
        step = expect_status('export %s %s' % (set_name, mode), B, ['export', '--set', set_name, '--mode', mode], 'SHEETS_WRITTEN')
        check('the export step of %s %s wrote sheet %s and names the pinned model id for the sub-agent' % (set_name, mode, sheet),
              [s['sheet'] for s in step['printed'].get('sheets', [])] == [sheet]
              and step['printed'].get('ask_for_the_sub_agent_with_model_id') == PINNED_ID, step['printed'].get('sheets'))
        write_text('solve/claude_answers_%s_%s_%s.txt' % (set_name, mode, sheet), ANSWERS[(set_name, mode, sheet)])
        expect_status('import %s %s sheet %s' % (set_name, mode, sheet), B, ['import', '--set', set_name, '--mode', mode, '--sheet', sheet,
                                                                              '--transcript-model', PINNED_ID], 'SHEET_IMPORTED')
    return expect_status('decide %s' % set_name, B, ['decide', '--set', set_name], 'KEY_CHECK_WRITTEN')


def with_changed_selection(change, label):
    """Run the writer's reserve check on a changed copy of select/selection_practice.json. The file is put back afterwards."""
    path = HERE / 'select' / 'selection_practice.json'
    kept = path.read_bytes()
    try:
        if change is None:
            path.unlink()
        else:
            doc = json.loads(kept.decode('utf-8'))
            change(doc)
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + LF, encoding='utf-8', newline=LF)
        expect_stop(label, W, ['--set', 'practice', '--pass', 'p1', '--practice-settings', '9', '--max-calls', '0'], 'RESERVE_RULE_NOT_MET')
    finally:
        path.write_bytes(kept)


def token_limit_checks(C):
    """Amendment A11: the DeepSeek token count of the key solver, on made-up call log lines. No service is called."""
    service = C['outside_services']['deepseek']
    rows = [{'usage': {'prompt_tokens': 10, 'completion_tokens': 4}}, {'usage': None}, {}, {'usage': {'completion_tokens': 9}},
            {'usage': {'prompt_tokens': 3, 'completion_tokens': 2}}]
    check('token count: the input and output counts are added up over the log lines; a line with no token count adds nothing',
          B.count_tokens(rows) == [13, 6] and B.usage_pair({'prompt_tokens': -1, 'completion_tokens': 2}) is None, B.count_tokens(rows))
    top_in, top_out = service['spend_cap_input_tokens'], service['spend_cap_output_tokens']
    check('token limit: reached when the input count is at its limit, or the output count is at its limit; not one token before',
          B.limit_reached([top_in, 0], service) and B.limit_reached([0, top_out], service) and not B.limit_reached([top_in - 1, top_out - 1], service))
    own = HERE / 'solve' / 'deepseek_calls_practice.jsonl'
    check('token count: a dry folder calls no service and counts nothing', B.tokens_at_start(B.Ctx(str(HERE)), service, own) is None)
    made = []
    for index, pair in enumerate(((100, 40), (30, 5), (7, 1), (0, 0))):
        name = 'replay/made_up_usage_log_%d.jsonl' % index
        write_text(name, ''.join(json.dumps({'usage': {'prompt_tokens': pair[0], 'completion_tokens': pair[1]}}) + LF for _ in range(2)))
        made.append(name)
    stand_in = type('NotDry', (), {'dry': False, 'work': HERE})()
    small = dict(service, spend_cap_counted_logs=made, spend_cap_input_tokens=1000, spend_cap_output_tokens=92)
    used = B.tokens_at_start(stand_in, small, HERE / made[1])
    check('token count: the four counted logs are read and added up (made-up logs: 274 input and 92 output tokens); 92 of 92 output tokens is the limit',
          used == [274, 92] and B.limit_reached(used, small) and not B.limit_reached([used[0], used[1] - 1], small), used)
    try:
        B.tokens_at_start(stand_in, small, own)
        check('token count: a step whose own call log is not one of the counted logs stops', False)
    except B.Stop as halt:
        check('token count: a step whose own call log is not one of the counted logs stops', halt.args[0] == 'PLAN_CONSTANTS_DISAGREE', halt.args[0])
    check('the four counted logs of the plan include both logs of the key solver',
          all('solve/deepseek_calls_%s.jsonl' % s in service['spend_cap_counted_logs'] for s in ('practice', 'final')), service['spend_cap_counted_logs'])
    log = lines('solve/deepseek_calls_practice.jsonl')
    check('a dry folder counts no tokens: every usage field of the solver log is null', all(row['usage'] is None for row in log), len(log))


# ---------------------------------------------------------------- the walk

def main():
    global PINNED_ID
    for name in MADE_FOLDERS:
        if (HERE / name).is_dir():
            shutil.rmtree(HERE / name)
    for path in list((HERE / 'replay').glob('used_*.json')) + list((HERE / 'replay').glob('made_up_usage_log_*.jsonl')) + [HERE / 'dry_run_log.json']:
        if path.exists():
            path.unlink()
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(OVERRIDES, indent=1, ensure_ascii=False) + LF)
    C = json.loads((ROOT / 'optionb' / 'PLAN_CONSTANTS.json').read_text(encoding='utf-8'))
    G = C['outside_services']['gemini_question_writer']
    PINNED_ID = C['outside_services']['claude_solver']['model_id']

    # ---- amendment A1: one writer model, 4 passages per call, seeded fixed order
    check('the plan names one writer model for both sets, and 4 passages per call',
          G['model_by_set'] == {'practice': 'gemini-3.5-flash-lite', 'final': 'gemini-3.5-flash-lite'} and G['passages_per_call'] == 4, G['model_by_set'])
    ids = ['M%02d' % n for n in range(10)]
    cut = W.cut_batches(ids, C['seeds']['writer_batch_order_p1'], G['passages_per_call'])
    check('10 made-up ids are cut into groups of 4, 4 and 2, in a seeded order that comes out the same twice',
          [len(group) for group in cut] == [4, 4, 2] and sorted(sum(cut, [])) == ids and cut == W.cut_batches(list(reversed(ids)), C['seeds']['writer_batch_order_p1'], 4)
          and cut != W.cut_batches(ids, C['seeds']['writer_batch_order_p2'], 4), cut)
    expect_stop('writer with a batch size above the plan value', W, ['--set', 'practice', '--pass', 'p1', '--max-calls', '0', '--batch-size', '5'], 'BAD_ARGUMENT')
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            W.main(['--set', 'practice', '--pass', 'p1', '--max-calls', '0', '--model', 'another-model', '--work', str(HERE)])
        no_option = False
    except SystemExit:
        no_option = True
    check('the writer has no option that names another model', no_option and not (HERE / 'questions').exists())
    two_models = dict(OVERRIDES, outside_services={'gemini_question_writer': {'model_by_set': {'final': 'MADE-UP-OTHER-MODEL'}}})
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(two_models, indent=1, ensure_ascii=False) + LF)
    expect_stop('writer when the constants name two different writer models', W, ['--set', 'practice', '--pass', 'p1', '--max-calls', '0'], 'ONE_MODEL_RULE')
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(OVERRIDES, indent=1, ensure_ascii=False) + LF)

    # ---- practice, 8 settings: a refused call, an unreadable reply, the spare pass
    step = writer('writer practice p1, the first call gets HTTP 429', 'practice', 'p1', 'writer_practice_p1_run1_cap', 'STOPPED_HTTP_429')
    state = load('questions/writer_state_practice_p1.json')
    check('a refused call stops the writer at once; it is not counted as a try and the checkpoint is kept',
          step['printed'].get('calls_this_run') == 1 and step['printed'].get('stops_after_http_429') == 1
          and state['waves'][0]['batches'][0]['attempts'] == 0 and state['waves'][0]['batches'][0]['status'] == 'PENDING' and len(state['cap_stops_utc']) == 1,
          {'calls': step['printed'].get('calls_this_run'), 'batch': state['waves'][0]['batches'][0]})
    step = writer('writer practice p1, run again later', 'practice', 'p1', 'writer_practice_p1_run2', 'ALL_WRITTEN')
    check('the resumed run asked twice: one unreadable reply, then a readable one', step['printed'].get('calls_this_run') == 2
          and load('questions/writer_state_practice_p1.json')['waves'][0]['batches'][0]['attempts'] == 2)
    writer('writer practice p2 (spare pass)', 'practice', 'p2', 'writer_practice_p2_run1', 'ALL_WRITTEN')
    log = lines('questions/writer_calls_practice_p1.jsonl')
    check('every call log line of the writer has the seventeen fields of the format (FILE_FORMATS.md section 4.2)', all(list(row) == WRITER_LOG_FIELDS for row in log), len(log))
    check('a writer log line holds the model name asked for; an answered call also holds the name in the reply, a refused call null',
          [(row['http_status'], row['model'], row['model_in_reply']) for row in log]
          == [(429, 'DRY-FIXTURE-NO-MODEL', None), (200, 'DRY-FIXTURE-NO-MODEL', WRITER_NAME), (200, 'DRY-FIXTURE-NO-MODEL', WRITER_NAME)],
          [(row['http_status'], row['model_in_reply']) for row in log])
    check('the writer checkpoint and the raw question file name the model asked for', state['model'] == 'DRY-FIXTURE-NO-MODEL'
          and load('questions/raw_questions_practice_p1.json')['model'] == 'DRY-FIXTURE-NO-MODEL')

    step = solve_set('practice', 'deepseek_practice_wave0', '01')
    check('with 8 practice settings 2 role-step and 1 plain-fact question pass both solver checks', step['printed']['counts']['survive'] == {'role_step': 2, 'plain_fact': 1},
          step['printed']['counts'])
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            B.main(['import', '--set', 'practice', '--mode', 'with_passage', '--sheet', '01', '--work', str(HERE)])
        needs_name = False
    except SystemExit:
        needs_name = True
    check('the import step refuses to run without --transcript-model', needs_name)
    expect_stop('import with an empty transcript model name', B, ['import', '--set', 'practice', '--mode', 'with_passage', '--sheet', '01',
                                                                  '--transcript-model', ' '], 'TRANSCRIPT_MODEL_MISSING')
    answers = load('solve/solver_answers_practice.json')['answers']
    check('every answer row holds model_in_reply: the name from the transcript for a Claude answer, the name in the reply for a DeepSeek answer',
          all(list(a)[-1] == 'model_in_reply' for a in answers)
          and {a['model_in_reply'] for a in answers if a['solver'] == 'claude-sonnet-subagent'} == {PINNED_ID}
          and {a['model_in_reply'] for a in answers if a['solver'] == 'deepseek-chat'} == {SOLVER_NAME}, sorted({str(a['model_in_reply']) for a in answers}))
    log = lines('solve/deepseek_calls_practice.jsonl')
    check('every call log line of the key solver has the fourteen fields of the format (FILE_FORMATS.md section 6.2)', all(list(row) == SOLVER_LOG_FIELDS for row in log), len(log))
    check('a solver log line holds the model name asked for; an answered call also holds the name in the reply, a call with no answer null',
          all(row['model'] == 'DRY-FIXTURE-NO-MODEL' for row in log) and {row['model_in_reply'] for row in log if row['http_status'] == 200} == {SOLVER_NAME}
          and [row['model_in_reply'] for row in log if row['http_status'] != 200] == [None], sorted({str(row['model_in_reply']) for row in log}))

    # ---- the reserve rule (amendment A8): floors met, a reserve target missed, a reserve setting left
    step = expect_status('select practice with 8 settings', S, ['select', '--set', 'practice'], 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING',
                         exit_code=1)
    selection = load('select/selection_practice.json')
    check('with 8 settings the practice set meets both launch floors and misses a reserve target: floor.met is true and reserve.finished is false',
          selection['counts']['role_step_tasks'] == 2 and selection['counts']['plain_fact_tasks'] == 1
          and selection['floor'] == {'practice_role_step_min': 2, 'practice_plain_fact_min': 1, 'met': True}
          and selection['reserve'] == {'role_step_target': 3, 'plain_fact_target': 1, 'target_met': False, 'settings_left': 4, 'finished': False},
          {'floor': selection['floor'], 'reserve': selection['reserve']})
    expect_stop('writer asks for reserve setting 2 while the selection was made with 8 settings', W,
                ['--set', 'practice', '--pass', 'p1', '--practice-settings', '10', '--max-calls', '0'], 'RESERVE_RULE_NOT_MET')
    with_changed_selection(None, 'writer asks for reserve setting 1 and there is no selection file')
    with_changed_selection(lambda doc: doc.pop('reserve'), 'writer asks for reserve setting 1 and the selection file has no reserve block')

    def old_rule_case(doc):
        doc['floor']['met'], doc['reserve']['finished'] = False, True

    with_changed_selection(old_rule_case, 'writer asks for reserve setting 1 when floor.met is false and reserve.finished is true')
    check('after the refused tries the checkpoint still holds one wave', len(load('questions/writer_state_practice_p1.json')['waves']) == 1)
    step = writer('writer practice p1 adds the wave of reserve setting 1 (floors met, a target missed)', 'practice', 'p1', 'writer_practice_p1_wave1',
                  'ALL_WRITTEN', ['--practice-settings', '9'])
    state = load('questions/writer_state_practice_p1.json')
    check('the writer added wave 1 with the one passage of reserve setting 1, and asked for it once', [w['wave'] for w in state['waves']] == [0, 1]
          and state['waves'][1]['settings'] == ['fixture market'] and state['waves'][1]['batches'][0]['passage_ids'] == ['V902']
          and step['printed'].get('calls_this_run') == 1 and step['printed'].get('practice_setting_count') == 9, state['waves'][1])
    writer('writer practice p2 adds the same wave (the other pass holds it)', 'practice', 'p2', 'writer_practice_p2_wave1', 'ALL_WRITTEN', ['--practice-settings', '9'])
    solve_set('practice', 'deepseek_practice_wave1', '02', ['--practice-settings', '9'])
    step = expect_status('select practice with 9 settings', S, ['select', '--set', 'practice', '--practice-settings', '9'], 'GO', exit_code=0)
    selection = load('select/selection_practice.json')
    check('with 9 settings both reserve targets are met: 4 role-step and 2 plain-fact tasks, reserve.finished is true',
          (selection['counts']['role_step_tasks'], selection['counts']['plain_fact_tasks']) == (4, 2)
          and selection['reserve'] == {'role_step_target': 3, 'plain_fact_target': 1, 'target_met': True, 'settings_left': 3, 'finished': True}, selection['reserve'])
    expect_stop('writer asks for reserve setting 2 after both reserve targets are met', W,
                ['--set', 'practice', '--pass', 'p1', '--practice-settings', '10', '--max-calls', '0'], 'RESERVE_RULE_NOT_MET')
    step = expect_status('fix the split', S, ['fix-split'], 'SPLIT_FIXED', exit_code=0)
    split = load('select/split_fixed.json')
    check('the split holds 9 practice settings and a history of two rows; no setting was moved after the targets were met',
          split['practice_setting_count'] == 9 and split['floor_met'] is True and split['reserve_target_met'] is True
          and [(r['practice_setting_count'], r['practice_role_step_tasks'], r['practice_plain_fact_tasks'], r['target_met']) for r in split['history']]
          == [(8, 2, 1, False), (9, 4, 2, True)], split['history'])

    # ---- the final set: the same writer model, the same tools
    writer('writer final p1', 'final', 'p1', 'writer_final_p1', 'ALL_WRITTEN')
    writer('writer final p2 (spare pass)', 'final', 'p2', 'writer_final_p2', 'ALL_WRITTEN')
    check('the practice set, the final set and both passes name one writer model',
          {load('questions/writer_state_%s_%s.json' % (s, p))['model'] for s in ('practice', 'final') for p in ('p1', 'p2')} == {'DRY-FIXTURE-NO-MODEL'})
    step = solve_set('final', 'deepseek_final', '01')
    check('2 final role-step questions and 1 final plain-fact question pass both solver checks', step['printed']['counts']['survive'] == {'role_step': 2, 'plain_fact': 1},
          step['printed']['counts'])
    step = expect_status('select final', S, ['select', '--set', 'final'], 'GO', exit_code=0)
    check('the final selection holds 1 role-step task and 1 plain-fact task', (step['printed']['counts']['role_step_tasks'], step['printed']['counts']['plain_fact_tasks']) == (1, 1),
          step['printed']['counts'])
    made = [load(name) for name in ('questions/raw_questions_final_p1.json', 'checks/candidates_final.json', 'solve/key_check_final.json', 'select/selection_final.json')]
    check('every file of the walk is marked as a dry fixture', all(doc['made_by']['program'].endswith(TAG) for doc in made))
    token_limit_checks(C)

    # ---- the stop case: the same practice files with the real floors and targets (no override file in that folder)
    for name in ('elig', 'questions', 'checks', 'solve'):
        shutil.copytree(HERE / name, HERE / 'stop_case' / name, ignore=lambda folder, names: [n for n in names if '_final' in n])
    step = expect_status('select practice in the stop case, real targets 45 and 25', S, ['select', '--set', 'practice', '--practice-settings', '9'],
                         'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING', work=HERE / 'stop_case', exit_code=1)
    stop_selection = json.loads((HERE / 'stop_case' / 'select' / 'selection_practice.json').read_text(encoding='utf-8'))
    check('with the real numbers the 4 and 2 made-up tasks miss the floors (36, 20) and the targets (45, 25); 3 reserve settings are left',
          stop_selection['floor'] == {'practice_role_step_min': 36, 'practice_plain_fact_min': 20, 'met': False}
          and stop_selection['reserve'] == {'role_step_target': 45, 'plain_fact_target': 25, 'target_met': False, 'settings_left': 3, 'finished': False},
          {'floor': stop_selection['floor'], 'reserve': stop_selection['reserve']})

    # ---- the floor case: the same files, with a final launch floor that the made-up final set misses (exit code 3)
    for name in ('elig', 'questions', 'checks', 'solve', 'select'):
        shutil.copytree(HERE / name, HERE / 'floor_case' / name)
    high = json.loads(json.dumps(OVERRIDES))
    high['launch_floor']['final_role_step_tasks_min'] = 99
    (HERE / 'floor_case' / 'DRY_CONSTANT_OVERRIDES.json').write_text(json.dumps(high, indent=1, ensure_ascii=False) + LF, encoding='utf-8', newline=LF)
    step = expect_status('select final in the floor case, a final floor of 99 role-step tasks', S, ['select', '--set', 'final'], 'STOP_DO_NOT_LAUNCH',
                         work=HERE / 'floor_case', exit_code=3)
    check('a selection that says do not launch names the missed floor and ends with exit code 3, not 0',
          step['printed'].get('stop_reasons') == ['final_role_step_tasks is 1; the launch floor is 99.'] and step['printed']['next'].startswith('Do not launch'),
          step['printed'].get('stop_reasons'))
    check('the exit codes of the selection tool are the ones of the formats file', S.EXIT_CODE_OF_DECISION
          == {'GO': 0, 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING': 1, 'STOP_DO_NOT_LAUNCH': 3})

    # ---- the UTF-8 case (FILE_FORMATS.md section 0): the import step as its own process, its output sent to a pipe
    for name in ('elig', 'questions', 'checks', 'solve', 'select'):
        shutil.copytree(HERE / name, HERE / 'utf8_case' / name)
    for name in ('solver_answers_final.json', 'key_check_final.json'):       # so that sheet 01 of the final set can be imported in this copy
        (HERE / 'utf8_case' / 'solve' / name).unlink()
    arrow = chr(0x2192)       # a sign the Windows code page cp1252 does not hold
    stray = 'My answers ' + arrow + ' one line for each item (a MADE-UP stray line)'
    (HERE / 'utf8_case' / 'solve' / 'claude_answers_final_with_passage_01.txt').write_text(
        stray + LF + ANSWERS[('final', 'with_passage', '01')], encoding='utf-8', newline=LF)
    plain = {name: value for name, value in os.environ.items() if name not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
    # operator decision C3: in this copy sheet 01 of the final set is not imported yet. A model name that is not the pinned id is refused first.
    step = run('import with a transcript model name that is not the pinned model id', B,
               ['import', '--set', 'final', '--mode', 'with_passage', '--sheet', '01', '--transcript-model', TRANSCRIPT_NAME], work=HERE / 'utf8_case')
    check('import with a transcript model name that is not the pinned model id -> stops with TRANSCRIPT_MODEL_NOT_THE_PINNED_ID',
          TRANSCRIPT_NAME != PINNED_ID and step['stop'] is not None and step['stop']['code'] == 'TRANSCRIPT_MODEL_NOT_THE_PINNED_ID' and step['exit'] == 2,
          step['stop'] or step['status'] or '')
    check('the refused import stored nothing: the answers file of the final set, which the import step writes, does not exist in this copy',
          not (HERE / 'utf8_case' / 'solve' / 'solver_answers_final.json').exists(),
          sorted(path.name for path in (HERE / 'utf8_case' / 'solve').glob('solver_answers_*')))
    done = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / 'ob_solve_blind.py'), 'import', '--set', 'final', '--mode', 'with_passage', '--sheet', '01',
                           '--transcript-model', PINNED_ID, '--work', str(HERE / 'utf8_case')], capture_output=True, env=plain, timeout=120)
    try:
        printed = json.loads(done.stdout.decode('utf-8'))
    except ValueError:
        printed = {}
    LOG['steps'].append({'label': 'import as its own process, output to a pipe, a stray line with an arrow sign', 'tool': B.PROGRAM,
                         'argv': ['import', '--set', 'final', '--mode', 'with_passage', '--sheet', '01'], 'exit': done.returncode, 'stop': None,
                         'status': printed.get('status'), 'printed': printed})
    check('the import step, run as its own process with its output sent to a pipe, ends with exit code 0 on a stray line that holds an arrow sign',
          done.returncode == 0 and printed.get('status') == 'SHEET_IMPORTED' and printed.get('readable') == 3
          and printed.get('first_such_lines') == [stray] and b'Traceback' not in done.stderr,
          {'exit': done.returncode, 'status': printed.get('status'), 'stderr': done.stderr.decode('utf-8', 'replace')[-300:]})

    failed = [c for c in LOG['checks'] if not c['held']]
    summary = {'made_by': {'program': 'optionb/dry/fixture_q/run_dry_q.py' + TAG, 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
               'note': 'DRY FIXTURE, NOT A RESULT. Made-up passages, label entries, questions, solver replies, answer sheets and model names. No outside call was made.',
               'tool_runs': len(LOG['steps']), 'checks': len(LOG['checks']), 'checks_held': len(LOG['checks']) - len(failed), 'checks_not_held': len(failed),
               'steps': LOG['steps'], 'check_list': LOG['checks']}
    write_text('dry_run_log.json', json.dumps(summary, indent=1, ensure_ascii=False) + LF)
    print(json.dumps({'dry_fixture': True, 'tool_runs': summary['tool_runs'], 'checks': summary['checks'], 'checks_held': summary['checks_held'],
                      'checks_not_held': failed}, indent=1, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
