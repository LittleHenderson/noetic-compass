"""[DRY FIXTURE, NOT A RESULT] Dry run of the four note tools on made-up passages.

Tools walked through, with no outside call and no key:
  tools/ob_write_ordinary_notes.py   tools/ob_check_support.py
  tools/ob_screen_notes.py           tools/ob_assemble.py

Everything in this folder is made up: the passages, the role entries, the questions, the keys, the
notes, the checker verdicts, the seal lines and the clock. Nothing here is a case. Nothing here is a
result. The only real text is the canon definition lines, which this script reads from Part A of the
labeling guide by the plan's own rule (it does not retype them), and, by amendment A13, the canonical
sayings lines. The sayings lines are read by read_sayings() of tools/ob_role_notes.py from the real
canon file docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, read-only. That file is canon text, not study
data. Nothing is retyped.

What this script does:
  1. It removes what an earlier run of this script wrote in this folder, and builds the inputs again.
  2. It runs the four tools in this folder (--work), feeding made-up replies through --replay-replies.
  3. It checks what each tool did against what was expected, and writes dry_run_log.json.
  4. It walks the rule "a note the writer can not produce" (plan section 10, Step 7) in two folders
     of their own, not_written_case/ and not_written_guard/, built from the same made-up passages.

Run:  python -B optionb/dry/fixture_n/run_dry_n.py
Exit code 0: every check held. Exit code 1: at least one check did not hold.
"""
import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if (HERE.name, HERE.parent.name, HERE.parent.parent.name) != ('fixture_n', 'dry', 'optionb'):
    raise SystemExit('This script runs only as optionb/dry/fixture_n/run_dry_n.py.')
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import ob_assemble as A            # noqa: E402
import ob_check_support as K       # noqa: E402
import ob_role_notes as R          # noqa: E402  (only read_sayings(): the sayings lines, copied from the canon file)
import ob_screen_notes as N        # noqa: E402
import ob_write_ordinary_notes as W  # noqa: E402

LF = chr(10)
TAG = ' [DRY FIXTURE, NOT A RESULT]'
FIXED_UTC = '2026-10-05T00:00:00Z'
MADE_BY = {'program': 'optionb/dry/fixture_n/run_dry_n.py' + TAG, 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'utc': FIXED_UTC}
S = 'casalescence/optionb/'
MADE_FOLDERS = ['elig', 'notes_role', 'questions', 'checks', 'solve', 'select', 'notes_ord', 'support', 'screen', 'prompts',
                'keys_practice', 'keys_final', 'review', 'assemble', 'replay', 'not_written_case', 'not_written_guard']
MADE_FILES = ['SEAL_OPTIONB.jsonl', 'removal_log.json', 'DRY_CONSTANT_OVERRIDES.json', 'dry_run_log.json']
OVERRIDES = {
    'note': 'MADE-UP. Dry fixture only. The four floors and the no-launch line are lowered so that a handful of made-up passages can walk '
            'through every step. A tool reads this file only when its work folder sits under optionb/dry/. The real floors are 100, 100, 36 and 20.',
    'launch_floor': {'final_role_step_tasks_min': 2, 'final_plain_fact_tasks_min': 2, 'practice_role_step_tasks_min': 2, 'practice_plain_fact_tasks_min': 2},
    'tiers': {'no_launch_below_final_role_step_tasks': 2},
    # plan v1.1 dry edition: this fixture fabricates two writer passes by hand, so the pass list is pinned to them here (the real plan has p1, p2, p3).
    'outside_services': {'gemini_question_writer': {'passes': ['p1', 'p2']}}}
# made-up model names that the made-up service "puts in its reply" (amendment A9: the tools store them as model_in_reply)
NOTE_WRITER_NAME = 'MADE-UP-NAME-IN-A-NOTE-WRITER-REPLY'
CHECKER_NAME = 'MADE-UP-NAME-IN-A-CHECKER-REPLY'

# ---------------------------------------------------------------- the made-up passages

PEOPLE = [
    dict(id='V901', set='practice', name='Tamsin', pron='She', place='boat shed', liked='tar brush', other='wire brush', disliked='bilge pump', obj='lantern', spot='shelf', thing='coil of rope'),
    dict(id='V902', set='practice', name='Odran', pron='He', place='net loft', liked='bone needle', other='steel needle', obj='kettle', spot='stove', thing='ball of twine'),
    dict(id='V903', set='practice', name='Ilse', pron='She', place='seed store', liked='oak scoop', other='tin scoop', obj='ledger', spot='counter', thing='sack of barley'),
    dict(id='V904', set='practice', name='Bram', pron='He', place='forge', liked='cross hammer', other='ball hammer', disliked='leaky bellows', obj='quench bucket', spot='stone floor', thing='pair of tongs'),
    dict(id='V905', set='practice', name='Maren', pron='She', place='dye house', liked='copper ladle', other='iron ladle', obj='drying rack', spot='back wall', thing='tub of madder'),
    dict(id='V906', set='final', name='Corin', pron='He', place='bell tower', liked='hemp rope', other='nylon rope', disliked='loose stair', obj='oil can', spot='window ledge', thing='pair of gloves'),
    dict(id='V907', set='final', name='Edda', pron='She', place='apple loft', liked='wicker tray', other='wire tray', obj='step stool', spot='landing', thing='heap of straw'),
    dict(id='V908', set='final', name='Joss', pron='He', place='tile yard', liked='wooden mould', other='metal mould', obj='wheelbarrow', spot='gravel path', thing='stack of pallets'),
    dict(id='V909', set='final', name='Wren', pron='She', place='map room', liked='brass ruler', other='plastic ruler', obj='globe', spot='side table', thing='roll of tape'),
    dict(id='V910', set='final', name='Fenn', pron='He', place='ice house', liked='long saw', other='short saw', obj='sledge', spot='ramp', thing='bale of sawdust'),
    dict(id='V911', set='final', name='Liesel', pron='She', place='weigh house', liked='small scale', other='large scale', disliked='cracked weight', obj='brass pan', spot='bench', thing='box of chalk',
         extra='She checked that every weight was correct.'),
    dict(id='V912', set='final', name='Ansel', pron='He', place='sail loft', liked='curved needle', other='straight needle', disliked='blunt shears', obj='wax pot', spot='trestle', thing='bolt of canvas'),
    dict(id='V913', set='final', name='Petra', pron='She', place='clock shop', liked='fine tweezers', other='flat pliers', disliked='sticky oil', quoted=True, obj='loupe', spot='felt mat', thing='tray of springs'),
    dict(id='V914', set='practice', name='Hale', pron='He', place='rope walk', liked='long spindle', other='short spindle', obj='tally board', spot='end post', thing='bucket of tallow', eligible=False),
    dict(id='V915', set='final', name='Sunniva', pron='She', place='salt store', liked='birch rake', other='iron rake', obj='hand cart', spot='loading step', thing='pile of sacks', eligible=False),
]
SETTINGS = {'practice': 'fixture practice yard', 'final': 'fixture final yard'}
MARKERS = ('three boats', 'built in 1950')    # a made-up checker says FAIL when a note holds one of these
NOTE_EXTRA = {
    ('V902', 'ORD-INFORMED', '100', 1): ' He also owns three boats.',                       # not supported: fails once, the rewrite is clean
    ('V907', 'ORD-FREE', '090', 1): ' The loft was built in 1950.',                         # not supported: fails twice, the passage is dropped
    ('V907', 'ORD-FREE', '090', 2): ' The loft was built in 1950.',
}
# planted for the answer-leak screen; the same text in both versions, so that a rewrite does not remove it
for _key, _text in {
        ('V903', 'ORD-FREE', '110'): ' Next week it will be reaching for the oak scoop again.',   # rule (c): an option that is not passage text
        ('V908', 'ORD-INFORMED', '090'): ' The side gate (B) is kept shut.',                 # rule (a): a letter written as a choice
        ('V909', 'ORD-FREE', '100'): ' The correct ruler is easy to find.',                  # rule (d): the word correct
        ('V910', 'ORD-INFORMED', '110'): ' A free hour comes up next week.',                 # rule (b): a sentence of the question
        ('V911', 'ORD-INFORMED', '100'): ' She checks that every weight is correct.',        # no hit: the passage holds the word once as well
}.items():
    NOTE_EXTRA[_key + (1,)] = NOTE_EXTRA[_key + (2,)] = _text
NOTE_PICK = {('ORD-INFORMED', '090'): [1, 2], ('ORD-INFORMED', '100'): [0, 1, 2], ('ORD-INFORMED', '110'): [0, 1, 2, 3],
             ('ORD-FREE', '090'): [0, 2], ('ORD-FREE', '100'): [0, 2, 3], ('ORD-FREE', '110'): [0, 1, 3, 2]}
# made-up outcomes of the question checks, so that the removal log has something of every kind
FORM_FAIL = {'V905.p1.GOES_FOR': ['OPTION_LENGTH_SPREAD', 'FORBIDDEN_LIST_C:drawn']}
OPTION_FAIL = {'V904.p1.KEEPS_AWAY', 'V904.p2.KEEPS_AWAY'}
KEY_FAIL = {'V912.p1.KEEPS_AWAY'}
NO_PASSAGE_FAIL = {'V906.p1.KEEPS_AWAY'}
BACKSTOP = {'V911.p1.KEEPS_AWAY'}
WRITER_MISSING = {('V903', 'p2')}
WRITES_A_FORM_THAT_IS_NOT_OPEN = {('V902', 'p1')}
BY_ID = {p['id']: p for p in PEOPLE}


def sents(p):
    out = ['%s opened the %s before dawn.' % (p['name'], p['place']),
           '%s always reached for the %s before the %s.' % (p['pron'], p['liked'], p['other']),
           'The %s stood on the %s by the door.' % (p['obj'], p['spot']),
           'A %s lay beside it.' % p['thing']]
    if p.get('disliked'):
        if p.get('quoted'):
            out.append('"Not near my bench," %s said, and kept well away from the %s.' % (p['pron'].lower(), p['disliked']))
        else:
            out.append('%s kept well away from the %s.' % (p['pron'], p['disliked']))
    if p.get('extra'):
        out.append(p['extra'])
    return out


def text_of(p):
    return ' '.join(sents(p))


def note_text(p, group, length, version):
    base = ['%s opens the %s before dawn.' % (p['name'], p['place']),
            '%s reaches for the %s before the %s.' % (p['name'], p['liked'], p['other']),
            'The %s stands on the %s by the door.' % (p['obj'], p['spot']),
            'A %s lies beside the %s.' % (p['thing'], p['obj'])]
    return ' '.join(base[i] for i in NOTE_PICK[(group, length)]) + NOTE_EXTRA.get((p['id'], group, length, version), '')


def q_goes(p):
    return {'question': 'A free hour comes up next week. Going only by the passage, which of these does %s do first?' % p['name'],
            'right': 'reaching for the %s again' % p['liked'],
            'wrong': ['reaching for the %s again' % p['other'], 'moving the %s to the yard' % p['obj'], 'hanging the %s on a hook' % p['thing'].split()[-1],
                      'sweeping the %s floor twice' % p['place'].split()[-1], 'leaving the door wide open'],
            'anchors': ['reached for the %s' % p['liked']]}


def q_keeps(p):
    bad = p.get('disliked') or 'old winch'
    return {'question': 'A visitor asks for help later that day. Going only by the passage, which of these does %s leave to someone else?' % p['name'],
            'right': 'working on the %s' % bad,
            'wrong': ['working with the %s' % p['liked'], 'carrying the %s outside' % p['obj'], 'counting every %s there' % p['thing'].split()[-1],
                      'locking up the %s' % p['place'], 'lighting the big lamp'],
            'anchors': ['away from the %s' % bad]}


def q_fact(p):
    return {'question': 'Where did the %s stand?' % p['obj'], 'right': 'on the %s' % p['spot'], 'wrong': ['under the bench', 'behind the gate', 'inside the cart']}


def open_forms(p):
    if p.get('eligible') is False:
        return []
    return ['GOES_FOR'] + (['KEEPS_AWAY'] if p.get('disliked') else [])


# ---------------------------------------------------------------- small helpers

def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def dump(name, schema, body):
    doc = {'schema': schema, 'made_by': MADE_BY, 'inputs': []}
    doc.update(body)
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline=LF) as stream:
        stream.write(json.dumps(doc, indent=1, ensure_ascii=False) + LF)
    return path


def load(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def write_text(name, text):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline=LF) as stream:
        stream.write(text)
    return path


