"""[DRY FIXTURE, NOT A RESULT] Dry run of the four question tools on three made-up passages. Plan v1.1 edition.

Tools walked through, with no outside call and no key:
  tools/ob_write_questions.py   tools/ob_check_questions.py
  tools/ob_solve_blind.py       tools/ob_select.py

Everything in this folder is made up: the passages and their label entries (elig/eligibility.json),
the writer replies (replay/writer_*.json), the DeepSeek replies and the answer sheets of the Claude
sub-agent (both written by this script from the outcome table OUTCOMES below, through the private
item map) and the model names. Nothing here is a case. Nothing here is a result.

This is the v1.0 walk (optionb/dry/fixture_q/run_dry_q.py of CASALESCENCE_NOETICS_v0_1), changed for
plan v1.1 (PLAN_V1_1_CHANGE_SPEC.md, parts C2 and C3):
  C2   the three new Step 2 rules. The made-up questions hold one planted fault for each code:
       QUESTION_REPEATS_KEY (V901.p1.TAKE_AWAY), OPTIONS_MATCH_EACH_OTHER (V901.p3.MEET_AGAIN),
       WRONG_OPTION_NOT_FROM_PASSAGE (V902.p1.WHAT_STUCK, and V902.p2.GOES_FOR beside its other faults).
       The v1.0 made-up wrong options were invented words, which the new rule drops; they were rewritten
       from passage words so that the rest of the walk still happens.
  C3   three passes. The writer takes --pass p3 with the seed writer_batch_order_p3. Every passing
       question of every pass is a candidate (candidates_per_pass). In Step 6 the survivors of a passage
       and form are reduced to the lowest pass (LATER_PASS_NOT_NEEDED) and each task records pass_used.
       The final set is checked while its p3 file does not exist (passes_missing).
What the walk still shows from 2026-10-05: A1 (one writer model; HTTP 429 stops the writer), A3 and
operator decision C3 (the import step and the pinned model id), A8 (the reserve rule), A9 (model names
in the call logs), A11 (the DeepSeek token count), A13 (exit codes; UTF-8 output).

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
DEEPSEEK, CLAUDE = 'deepseek-chat', 'claude-sonnet-subagent'
OVERRIDES = {
    'note': 'MADE-UP. Dry fixture only. These four floors are lowered so that three made-up passages can walk through every step. A tool reads '
            'this file only when its work folder sits under optionb/dry/. The real floors are 100, 100, 36 and 20. The two reserve targets of '
            'the reserve rule are lowered in the same way; the real reserve targets are 45 and 25. The practice role-step floor (2) is below '
            'its reserve target (3) on purpose: with 8 practice settings the made-up practice set meets both floors and misses a reserve '
            'target. That is the case of amendment A8. Plan v1.1: the passes, the p3 seed and the three question_rules keys are read from '
            'optionb/PLAN_CONSTANTS.json itself; nothing of v1.1 is overridden here.',
    'launch_floor': {'final_role_step_tasks_min': 1, 'final_plain_fact_tasks_min': 1, 'practice_role_step_tasks_min': 2, 'practice_plain_fact_tasks_min': 1},
    'split': {'reserve_target_practice_role_step_tasks': 3, 'reserve_target_practice_plain_fact_tasks': 1}}
# The made-up solver outcomes, per question id: (DeepSeek with the passage, DeepSeek without, Claude with, Claude without).
# RIGHT / WRONG pick the key or another letter. MORE_THAN_ONE is the flag. UNREADABLE is a reply with no JSON (DeepSeek) or a
# sheet line that does not fit (Claude). REPEATED is one item answered twice on a sheet (counts as unreadable).
OUTCOMES = {
    'V901.p1.MEET_AGAIN': ('RIGHT', 'WRONG', 'RIGHT', 'RIGHT'),            # survives; the p1 task of its pair
    'V901.p2.MEET_AGAIN': ('RIGHT', 'RIGHT', 'RIGHT', 'WRONG'),            # survives too; LATER_PASS_NOT_NEEDED behind p1
    'V901.p2.TAKE_AWAY': ('RIGHT', 'WRONG', 'MORE_THAN_ONE', 'WRONG'),     # fails the key check (a flag)
    'V901.p3.TAKE_AWAY': ('RIGHT', 'UNREADABLE', 'RIGHT', 'WRONG'),        # survives; stands in for its pair: pass_used p3
    'V901.p1.FACT': ('RIGHT', 'RIGHT', 'RIGHT', 'WRONG'),                  # survives; the p1 task
    'V901.p2.FACT': ('WRONG', 'WRONG', 'WRONG', 'REPEATED'),               # fails the key check
    'V901.p3.FACT': ('RIGHT', 'WRONG', 'RIGHT', 'RIGHT'),                  # survives; LATER_PASS_NOT_NEEDED behind p1
    'V902.p1.GOES_FOR': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),              # survives; the pair rule prefers two types and leaves it out
    'V902.p1.KEEPS_AWAY': ('RIGHT', 'RIGHT', 'RIGHT', 'WRONG'),            # survives; picked
    'V902.p3.KEEPS_AWAY': ('RIGHT', 'WRONG', 'RIGHT', 'UNREADABLE'),       # survives; LATER_PASS_NOT_NEEDED behind p1
    'V902.p1.WHAT_SLID_OFF': ('RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'),         # both solvers right without the passage: dropped as guessable
    'V902.p2.WHAT_STUCK': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),            # survives; stands in (p1 WHAT_STUCK was dropped in Step 2): pass_used p2
    'V902.p2.FACT': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),                  # survives (p1 FACT held a forbidden word): pass_used p2
    'V903.p1.LONG_BREAK': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),            # survives
    'V903.p1.NEW_STARTER': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),           # survives; same right thing as LONG_BREAK: one of the two is picked
    'V903.p1.FACT': ('RIGHT', 'WRONG', 'RIGHT', 'WRONG'),                  # survives; the p1 task
    'V903.p2.FACT': ('RIGHT', 'RIGHT', 'RIGHT', 'WRONG')}                  # survives; LATER_PASS_NOT_NEEDED behind p1
WRITER_LOG_FIELDS = ['utc', 'set', 'pass', 'model', 'model_in_reply', 'wave', 'batch', 'attempt', 'http_status', 'passage_ids', 'prompt_sha256',
                     'reply_sha256', 'ok', 'error', 'usage', 'prompt', 'reply']
SOLVER_LOG_FIELDS = ['utc', 'item_id', 'mode', 'question_id', 'model', 'model_in_reply', 'usage', 'http_status', 'ok', 'error', 'prompt_sha256',
                     'reply_sha256', 'prompt', 'reply']
LOG = {'steps': [], 'checks': []}
PINNED_ID = None   # the pinned model id of the Claude sub-agents; main() reads it from the plan constants
ANSWERS_MADE = {}  # (set, mode, sheet) -> the answer sheet text this script wrote


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


# ---------------------------------------------------------------- made-up solver replies from the outcome table

def letters_of(item, outcome):
    """The letter(s) a made-up solver gives for one item of the private map."""
    shown = 'ABCDEFGH'[:len(item['shown'])]
    right = item['right_letter']
    wrong = shown[(shown.index(right) + 1) % len(shown)]
    other = shown[(shown.index(right) + 2) % len(shown)]
    return {'RIGHT': [right], 'WRONG': [wrong], 'MORE_THAN_ONE': ['MORE_THAN_ONE'], 'REPEATED': [wrong, other], 'UNREADABLE': [None]}[outcome]


def outcome_of(item):
    pos = {(DEEPSEEK, 'with_passage'): 0, (DEEPSEEK, 'no_passage'): 1, (CLAUDE, 'with_passage'): 2, (CLAUDE, 'no_passage'): 3}[(item['solver'], item['mode'])]
    return OUTCOMES[item['question_id']][pos]


def deepseek_replay(set_name, tag):
    """A made-up DeepSeek reply for every DeepSeek item of the private map (items answered earlier are not asked again)."""
    made = {}
    for item in load('solve/solver_items_%s.json' % set_name)['items']:
        if item['solver'] != DEEPSEEK:
            continue
        letter = letters_of(item, outcome_of(item))[0]
        if letter is None:
            made[item['item_id']] = {'http_status': 200, 'content': 'MADE-UP reply with no JSON: I think A', 'model': SOLVER_NAME}
        else:
            made[item['item_id']] = {'http_status': 200, 'content_json': {'answer': letter}, 'model': SOLVER_NAME}
    return str(write_text('replay/used_deepseek_%s_%s.json' % (set_name, tag), json.dumps(made, indent=1, ensure_ascii=False) + LF))


def claude_sheet_answers(set_name, mode, sheet, stray=None):
    """The made-up answer sheet of one Claude sheet, as the operator would save it, from the private map and the outcome table."""
    rows = []
    for item in load('solve/solver_items_%s.json' % set_name)['items']:
        if (item['solver'], item['mode'], item['sheet']) != (CLAUDE, mode, sheet):
            continue
        for letter in letters_of(item, outcome_of(item)):
            rows.append('%s: X' % item['item_id'] if letter is None else '%s %s' % (item['item_id'], letter))
    rows.sort()
    text = ''.join(line + LF for line in ([stray] if stray else []) + rows)
    ANSWERS_MADE[(set_name, mode, sheet)] = text
    return text


def solve_set(set_name, tag, sheet, more=(), stray=None):
    """The check, both solvers and the decide step for one set, as far as its candidates stand now."""
    checked = expect_status('check %s' % set_name, Q, ['--set', set_name] + list(more), 'CHECKED', exit_code=0)
    # a run with --max-calls 0 makes the item map and leaves every new item open: the status is a stop and the exit code is 1
    expect_status('deepseek %s, the item map only' % set_name, B, ['deepseek', '--set', set_name, '--max-calls', '0'], 'STOPPED_CALL_BUDGET', exit_code=1)
    expect_status('deepseek %s' % set_name, B, ['deepseek', '--set', set_name, '--max-calls', '50', '--workers', '1',
                                                '--replay-replies', deepseek_replay(set_name, tag)], 'ALL_ANSWERED', exit_code=0)
    for mode in ('with_passage', 'no_passage'):
        step = expect_status('export %s %s' % (set_name, mode), B, ['export', '--set', set_name, '--mode', mode], 'SHEETS_WRITTEN')
        check('the export step of %s %s wrote sheet %s and names the pinned model id for the sub-agent' % (set_name, mode, sheet),
              [s['sheet'] for s in step['printed'].get('sheets', [])] == [sheet]
              and step['printed'].get('ask_for_the_sub_agent_with_model_id') == PINNED_ID, step['printed'].get('sheets'))
        write_text('solve/claude_answers_%s_%s_%s.txt' % (set_name, mode, sheet),
                   claude_sheet_answers(set_name, mode, sheet, stray if mode == 'with_passage' else None))
        expect_status('import %s %s sheet %s' % (set_name, mode, sheet), B, ['import', '--set', set_name, '--mode', mode, '--sheet', sheet,
                                                                              '--transcript-model', PINNED_ID], 'SHEET_IMPORTED')
    decided = expect_status('decide %s' % set_name, B, ['decide', '--set', set_name], 'KEY_CHECK_WRITTEN')
    return checked, decided


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


def no_option(module, argv):
    """True when argparse refuses the options (SystemExit) before any tool code runs."""
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            module.main(list(argv) + ['--work', str(HERE)])
        return False
    except SystemExit:
        return True


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

    # ---- plan v1.1 constants (C2, C3)
    check('the plan names three passes p1, p2, p3 and a seed for each (writer_batch_order_p3 = 20261018)',
          G['passes'] == ['p1', 'p2', 'p3'] and all('writer_batch_order_' + p in C['seeds'] for p in G['passes'])
          and C['seeds']['writer_batch_order_p3'] == 20261018, {'passes': G['passes'], 'seeds': {k: v for k, v in C['seeds'].items() if 'writer' in k}})
    rules = C['question_rules']
    check('the plan holds the three v1.1 question rules: question_must_not_match_right_option, no_two_options_match, wrong_options_must_match_passage_forms (nine forms)',
          rules.get('question_must_not_match_right_option') is True and rules.get('no_two_options_match') is True
          and sorted(rules.get('wrong_options_must_match_passage_forms', [])) == sorted(['GOES_FOR', 'KEEPS_AWAY', 'WHAT_STUCK', 'WHAT_SLID_OFF', 'WHAT_LEFT',
                                                                                        'NOT_BELONG', 'LONG_BREAK', 'NEW_STARTER', 'TAKE_AWAY']),
          rules.get('wrong_options_must_match_passage_forms'))

    # ---- amendment A1: one writer model, 4 passages per call, seeded fixed order
    check('the plan names one writer model for both sets, and 4 passages per call',
          G['model_by_set'] == {'practice': 'gemini-3.5-flash-lite', 'final': 'gemini-3.5-flash-lite'} and G['passages_per_call'] == 4, G['model_by_set'])
    ids = ['M%02d' % n for n in range(10)]
    cut = {p: W.cut_batches(ids, C['seeds']['writer_batch_order_' + p], G['passages_per_call']) for p in G['passes']}
    check('10 made-up ids are cut into groups of 4, 4 and 2, in a seeded order that comes out the same twice; the three pass seeds give three different orders',
          all([len(group) for group in cut[p]] == [4, 4, 2] and sorted(sum(cut[p], [])) == ids for p in cut)
          and cut['p1'] == W.cut_batches(list(reversed(ids)), C['seeds']['writer_batch_order_p1'], 4)
          and len({json.dumps(cut[p]) for p in cut}) == 3, cut)
    expect_stop('writer with a batch size above the plan value', W, ['--set', 'practice', '--pass', 'p1', '--max-calls', '0', '--batch-size', '5'], 'BAD_ARGUMENT')
    check('the writer has no option that names another model', no_option(W, ['--set', 'practice', '--pass', 'p1', '--max-calls', '0', '--model', 'another-model'])
          and not (HERE / 'questions').exists())
    check('the writer refuses a pass name that is not in the plan (--pass p4)', no_option(W, ['--set', 'practice', '--pass', 'p4', '--max-calls', '0'])
          and not (HERE / 'questions').exists())
    two_models = dict(OVERRIDES, outside_services={'gemini_question_writer': {'model_by_set': {'final': 'MADE-UP-OTHER-MODEL'}}})
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(two_models, indent=1, ensure_ascii=False) + LF)
    expect_stop('writer when the constants name two different writer models', W, ['--set', 'practice', '--pass', 'p1', '--max-calls', '0'], 'ONE_MODEL_RULE')
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(OVERRIDES, indent=1, ensure_ascii=False) + LF)

    # ---- practice, 8 settings: a refused call, an unreadable reply, three passes
    step = writer('writer practice p1, the first call gets HTTP 429', 'practice', 'p1', 'writer_practice_p1_run1_cap', 'STOPPED_HTTP_429')
    state = load('questions/writer_state_practice_p1.json')
    check('a refused call stops the writer at once; it is not counted as a try and the checkpoint is kept',
          step['printed'].get('calls_this_run') == 1 and step['printed'].get('stops_after_http_429') == 1
          and state['waves'][0]['batches'][0]['attempts'] == 0 and state['waves'][0]['batches'][0]['status'] == 'PENDING' and len(state['cap_stops_utc']) == 1,
          {'calls': step['printed'].get('calls_this_run'), 'batch': state['waves'][0]['batches'][0]})
    step = writer('writer practice p1, run again later', 'practice', 'p1', 'writer_practice_p1_run2', 'ALL_WRITTEN')
    check('the resumed run asked twice: one unreadable reply, then a readable one', step['printed'].get('calls_this_run') == 2
          and load('questions/writer_state_practice_p1.json')['waves'][0]['batches'][0]['attempts'] == 2)
    writer('writer practice p2 (second pass)', 'practice', 'p2', 'writer_practice_p2_run1', 'ALL_WRITTEN')
    writer('writer practice p3 (third pass)', 'practice', 'p3', 'writer_practice_p3_run1', 'ALL_WRITTEN')
    states = {p: load('questions/writer_state_practice_%s.json' % p) for p in G['passes']}
    check('each pass checkpoint carries its own pass name and seed (writer_batch_order_<pass>); p3 carries 20261018',
          all(states[p]['pass'] == p and states[p]['seed'] == C['seeds']['writer_batch_order_' + p] for p in G['passes']) and states['p3']['seed'] == 20261018,
          {p: states[p]['seed'] for p in states})
    check('the three practice pass files follow the file name pattern of FILE_FORMATS.md section 4',
          all((HERE / 'questions' / ('%s_practice_%s.%s' % (kind, p, ext))).exists() for p in G['passes']
              for kind, ext in (('writer_state', 'json'), ('writer_calls', 'jsonl'), ('raw_questions', 'json'))))
    log = lines('questions/writer_calls_practice_p1.jsonl')
    check('every call log line of the writer has the seventeen fields of the format (FILE_FORMATS.md section 4.2)', all(list(row) == WRITER_LOG_FIELDS for row in log), len(log))
    check('a writer log line holds the model name asked for; an answered call also holds the name in the reply, a refused call null',
          [(row['http_status'], row['model'], row['model_in_reply']) for row in log]
          == [(429, 'DRY-FIXTURE-NO-MODEL', None), (200, 'DRY-FIXTURE-NO-MODEL', WRITER_NAME), (200, 'DRY-FIXTURE-NO-MODEL', WRITER_NAME)],
          [(row['http_status'], row['model_in_reply']) for row in log])
    check('the writer checkpoint and the raw question file name the model asked for', state['model'] == 'DRY-FIXTURE-NO-MODEL'
          and load('questions/raw_questions_practice_p1.json')['model'] == 'DRY-FIXTURE-NO-MODEL')

    checked, decided = solve_set('practice', 'wave0', '01', stray='Here are my answers (a MADE-UP stray line; the tool must log it and go on)')
    check('check practice (8 settings) read all three passes', checked['printed'].get('passes_read') == ['p1', 'p2', 'p3'] and checked['printed'].get('passes_missing') == [],
          {'read': checked['printed'].get('passes_read'), 'missing': checked['printed'].get('passes_missing')})
    form = load('checks/form_check_practice.json')
    by_id = {row['question_id']: row for row in form['rows']}
    check('v1.1 Step 2: V901.p1.TAKE_AWAY drops with QUESTION_REPEATS_KEY (its question sentence repeats the right option)',
          by_id['V901.p1.TAKE_AWAY']['reasons'] == ['QUESTION_REPEATS_KEY'], by_id['V901.p1.TAKE_AWAY']['reasons'])
    check('v1.1 Step 2: V901.p3.MEET_AGAIN drops with OPTIONS_MATCH_EACH_OTHER (two options share their content words)',
          by_id['V901.p3.MEET_AGAIN']['reasons'] == ['OPTIONS_MATCH_EACH_OTHER'], by_id['V901.p3.MEET_AGAIN']['reasons'])
    check('v1.1 Step 2: the new codes are counted in dropped_by_reason, and the sound questions of every pass pass',
          form['counts']['dropped_by_reason'].get('QUESTION_REPEATS_KEY') == 1 and form['counts']['dropped_by_reason'].get('OPTIONS_MATCH_EACH_OTHER') == 1
          and all(by_id[q]['passed'] for q in ('V901.p1.MEET_AGAIN', 'V901.p2.MEET_AGAIN', 'V901.p2.TAKE_AWAY', 'V901.p3.TAKE_AWAY', 'V901.p1.FACT', 'V901.p2.FACT', 'V901.p3.FACT')),
          form['counts'])
    cands = load('checks/candidates_practice.json')
    check('v1.1 candidates (8 settings): every passing question of every pass; 4 role-step and 3 plain-fact over the passes; each row carries its pass; '
          'counts carry candidates_per_pass per family and pairs_with_a_candidate; spares_used is gone',
          [c['question_id'] for c in cands['candidates']] == ['V901.p1.MEET_AGAIN', 'V901.p2.MEET_AGAIN', 'V901.p2.TAKE_AWAY', 'V901.p3.TAKE_AWAY',
                                                               'V901.p1.FACT', 'V901.p2.FACT', 'V901.p3.FACT']
          and all(c['pass'] == c['question_id'].split('.')[1] for c in cands['candidates'])
          and cands['counts'] == {'role_step': 4, 'plain_fact': 3,
                                  'candidates_per_pass': {'p1': {'role_step': 1, 'plain_fact': 1}, 'p2': {'role_step': 2, 'plain_fact': 1}, 'p3': {'role_step': 1, 'plain_fact': 1}},
                                  'pairs_with_a_candidate': 2},
          cands['counts'])
    check('the candidates file holds no label information and no key', not any(key in c for c in cands['candidates'] for key in ('entries', 'noetic', 'agreed', 'key', 'right_letter')))
    check('with 8 practice settings 3 role-step and 2 plain-fact questions pass both solver checks (over the passes)',
          decided['printed']['counts']['survive'] == {'role_step': 3, 'plain_fact': 2}, decided['printed']['counts'])
    check('the import step refuses to run without --transcript-model', no_option(B, ['import', '--set', 'practice', '--mode', 'with_passage', '--sheet', '01']))
    expect_stop('import with an empty transcript model name', B, ['import', '--set', 'practice', '--mode', 'with_passage', '--sheet', '01',
                                                                  '--transcript-model', ' '], 'TRANSCRIPT_MODEL_MISSING')
    answers = load('solve/solver_answers_practice.json')['answers']
    check('every answer row holds model_in_reply: the name from the transcript for a Claude answer, the name in the reply for a DeepSeek answer',
          all(list(a)[-1] == 'model_in_reply' for a in answers)
          and {a['model_in_reply'] for a in answers if a['solver'] == CLAUDE} == {PINNED_ID}
          and {a['model_in_reply'] for a in answers if a['solver'] == DEEPSEEK} == {SOLVER_NAME}, sorted({str(a['model_in_reply']) for a in answers}))
    log = lines('solve/deepseek_calls_practice.jsonl')
    check('every call log line of the key solver has the fourteen fields of the format (FILE_FORMATS.md section 6.2)', all(list(row) == SOLVER_LOG_FIELDS for row in log), len(log))
    check('a solver log line holds the model name asked for and the name in the reply',
          all(row['model'] == 'DRY-FIXTURE-NO-MODEL' for row in log) and {row['model_in_reply'] for row in log if row['http_status'] == 200} == {SOLVER_NAME},
          sorted({str(row['model_in_reply']) for row in log}))
    sheets = [p.read_text(encoding='utf-8') for p in (HERE / 'solve').glob('claude_sheet_practice_*_01.txt')]
    check('no Claude sheet holds a question id, a pass name tag or a form name', sheets and not any(('.p1.' in t or '.p2.' in t or '.p3.' in t or 'MEET_AGAIN' in t) for t in sheets))

    # ---- the reserve rule (amendment A8): floors met, a reserve target missed, a reserve setting left
    step = expect_status('select practice with 8 settings', S, ['select', '--set', 'practice'], 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING',
                         exit_code=1)
    selection = load('select/selection_practice.json')
    check('with 8 settings the practice set meets both launch floors and misses a reserve target: floor.met is true and reserve.finished is false',
          selection['counts']['role_step_tasks'] == 2 and selection['counts']['plain_fact_tasks'] == 1
          and selection['floor'] == {'practice_role_step_min': 2, 'practice_plain_fact_min': 1, 'met': True}
          and selection['reserve'] == {'role_step_target': 3, 'plain_fact_target': 1, 'target_met': False, 'settings_left': 4, 'finished': False},
          {'floor': selection['floor'], 'reserve': selection['reserve']})
    used = {t['task_id']: t['pass_used'] for t in selection['tasks']}
    check('v1.1 Step 6 (8 settings): the lowest surviving pass supplies each task: MEET_AGAIN from p1, TAKE_AWAY from p3 (p1 dropped in Step 2, p2 failed the key check), FACT from p1; '
          'pass_used equals the pass in question_id',
          used == {'V901.MEET_AGAIN': 'p1', 'V901.TAKE_AWAY': 'p3', 'V901.FACT': 'p1'} and all(t['question_id'].split('.')[1] == t['pass_used'] for t in selection['tasks']), used)
    check('v1.1 Step 6 (8 settings): the later-pass survivors V901.p2.MEET_AGAIN and V901.p3.FACT are logged with LATER_PASS_NOT_NEEDED',
          sorted((d['question_id'], d['reason']) for d in selection['dropped']) == [('V901.p2.MEET_AGAIN', 'LATER_PASS_NOT_NEEDED'), ('V901.p3.FACT', 'LATER_PASS_NOT_NEEDED')],
          selection['dropped'])
    check('v1.1 selection file carries the survival block of FILE_FORMATS.md 7.1 (ids over every pass, then pairs)',
          selection['survival'] == {'role_step': {'candidates': 4, 'after_key_check': 3, 'after_no_passage': 3, 'after_lowest_pass': 2, 'selected': 2},
                                    'plain_fact': {'candidates': 3, 'after_key_check': 2, 'after_no_passage': 2, 'after_lowest_pass': 1, 'selected': 1}},
          selection['survival'])
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
    writer('writer practice p2 adds the same wave (another pass holds it)', 'practice', 'p2', 'writer_practice_p2_wave1', 'ALL_WRITTEN', ['--practice-settings', '9'])
    writer('writer practice p3 adds the same wave (another pass holds it)', 'practice', 'p3', 'writer_practice_p3_wave1', 'ALL_WRITTEN', ['--practice-settings', '9'])
    checked, decided = solve_set('practice', 'wave1', '02', ['--practice-settings', '9'])
    form = load('checks/form_check_practice.json')
    by_id = {row['question_id']: row for row in form['rows']}
    check('v1.1 Step 2: V902.p1.WHAT_STUCK drops with WRONG_OPTION_NOT_FROM_PASSAGE (one wrong option is not from the passage); the three new codes sit after the old ones',
          by_id['V902.p1.WHAT_STUCK']['reasons'] == ['WRONG_OPTION_NOT_FROM_PASSAGE']
          and by_id['V902.p2.GOES_FOR']['reasons'] == ['ANCHOR_NOT_IN_PASSAGE', 'FORBIDDEN_LIST_C:drawn', 'WRONG_OPTION_NOT_FROM_PASSAGE'],
          {q: by_id[q]['reasons'] for q in ('V902.p1.WHAT_STUCK', 'V902.p2.GOES_FOR')})
    check('v1.1 Step 2: a plain-fact question with a forbidden word still drops (FORBIDDEN_LIST_A), and the v1.1 rules do not drop a sound plain-fact question',
          by_id['V902.p1.FACT']['reasons'] == ['FORBIDDEN_LIST_A:mind'] and by_id['V902.p2.FACT']['passed'], by_id['V902.p1.FACT']['reasons'])
    cands = load('checks/candidates_practice.json')
    check('v1.1 candidates (9 settings): 9 role-step and 4 plain-fact over the passes; per pass p1 4/1, p2 3/2, p3 2/1; 6 passage-and-form pairs with a role-step candidate',
          cands['counts'] == {'role_step': 9, 'plain_fact': 4,
                              'candidates_per_pass': {'p1': {'role_step': 4, 'plain_fact': 1}, 'p2': {'role_step': 3, 'plain_fact': 2}, 'p3': {'role_step': 2, 'plain_fact': 1}},
                              'pairs_with_a_candidate': 6}, cands['counts'])
    check('check (9 settings) survival rows count passage-and-form pairs, any pass passing: 6 open pairs written, 6 after the form check, 6 after the option check',
          checked['printed']['survival_after_each_filter'] == [{'filter': 'written for an open form', 'role_step': 6, 'plain_fact': 2},
                                                               {'filter': 'form check', 'role_step': 6, 'plain_fact': 2},
                                                               {'filter': 'anchor check', 'role_step': 6, 'plain_fact': 2},
                                                               {'filter': 'option check', 'role_step': 6, 'plain_fact': 2}],
          checked['printed']['survival_after_each_filter'])
    check('with 9 settings 7 role-step and 3 plain-fact questions pass both solver checks (over the passes)',
          decided['printed']['counts']['survive'] == {'role_step': 7, 'plain_fact': 3}, decided['printed']['counts'])
    step = expect_status('select practice with 9 settings', S, ['select', '--set', 'practice', '--practice-settings', '9'], 'GO', exit_code=0)
    selection = load('select/selection_practice.json')
    check('with 9 settings both reserve targets are met: 4 role-step and 2 plain-fact tasks, reserve.finished is true',
          (selection['counts']['role_step_tasks'], selection['counts']['plain_fact_tasks']) == (4, 2)
          and selection['reserve'] == {'role_step_target': 3, 'plain_fact_target': 1, 'target_met': True, 'settings_left': 3, 'finished': True}, selection['reserve'])
    used = {t['task_id']: t['pass_used'] for t in selection['tasks']}
    check('v1.1 Step 6 (9 settings): pass_used per task: V901 MEET_AGAIN p1, TAKE_AWAY p3, FACT p1; V902 KEEPS_AWAY p1, WHAT_STUCK p2 (stands in for the dropped p1), FACT p2',
          used == {'V901.MEET_AGAIN': 'p1', 'V901.TAKE_AWAY': 'p3', 'V901.FACT': 'p1', 'V902.KEEPS_AWAY': 'p1', 'V902.WHAT_STUCK': 'p2', 'V902.FACT': 'p2'}, used)
    dropped = sorted((d['question_id'], d['reason']) for d in selection['dropped'])
    check('v1.1 Step 6 (9 settings): three LATER_PASS_NOT_NEEDED drops (V901.p2.MEET_AGAIN, V901.p3.FACT, V902.p3.KEEPS_AWAY) and one NOT_PICKED_BY_PAIR_RULE (V902.p1.GOES_FOR); '
          'the guessable V902.p1.WHAT_SLID_OFF never reaches Step 6',
          dropped == [('V901.p2.MEET_AGAIN', 'LATER_PASS_NOT_NEEDED'), ('V901.p3.FACT', 'LATER_PASS_NOT_NEEDED'), ('V902.p1.GOES_FOR', 'NOT_PICKED_BY_PAIR_RULE'),
                      ('V902.p3.KEEPS_AWAY', 'LATER_PASS_NOT_NEEDED')], dropped)
    check('v1.1 survival block (9 settings): role-step 9 / 8 / 7 / 5 / 4, plain-fact 4 / 3 / 3 / 2 / 2',
          selection['survival'] == {'role_step': {'candidates': 9, 'after_key_check': 8, 'after_no_passage': 7, 'after_lowest_pass': 5, 'selected': 4},
                                    'plain_fact': {'candidates': 4, 'after_key_check': 3, 'after_no_passage': 3, 'after_lowest_pass': 2, 'selected': 2}},
          selection['survival'])
    rows = {r['filter']: (r['role_step'], r['plain_fact']) for r in step['printed']['rows']}
    check('the survival table of select (9 settings) counts pairs at every filter: 6/2 written, 6/2 form, 6/2 anchor, 6/2 option, 6/2 key check, 5/2 no-passage, 4/2 selection, 4/2 backstop',
          rows == {'written for an open form': (6, 2), 'form check': (6, 2), 'anchor check': (6, 2), 'option check': (6, 2), 'key check': (6, 2),
                   'no-passage check': (5, 2), 'selection': (4, 2), 'length backstop': (4, 2)}, rows)
    check('select prints tasks_by_pass_used', step['printed'].get('tasks_by_pass_used') == {'p1': 3, 'p2': 2, 'p3': 1}, step['printed'].get('tasks_by_pass_used'))
    expect_stop('writer asks for reserve setting 2 after both reserve targets are met', W,
                ['--set', 'practice', '--pass', 'p1', '--practice-settings', '10', '--max-calls', '0'], 'RESERVE_RULE_NOT_MET')
    step = expect_status('fix the split', S, ['fix-split'], 'SPLIT_FIXED', exit_code=0)
    split = load('select/split_fixed.json')
    check('the split holds 9 practice settings and a history of two rows; no setting was moved after the targets were met',
          split['practice_setting_count'] == 9 and split['floor_met'] is True and split['reserve_target_met'] is True
          and [(r['practice_setting_count'], r['practice_role_step_tasks'], r['practice_plain_fact_tasks'], r['target_met']) for r in split['history']]
          == [(8, 2, 1, False), (9, 4, 2, True)], split['history'])

    # ---- the final set: the same writer model, the same tools; p3 is not written yet when the check runs
    writer('writer final p1', 'final', 'p1', 'writer_final_p1', 'ALL_WRITTEN')
    writer('writer final p2 (second pass)', 'final', 'p2', 'writer_final_p2', 'ALL_WRITTEN')
    check('the practice set, the final set and every written pass name one writer model',
          {load('questions/writer_state_%s_%s.json' % (s, p))['model'] for s, p in (('practice', 'p1'), ('practice', 'p2'), ('practice', 'p3'), ('final', 'p1'), ('final', 'p2'))}
          == {'DRY-FIXTURE-NO-MODEL'})
    checked, decided = solve_set('final', 'all', '01')
    check('check final with no p3 file: the first two passes are read and p3 is named as missing (a dry fixture only; seal step 3C needs every pass)',
          checked['printed'].get('passes_read') == ['p1', 'p2'] and checked['printed'].get('passes_missing') == ['p3'],
          {'read': checked['printed'].get('passes_read'), 'missing': checked['printed'].get('passes_missing')})
    check('2 final role-step questions and 2 final plain-fact questions (p1 and p2) pass both solver checks', decided['printed']['counts']['survive'] == {'role_step': 2, 'plain_fact': 2},
          decided['printed']['counts'])
    step = expect_status('select final', S, ['select', '--set', 'final'], 'GO', exit_code=0)
    selection = load('select/selection_final.json')
    check('the final selection holds 1 role-step task and 1 plain-fact task; the plain-fact task is the p1 one and V903.p2.FACT is LATER_PASS_NOT_NEEDED',
          (step['printed']['counts']['role_step_tasks'], step['printed']['counts']['plain_fact_tasks']) == (1, 1)
          and [t['pass_used'] for t in selection['tasks'] if t['family'] == 'plain_fact'] == ['p1']
          and ('V903.p2.FACT', 'LATER_PASS_NOT_NEEDED') in {(d['question_id'], d['reason']) for d in selection['dropped']}
          and 'SAME_RIGHT_THING' in {d['reason'] for d in selection['dropped']}, selection['dropped'])
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
        stray + LF + ANSWERS_MADE[('final', 'with_passage', '01')], encoding='utf-8', newline=LF)
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
    check('the import step, run as its own process with its output sent to a pipe, ends with exit code 0 on a stray line that holds an arrow sign (4 final items)',
          done.returncode == 0 and printed.get('status') == 'SHEET_IMPORTED' and printed.get('readable') == 4
          and printed.get('first_such_lines') == [stray] and b'Traceback' not in done.stderr,
          {'exit': done.returncode, 'status': printed.get('status'), 'readable': printed.get('readable'), 'stderr': done.stderr.decode('utf-8', 'replace')[-300:]})

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