def seal_append(step, names):
    """A made-up seal line, in the form of FILE_FORMATS.md section 15. Written by this script, not by tools/ob_seal.py."""
    seal = HERE / 'SEAL_OPTIONB.jsonl'
    lines = [line for line in seal.read_bytes().split(b'\n') if line.strip()] if seal.exists() else []
    files = []
    for name in names:
        data = (HERE / name).read_bytes()
        files.append({'path': rel(HERE / name), 'package_path': None, 'bytes': len(data), 'sha256': sha(data)})
    row = {'schema': S + 'seal-step/v1', 'n': len(lines) + 1, 'step': step, 'utc': FIXED_UTC, 'files': files, 'values': {},
           'who_could_open': 'DRY FIXTURE: a made-up line written by run_dry_n.py', 'previous_line_sha256': sha(lines[-1]) if lines else None,
           'made_by': MADE_BY}
    with open(seal, 'ab') as stream:
        stream.write(json.dumps(row, ensure_ascii=False).encode('utf-8') + b'\n')


LOG = {'steps': [], 'checks': []}


def run(label, module, argv):
    """Run one tool in this folder. Returns its exit code (2 for a clean stop), its stop code and what it printed."""
    buffer, exit_code, stop = io.StringIO(), None, None
    with contextlib.redirect_stdout(buffer):
        try:
            exit_code = module.main(list(argv) + ['--work', str(HERE)])
        except module.Stop as halt:
            exit_code, stop = 2, {'code': halt.args[0], 'reason': halt.args[1]}
    text = buffer.getvalue().strip()
    out = json.loads(text) if text else {}
    step = {'label': label, 'tool': module.PROGRAM, 'argv': list(argv), 'exit': exit_code, 'stop': stop,
            'status': out.get('status'), 'printed': out}
    LOG['steps'].append(step)
    return step


def quiet(module, argv):
    """Run a tool for its side effect only (the plan is written again). Not counted as a step."""
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            module.main(list(argv) + ['--work', str(HERE)])
        except module.Stop:
            pass


def check(name, held, detail=''):
    LOG['checks'].append({'check': name, 'held': bool(held), 'detail': detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)})
    return held


def expect_stop(label, module, argv, code):
    step = run(label, module, argv)
    check('%s -> stops with %s' % (label, code), step['stop'] is not None and step['stop']['code'] == code, step['stop'] or step['status'] or '')
    return step


def expect_status(label, module, argv, status, exit_code=None):
    step = run(label, module, argv)
    held = step['status'] == status and (exit_code is None or step['exit'] == exit_code)
    check('%s -> status %s%s' % (label, status, '' if exit_code is None else ', exit %d' % exit_code), held,
          {'status': step['status'], 'exit': step['exit'], 'stop': step['stop']})
    return step


# ---------------------------------------------------------------- building the inputs

def clean_start():
    for name in MADE_FOLDERS:
        if (HERE / name).is_dir():
            shutil.rmtree(HERE / name)
    for name in MADE_FILES:
        if (HERE / name).exists():
            (HERE / name).unlink()


def canon_from_guide(C):
    """The canon lines and names, read from Part A of the labeling guide by the plan's rule. Not retyped.

    Also the sayings lines of amendment A13. The role-note tool's own function reads them from the
    pinned canon file, with its three refusals. Returns (canon lines, names, sayings lines).
    """
    rule, source = C['role_notes'], C['sources']['labeling_guide']
    data = (ROOT / source['path']).read_bytes()
    if sha(data) != source['sha256']:
        raise SystemExit('The labeling guide does not have the pinned hash.')
    text = data.decode('utf-8').replace('\r\n', LF)
    part = text[text.find(rule['canon_section_start']):text.find(rule['canon_section_end'])]
    pattern, lines, names = re.compile(rule['canon_line_regex']), {}, {}
    for line in part.split(LF):
        found = pattern.match(line)
        if found and found.group(1) in rule['canon_noetics_used']:
            lines[found.group(1)] = W.fill(rule['canon_note_line'], {'NOETIC': found.group(1), 'NAME': found.group(2), 'DEFINITION': found.group(3)})
            names[found.group(1)] = found.group(2)
    sayings, _ = R.read_sayings(ROOT, C)
    return lines, names, sayings


def build_role_note(C, p, lines, names, sayings):
    rule, swap = C['role_notes'], C['role_notes']['mixed_swap_table']
    text, parts = text_of(p), sents(p)
    entries = [{'noetic': '^1', 'label': p['name'], 'mind': '', 'relative_to': '', 'supporting_quote': None},
               {'noetic': '^2', 'label': 'the ' + p['liked'], 'mind': p['name'], 'relative_to': '', 'supporting_quote': parts[1]}]
    if p.get('disliked'):
        entries.append({'noetic': '^3', 'label': 'the ' + p['disliked'], 'mind': p['name'], 'relative_to': '', 'supporting_quote': parts[4]})
    for index, entry in enumerate(entries):
        entry.update({'name': names[entry['noetic']], 'mixed_noetic': swap[entry['noetic']], 'mixed_name': names[swap[entry['noetic']]],
                      'same_as_label': None, 'offset': text.find(entry['label']), 'a_index': index, 'b_index': index})

    def line(entry, tag, name, blank):
        value = (lambda x: '') if blank else (lambda x: x)
        if entry['noetic'] == '^1':
            return W.fill(rule['line_mind_entry'], {'NOETIC': tag, 'NAME': name, 'LABEL': value(entry['label'])})
        out = W.fill(rule['line_entry_start'], {'NOETIC': tag, 'NAME': name, 'LABEL': value(entry['label'])})
        if entry['mind']:
            out += W.fill(rule['line_part_mind'], {'MIND': value(entry['mind'])})
        if entry['relative_to']:
            out += W.fill(rule['line_part_relative'], {'RELATIVE_TO': value(entry['relative_to'])})
        return out + W.fill(rule['line_part_quote'], {'QUOTE': value(entry['supporting_quote'])})

    def quote_line(entry, blank):
        value = (lambda x: '') if blank else (lambda x: x)
        out = W.fill(rule['quotes_only_line_start'], {'LABEL': value(entry['label'])})
        if entry['supporting_quote'] is not None:
            out += W.fill(rule['line_part_quote'], {'QUOTE': value(entry['supporting_quote'])})
        return out

    def note(tag_field, name_field, blank):
        tags = sorted({entry[tag_field] for entry in entries}, key=lambda t: int(t[1:]))
        head = [one for t in tags for one in (lines[t], sayings[t])]      # amendment A13: the canon line, then its sayings line
        return LF.join(head + [line(entry, entry[tag_field], entry[name_field], blank) for entry in entries])

    role_text = note('noetic', 'name', False)
    size_rule, word_rule = re.compile(rule['size_count_regex']), re.compile(C['question_rules']['word_sequence_regex'])
    order = ['noetic', 'name', 'mixed_noetic', 'mixed_name', 'label', 'mind', 'relative_to', 'supporting_quote', 'same_as_label', 'offset', 'a_index', 'b_index']
    return {'id': p['id'], 'entries': [{name: entry[name] for name in order} for entry in entries],
            'role_text': role_text, 'mixed_text': note('mixed_noetic', 'mixed_name', False),
            'quotes_only_text': LF.join(quote_line(entry, False) for entry in entries),
            'frame_blanked': {'role': note('noetic', 'name', True), 'mixed': note('mixed_noetic', 'mixed_name', True),
                              'quotes_only': LF.join(quote_line(entry, True) for entry in entries)},
            'size': {'role_size_count': len(size_rule.findall(role_text)), 'role_words': len(word_rule.findall(role_text)),
                     'passage_size_count': len(size_rule.findall(text)), 'passage_words': len(word_rule.findall(text))},
            'left_out': {'only_a': {}, 'only_b': {}}}


def build_inputs(C):
    lines, names, sayings = canon_from_guide(C)
    sayings_source = C['sources'][C['role_notes']['sayings_source_key']]
    write_text('DRY_CONSTANT_OVERRIDES.json', json.dumps(OVERRIDES, indent=1, ensure_ascii=False) + LF)

    passages = []
    for p in PEOPLE:
        eligible, forms = p.get('eligible') is not False, open_forms(p)
        agreed = {'^1': 1, '^2': 1}
        if p.get('disliked'):
            agreed['^3'] = 1
        passages.append({'id': p['id'], 'kind': 'K2', 'setting': SETTINGS[p['set']], 'text': text_of(p), 'setting_role': p['set'], 'writer_asks': True,
                         'excluded': False, 'barred': False, 'eligible': eligible, 'agreed': agreed if eligible else {'^1': 1}, 'only_a': {}, 'only_b': {},
                         'open_forms': forms, 'open_types': ['PULL-PUSH'] if forms else [], 'max_role_step_tasks': min(2, len(forms)),
                         'leftover_on_type': {'PULL-PUSH': False} if forms else {}, 'any_leftover_2_to_9': False,
                         'entries': {'agreed': [], 'only_a': [], 'only_b': []}})
    dump('elig/eligibility.json', S + 'eligibility/v1', {
        'practice_settings': [SETTINGS['practice']], 'reserve_settings_in_order': [], 'counts': {'passages': len(passages)},
        'counts_match_plan': False, 'passages': passages})
    dump('elig/exclusions.json', S + 'exclusions/v1', {'count': 0, 'by_kind': {}, 'passages': []})
    dump('notes_role/role_notes.json', S + 'role_notes/v1', {
        'canon': {'source': C['sources']['labeling_guide']['path'], 'sha256': C['sources']['labeling_guide']['sha256'], 'lines': lines, 'names': names,
                  'sayings_source': sayings_source['path'], 'sayings_sha256': sayings_source['sha256'], 'sayings_lines': sayings},
        'passages': [build_role_note(C, p, lines, names, sayings) for p in PEOPLE if p.get('eligible') is not False]})

    for set_name in ('practice', 'final'):
        people = [p for p in PEOPLE if p['set'] == set_name]
        raw, form_rows, anchor_rows, option_rows, by_question = {'p1': [], 'p2': []}, [], [], [], {}
        for pass_name in ('p1', 'p2'):
            for p in people:
                if (p['id'], pass_name) in WRITER_MISSING:
                    raw[pass_name].append({'passage_id': p['id'], 'wave': 0, 'batch': 0, 'status': 'MISSING', 'what_follows': [], 'plain_fact': None, 'extra_dropped': []})
                    continue
                forms = ['GOES_FOR'] + (['KEEPS_AWAY'] if p.get('disliked') or (p['id'], pass_name) in WRITES_A_FORM_THAT_IS_NOT_OPEN else [])
                what_follows = []
                for form in forms:
                    question = dict({'question_id': '%s.%s.%s' % (p['id'], pass_name, form), 'form': form}, **(q_goes(p) if form == 'GOES_FOR' else q_keeps(p)))
                    what_follows.append(question)
                    by_question[question['question_id']] = dict(question, passage_id=p['id'], family='role_step', **{'pass': pass_name})
                fact = dict({'question_id': '%s.%s.FACT' % (p['id'], pass_name)}, **q_fact(p))
                by_question[fact['question_id']] = dict(fact, passage_id=p['id'], family='plain_fact', form='FACT', anchors=[], **{'pass': pass_name})
                extra = [dict({'form': 'GOES_FOR'}, **q_goes(p))] if (p['id'], pass_name) == ('V901', 'p1') else []
                raw[pass_name].append({'passage_id': p['id'], 'wave': 0, 'batch': 0, 'status': 'OK', 'what_follows': what_follows, 'plain_fact': fact, 'extra_dropped': extra})
            dump('questions/raw_questions_%s_%s.json' % (set_name, pass_name), S + 'raw_questions/v1',
                 {'set': set_name, 'pass': pass_name, 'model': 'DRY-FIXTURE-NO-MODEL', 'passages': raw[pass_name]})

        def ok_form(qid):
            return qid in by_question and qid not in FORM_FAIL

        def anchor_reason(qid):
            p = BY_ID[by_question[qid]['passage_id']]
            if p.get('eligible') is False:
                return 'PASSAGE_NOT_ELIGIBLE'
            return None if by_question[qid]['form'] in open_forms(p) else 'FORM_NOT_OPEN'

        def ok_all(qid):
            if not ok_form(qid):
                return False
            return by_question[qid]['family'] == 'plain_fact' or (anchor_reason(qid) is None and qid not in OPTION_FAIL)

        for qid, question in sorted(by_question.items()):
            form_rows.append({'question_id': qid, 'family': question['family'], 'passed': ok_form(qid), 'reasons': FORM_FAIL.get(qid, [])})
            if question['family'] == 'role_step' and ok_form(qid):
                reason = anchor_reason(qid)
                anchor_rows.append({'question_id': qid, 'passed': reason is None, 'reason': reason,
                                    'matched': [] if reason else [{'anchor': question['anchors'][0], 'noetic': '^2' if question['form'] == 'GOES_FOR' else '^3',
                                                                   'agreed_index': 0, 'field': 'words_a'}]})
                if reason is None:
                    hits = [{'option_index': 2, 'option': question['wrong'][1], 'noetic': '^3', 'team': 'b', 'entry_index': 4, 'field': 'words'}] if qid in OPTION_FAIL else []
                    option_rows.append({'question_id': qid, 'passed': not hits, 'hits': hits})
        dump('checks/form_check_%s.json' % set_name, S + 'form_check/v1', {'set': set_name, 'rows': form_rows, 'counts': {'checked': len(form_rows)}})
        dump('checks/anchor_check_%s.json' % set_name, S + 'anchor_check/v1', {'set': set_name, 'rows': anchor_rows, 'counts': {'checked': len(anchor_rows)}})
        dump('checks/option_check_%s.json' % set_name, S + 'option_check/v1', {'set': set_name, 'rows': option_rows, 'counts': {'checked': len(option_rows)}})

        # plan v1.1 candidate rule: every question of every pass that passes the checks is a candidate (no spare rule)
        candidates = []
        for chosen in sorted(by_question):
            if ok_all(chosen):
                question = by_question[chosen]
                candidates.append({'question_id': chosen, 'passage_id': question['passage_id'], 'family': question['family'], 'form': question['form'],
                                   'pass': question['pass'], 'passage': text_of(BY_ID[question['passage_id']]), 'question': question['question'],
                                   'right': question['right'], 'wrong': question['wrong'], 'anchors': question['anchors']})
        dump('checks/candidates_%s.json' % set_name, S + 'candidates/v1', {'set': set_name, 'candidates': candidates, 'counts': {}})
        key_rows = []
        for candidate in candidates:
            qid = candidate['question_id']
            # the made-up fail sets name p1 ids; the p2 twin of a question gets the same outcome, so the pair counts worked out by hand still hold
            twin = qid.replace('.p2.', '.p1.')
            key_ok, guess_ok = twin not in KEY_FAIL, twin not in NO_PASSAGE_FAIL
            key_rows.append({'question_id': qid, 'family': candidate['family'],
                             'with_passage': {'deepseek-chat': 'RIGHT' if key_ok else 'WRONG', 'claude-sonnet-subagent': 'RIGHT'}, 'key_check_passed': key_ok,
                             'no_passage': {'deepseek-chat': 'WRONG' if guess_ok else 'RIGHT', 'claude-sonnet-subagent': 'RIGHT'}, 'no_passage_passed': guess_ok,
                             'survives': key_ok and guess_ok})
        dump('solve/key_check_%s.json' % set_name, S + 'key_check/v1', {'set': set_name, 'rows': key_rows, 'counts': {}})
        survive = {row['question_id'] for row in key_rows if row['survives']}
        tasks, dropped = [], []
        # plan v1.1 Step 6: per passage and form the survivors are reduced to the lowest pass; the others are LATER_PASS_NOT_NEEDED
        lowest = {}
        for candidate in sorted(candidates, key=lambda c: (c['passage_id'], c['form'], c['pass'])):
            if candidate['question_id'] in survive and BY_ID[candidate['passage_id']].get('eligible') is not False:
                lowest.setdefault((candidate['passage_id'], candidate['form']), candidate['question_id'])
        for candidate in candidates:
            qid, p = candidate['question_id'], BY_ID[candidate['passage_id']]
            if qid not in survive or p.get('eligible') is False:
                continue
            if lowest[(candidate['passage_id'], candidate['form'])] != qid:
                dropped.append({'question_id': qid, 'reason': 'LATER_PASS_NOT_NEEDED'})
                continue
            if qid in BACKSTOP:
                dropped.append({'question_id': qid, 'reason': 'LENGTH_BACKSTOP_LONGEST'})
                continue
            fact = candidate['family'] == 'plain_fact'
            tasks.append({'task_id': '%s.%s' % (p['id'], candidate['form']), 'passage_id': p['id'], 'question_id': qid, 'family': candidate['family'],
                          'type': 'FACT' if fact else 'PULL-PUSH', 'form': candidate['form'], 'pass_used': candidate['pass'],
                          'question': candidate['question'], 'right': candidate['right'],
                          'wrong': candidate['wrong'], 'anchors': candidate['anchors'], 'anchors_matched': candidate['anchors'],
                          'right_is_single_longest': False, 'right_is_single_shortest': False})
        body = {'set': set_name, 'practice_setting_count': 8, 'tasks': tasks, 'dropped': dropped, 'counts': {}}
        if set_name == 'practice':
            # made-up blocks in the form of FILE_FORMATS.md section 7.1 (review round 1: both task families, and the reserve block)
            body['floor'] = {'practice_role_step_min': 2, 'practice_plain_fact_min': 2, 'met': True}
            body['reserve'] = {'role_step_target': 2, 'plain_fact_target': 2, 'target_met': True, 'settings_left': 4, 'finished': True}
        dump('select/selection_%s.json' % set_name, S + 'selection/v1', body)
    dump('select/split_fixed.json', S + 'split_fixed/v1', {
        'practice_setting_count': 8, 'practice_settings': [SETTINGS['practice']], 'final_settings': [SETTINGS['final']],
        'history': [{'practice_setting_count': 8, 'practice_role_step_tasks': 6, 'practice_plain_fact_tasks': 5, 'target_met': True}],
        'reserve_target_met': True, 'floor_met': True,
        'final_writer_passage_ids': sorted(p['id'] for p in PEOPLE if p['set'] == 'final')})


def set_files(set_name, folders):
    out = []
    for folder in folders:
        out += sorted(path.relative_to(HERE).as_posix() for path in (HERE / folder).glob('*') if path.is_file() and ('_%s' % set_name) in path.name)
    return out


# ---------------------------------------------------------------- made-up replies

def note_replay(name, set_name, version, special=None):
    """A reply table for the note writer: one made-up note per note id. special overrides single entries."""
    table = {}
    for p in PEOPLE:
        if p['set'] != set_name or p.get('eligible') is False:
            continue
        for group, length in NOTE_PICK:
            note_id = '%s|%s|%s|v%d' % (p['id'], group, length, version)
            table[note_id] = {'http_status': 200, 'model': NOTE_WRITER_NAME, 'content': '  ' + note_text(p, group, length, version) + '\r\n'}
    table.update(special or {})
    return str(write_text('replay/%s.json' % name, json.dumps(table, indent=1, ensure_ascii=False) + LF))


def support_view(set_name):
    state, items = load('support/support_state_%s.json' % set_name), load('support/support_items_%s.json' % set_name)
    results, notes = load('support/support_results_%s.json' % set_name), load('notes_ord/ordinary_notes_%s.json' % set_name)
    text = {}
    for passage in notes['passages']:
        for group, by_length in passage['notes'].items():
            for length, slot in by_length.items():
                for version in slot['versions']:
                    text['%s|%s|%s|v%d' % (passage['passage_id'], group, length, version['version'])] = version['text']
    note_of = {item['item_id']: item['note_id'] for item in items['items']}
    done = {row['item_id'] for row in results['results']}
    return {'state': state, 'items': items['items'], 'results': results, 'note_text': {i: text[n] for i, n in note_of.items()}, 'note_of': note_of, 'done': done}


def made_up_verdict(view, item_id):
    return 'FAIL' if any(marker in view['note_text'][item_id] for marker in MARKERS) else 'PASS'


def next_open(view):
    for one_round in view['state']['rounds']:
        for batch in one_round['batches']:
            if batch['status'] == 'PENDING':
                return one_round['round'], batch, [i for i in batch['item_ids'] if i not in view['done']]
    return None, None, []


COUNTER = [0]


def gemini_call(set_name, now, kind, budget=1):
    """One or more made-up calls of the first checker. kind says what the made-up service answers."""
    quiet(K, ['gemini', '--set', set_name, '--max-calls', '0', '--dry-now', now])   # the plan is brought up to date first
    view = support_view(set_name)
    _, batch, open_items = next_open(view)
    full = [{'item': i, 'verdict': made_up_verdict(view, i)} for i in open_items]
    steps = {'full': [{'http_status': 200, 'model': CHECKER_NAME, 'content_json': full}],
             'partial': [{'http_status': 200, 'model': CHECKER_NAME, 'content': '```json' + LF + json.dumps(full[:-2]) + LF + '```'}],
             'garbage': [{'http_status': 200, 'content': 'I am sorry, I can not help with that.'}],
             'garbage_twice': [{'http_status': 200, 'content': 'no JSON here'}, {'http_status': 200, 'content': '[{"item": "X", "verdict": "MAYBE"}]'}],
             'daily_cap': [{'http_status': 429, 'error': 'HTTPError 429: made-up: quota exceeded, limit GenerateRequestsPerDayPerProjectPerModel-FreeTier'}],
             'minute_limit_three_times': [{'http_status': 429, 'error': 'HTTPError 429: made-up: too many requests per minute'}] * 3,
             'no_answer': [{'http_status': 0, 'error': 'URLError: made-up: no route'}]}[kind]
    COUNTER[0] += 1
    path = write_text('replay/support_%s_%03d_%s.json' % (set_name, COUNTER[0], kind), json.dumps(steps, indent=1, ensure_ascii=False) + LF)
    return run('support %s: gemini, made-up service answers %s' % (set_name, kind), K,
               ['gemini', '--set', set_name, '--max-calls', str(budget), '--replay-replies', str(path), '--dry-now', now])


def token_limit_checks(C):
    """Amendment A11: the DeepSeek token count of the note writer, on made-up call log lines. No service is called."""
    service = C['outside_services']['deepseek']
    rows = [{'usage': {'prompt_tokens': 10, 'completion_tokens': 4, 'total_tokens': 14}}, {'usage': None}, {},
            {'usage': {'prompt_tokens': 5}}, {'usage': {'prompt_tokens': 7, 'completion_tokens': True}},
            {'usage': {'prompt_tokens': 3, 'completion_tokens': 2}}]
    check('token count: the input and output counts are added up over the log lines; a line with no token count adds nothing',
          W.count_tokens(rows) == [13, 6] and W.usage_pair({'prompt_tokens': 1.5, 'completion_tokens': 2}) is None, W.count_tokens(rows))
    top_in, top_out = service['spend_cap_input_tokens'], service['spend_cap_output_tokens']
    check('token limit: reached when the input count is at its limit, or the output count is at its limit; not one token before',
          (top_in, top_out) == (2430240, 1156520) and W.limit_reached([top_in, 0], service) and W.limit_reached([0, top_out], service)
          and not W.limit_reached([top_in - 1, top_out - 1], service), {'input': top_in, 'output': top_out})
    ctx = W.Ctx(str(HERE))
    own = HERE / 'notes_ord' / 'ordinary_calls_practice.jsonl'
    check('token count: a dry folder calls no service and counts nothing', W.tokens_at_start(ctx, service, own) is None)
    # the same reader on four made-up logs, with a stand-in for a folder that is not dry (nothing is called)
    made = []
    for index, pair in enumerate(((100, 40), (30, 5), (7, 1), (0, 0))):
        name = 'replay/made_up_usage_log_%d.jsonl' % index
        write_text(name, ''.join(json.dumps({'usage': {'prompt_tokens': pair[0], 'completion_tokens': pair[1]}}) + LF for _ in range(2))
                   + json.dumps({'usage': None}) + LF)
        made.append(name)
    stand_in = type('NotDry', (), {'dry': False, 'work': HERE})()
    small = dict(service, spend_cap_counted_logs=made, spend_cap_input_tokens=275, spend_cap_output_tokens=1000)
    used = W.tokens_at_start(stand_in, small, HERE / made[0])
    check('token count: the four counted logs are read and added up (made-up logs: 274 input and 92 output tokens)', used == [274, 92], used)
    check('token limit: 274 of 275 input tokens is not yet the limit; one more token is', not W.limit_reached(used, small) and W.limit_reached([used[0] + 1, used[1]], small))
    try:
        W.tokens_at_start(stand_in, small, own)
        check('token count: a tool whose own call log is not one of the counted logs stops', False)
    except W.Stop as halt:
        check('token count: a tool whose own call log is not one of the counted logs stops', halt.args[0] == 'PLAN_DOES_NOT_MATCH_PROGRAM', halt.args[0])
    check('the plan names the two stop statuses of the token count', (service['spend_cap_stop_status'], service['spend_cap_no_count_status'])
          == ('STOPPED_TOKEN_CAP', 'STOPPED_NO_TOKEN_COUNT'))
    check('the four counted logs of the plan include both logs of the note writer',
          all('notes_ord/ordinary_calls_%s.jsonl' % s in service['spend_cap_counted_logs'] for s in ('practice', 'final')), service['spend_cap_counted_logs'])


# ---------------------------------------------------------------- a note the writer can not produce

def slot_of(set_name, note_id):
    passage_id, group, length = note_id.split('|')[:3]
    row = [p for p in load('notes_ord/ordinary_notes_%s.json' % set_name)['passages'] if p['passage_id'] == passage_id][0]
    return row['notes'][group][length]


def seal_up_to_3b():
    seal_append('1_PLAN_AND_SOURCES', ['elig/eligibility.json', 'elig/exclusions.json'])
    seal_append('2_ROLE_NOTES', ['notes_role/role_notes.json'])
    seal_append('3A_PRACTICE_QUESTIONS_AND_KEYS', set_files('practice', ['questions', 'checks', 'solve', 'select']))
    seal_append('3B_PRACTICE_SET_FIXED', ['select/split_fixed.json'])


def not_written_case(C):
    """Plan section 10, Step 7, "A note the writer can not produce", walked through all four note tools.

    Practice set: one first version comes back empty, then cut off: the note is given up and its passage
    is dropped. Final set: one rewrite comes back empty twice: the same. Everything is made up.
    """
    global HERE
    rules = C['ordinary_notes']
    word = rules['not_written_status']
    main_folder, HERE = HERE, HERE / 'not_written_case'
    try:
        build_inputs(C)
        seal_up_to_3b()
        first = ['--set', 'practice', '--step', 'first', '--max-calls', '100', '--replay-replies']
        gone = 'V902|ORD-FREE|090|v1'
        good = lambda text: {'http_status': 200, 'model': NOTE_WRITER_NAME, 'content': text}      # noqa: E731
        step = expect_status('not written: practice, the reply for one note is empty', W,
                             first + [note_replay('nw_practice_empty', 'practice', 1, {gone: good('   ')})], 'STOPPED_NOTES_NOT_WRITTEN', 1)
        check('not written: after one empty reply the note is still due and nothing is given up',
              step['printed'].get('still_open_in_this_step') == 1 and step['printed'].get('empty_or_cut_off_replies_in_the_log') == {gone: 1}
              and slot_of('practice', gone) == {'target_words': slot_of('practice', gone)['target_words'], 'current': 1, 'not_written': None, 'versions': []},
              step['printed'].get('empty_or_cut_off_replies_in_the_log'))
        check('not written: every slot of the notes file holds the field not_written, in the place the format gives it',
              all(list(slot) == ['target_words', 'current', 'not_written', 'versions'] and slot['not_written'] is None
                  for p in load('notes_ord/ordinary_notes_practice.json')['passages'] for by_length in p['notes'].values() for slot in by_length.values()))
        step = expect_status('not written: practice, the same note gets no answer at all', W,
                             first + [note_replay('nw_practice_no_answer', 'practice', 1, {gone: {'http_status': 0, 'error': 'URLError: made-up: no route'}})],
                             'STOPPED_NOTES_NOT_WRITTEN', 1)
        check('not written: a call with no answer is not counted; the count for the note is still 1',
              step['printed'].get('empty_or_cut_off_replies_in_the_log') == {gone: 1} and slot_of('practice', gone)['not_written'] is None
              and step['printed'].get('calls_this_run') == 1 + C['outside_services']['deepseek']['transport_retries'], step['printed'].get('calls_this_run'))
        cut = dict(good('Odran opens the net loft before'), finish_reason='length')
        step = expect_status('not written: practice, the second reply for the note is cut off', W,
                             first + [note_replay('nw_practice_cut_off', 'practice', 1, {gone: cut})], 'ALL_WRITTEN', 0)
        want = {'version': 1, 'replies': 2, 'errors': ['REPLY_EMPTY', 'REPLY_CUT_OFF']}
        check('not written: after two such replies the note is given up: not_written is set, the note has no version, the step ends with exit code 0',
              slot_of('practice', gone)['not_written'] == want and slot_of('practice', gone)['versions'] == []
              and step['printed'].get('notes_given_up_after_2_such_replies') == [gone]
              and step['printed'].get('passages_dropped_because_a_note_was_given_up') == ['V902']
              and step['printed'].get('passages_beyond_the_guard_of_3') == [] and step['printed'].get('still_open_in_this_step') == 0,
              slot_of('practice', gone)['not_written'])
        step = expect_status('not written: practice, one more run', W, first + [note_replay('nw_practice_full', 'practice', 1)], 'ALL_WRITTEN', 0)
        log = [row for row in W.read_jsonl(HERE / 'notes_ord' / 'ordinary_calls_practice.jsonl') if row['note_id'] == gone]
        check('not written: the note is never asked for a third time; its two counted log lines carry the two errors of the plan',
              step['printed'].get('calls_this_run') == 0 and step['printed'].get('due_in_this_step_at_start') == 0
              and [(row['http_status'], row['ok'], row['error']) for row in log if row['http_status'] == 200]
              == [(200, False, 'REPLY_EMPTY'), (200, False, 'REPLY_CUT_OFF')] and sorted(rules['not_written_errors']) == ['REPLY_CUT_OFF', 'REPLY_EMPTY'],
              [(row['http_status'], row['error']) for row in log])

        # the support check: the passage is put in no batch and gets the status of the plan
        step = expect_status('not written: support practice, plan only', K, ['gemini', '--set', 'practice', '--max-calls', '0', '--dry-now', FIXED_UTC], 'STOPPED_CALL_BUDGET', 1)
        items = load('support/support_items_practice.json')['items']
        check('not written: the dropped passage is in no batch: 24 items for the 4 other passages, in 2 batches',
              len(items) == 24 and not [i for i in items if i['note_id'].startswith('V902|')] and step['printed']['batches'] == {'DONE': 0, 'PENDING': 2, 'UNREADABLE': 0},
              step['printed']['batches'])
        gemini_call('practice', FIXED_UTC, 'full')
        step = gemini_call('practice', FIXED_UTC, 'full')
        results = load('support/support_results_practice.json')
        check('not written: the practice set is ready for seal step 4 with one passage dropped for a note that could not be written',
              step['printed']['passages_by_status'] == {'ALL_PASS': 4, word: 1} and step['printed'].get('ready_for_seal_step_4') is True and step['exit'] == 0
              and [p for p in results['passages'] if p['passage_id'] == 'V902'] == [{'passage_id': 'V902', 'status': word, 'rewrite_note_ids': []}]
              and results['counts'] == {'notes_checked': 24, 'passed': 24, 'failed_once': 0, 'failed_twice': 0, 'passages_dropped': 0,
                                        'passages_dropped_note_not_written': 1}, step['printed'].get('passages_by_status'))
        calls = K.read_jsonl(HERE / 'support' / 'support_calls_practice.jsonl')
        check('not written: no note of the dropped passage was sent to the checker', all('Odran' not in row['prompt'] for row in calls), '%d calls looked at' % len(calls))
        step = expect_status('not written: screen report-only on the practice set', N, ['--set', 'practice', '--report-only'], 'REPORT_ONLY', 0)
        check('not written: the dropped passage is not screened', step['printed']['screen_counts']['passages_screened'] == 4
              and step['printed']['what_would_be_left']['passages_dropped_by_the_support_check'] == 1, step['printed'].get('what_would_be_left'))

        # the final set: a rewrite that can not be written
        seal_append('3C_FINAL_QUESTIONS_AND_KEYS', set_files('final', ['questions', 'checks', 'solve', 'select']))
        final = ['--set', 'final', '--max-calls', '100', '--replay-replies']
        expect_status('not written: writer final, first versions', W, final + [note_replay('nw_final_full', 'final', 1), '--step', 'first'], 'ALL_WRITTEN', 0)
        for _ in range(10):
            quiet(K, ['gemini', '--set', 'final', '--max-calls', '0', '--dry-now', FIXED_UTC])
            if next_open(support_view('final'))[1] is None:
                break
            step = gemini_call('final', FIXED_UTC, 'full')
        check('not written: round 1 of the final set finds the one unsupported note; round 2 waits for the rewrite',
              step['printed'].get('round_2_waits_for') == 'REWRITE' and step['printed']['passages_by_status'] == {'ALL_PASS': 7, 'REWRITE_NEEDED': 1} and step['exit'] == 1,
              step['printed'].get('passages_by_status'))
        again = 'V907|ORD-FREE|090|v2'
        empty_rewrite = note_replay('nw_final_rewrite_empty', 'final', 2, {again: good('')})
        expect_status('not written: writer final rewrite, the reply is empty', W, final + [empty_rewrite, '--step', 'rewrite'], 'STOPPED_NOTES_NOT_WRITTEN', 1)
        step = expect_status('not written: writer final rewrite, the reply is empty again', W, final + [empty_rewrite, '--step', 'rewrite'], 'ALL_WRITTEN', 0)
        slot = slot_of('final', again)
        check('not written: a rewrite that comes back empty twice is given up; the first version stays on record',
              slot['not_written'] == {'version': 2, 'replies': 2, 'errors': ['REPLY_EMPTY', 'REPLY_EMPTY']} and [v['version'] for v in slot['versions']] == [1]
              and slot['current'] == 1 and step['printed'].get('notes_with_version_2') == 0, slot['not_written'])
        step = expect_status('not written: support final after the rewrite was given up', K, ['gemini', '--set', 'final', '--max-calls', '5', '--dry-now', FIXED_UTC,
                                                                                               '--replay-replies', str(write_text('replay/nw_no_replies.json', '[]' + LF))], 'NOTHING_PENDING', 0)
        check('not written: no round 2 is planned for the dropped passage; the final set is ready for seal step 4',
              step['printed'].get('rounds_planned') == [1] and step['printed'].get('calls_this_run') == 0
              and step['printed']['passages_by_status'] == {'ALL_PASS': 7, word: 1} and step['printed'].get('ready_for_seal_step_4') is True,
              step['printed'].get('passages_by_status'))
        expect_status('not written: support final, decide', K, ['decide', '--set', 'final', '--dry-now', FIXED_UTC], 'DECIDED', 0)
        expect_status('not written: support practice, decide', K, ['decide', '--set', 'practice', '--dry-now', FIXED_UTC], 'DECIDED', 0)
        row = [p for p in load('support/support_results_final.json')['passages'] if p['passage_id'] == 'V907'][0]
        check('not written: the results file gives the passage the status of the plan and keeps the failed first check on record',
              row == {'passage_id': 'V907', 'status': word, 'rewrite_note_ids': ['V907|ORD-FREE|090|v1']}, row)

        # seal step 4 (a made-up line), the screen and the assemble tool
        seal_append('4_ORDINARY_NOTES', set_files('practice', ['notes_ord', 'support']) + set_files('final', ['notes_ord', 'support']))
        step = expect_status('not written: screen both sets', N, ['--set', 'both'], 'SCREENED', 0)
        screened = {s: [p['passage_id'] for p in load('screen/leak_screen_%s.json' % s)['passages']] for s in ('practice', 'final')}
        check('not written: the two dropped passages are not screened', 'V902' not in screened['practice'] and 'V907' not in screened['final']
              and len(screened['practice']) == 4 and len(screened['final']) == 7, screened)
        step = expect_status('not written: assemble', A, [], 'ASSEMBLED', 0)
        removal = load('removal_log.json')
        mine = [(e['set'], e['step'], e['program'], e['object'], e['id']) for e in removal['entries'] if e['rule'] == word]
        check('not written: the removal log names both drops under the step of the support check, with the note writer as the program',
              mine == [('practice', 'STEP_7_SUPPORT_CHECK', 'tools/ob_write_ordinary_notes.py', 'passage', 'V902'),
                       ('final', 'STEP_7_SUPPORT_CHECK', 'tools/ob_write_ordinary_notes.py', 'passage', 'V907')]
              and removal['counts_by_step_and_rule']['STEP_7_SUPPORT_CHECK'].get(word) == 2, mine)
        details = [e['detail'] for e in removal['entries'] if e['rule'] == word]
        check('not written: each log entry names the note and the logged reasons', gone + ' (REPLY_EMPTY, REPLY_CUT_OFF)' in details[0]
              and again + ' (REPLY_EMPTY, REPLY_EMPTY)' in details[1], details)
        kept = {s: [p['passage_id'] for p in load('prompts/prompt_parts_%s.json' % s)['passages']] for s in ('practice', 'final')}
        check('not written: no prompt part is written for a dropped passage', kept == {'practice': ['V901', 'V904', 'V905'], 'final': ['V906', 'V911', 'V912', 'V913']}, kept)
        rows = {s: {r['filter']: (r['role_step'], r['plain_fact']) for r in removal['survival'][s]} for s in ('practice', 'final')}
        check('not written: the survival row "support check" counts the dropped passages as removed',
              rows['practice']['length backstop'] == (6, 5) and rows['practice']['support check'] == (5, 4)
              and rows['final']['length backstop'] == (9, 8) and rows['final']['support check'] == (8, 7), rows)
    finally:
        HERE = main_folder


def not_written_guard(C):
    """The guard of the same rule: at most 3 passages of a set are given up; one more stops the tool. Everything is made up."""
    global HERE
    rules = C['ordinary_notes']
    stop = rules['not_written_stop_status']
    main_folder, HERE = HERE, HERE / 'not_written_guard'
    try:
        build_inputs(C)
        seal_up_to_3b()
        first = ['--set', 'practice', '--step', 'first', '--max-calls', '100', '--replay-replies']
        four = ['%s|ORD-FREE|090|v1' % pid for pid in ('V901', 'V902', 'V903', 'V904')]
        replay = note_replay('guard_practice_four_empty', 'practice', 1, {note_id: {'http_status': 200, 'model': NOTE_WRITER_NAME, 'content': ''} for note_id in four})
        step = expect_status('guard: practice, one note of each of 4 passages comes back empty', W, first + [replay], 'STOPPED_NOTES_NOT_WRITTEN', 1)
        check('guard: after the first run 4 notes are still due and nothing is given up', step['printed'].get('still_open_in_this_step') == 4
              and step['printed'].get('notes_given_up_after_2_such_replies') == [], step['printed'].get('still_open_in_this_step'))
        step = expect_status('guard: practice, the same 4 notes come back empty again', W, first + [replay], stop, 2)
        check('guard: the first 3 passages in the order of the call log are given up; the 4th is not, and the tool stops with exit code 2',
              (rules['not_written_max_replies'], rules['not_written_max_passages_per_set'], stop) == (2, 3, 'STOPPED_TOO_MANY_NOTES_NOT_WRITTEN')
              and step['printed'].get('notes_given_up_after_2_such_replies') == four[:3] and step['printed'].get('passages_beyond_the_guard_of_3') == ['V904']
              and slot_of('practice', four[3])['not_written'] is None and slot_of('practice', four[2])['not_written'] is not None,
              {'given_up': step['printed'].get('notes_given_up_after_2_such_replies'), 'beyond': step['printed'].get('passages_beyond_the_guard_of_3')})
        step = expect_status('guard: practice, one more run makes no call', W, first + [note_replay('guard_practice_full', 'practice', 1)], stop, 2)
        check('guard: once the guard is passed the tool makes no further call and gives nothing more up', step['printed'].get('calls_this_run') == 0
              and step['printed'].get('notes_given_up_after_2_such_replies') == four[:3] and slot_of('practice', four[3])['versions'] == [],
              step['printed'].get('calls_this_run'))
        expect_stop('guard: support practice while a note is neither written nor given up', K, ['gemini', '--set', 'practice', '--max-calls', '0'], 'NOTES_NOT_ALL_WRITTEN')
    finally:
        HERE = main_folder


# ---------------------------------------------------------------- the walk

def main():
    clean_start()
    C = json.loads((ROOT / 'optionb' / 'PLAN_CONSTANTS.json').read_text(encoding='utf-8'))
    build_inputs(C)
    words = [len(text_of(p).split()) for p in PEOPLE]
    check('the fixture holds 15 made-up passages', len(PEOPLE) == 15, 'words per passage: %d to %d' % (min(words), max(words)))

    seal_append('1_PLAN_AND_SOURCES', ['elig/eligibility.json', 'elig/exclusions.json'])
    seal_append('2_ROLE_NOTES', ['notes_role/role_notes.json'])
    practice_question_files = set_files('practice', ['questions', 'checks', 'solve', 'select'])
    final_question_files = set_files('final', ['questions', 'checks', 'solve', 'select'])

    # ---- the note writer: seal order, plan, no network, stops, resume
    first = ['--set', 'practice', '--step', 'first']
    expect_stop('writer practice before seal step 3A', W, first + ['--max-calls', '0'], 'SEAL_STEP_MISSING')
    check('nothing was written before seal step 3A', not (HERE / 'notes_ord').exists())
    seal_append('3A_PRACTICE_QUESTIONS_AND_KEYS', practice_question_files)
    seal_append('3B_PRACTICE_SET_FIXED', ['select/split_fixed.json'])
    step = expect_status('writer practice, plan only', W, first + ['--max-calls', '0'], 'PLAN_ONLY', 1)
    check('the plan holds 6 notes for each of the 5 practice passages that carry a task', step['printed'].get('notes_planned') == 30, step['printed'].get('notes_planned'))
    expect_stop('writer in a dry folder with a call budget and no made-up replies', W, first + ['--max-calls', '5'], 'DRY_FIXTURE_NEEDS_REPLAY')
    expect_stop('writer final before seal step 3C', W, ['--set', 'final', '--step', 'first', '--max-calls', '0'], 'SEAL_STEP_MISSING')
    expect_stop('writer rewrite before any support check', W, ['--set', 'practice', '--step', 'rewrite', '--max-calls', '5', '--replay-replies',
                                                                 note_replay('writer_practice_unused', 'practice', 2)], 'NO_SUPPORT_RESULTS')

    seventh = '%s|%s|%s|v1' % sorted((p['id'], g, n) for p in PEOPLE if p['set'] == 'practice' and p.get('eligible') is not False for g, n in NOTE_PICK)[6]
    replay_429 = note_replay('writer_practice_run1_http429', 'practice', 1, {seventh: {'http_status': 429, 'error': 'HTTPError 429: made-up: slow down'}})
    step = expect_status('writer practice, the 7th call gets HTTP 429', W, first + ['--max-calls', '100', '--replay-replies', replay_429], 'STOPPED_HTTP_429', 1)
    check('6 notes were written before the stop', step['printed'].get('notes_written_this_run') == 6, step['printed'].get('notes_written_this_run'))
    replay_full = note_replay('writer_practice_full', 'practice', 1)
    step = expect_status('writer practice, call budget 4', W, first + ['--max-calls', '4', '--replay-replies', replay_full], 'STOPPED_CALL_BUDGET', 1)
    check('the resumed run wrote 4 more notes and asked for no note twice', step['printed'].get('notes_with_version_1') == 10, step['printed'].get('notes_with_version_1'))

    before = load('notes_ord/ordinary_notes_practice.json')['passages']
    (HERE / 'notes_ord' / 'ordinary_notes_practice.json').unlink()      # as if the run had been killed before the notes file was written
    step = expect_status('writer practice, notes file lost, rebuilt from the call log', W, first + ['--max-calls', '0'], 'PLAN_ONLY', 1)
    check('the rebuilt notes file equals the lost one', load('notes_ord/ordinary_notes_practice.json')['passages'] == before)

    thirteenth = '%s|%s|%s|v1' % sorted((p['id'], g, n) for p in PEOPLE if p['set'] == 'practice' and p.get('eligible') is not False for g, n in NOTE_PICK)[12]
    replay_empty = note_replay('writer_practice_run4_empty_reply', 'practice', 1, {thirteenth: {'http_status': 200, 'model': NOTE_WRITER_NAME, 'content': '   '}})
    step = expect_status('writer practice, one reply is empty', W, first + ['--max-calls', '100', '--replay-replies', replay_empty], 'STOPPED_NOTES_NOT_WRITTEN', 1)
    check('the empty reply is reported and its note stays open', step['printed'].get('empty_or_cut_off_replies_this_run') == [thirteenth]
          and step['printed'].get('still_open_in_this_step') == 1, step['printed'].get('empty_or_cut_off_replies_this_run'))
    step = expect_status('writer practice, last run', W, first + ['--max-calls', '100', '--replay-replies', replay_full], 'ALL_WRITTEN', 0)
    check('all 30 practice notes have a first version', step['printed'].get('notes_with_version_1') == 30 and step['printed'].get('calls_this_run') == 1,
          {'notes': step['printed'].get('notes_with_version_1'), 'calls': step['printed'].get('calls_this_run')})
    notes = load('notes_ord/ordinary_notes_practice.json')
    slot = notes['passages'][0]['notes']['ORD-INFORMED']['100']
    check('a note text is the reply with outer white space removed', slot['versions'][0]['text'] == note_text(BY_ID['V901'], 'ORD-INFORMED', '100', 1))
    check('the notes file is marked as a dry fixture', notes['made_by']['program'].endswith(TAG) and notes['writer'] == 'DRY-FIXTURE-NO-MODEL')
    size = load('notes_role/role_notes.json')['passages'][0]['size']
    by_hand = {n: max((pc * size['role_size_count'] * size['passage_words'] + 50 * size['passage_size_count']) // (100 * size['passage_size_count']), 20)
               for n, pc in (('090', 90), ('100', 100), ('110', 110))}
    got = {n: notes['passages'][0]['notes']['ORD-FREE'][n]['target_words'] for n in by_hand}
    check('the three word targets of V901 follow the plan formula', got == by_hand, {'by_hand': by_hand, 'tool': got})
    calls = W.read_jsonl(HERE / 'notes_ord' / 'ordinary_calls_practice.jsonl')
    informed = [row for row in calls if '|ORD-INFORMED|' in row['note_id']][0]
    brief = C['briefs']['ord_informed_brief'][0].replace('<<N>>', str(notes['passages'][0]['notes']['ORD-INFORMED']['090']['target_words']))
    expected_prompt = brief + LF + LF + 'Reply with the notes only, as plain text. No heading.' + LF + LF + 'Passage:' + LF + text_of(BY_ID['V901'])
    check('a prompt holds the brief word for word, the fixed reply line and the passage, and nothing else', informed['prompt'] == expected_prompt)
    held = all(q not in row['prompt'] for row in calls for q in ('A free hour comes up', 'reaching for the', 'Where did the', '^1', '^2', 'Supporting quote'))
    check('no prompt of the note writer holds a question, an option or a role-note word', held, '%d logged calls looked at' % len(calls))
    check('every logged call has the thirteen fields of the format (FILE_FORMATS.md section 8.2)',
          all(list(row) == ['utc', 'note_id', 'frame', 'model', 'model_in_reply', 'usage', 'http_status', 'ok', 'error', 'prompt_sha256',
                            'reply_sha256', 'prompt', 'reply'] for row in calls))
    check('every call log line of the note writer holds the model name asked for; an answered call also holds the name in the reply, a refused call null',
          all(row['model'] == 'DRY-FIXTURE-NO-MODEL' for row in calls)
          and all(row['model_in_reply'] == NOTE_WRITER_NAME for row in calls if row['http_status'] == 200)
          and [row['model_in_reply'] for row in calls if row['http_status'] == 429] == [None],
          sorted({str(row['model_in_reply']) for row in calls}))
    check('a dry folder counts no tokens: every usage field is null and no run stopped for a missing token count',
          all(row['usage'] is None for row in calls) and step['printed'].get('deepseek_tokens_in_the_four_call_logs') is None)
    token_limit_checks(C)

    selection_path = HERE / 'select' / 'selection_practice.json'
    kept_bytes = selection_path.read_bytes()
    selection_path.write_bytes(kept_bytes + b' ')
    expect_stop('writer practice after a sealed file was changed by one byte', W, first + ['--max-calls', '0'], 'SEALED_FILE_CHANGED')
    selection_path.write_bytes(kept_bytes)

    seal_append('3C_FINAL_QUESTIONS_AND_KEYS', final_question_files)
    step = expect_status('writer final, one run', W, ['--set', 'final', '--step', 'first', '--max-calls', '100', '--replay-replies', note_replay('writer_final_full', 'final', 1)], 'ALL_WRITTEN', 0)
    check('all 48 final notes have a first version', step['printed'].get('notes_with_version_1') == 48, step['printed'].get('notes_with_version_1'))

    # ---- the support check, practice set: unreadable reply, partial reply, one failed note, its rewrite, round 2
    T = ['2026-10-06T10:00:00Z', '2026-10-06T20:00:00Z', '2026-10-07T08:00:00Z', '2026-10-07T10:00:01Z', '2026-10-08T12:00:00Z']
    U = ['2026-10-07T22:00:01Z', '2026-10-08T10:00:01Z']   # 12 hours and 24 hours after T[3]
    expect_stop('support in a dry folder with a call budget and no made-up replies', K, ['gemini', '--set', 'practice', '--max-calls', '1'], 'DRY_FIXTURE_NEEDS_REPLAY')
    step = expect_status('support practice, plan only', K, ['gemini', '--set', 'practice', '--max-calls', '0', '--dry-now', T[0]], 'STOPPED_CALL_BUDGET', 1)
    check('the plan holds 3 batches for 5 passages', step['printed']['batches'] == {'DONE': 0, 'PENDING': 3, 'UNREADABLE': 0}, step['printed']['batches'])
    state = load('support/support_state_practice.json')
    check('a batch holds the six notes of two passages', [len(b['item_ids']) for b in state['rounds'][0]['batches']] == [12, 12, 6])
    gemini_call('practice', T[0], 'garbage')
    view = support_view('practice')
    check('after an unreadable reply the batch is still open with one try used', view['state']['rounds'][0]['batches'][0] ['attempts'] == 1
          and view['state']['rounds'][0]['batches'][0]['status'] == 'PENDING' and not view['done'])
    gemini_call('practice', T[0], 'full')
    gemini_call('practice', T[0], 'partial')
    view = support_view('practice')
    _, batch, open_items = next_open(view)
    check('after a partial reply only the two items with no verdict are asked once more', batch['batch'] == 1 and len(open_items) == 2, open_items)
    gemini_call('practice', T[0], 'full')
    step = gemini_call('practice', T[0], 'full')
    check('round 1 of the practice set is finished and round 2 waits for the rewrite', step['printed'].get('round_2_waits_for') == 'REWRITE'
          and step['printed']['passages_by_status'] == {'ALL_PASS': 4, 'REWRITE_NEEDED': 1}, step['printed'].get('passages_by_status'))
    results = load('support/support_results_practice.json')
    row = [p for p in results['passages'] if p['passage_id'] == 'V902'][0]
    check('the one note with an unsupported sentence is listed for a rewrite', row == {'passage_id': 'V902', 'status': 'REWRITE_NEEDED', 'rewrite_note_ids': ['V902|ORD-INFORMED|100|v1']}, row)
    expect_stop('screen report-only before the practice support check is finished', N, ['--set', 'practice', '--report-only'], 'SUPPORT_CHECK_NOT_FINISHED')
    log = K.read_jsonl(HERE / 'support' / 'support_calls_practice.jsonl')
    # (one planted note of this fixture itself holds an option text; so option words are not looked for here)
    held = all(word not in entry['prompt'] for entry in log for word in ('ORD-INFORMED', 'ORD-FREE', '|v1', '|090|', 'V90', 'Going only by the passage', 'Where did the', '^1', 'Supporting quote'))
    check('no prompt of the checker holds a group name, a length tag, a passage id, a question or a role-note word', held, '%d logged calls looked at' % len(log))
    first_prompt = log[0]['prompt']
    check('a checker prompt opens with the support brief word for word', first_prompt.startswith(LF.join(C['briefs']['support_brief']) + LF + LF + '=== ITEM N0001 ===' + LF + 'Passage:' + LF))
    step = expect_status('writer practice rewrite', W, ['--set', 'practice', '--step', 'rewrite', '--max-calls', '10', '--replay-replies', note_replay('writer_practice_rewrite', 'practice', 2)], 'ALL_WRITTEN', 0)
    check('exactly one note was written again', step['printed'].get('notes_written_this_run') == 1 and step['printed'].get('notes_with_version_2') == 1, step['printed'].get('notes_written_this_run'))
    rewrite_row = [r for r in W.read_jsonl(HERE / 'notes_ord' / 'ordinary_calls_practice.jsonl') if r['frame'] == 'rewrite'][0]
    check('the rewrite prompt holds the fixed rewrite sentence of the plan', C['briefs']['ordinary_rewrite_frame'][2] in rewrite_row['prompt'] and rewrite_row['note_id'] == 'V902|ORD-INFORMED|100|v2')
    step = gemini_call('practice', T[0], 'full')
    check('round 2 checked the one rewritten note; the practice set is ready for seal step 4', step['printed'].get('ready_for_seal_step_4') is True and step['exit'] == 0
          and step['printed']['notes'] == {'notes_checked': 31, 'passed': 30, 'failed_once': 1, 'failed_twice': 0, 'passages_dropped': 0,
                                           'passages_dropped_note_not_written': 0}, step['printed'].get('notes'))
    step = expect_status('writer practice rewrite, nothing more is due', W, ['--set', 'practice', '--step', 'rewrite', '--max-calls', '10', '--replay-replies', note_replay('writer_practice_rewrite', 'practice', 2)], 'ALL_WRITTEN', 0)
    check('no note is ever written a third time', step['printed'].get('calls_this_run') == 0 and step['printed'].get('due_in_this_step_at_start') == 0)

    # ---- the report-only screen of the practice set (review round 1): before seal step 4, it prints its counts and writes no file
    expect_stop('screen report-only for the final set', N, ['--set', 'final', '--report-only'], 'REPORT_ONLY_IS_FOR_THE_PRACTICE_SET')
    expect_stop('screen report-only for both sets', N, ['--set', 'both', '--report-only'], 'REPORT_ONLY_IS_FOR_THE_PRACTICE_SET')
    step = expect_status('screen report-only on the practice set, before seal step 4', N, ['--set', 'practice', '--report-only'], 'REPORT_ONLY', 0)
    early = step['printed']
    check('the report-only run prints the hits per rule and what would be left beside the two practice launch floors',
          early.get('passages_hit') == [{'passage_id': 'V903', 'rules': ['c']}] and early['screen_counts']['passages_screened'] == 5 and early['screen_counts']['passages_hit'] == 1
          and [(line['what'], line['left'], line['floor'], line['met']) for line in early['practice_launch_floor']]
          == [('practice role_step tasks', 5, 2, True), ('practice plain_fact tasks', 4, 2, True)], {k: early.get(k) for k in ('passages_hit', 'screen_counts', 'practice_launch_floor')})
    check('the report-only run writes no file', early.get('files_written') == [] and not (HERE / 'screen').exists())
    overrides_path = HERE / 'DRY_CONSTANT_OVERRIDES.json'
    kept_overrides = overrides_path.read_bytes()
    high = json.loads(kept_overrides)
    high['launch_floor']['practice_role_step_tasks_min'] = 99
    overrides_path.write_text(json.dumps(high, indent=1) + LF, encoding='utf-8', newline=LF)
    step = expect_status('screen report-only with a practice floor of 99 role-step tasks', N, ['--set', 'practice', '--report-only'], 'REPORT_ONLY_PRACTICE_FLOOR_NOT_MET', 3)
    check('the report-only run says do not launch when the practice set is under the floor', step['printed']['next'].startswith('DO NOT LAUNCH') and not (HERE / 'screen').exists())
    overrides_path.write_bytes(kept_overrides)

    # ---- the support check, final set: one checker and no fallback (amendment A2): a daily-cap stop, a rate stop, unreadable replies, a second failure
    # There is no fallback checker and no Claude checker any more. If Gemini refuses a call, the build waits: the same step is run again
    # later, from its checkpoint. No batch ever moves to another checker, however long the refusals last.
    for gone in ('export', 'import'):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                K.main([gone, '--set', 'final', '--work', str(HERE), '--dry-now', T[0]])
            refused_command = False
        except SystemExit:
            refused_command = True
        check('the support check has no %s step any more' % gone, refused_command and not (HERE / 'support' / 'support_state_final.json').exists())
    gemini_call('final', T[0], 'full')
    step = gemini_call('final', T[0], 'daily_cap')
    check('a daily-cap answer stops the run cleanly and is not counted as a try', step['status'] == 'STOPPED_DAILY_CAP' and step['printed'].get('first_cap_stop_utc') == T[0]
          and load('support/support_state_final.json')['rounds'][0]['batches'][1]['attempts'] == 0, step['status'])
    step = gemini_call('final', T[2], 'garbage_twice', budget=2)
    state = load('support/support_state_final.json')
    check('two unreadable replies close the batch as UNREADABLE', state['rounds'][0]['batches'][1]['status'] == 'UNREADABLE' and state['rounds'][0]['batches'][1]['attempts'] == 2)
    step = gemini_call('final', T[2], 'minute_limit_three_times', budget=5)
    check('a rate refusal is waited out twice, then the run stops with STOPPED_RATE_LIMIT; it is never counted as a daily-cap stop',
          step['status'] == 'STOPPED_RATE_LIMIT' and step['printed'].get('calls_this_run') == 3
          and step['printed'].get('daily_cap_stops') == 1 and step['printed'].get('first_cap_stop_utc') == T[0], {'status': step['status'], 'stops': step['printed'].get('daily_cap_stops')})
    log = K.read_jsonl(HERE / 'support' / 'support_calls_final.jsonl')
    marks = [(row['error'] or '').startswith('DAILY_CAP_STOP: ') for row in log if row['http_status'] == 429]
    check('in the call log only the daily-cap refusal carries the mark; the three rate refusals do not', marks == [True, False, False, False], marks)
    # Before amendment A2 these three refusals (the second one 24 hours after the first, with no answered call between them) moved every
    # unanswered batch to a Claude sub-agent. Now nothing moves: the build waits for Gemini.
    step = gemini_call('final', T[3], 'daily_cap')
    step = gemini_call('final', U[0], 'daily_cap')
    step = gemini_call('final', U[1], 'daily_cap')
    state = load('support/support_state_final.json')
    check('after daily-cap refusals more than 24 hours apart with no answered call between them, no batch has moved: the build waits for Gemini',
          step['status'] == 'STOPPED_DAILY_CAP' and [b['status'] for b in state['rounds'][0]['batches']] == ['DONE', 'UNREADABLE', 'PENDING', 'PENDING']
          and [b['attempts'] for b in state['rounds'][0]['batches']] == [1, 2, 0, 0] and step['printed']['batches'] == {'DONE': 1, 'PENDING': 2, 'UNREADABLE': 1},
          [b['status'] for b in state['rounds'][0]['batches']])
    check('the checkpoint has exactly the fields of the format, with the times of the daily-cap refusals only, and no fallback object',
          list(state) == ['schema', 'made_by', 'inputs', 'set', 'model', 'rounds', 'cap_stops_utc', 'first_cap_stop_utc', 'complete']
          and state['cap_stops_utc'] == [T[0], T[3], U[0], U[1]] and state['first_cap_stop_utc'] == T[0] and state['complete'] is False
          and 'MOVED_TO_FALLBACK' not in json.dumps(state), list(state))
    check('the summary names one checker and no fallback', 'fallback' not in json.dumps(step['printed']).lower()
          and step['printed'].get('checker') == 'DRY-FIXTURE-NO-MODEL', sorted(step['printed']))
    check('the next-step text of a daily-cap stop says: the build waits, nobody else judges a note',
          'The build waits' in step['printed']['next'] and 'Nobody else judges a note' in step['printed']['next'], step['printed']['next'])
    gemini_call('final', T[4], 'full')
    step = gemini_call('final', T[4], 'full')
    check('when Gemini answers again, the same checker finishes round 1; round 2 waits for the rewrite',
          step['printed'].get('round_2_waits_for') == 'REWRITE' and step['printed']['batches'] == {'DONE': 3, 'PENDING': 0, 'UNREADABLE': 1}, step['printed'].get('batches'))
    results = load('support/support_results_final.json')
    unreadable = [r for r in results['results'] if r['verdict'] == 'UNREADABLE']
    check('the 12 items of the batch that was unreadable twice get the verdict UNREADABLE, which counts as FAIL', len(unreadable) == 12
          and all(r['round'] == 1 for r in unreadable), len(unreadable))
    need = sum(len(p['rewrite_note_ids']) for p in results['passages'])
    step = expect_status('writer final rewrite', W, ['--set', 'final', '--step', 'rewrite', '--max-calls', '100', '--replay-replies', note_replay('writer_final_rewrite', 'final', 2)], 'ALL_WRITTEN', 0)
    check('every failed final note was written again once', step['printed'].get('notes_written_this_run') == need and need >= 12, {'rewritten': step['printed'].get('notes_written_this_run'), 'failed': need})
    step = run('support final: plan round 2', K, ['gemini', '--set', 'final', '--max-calls', '0', '--dry-now', T[4]])
    items = load('support/support_items_final.json')['items']
    check('round 2 holds one item for every rewritten note, in batches of up to 12 items', sum(1 for i in items if i['round'] == 2) == need
          and all(len(b['item_ids']) <= 12 for b in load('support/support_state_final.json')['rounds'][1]['batches']), {'round 2 items': sum(1 for i in items if i['round'] == 2)})
    for _ in range(10):
        if next_open(support_view('final'))[1] is None:
            break
        gemini_call('final', T[4], 'full')
    step = expect_status('support final, decide', K, ['decide', '--set', 'final', '--dry-now', T[4]], 'DECIDED', 0)
    check('the final set is ready for seal step 4: seven passages pass, one is dropped after a second failure',
          step['printed']['passages_by_status'] == {'ALL_PASS': 7, 'DROPPED_SECOND_FAILURE': 1} and step['printed'].get('ready_for_seal_step_4') is True, step['printed'].get('passages_by_status'))
    results = load('support/support_results_final.json')
    check('the dropped passage is the one whose note failed twice', [p['passage_id'] for p in results['passages'] if p['status'] == 'DROPPED_SECOND_FAILURE'] == ['V907'])
    items = load('support/support_items_final.json')['items']
    check('one checker judged every note of both rounds: the item map and the results name it for every item, on sheet 00',
          {r['checker'] for r in results['results']} == {'DRY-FIXTURE-NO-MODEL'} and {(i['checker'], i['sheet']) for i in items} == {('DRY-FIXTURE-NO-MODEL', '00')}
          and len(results['results']) == len(items))
    check('no sheet and no answer file for another checker exists', not list((HERE / 'support').glob('claude_support_*'))
          and sorted(p.name for p in (HERE / 'support').iterdir()) == sorted('support_%s_%s.%s' % (kind, s, 'jsonl' if kind == 'calls' else 'json')
                                                                            for s in ('practice', 'final') for kind in ('calls', 'items', 'results', 'state')))
    log = K.read_jsonl(HERE / 'support' / 'support_calls_final.jsonl')
    check('every call log line of the checker has the fourteen fields of the format (FILE_FORMATS.md section 9.3)',
          all(list(row) == ['utc', 'model', 'model_in_reply', 'round', 'batch', 'item_ids', 'attempt', 'http_status', 'ok', 'error', 'prompt_sha256',
                            'reply_sha256', 'prompt', 'reply'] for row in log), len(log))
    check('a call log line of the checker holds the model name asked for; an answered call holds the name the made-up reply carried, a refused call null',
          all(row['model'] == 'DRY-FIXTURE-NO-MODEL' for row in log)
          and {row['model_in_reply'] for row in log if row['http_status'] == 200} == {CHECKER_NAME, None}
          and {row['model_in_reply'] for row in log if row['http_status'] != 200} == {None}
          and step['printed'].get('model_names_in_the_replies') == sorted([CHECKER_NAME, 'None']),
          sorted({str(row['model_in_reply']) for row in log}))
    expect_status('support practice, decide', K, ['decide', '--set', 'practice', '--dry-now', T[4]], 'DECIDED', 0)

    # ---- seal step 4, then the screen
    expect_stop('screen before seal step 4', N, ['--set', 'both'], 'SEAL_STEP_MISSING')
    seal_append('4_ORDINARY_NOTES', set_files('practice', ['notes_ord', 'support']) + set_files('final', ['notes_ord', 'support']))
    expect_stop('writer after seal step 4', W, first + ['--max-calls', '0'], 'SET_IS_SEALED')
    expect_stop('support decide after seal step 4', K, ['decide', '--set', 'practice'], 'SET_IS_SEALED')
    expect_status('support status after seal step 4 (writes nothing)', K, ['status', '--set', 'practice'], 'STATUS_ONLY', 0)
    files_before_screen = {n: sha((HERE / n).read_bytes()) for s in ('practice', 'final') for n in set_files(s, ['notes_ord', 'support'])}
    step = expect_status('screen practice only', N, ['--set', 'practice'], 'SCREENED', 0)
    check('with one set screened the launch floor is not yet checked on both sets', step['printed']['launch_floor']['checked_on_both_sets'] is False)
    step = expect_status('screen both sets', N, ['--set', 'both'], 'SCREENED', 0)
    printed = step['printed']
    screens = {s: load('screen/leak_screen_%s.json' % s) for s in ('practice', 'final')}
    hit = {s: {p['passage_id']: sorted({h['rule'] for h in p['hits']}) for p in screens[s]['passages'] if p['hit']} for s in screens}
    check('the screen hits exactly the four planted notes, one for each rule', hit == {'practice': {'V903': ['c']}, 'final': {'V908': ['a'], 'V909': ['d'], 'V910': ['b']}}, hit)
    check('a word that the passage holds as often as the note is no hit (V911, the word correct)', 'V911' not in hit['final'])
    check('the passage dropped by the support check is not screened', 'V907' not in [p['passage_id'] for p in screens['final']['passages']])
    one = [h for p in screens['practice']['passages'] for h in p['hits']][0]
    check('a hit names the group, the length, the rule and the task', (one['group'], one['length'], one['rule'], one['task_id']) == ('ORD-FREE', '110', 'c', 'V903.GOES_FOR'), one)
    check('the screen of record gives the practice counts that the report-only run printed', screens['practice']['counts'] == early['screen_counts'], screens['practice']['counts'])
    check('the screen file has exactly the fields of the format', list(screens['final']) == ['schema', 'made_by', 'inputs', 'set', 'passages', 'counts']
          and list(screens['final']['counts']) == ['passages_screened', 'passages_hit', 'hits_by_rule'])
    left = printed['what_is_left']
    check('what is left: practice 4 passages, 5 role-step and 4 plain-fact tasks; final 4 passages, 5 and 4',
          (left['practice']['passages_left'], left['practice']['role_step_tasks_left'], left['practice']['plain_fact_tasks_left'],
           left['final']['passages_left'], left['final']['role_step_tasks_left'], left['final']['plain_fact_tasks_left']) == (4, 5, 4, 4, 5, 4), left)
    check('the launch floor of the fixture is met and the tier is EXPLORATORY', printed['launch_floor']['met'] is True and printed['launch_floor']['tier'] == 'EXPLORATORY', printed['launch_floor'])
    check('the screen changed no note file and no support file', files_before_screen == {n: sha((HERE / n).read_bytes()) for n in files_before_screen},
          '%d files compared' % len(files_before_screen))

    # the screen's rules on small made-up texts
    rules = N.Rules(W.Ctx(str(HERE)).constants)
    task = {'task_id': 'T.X', 'question': 'Dr. Hale waits by the gate for a long hour. What happens next?', 'right': 'he rings the bell', 'wrong': ['he walks home']}
    check('the sentence rule does not cut after Dr.', rules.sentences(task['question']) == ['Dr. Hale waits by the gate for a long hour.', 'What happens next?'])
    probe = lambda kind, note, passage='Ward B. is at the gate.': sorted({h['rule'] for h in N.screen_note(rules, kind, 'G', None, note, passage, [task])})  # noqa: E731
    check('rule (a): a letter that the passage holds as often is no hit; one more is a hit',
          probe('free', 'Ward B. is near.') == [] and probe('free', 'Ward B. is near. Pick B. now.') == ['a'] and probe('frame', 'Ward B. is near.') == ['a'])
    check('rule (a): answer: C and (D) are hits', probe('free', 'So the answer: C is best.') == ['a', 'd'] and probe('free', 'See (D) for more.') == ['a'])
    check('rule (b): the whole question or a sentence of 5 or more words is a hit; a short sentence is not',
          probe('free', 'Dr Hale waits by the gate for a long hour') == ['b'] and probe('free', 'What happens next') == [])
    check('rule (c): an option the passage does not hold is a hit; an option that is passage text is not',
          probe('free', 'Then he rings the bell.') == ['c'] and probe('free', 'Then he rings the bell.', 'He rings the bell at noon.') == [])
    check('rule (d): the words answer, option, correct count as whole words only', probe('free', 'An optional extra, answered correctly.') == [] and probe('frame', 'One option.') == ['d'])
    role = load('notes_role/role_notes.json')
    broken = json.loads(json.dumps(role['passages'][0]))
    broken['frame_blanked']['role'] = broken['frame_blanked']['role'].replace('For the Mind ""', 'For the Mind "Tamsin"', 1)
    pairs = N.head_pairs(role)
    try:
        N.check_blanked(broken, text_of(BY_ID['V901']), pairs)
        check('a blanked text that still holds a quoted part is refused', False)
    except N.Stop as halt:
        check('a blanked text that still holds a quoted part is refused', halt.args[0] == 'BLANKED_TEXT_NOT_SOUND')
    # amendment A13: the head of a ROLE or MIXED note is pairs of lines, a canon line and then the sayings line of the same Noetic
    sound = role['passages'][0]
    try:
        N.check_blanked(sound, text_of(BY_ID['V901']), pairs)
        check('the head check holds for a note whose head is: canon line, sayings line, for each Noetic', True)
    except N.Stop as halt:
        check('the head check holds for a note whose head is: canon line, sayings line, for each Noetic', False, halt.args[1])
    canon_block = role['canon']

    def refused(change, what):
        other = json.loads(json.dumps(sound))
        change(other)
        try:
            N.check_blanked(other, text_of(BY_ID['V901']), pairs)
            check(what, False)
        except N.Stop as halt:
            check(what, halt.args[0] == 'BLANKED_TEXT_NOT_SOUND', halt.args[1])

    def drop_line(passage, index):
        for holder, name in ((passage, 'role_text'), (passage['frame_blanked'], 'role')):
            rows = holder[name].split(LF)
            del rows[index]
            holder[name] = LF.join(rows)

    def swap_sayings(passage):
        for holder, name in ((passage, 'role_text'), (passage['frame_blanked'], 'role')):
            rows = holder[name].split(LF)
            rows[1] = canon_block['sayings_lines']['^2']       # the sayings line of another Noetic under the canon line of ^1
            holder[name] = LF.join(rows)

    def blank_sayings(passage):
        rows = passage['frame_blanked']['role'].split(LF)
        rows[1] = rows[1].split(': ', 1)[0] + ': '       # the frame word and the colon stay; the sayings text is emptied
        passage['frame_blanked']['role'] = LF.join(rows)

    refused(lambda passage: drop_line(passage, 1), 'a ROLE note whose head lacks a sayings line is refused')
    refused(swap_sayings, 'a ROLE note whose canon line is followed by the sayings line of another Noetic is refused')
    refused(blank_sayings, 'a blanked text whose sayings line was emptied is refused: a sayings line stays whole in the frame text')
    old_file = json.loads(json.dumps(role))
    del old_file['canon']['sayings_lines']
    try:
        N.head_pairs(old_file)
        check('a role-notes file with no sayings lines (built before amendment A13) is refused by the screen', False)
    except N.Stop as halt:
        check('a role-notes file with no sayings lines (built before amendment A13) is refused by the screen', halt.args[0] == 'ROLE_NOTES_WITHOUT_SAYINGS_LINES')
    frame = sound['frame_blanked']['role']
    check('the frame text of a ROLE note holds its sayings lines whole, and the screen finds no letter pattern and none of the three words in it',
          all(canon_block['sayings_lines'][n] in frame.split(LF) for n in ('^1', '^2', '^3'))
          and N.screen_note(rules, 'frame', 'ROLE', None, frame, text_of(BY_ID['V901']), []) == [])
    in_saying = {'task_id': 'T.Y', 'question': 'What does Tamsin do with the lantern at dusk today?', 'right': 'she carries it home',
                 'wrong': [' '.join(rules.word.findall(canon_block['sayings_lines']['^2'].split(': ', 1)[1])[:3])]}
    check('rule (c): an option whose whole text stands inside a sayings line, and not in the passage, is a hit of the ROLE frame text',
          sorted({h['rule'] for h in N.screen_note(rules, 'frame', 'ROLE', None, frame, text_of(BY_ID['V901']), [in_saying])}) == ['c'])
    quoted = [p for p in role['passages'] if p['id'] == 'V913'][0]
    check('the blanked-text check holds for a passage whose quote holds quote marks', '""Not near my bench,"' in quoted['role_text'])

    # ---- assemble: floor not met, cap not met, then the real walk
    overrides_path = HERE / 'DRY_CONSTANT_OVERRIDES.json'
    kept_overrides = overrides_path.read_bytes()
    high = json.loads(kept_overrides)
    high['launch_floor']['final_role_step_tasks_min'] = 99
    overrides_path.write_text(json.dumps(high, indent=1) + LF, encoding='utf-8', newline=LF)
    step = expect_status('screen with a floor of 99 final role-step tasks', N, ['--set', 'both'], 'SCREENED_LAUNCH_FLOOR_NOT_MET', 3)
    check('the screen says do not launch when the floor is missed', step['printed']['launch_floor']['met'] is False and step['printed']['launch_floor']['tier'] == 'NO_LAUNCH'
          and step['printed']['next'].startswith('DO NOT LAUNCH'), step['printed']['launch_floor'])
    step = expect_status('assemble with a floor of 99 final role-step tasks', A, [], 'DO_NOT_LAUNCH_FLOOR_NOT_MET', 3)
    check('below the floor only the removal log is written', (HERE / 'removal_log.json').exists() and not (HERE / 'prompts').exists() and not (HERE / 'keys_final').exists()
          and not (HERE / 'assemble').exists() and load('removal_log.json')['tier'] == 'NO_LAUNCH' and load('removal_log.json')['launch_floor_met'] is False)
    low = json.loads(kept_overrides)
    low['aws'] = {'gpu_job': {'call_cap': 100}}
    overrides_path.write_text(json.dumps(low, indent=1) + LF, encoding='utf-8', newline=LF)
    step = expect_status('assemble with a call cap of 100', A, [], 'DO_NOT_LAUNCH_PLANNED_CALLS_ABOVE_THE_CAP', 3)
    check('above the call cap no prompt part is written', not (HERE / 'prompts').exists(), step['printed'].get('planned_calls'))
    overrides_path.write_bytes(kept_overrides)

    step = expect_status('assemble', A, [], 'ASSEMBLED', 0)
    printed = step['printed']
    check('the final counts are 5 and 4 final tasks on 4 passages, 5 and 4 practice tasks',
          printed['final_counts'] == {'final_role_step_tasks': 5, 'final_plain_fact_tasks': 4, 'final_passages_with_a_role_step_task': 4,
                                      'practice_role_step_tasks': 5, 'practice_plain_fact_tasks': 4}, printed['final_counts'])
    check('the planned calls follow 12 and 8 per practice task, 7 and 6 per final task, 1 more per final role-step task',
          printed['planned_calls'] == {'practice': 12 * 5 + 8 * 4, 'final_must_run': 7 * 5 + 6 * 4, 'final_no_passage': 5, 'whole_job': 92 + 59 + 5, 'cap': 5000}, printed['planned_calls'])
    removal = load('removal_log.json')
    expected_survival = {
        'practice': [(7, 6), (7, 6), (7, 6), (6, 6), (6, 6), (6, 6), (6, 5), (6, 5), (6, 5), (5, 4)],
        'final': [(12, 9), (12, 9), (12, 9), (12, 9), (11, 9), (10, 9), (10, 8), (9, 8), (8, 7), (5, 4)]}
    got = {s: [(r['role_step'], r['plain_fact']) for r in removal['survival'][s]] for s in ('practice', 'final')}
    check('the survival rows are the ones worked out by hand for this fixture', got == expected_survival, got)
    check('the survival rows carry the ten filter names of the format, in order', [r['filter'] for r in removal['survival']['final']] == A.FILTERS)
    check('the removal log has an entry for every step', sorted(removal['counts_by_step_and_rule']) == sorted(A.STEPS), sorted(removal['counts_by_step_and_rule']))
    check('the removal log has exactly the fields of the format', list(removal) == ['schema', 'made_by', 'inputs', 'entries', 'counts_by_step_and_rule', 'survival', 'final_counts',
                                                                               'launch_floor_met', 'tier', 'estimated_padding']
          and all(list(e) == ['set', 'step', 'program', 'object', 'id', 'rule', 'detail'] for e in removal['entries']), len(removal['entries']))
    check('the removal log names the rule of every leak drop', sorted((e['id'], e['rule']) for e in removal['entries'] if e['step'] == 'STEP_7_LEAK_SCREEN')
          == [('V903', 'c'), ('V908', 'a'), ('V909', 'd'), ('V910', 'b')])
    parts = {s: load('prompts/prompt_parts_%s.json' % s) for s in ('practice', 'final')}
    keys = {s: load('keys_%s/keys_%s.json' % (s, s)) for s in ('practice', 'final')}
    meta = {s: load('keys_%s/task_meta_%s.json' % (s, s)) for s in ('practice', 'final')}
    check('the kept passages are the expected ones', ([p['passage_id'] for p in parts['practice']['passages']], [p['passage_id'] for p in parts['final']['passages']])
          == (['V901', 'V902', 'V904', 'V905'], ['V906', 'V911', 'V912', 'V913']))
    final_text = (HERE / 'prompts' / 'prompt_parts_final.json').read_text(encoding='utf-8')
    check('the final prompt parts hold no answer_given list, no ANSWER-GIVEN sentence and no key field',
          'answer_given' not in parts['final'] and 'The right answer to the question is' not in final_text
          and all(list(t) == A.TASK_FIELDS for t in parts['final']['tasks']) and '"right' not in final_text and 'keys' not in parts['final'])
    check('the practice prompt parts hold two ANSWER-GIVEN notes per practice role-step task and they name the key letter',
          len(parts['practice']['answer_given']) == 10 and all(a['note'] == 'The right answer to the question is %s.' % keys['practice']['keys'][a['task_id']][a['level']]
                                                              for a in parts['practice']['answer_given']))
    selection = {s: {t['task_id']: t for t in load('select/selection_%s.json' % s)['tasks']} for s in ('practice', 'final')}
    held = True
    for s in ('practice', 'final'):
        for task in parts[s]['tasks']:
            source = selection[s][task['task_id']]
            for level, shown in task['options'].items():
                texts = {o['letter']: o['text'] for o in shown}
                want = [source['right']] + source['wrong'][:len(shown) - 1]
                held = held and sorted(texts.values()) == sorted(want) and texts[keys[s]['keys'][task['task_id']][level]] == source['right']
            held = held and sorted(task['options']) == (['1', '2'] if task['family'] == 'role_step' else ['1'])
            held = held and len(task['options']['1']) == 4 and (task['family'] != 'role_step' or len(task['options']['2']) == 6)
    check('level 1 shows the right option and the first three wrong ones, level 2 all six; the key letter points at the right option', held)
    balance = printed['right_letter_counts']
    check('each letter is right equally often, to within one task, inside every type and over the whole family, at each level',
          all(max(c.values()) - min(c.values()) <= 1 for s in balance for c in balance[s].values())
          and all(name in balance[s] for s in balance for name in ('role_step family level 1', 'role_step family level 2', 'plain_fact family level 1')), balance)
    # the letters rule of review round 1 on made-up tasks: the count does not start again at A for a new type
    sizes = dict(zip(C['types_in_order'], (5, 9, 6, 7, 5, 4)))
    made = [{'task_id': 'X%s%02d.F' % (name[:2], n), 'type': name, 'right': 'right %s %d' % (name, n), 'wrong': ['w1', 'w2', 'w3', 'w4', 'w5']}
            for name, size in sizes.items() for n in range(size)]
    made_balance = A.set_letters(C, 'practice', made)[2]
    check('36 made-up tasks in types of 5, 9, 6, 7, 5 and 4: each of A to D is right 9 times at level 1, each of A to F 6 times at level 2',
          made_balance['role_step family level 1'] == {letter: 9 for letter in 'ABCD'} and made_balance['role_step family level 2'] == {letter: 6 for letter in 'ABCDEF'}
          and all(max(c.values()) - min(c.values()) <= 1 for c in made_balance.values()), made_balance)
    again = A.set_letters(A.Ctx(str(HERE)).constants, 'final', list(selection['final'][t['task_id']] for t in parts['final']['tasks']))[1]
    check('the letters come out the same when worked out a second time (seeded)', again == keys['final']['keys'])
    one = parts['final']['passages'][0]['notes']
    check('a passage carries the notes text of every group, three lengths for each ordinary group, and no padding line',
          list(one) == ['FILLER', 'ROLE', 'MIXED', 'QUOTES-ONLY', 'ORD-INFORMED', 'ORD-FREE'] and sorted(one['ORD-FREE']) == ['090', '100', '110']
          and one['FILLER'] == 'No notes are provided for this passage.' and '[Padding' not in final_text)
    canon = load('notes_role/role_notes.json')['canon']['lines']
    said = load('notes_role/role_notes.json')['canon']['sayings_lines']
    head = [canon['^1'], said['^1'], canon['^2'], said['^2'], canon['^3'], said['^3']]
    check('a ROLE note opens with its head: for each Noetic the guide line letter for letter, then its sayings line; MIXED with the swapped ones',
          one['ROLE'].split(LF)[:6] == head and one['MIXED'].split(LF)[:6] == head
          and '- ^3 ' in one['MIXED'].split(LF)[7] and '- ^2 ' in one['ROLE'].split(LF)[7])
    check('every sayings line in the fixture starts with the frame word of the plan and equals the line the role-note tool reads from the canon file',
          all(line.startswith(C['role_notes']['sayings_frame_word'] + ': ') for line in said.values()) and said == R.read_sayings(ROOT, C)[0]
          and printed.get('sayings_lines_read_from_the_table') == 9 and printed.get('canon_lines_read_from_the_guide') == 9, sorted(said))
    check('the QUOTES-ONLY note and the FILLER note hold no sayings line', C['role_notes']['sayings_frame_word'] + ':' not in one['QUOTES-ONLY']
          and C['role_notes']['sayings_frame_word'] not in one['FILLER'])
    check('no struck group appears anywhere in the prompt parts', 'ROLE-PLAIN' not in final_text and 'ROLE-PLAIN' not in (HERE / 'prompts' / 'prompt_parts_practice.json').read_text(encoding='utf-8'))
    check('the groups of a role-step task are the seven must-run groups, of a plain-fact task the first six',
          all(t['groups'] == (C['groups']['must_run_in_order'] if t['family'] == 'role_step' else C['groups']['must_run_in_order'][:6]) for s in parts for t in parts[s]['tasks']))
    check('the task facts sit beside the keys, not in the prompt parts', sorted(meta['final']['tasks']) == sorted(keys['final']['keys'])
          and meta['final']['tasks']['V913.KEEPS_AWAY']['right_text'] == 'working on the sticky oil')
    manifest = load('assemble/manifest_step5.json')
    held = all(sha((ROOT / f['path']).read_bytes()) == f['sha256'] and (ROOT / f['path']).stat().st_size == f['bytes'] for f in manifest['files'])
    names = [f['path'].split('fixture_n/')[1] for f in manifest['files']]
    check('the manifest lists the 11 files of seal step 5 with their true sha256 and size', held and len(names) == 11 and manifest['seal_step'] == '5_PROMPT_PARTS_AND_REMOVAL_LOG', names)
    check('the manifest marks exactly the six package files', sorted(f['package_path'] for f in manifest['files'] if f['package_path']) == sorted(A.IN_PACKAGE))
    planned = load('assemble/planned_calls.json')
    check('the list of planned calls adds up to the totals', sum(r['calls'] for r in planned['calls']) == planned['planned_calls']['whole_job'] == 156 and planned['under_cap'] is True)
    pack = load('review/review_pack.json')
    check('the review pack holds all practice tasks and a seeded tenth of the final tasks, rounded up', pack['counts'] == {'practice_tasks': 9, 'final_tasks': 9, 'final_tasks_in_the_sample': 1}, pack['counts'])
    check('every assembled file is marked as a dry fixture', all(load(n)['made_by']['program'].endswith(TAG) for n in names))

    seal_append('5_PROMPT_PARTS_AND_REMOVAL_LOG', [n for n in names if not n.startswith('assemble/')])
    expect_stop('assemble after seal step 5', A, [], 'SET_IS_SEALED')
    expect_stop('screen after seal step 5', N, ['--set', 'both'], 'SET_IS_SEALED')

    # ---- a note the writer can not produce (plan section 10, Step 7), in two folders of their own
    not_written_case(C)
    not_written_guard(C)

    failed = [c for c in LOG['checks'] if not c['held']]
    summary = {'made_by': MADE_BY, 'note': 'DRY FIXTURE, NOT A RESULT. Made-up passages, questions, notes, verdicts, seal lines and clock. No outside call was made.',
               'tool_runs': len(LOG['steps']), 'checks': len(LOG['checks']), 'checks_held': len(LOG['checks']) - len(failed), 'checks_not_held': len(failed),
               'steps': LOG['steps'], 'check_list': LOG['checks']}
    write_text('dry_run_log.json', json.dumps(summary, indent=1, ensure_ascii=False) + LF)
    print(json.dumps({'dry_fixture': True, 'tool_runs': summary['tool_runs'], 'checks': summary['checks'], 'checks_held': summary['checks_held'],
                      'checks_not_held': [c for c in failed]}, indent=1, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
