"""[MADE-UP DATA, NOT A RESULT] Build the package of the development test (amendment A10).

Plan: 08_OPTION_B_PLAN_v1_0.md, section 19.1. File formats: optionb/FILE_FORMATS.md, section 20.

What the development test is. Before seal step 1 one CPU-only AWS job of kind DEVELOPMENT_TEST runs
'runner_b1.py selftest' on a small package of made-up data. Its purpose is to catch program faults
before anything is sealed. Its output is never evidence about roles. This script builds that package
on the laptop. It calls no outside service and no AWS service. It needs no key.

Everything in the package is made up: the passages, the label entries, the questions, the answers of
the made-up solvers, the ordinary notes, the checker verdicts, the model names and the seal lines.
This script never opens a real passage, a real question, a real label file or a real note.
The only real study text it touches is the canon definition lines and, by amendment A13, the
canonical sayings lines: the role-note tool copies the first from Part A of the labeling guide and
the second from the table of Clarification 6 in docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md (the real
canon file, read-only), by the plan's own rules, as it always does. Nothing is retyped here.
The package also holds the plan, the constants, the file formats, the five job files and
tools/verdict.py as they stand on the day of the build. They are programs and rule texts, not cases.

What this script does, in order:
  1. It writes a made-up fixture (16 passages) into <folder>/work/ and runs the real laptop tools
     there, each with --work, in the order of a real build. The made-up passages open two task
     types, PULL-PUSH and HABIT, and two of them open one form only, so that the made-up practice
     set has tasks of both types at even and at odd places of the sorted task list (the made-up
     answer set DESIGNED of the self-test goes by those places):
       ob_role_notes (its three functions read_canon, read_sayings and build_passage; see the note below),
       ob_write_questions, ob_check_questions, ob_solve_blind, ob_select   (practice, 8 settings)
       the reserve rule: the same four tools again with one more practice setting
       ob_write_ordinary_notes, ob_check_support, ob_screen_notes --report-only   (practice)
       the four question tools for the final set
       ob_write_ordinary_notes, ob_check_support (final), ob_screen_notes, ob_assemble
     A made-up seal file in the work folder grows line by line, so each tool finds the seal steps it
     depends on. Made-up replies go in through --replay-replies. No tool calls a service from a
     folder under optionb/dry/.
  2. It lays the result out as a made-up study folder, <folder>/project/, in the layout of the
     study folder, with its own made-up seal file project/optionb/SEAL_OPTIONB.jsonl (steps 1 to 6;
     FILE_FORMATS.md section 15). The real seal tool then reads that made-up seal file and checks
     that every file it names is unchanged (ob_seal.require_steps with the made-up folder as project).
  3. It calls the two real builders of optionb/controller_b1_draft/:
       build_source_zip_b1.py --study-root <folder>/project --out <folder>/package --guest worker_v02.py
       build_contract_b1.py   --study-root <folder>/project --out <folder>/package --stamp-only
     The first one writes source.zip (18 members) and SOURCE_ZIP_BUILD_RECEIPT.json. The second one
     stamps a COPY of the guest in the package folder and checks its two size limits. It writes no
     contract: a contract needs seal step 7 of the real seal file, which a made-up seal never has.
     The development test does not need a contract. If the second builder stops, that is recorded
     and source.zip stays as built.
  4. It writes <folder>/BUILD_LOG.json: every tool run, every check, the counts and the hashes.

Note on ob_role_notes. Its command refuses any set that does not hold the plan's real number of
eligible passages. So this script calls its building functions directly: read_canon(),
read_sayings() (amendment A13, with its three refusals) and build_passage(). The notes come out in
the tool's own format: each canon line is followed by the sayings line of the same Noetic.
Not run here, by rule: ob_eligibility (it reads the real label files) and the seal steps of ob_seal
(they check the real counts and sources). The made-up eligibility file and the made-up seal lines are
written by this script and say so.

It stops, and writes no package, when: the real seal file optionb/SEAL_OPTIONB.jsonl exists (the
development test can only run before seal step 1); the output folder exists; a tool does not end
with the expected status; a count is not the planned one; the made-up practice set is too small for
the self-test (fewer than 20 role-step tasks or no plain-fact task; FILE_FORMATS.md section 20).

Usage:
  python -B optionb/dry/build_dev_package.py
  python -B optionb/dry/build_dev_package.py --folder-name dev_package_2      a second package (job d2)
  python -B optionb/dry/build_dev_package.py --stop-before-the-builders       steps 1, 2 and 4 only; prints the two builder commands

The output folder is optionb/dry/dev_package/ (or the given name, which must start with dev_package).
It must not exist. A package is never overwritten: once a job ran on it, it is the record of that test.

Exit code 0: built. Exit code 2: stopped; the reason is printed.
"""
import argparse
import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if (HERE.name, HERE.parent.name) != ('dry', 'optionb'):
    raise SystemExit('This script runs only as optionb/dry/build_dev_package.py.')
OPTIONB = HERE.parent
ROOT = OPTIONB.parent
CONTROLLER = OPTIONB / 'controller_b1_draft'
sys.path.insert(0, str(ROOT / 'tools'))

import ob_assemble as A              # noqa: E402
import ob_check_questions as Q       # noqa: E402
import ob_check_support as K         # noqa: E402
import ob_role_notes as R            # noqa: E402
import ob_screen_notes as N          # noqa: E402
import ob_seal as SEAL               # noqa: E402
import ob_select as S                # noqa: E402
import ob_solve_blind as B           # noqa: E402
import ob_write_ordinary_notes as O  # noqa: E402
import ob_write_questions as W       # noqa: E402

LF = chr(10)
PROGRAM = 'optionb/dry/build_dev_package.py'
TAG = ' [MADE-UP DATA FOR THE DEVELOPMENT TEST, NOT A RESULT]'
SCHEMA = 'casalescence/optionb/'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
STEPS = ('1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
         '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES', '5_PROMPT_PARTS_AND_REMOVAL_LOG', '6_PROGRAMS')
# made-up model names that the made-up services "put in their replies" (amendment A9: the tools store them as given).
# The transcript name is the one exception: since operator decision C3 (amendment 3) the import step of
# tools/ob_solve_blind.py takes a sheet only under the pinned id outside_services.claude_solver.model_id, so that id is read
# from PLAN_CONSTANTS.json here. It is a model id, not a passage, question, label, note or key (FILE_FORMATS.md section 20).
NAMES = {'writer': 'MADE-UP-NAME-IN-A-WRITER-REPLY', 'solver': 'MADE-UP-NAME-IN-A-SOLVER-REPLY',
         'transcript': json.loads((OPTIONB / 'PLAN_CONSTANTS.json').read_bytes().decode('utf-8'))['outside_services']['claude_solver']['model_id'],
         'note_writer': 'MADE-UP-NAME-IN-A-NOTE-WRITER-REPLY', 'checker': 'MADE-UP-NAME-IN-A-CHECKER-REPLY'}
# what FILE_FORMATS.md section 20 asks of the made-up practice set (from optionb/job/SELFTEST_EXPECTED.json)
PRACTICE_ROLE_STEP_MIN, PRACTICE_ROLE_STEP_BELOW = 20, 200
PRACTICE_PLAIN_FACT_MIN, PRACTICE_PLAIN_FACT_BELOW = 1, 100

# ---------------------------------------------------------------- the made-up passages

# name, pronoun, place, liked thing, other thing, disliked thing, object, spot, thing beside it. All made up.
PEOPLE_ROWS = [
    ('Tamsin', 'She', 'boat shed', 'tar brush', 'wire brush', 'bilge pump', 'lantern', 'shelf', 'coil of rope'),
    ('Odran', 'He', 'net loft', 'bone needle', 'steel needle', 'rusty winch', 'kettle', 'stove', 'ball of twine'),
    ('Ilse', 'She', 'seed store', 'oak scoop', 'tin scoop', 'damp cellar', 'ledger', 'counter', 'sack of barley'),
    ('Bram', 'He', 'nail forge', 'cross hammer', 'ball hammer', 'leaky bellows', 'bucket', 'floor', 'pair of tongs'),
    ('Maren', 'She', 'dye house', 'copper ladle', 'iron ladle', 'lye vat', 'rack', 'wall', 'tub of madder'),
    ('Corin', 'He', 'bell tower', 'hemp rope', 'nylon rope', 'loose stair', 'oilcan', 'ledge', 'pair of gloves'),
    ('Edda', 'She', 'apple loft', 'wicker tray', 'wire tray', 'broken ladder', 'stool', 'landing', 'heap of straw'),
    ('Joss', 'He', 'tile yard', 'wooden mould', 'metal mould', 'cracked kiln', 'wheelbarrow', 'path', 'stack of pallets'),
    ('Wren', 'She', 'map room', 'brass ruler', 'plastic ruler', 'ink press', 'globe', 'table', 'roll of tape'),
    ('Fenn', 'He', 'ice house', 'long saw', 'short saw', 'steep ramp', 'sledge', 'step', 'bale of sawdust'),
    ('Liesel', 'She', 'weigh house', 'small scale', 'large scale', 'cracked weight', 'pan', 'sill', 'box of chalk'),
    ('Ansel', 'He', 'sail loft', 'curved needle', 'straight needle', 'blunt shears', 'pot', 'trestle', 'bolt of canvas'),
    ('Petra', 'She', 'clock shop', 'fine tweezers', 'flat pliers', 'sticky oil', 'loupe', 'mat', 'tray of springs'),
    ('Hale', 'He', 'rope walk', 'long spindle', 'short spindle', 'tar kettle', 'board', 'post', 'bucket of tallow'),
    ('Sunniva', 'She', 'salt store', 'birch rake', 'iron rake', 'wet sacks', 'barrow', 'ramp', 'pile of crates'),
    ('Garrick', 'He', 'cooper yard', 'curved adze', 'straight adze', 'split stave', 'mallet', 'block', 'hoop of iron'),
]
PRACTICE_SETTINGS = ['dev practice yard %d' % n for n in range(1, 9)]
RESERVE_SETTINGS = ['dev reserve yard %d' % n for n in range(1, 5)]
FINAL_SETTING = 'dev final yard'
# passages 1 to 10: the 8 practice settings; 11 and 12: reserve setting 1; 13 to 16: the final setting
# The made-up label teams "agree" on ^1, ^2, ^3 and ^7 for every passage but two. For passages 6 and 14 they agree on ^1 and ^2 only.
# So those two open one form (GOES_FOR) and carry one role-step task; every other passage carries two, one of each type.
SINGLE_FORM_PASSAGES = (6, 14)
OVERRIDES = {
    'note': 'MADE-UP. Development-test fixture only. A tool reads this file only when its work folder sits under optionb/dry/. The real launch '
            'floors are 100, 100, 36 and 20 and the real reserve targets are 45 and 25. Here they are set so that 16 made-up passages walk through '
            'every step: with 8 practice settings the made-up practice set holds 19 role-step and 10 plain-fact tasks, which meets both practice '
            'floors (19, 10) and misses both reserve targets (23, 12). So the reserve rule moves one setting, as in a real build. The job never '
            'reads this file: the package holds the real PLAN_CONSTANTS.json.',
    'launch_floor': {'final_role_step_tasks_min': 2, 'final_plain_fact_tasks_min': 2, 'practice_role_step_tasks_min': 19, 'practice_plain_fact_tasks_min': 10},
    'split': {'reserve_target_practice_role_step_tasks': 23, 'reserve_target_practice_plain_fact_tasks': 12},
    'tiers': {'no_launch_below_final_role_step_tasks': 2}}
EXPECT = {'practice_8': (19, 10), 'practice_9': (23, 12), 'final': (7, 4)}


def people():
    out = []
    for index, row in enumerate(PEOPLE_ROWS):
        p = dict(zip(('name', 'pron', 'place', 'liked', 'other', 'disliked', 'obj', 'spot', 'thing'), row))
        p['id'] = 'D%03d' % (index + 1)
        p['pron_l'] = p['pron'].lower()
        p['single'] = (index + 1) in SINGLE_FORM_PASSAGES
        if index < 10:
            p['setting'], p['role'] = PRACTICE_SETTINGS[index % 8], 'practice'
        elif index < 12:
            p['setting'], p['role'] = RESERVE_SETTINGS[0], 'reserve_1'
        else:
            p['setting'], p['role'] = FINAL_SETTING, 'final'
        out.append(p)
    return out


def sentences(p):
    return ['%(name)s opened the %(place)s before dawn.' % p,
            '%(pron)s always reached for the %(liked)s before the %(other)s.' % p,
            'The %(obj)s stood on the %(spot)s by the door.' % p,
            'A %(thing)s lay beside it.' % p,
            '%(pron)s kept well away from the %(disliked)s.' % p,
            'Every morning for nine years %(pron_l)s had dusted the %(obj)s first.' % p]


def passage_text(p):
    return ' '.join(sentences(p))


def question_goes_for(p):
    return {'form': 'GOES_FOR',
            'question': 'A free hour comes up next week. Going only by the passage, which of these does %(name)s do first?' % p,
            'right': 'reaching for the %(liked)s again' % p,
            'wrong': ['reaching for the %(other)s again' % p, 'moving the %(obj)s to the yard' % p, 'hanging the %s on a hook' % p['thing'].split()[-1],
                      'sweeping the %s floor twice' % p['place'].split()[-1], 'leaving the door wide open'],
            'anchors': ['reached for the %(liked)s' % p]}


def question_keeps_away(p):
    return {'form': 'KEEPS_AWAY',
            'question': 'A visitor asks for help later that day. Going only by the passage, which of these does %(name)s leave to someone else?' % p,
            'right': 'working on the %(disliked)s' % p,
            'wrong': ['working with the %(liked)s' % p, 'carrying the %(obj)s outside' % p, 'counting every %s there' % p['thing'].split()[-1],
                      'locking up the %(place)s' % p, 'lighting the big lamp'],
            'anchors': ['away from the %(disliked)s' % p]}


def question_long_break(p):
    return {'form': 'LONG_BREAK',
            'question': '%(name)s spends two years far from the %(place)s. Going only by the passage, which of these has most likely faded '
                        'when %(pron_l)s comes back?' % p,
            'right': 'dusting the %(obj)s before anything else' % p,
            'wrong': ['opening the %(place)s before dawn' % p, 'finding the %(spot)s by the door' % p, 'seeing the %s beside it' % p['thing'].split()[-1],
                      'knowing where the %(obj)s stands' % p, 'walking in through the door'],
            'anchors': ['Every morning for nine years']}


def question_fact(p):
    return {'question': 'Where did the %(obj)s stand?' % p, 'right': 'on the %(spot)s' % p, 'wrong': ['under the bench', 'behind the gate', 'inside the cart']}


def note_pool(p):
    """Made-up sentences a made-up note writer might write about the passage. None holds an option text or a sentence of a question."""
    return ['%(name)s opens the %(place)s before dawn.' % p,
            '%(name)s reaches for the %(liked)s before the %(other)s.' % p,
            'The %(obj)s stands on the %(spot)s by the door.' % p,
            'A %(thing)s lies beside the %(obj)s.' % p,
            '%(name)s keeps well away from the %(disliked)s.' % p,
            'The %(other)s comes after the %(liked)s.' % p,
            'The %(spot)s is by the door of the %(place)s.' % p,
            '%(name)s dusts the %(obj)s first every morning.' % p,
            'The %(place)s is open before dawn.' % p]


def made_up_note(p, size_rule, goal, shift):
    """A made-up ordinary note of about goal size units (words and punctuation marks, counted by the plan's own rule)."""
    pool, text, at = note_pool(p), '', shift
    while True:
        longer = (text + ' ' + pool[at % len(pool)]).strip()
        if text and abs(len(size_rule.findall(longer)) - goal) >= abs(len(size_rule.findall(text)) - goal):
            return text
        text, at = longer, at + 1


# ---------------------------------------------------------------- small helpers

class Halt(Exception):
    """This build stops. The first argument is a code, the second a plain sentence."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return SEAL.utc_now()


class Build:
    """One build: the folders, the log and the helpers that run a tool."""

    def __init__(self, folder):
        self.folder = folder
        self.work, self.project, self.package = folder / 'work', folder / 'project', folder / 'package'
        self.steps, self.checks = [], []
        self.made_by = {'program': PROGRAM + TAG, 'sha256': sha(Path(__file__).read_bytes()), 'utc': utc_now()}
        self.constants = json.loads((OPTIONB / 'PLAN_CONSTANTS.json').read_bytes().decode('utf-8'))
        self.people = people()
        self.by_id = {p['id']: p for p in self.people}

    # ---- files

    def rel(self, path):
        return Path(path).resolve().relative_to(ROOT).as_posix()

    def load(self, name):
        return json.loads((self.work / name).read_text(encoding='utf-8'))

    def write_text(self, path, text):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline=LF) as stream:
            stream.write(text)
        return path

    def dump(self, name, schema, body):
        doc = {'schema': schema, 'made_by': self.made_by, 'inputs': []}
        doc.update(body)
        return self.write_text(self.work / name, json.dumps(doc, indent=1, ensure_ascii=False) + LF)

    def replay(self, name, doc):
        return str(self.write_text(self.work / 'replay' / (name + '.json'), json.dumps(doc, indent=1, ensure_ascii=False) + LF))

    def set_files(self, set_name, folders):
        out = []
        for folder in folders:
            out += sorted(path.relative_to(self.work).as_posix() for path in (self.work / folder).glob('*')
                          if path.is_file() and re.search(r'_%s(?=[_.])' % set_name, path.name))
        return out

    def seal_line(self, seal, step, records):
        """Add one made-up seal line, in the form of FILE_FORMATS.md section 15. Written by this script, not by tools/ob_seal.py."""
        lines = [line for line in seal.read_bytes().split(b'\n') if line.strip()] if seal.exists() else []
        row = {'schema': SCHEMA + 'seal-step/v1', 'n': len(lines) + 1, 'step': step, 'utc': utc_now(), 'files': records,
               'values': {'made_up': True, 'never_the_seal_file_of_the_study': True},
               'who_could_open': 'MADE-UP seal line of a development-test package, written by %s. It seals nothing of the study.' % PROGRAM,
               'previous_line_sha256': sha(lines[-1]) if lines else None, 'made_by': self.made_by}
        seal.parent.mkdir(parents=True, exist_ok=True)
        with open(seal, 'ab') as stream:
            stream.write(json.dumps(row, ensure_ascii=False).encode('utf-8') + b'\n')

    def work_seal(self, step, names):
        """A line of the made-up seal file of the work folder. Paths are relative to the study folder, as the tools read them."""
        records = []
        for name in names:
            data = (self.work / name).read_bytes()
            records.append({'path': self.rel(self.work / name), 'package_path': None, 'bytes': len(data), 'sha256': sha(data)})
        self.seal_line(self.work / SEAL_NAME, step, records)

    # ---- running a tool

    def check(self, name, held, detail=''):
        self.checks.append({'check': name, 'held': bool(held), 'detail': detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)})
        if not held:
            raise Halt('CHECK_DID_NOT_HOLD', '%s. Detail: %s' % (name, self.checks[-1]['detail']))

    def tool(self, label, module, argv, want):
        """Run one real tool in the work folder. It must end with the wanted status (or decision). Returns what it printed."""
        buffer, exit_code, stop = io.StringIO(), None, None
        with contextlib.redirect_stdout(buffer):
            try:
                exit_code = module.main(list(argv) + ['--work', str(self.work)])
            except module.Stop as halt:
                exit_code, stop = 2, {'code': halt.args[0], 'reason': halt.args[1]}
        text = buffer.getvalue().strip()
        try:
            out = json.loads(text) if text else {}
        except ValueError:
            out = {'printed_text': text[-2000:]}
        status = out.get('status') or out.get('decision')
        self.steps.append({'label': label, 'tool': module.PROGRAM, 'argv': list(argv), 'exit': exit_code, 'stop': stop, 'status': status})
        if stop is not None or status != want:
            raise Halt('TOOL_DID_NOT_END_AS_EXPECTED', '%s (%s): wanted %s, got %s%s' % (label, module.PROGRAM, want, status,
                                                                                        '' if stop is None else ', stop %s: %s' % (stop['code'], stop['reason'])))
        return out


# ---------------------------------------------------------------- step 1: the fixture and the laptop tools

def write_fixture(b):
    C = b.constants
    b.write_text(b.work / 'DRY_CONSTANT_OVERRIDES.json', json.dumps(OVERRIDES, indent=1, ensure_ascii=False) + LF)
    rows = []
    for p in b.people:
        text, entries = passage_text(p), []
        agreed = [('^1', p['name'], '', ''), ('^2', 'the ' + p['liked'], p['name'], '')]
        if not p['single']:
            agreed += [('^3', 'the ' + p['disliked'], p['name'], ''), ('^7', 'Every morning for nine years', p['name'], 'dusted the ' + p['obj'])]
        for index, (noetic, words, mind, related) in enumerate(agreed):
            side = {'index': index, 'words': words, 'mind': mind, 'relative_to': related}
            entries.append({'noetic': noetic, 'a': dict(side), 'b': dict(side)})
        have = {noetic: 1 for noetic, _, _, _ in agreed}
        forms = [form for form in C['forms_in_order'] if all(have.get(noetic, 0) >= need for noetic, need in C['forms'][form]['opens_when'].items())]
        types = [name for name in C['types_in_order'] if any(C['forms'][form]['type'] == name for form in forms)]
        rows.append({'id': p['id'], 'kind': 'K2', 'setting': p['setting'], 'text': text, 'setting_role': p['role'], 'writer_asks': True,
                     'excluded': False, 'barred': False, 'eligible': True, 'agreed': have, 'only_a': {}, 'only_b': {},
                     'open_forms': forms, 'open_types': types, 'max_role_step_tasks': min(2, len(forms)),
                     'leftover_on_type': {name: False for name in types}, 'any_leftover_2_to_9': False,
                     'entries': {'agreed': entries, 'only_a': [], 'only_b': []}})
    b.check('the made-up passages open the planned forms: GOES_FOR alone for two of them, two PULL-PUSH forms and two HABIT forms for the others',
            sorted(row['id'] for row in rows if row['open_forms'] == ['GOES_FOR']) == ['D%03d' % n for n in SINGLE_FORM_PASSAGES]
            and all(row['open_forms'] in (['GOES_FOR'], ['GOES_FOR', 'KEEPS_AWAY', 'LONG_BREAK', 'NEW_STARTER']) for row in rows),
            sorted({' '.join(row['open_forms']) for row in rows}))
    note = 'MADE-UP. %d made-up passages and made-up label entries, written by %s. Never a case.' % (len(rows), PROGRAM)
    b.dump('elig/eligibility.json', SCHEMA + 'eligibility/v1', {
        'fixture_note': note, 'practice_settings': PRACTICE_SETTINGS, 'reserve_settings_in_order': RESERVE_SETTINGS,
        'counts': {'passages': len(rows)}, 'counts_match_plan': False, 'passages': rows})
    b.dump('elig/exclusions.json', SCHEMA + 'exclusions/v1', {'fixture_note': note, 'count': 0, 'by_kind': {}, 'passages': []})
    # the role notes: the building functions of the real tool; the canon lines are copied from the guide by its rule, and the
    # sayings lines (amendment A13) from the table of the real canon file, read-only, with the tool's three refusals
    canon_lines, names, guide_record = R.read_canon(ROOT, C)
    try:
        sayings_lines, sayings_record = R.read_sayings(ROOT, C)
    except R.Stop as refusal:
        raise Halt('THE_ROLE_NOTE_TOOL_REFUSES_THE_SAYINGS', '%s: %s' % (refusal.code, refusal.detail))
    records = [R.build_passage(C, canon_lines, sayings_lines, names, row)[0] for row in rows]
    b.dump('notes_role/role_notes.json', R.SCHEMA_NOTES, {
        'fixture_note': 'MADE-UP passages. Built by read_canon(), read_sayings() and build_passage() of tools/ob_role_notes.py, called by %s.' % PROGRAM,
        'canon': {'source': C['sources']['labeling_guide']['path'], 'sha256': guide_record['sha256'], 'lines': canon_lines, 'names': names,
                  'sayings_source': sayings_record['path'], 'sayings_sha256': sayings_record['sha256'], 'sayings_lines': sayings_lines},
        'passages': records})
    b.steps.append({'label': 'role notes of %d made-up passages' % len(records), 'tool': R.PROGRAM, 'argv': ['read_canon()', 'read_sayings()', 'build_passage()'],
                    'exit': 0, 'stop': None, 'status': 'CALLED_DIRECTLY'})
    b.check('every made-up passage has a role note that opens, for each of its Noetics in number order, with the canon line copied from the guide '
            'and then the sayings line copied from the table of the canon file',
            all(record['role_text'].split(LF)[:2 * len(row['agreed'])] == [line for noetic in sorted(row['agreed']) for line in (canon_lines[noetic], sayings_lines[noetic])]
                for row, record in zip(rows, records)), len(records))
    b.check('no sayings line stands in a QUOTES-ONLY note', all(C['role_notes']['sayings_frame_word'] + ':' not in record['quotes_only_text'] for record in records))
    b.work_seal('1_PLAN_AND_SOURCES', ['elig/eligibility.json', 'elig/exclusions.json'])
    b.work_seal('2_ROLE_NOTES', ['notes_role/role_notes.json'])


def write_questions(b, set_name, more=()):
    """Both writer passes for the waves that are not written yet. The made-up writer answers every batch in full."""
    for pass_name in ('p1', 'p2'):
        base = ['--set', set_name, '--pass', pass_name] + list(more)
        b.tool('writer %s %s: the plan' % (set_name, pass_name), W, base + ['--max-calls', '0'], 'STOPPED_CALL_BUDGET')
        state = b.load('questions/writer_state_%s_%s.json' % (set_name, pass_name))
        pending = [batch for wave in state['waves'] for batch in wave['batches'] if batch['status'] == 'PENDING']
        b.check('writer %s %s: no batch holds more than %d passages' % (set_name, pass_name, b.constants['outside_services']['gemini_question_writer']['passages_per_call']),
                all(1 <= len(batch['passage_ids']) <= b.constants['outside_services']['gemini_question_writer']['passages_per_call'] for batch in pending),
                [len(batch['passage_ids']) for batch in pending])
        replies = []
        for batch in pending:
            # the made-up writer is blind: it writes the same three forms for every passage, also where a form is not open
            objects = [{'passage': pid, 'what_follows': [question_goes_for(b.by_id[pid]), question_keeps_away(b.by_id[pid]), question_long_break(b.by_id[pid])],
                        'plain_fact': question_fact(b.by_id[pid])} for pid in batch['passage_ids']]
            replies.append({'http_status': 200, 'model': NAMES['writer'], 'content_json': objects})
        path = b.replay('writer_%s_%s_%d' % (set_name, pass_name, len(state['waves'])), replies)
        b.tool('writer %s %s: %d made-up replies' % (set_name, pass_name, len(replies)), W,
               base + ['--max-calls', str(len(replies)), '--replay-replies', path], 'ALL_WRITTEN')


def solve(b, set_name, more=()):
    """The check, the two made-up solvers and the decide step. With the passage both pick the right option; without it one does not."""
    letters = b.constants['levels']['letters']
    deepseek = b.constants['outside_services']['deepseek']['model']      # the solver name of a DeepSeek item in the item map
    b.tool('check %s' % set_name, Q, ['--set', set_name] + list(more), 'CHECKED')
    b.tool('deepseek %s: the item map' % set_name, B, ['deepseek', '--set', set_name, '--max-calls', '0'], 'STOPPED_CALL_BUDGET')
    items = b.load('solve/solver_items_%s.json' % set_name)['items']
    log = b.work / 'solve' / ('deepseek_calls_%s.jsonl' % set_name)
    done = {json.loads(line)['item_id'] for line in log.read_text(encoding='utf-8').split(LF) if line.strip()} if log.exists() else set()
    table = {}
    for item in items:
        if item['solver'] == deepseek and item['item_id'] not in done:
            wrong = [letter for letter in letters[:len(item['shown'])] if letter != item['right_letter']][0]
            table[item['item_id']] = {'http_status': 200, 'model': NAMES['solver'],
                                      'content_json': {'answer': item['right_letter'] if item['mode'] == 'with_passage' else wrong}}
    path = b.replay('deepseek_%s_%d' % (set_name, len(done)), table)
    b.tool('deepseek %s: %d made-up replies' % (set_name, len(table)), B,
           ['deepseek', '--set', set_name, '--max-calls', str(len(table)), '--workers', '1', '--replay-replies', path], 'ALL_ANSWERED')
    for mode in ('with_passage', 'no_passage'):
        out = b.tool('export %s %s' % (set_name, mode), B, ['export', '--set', set_name, '--mode', mode], 'SHEETS_WRITTEN')
        b.check('export %s %s: one sheet, and it names the pinned model id' % (set_name, mode), len(out['sheets']) == 1
                and out['ask_for_the_sub_agent_with_model_id'] == b.constants['outside_services']['claude_solver']['model_id'], out.get('sheets'))
        sheet = out['sheets'][0]['sheet']
        on_sheet = [item for item in b.load('solve/solver_items_%s.json' % set_name)['items']
                    if item['solver'] != deepseek and item['mode'] == mode and item['sheet'] == sheet]
        b.write_text(b.work / 'solve' / ('claude_answers_%s_%s_%s.txt' % (set_name, mode, sheet)),
                     ''.join('%s %s' % (item['item_id'], item['right_letter']) + LF for item in sorted(on_sheet, key=lambda item: item['item_id'])))
        b.tool('import %s %s sheet %s' % (set_name, mode, sheet), B,
               ['import', '--set', set_name, '--mode', mode, '--sheet', sheet, '--transcript-model', NAMES['transcript']], 'SHEET_IMPORTED')
    return b.tool('decide %s' % set_name, B, ['decide', '--set', set_name], 'KEY_CHECK_WRITTEN')


def notes_and_support(b, set_name):
    """The made-up ordinary notes and the made-up support check: every note passes at once."""
    size_rule = re.compile(b.constants['role_notes']['size_count_regex'])
    percent = b.constants['ordinary_notes']['length_percent']
    base = ['--set', set_name, '--step', 'first']
    b.tool('notes %s: the plan' % set_name, O, base + ['--max-calls', '0'], 'PLAN_ONLY')
    table = {}
    for passage in b.load('notes_ord/ordinary_notes_%s.json' % set_name)['passages']:
        for shift, group in enumerate(sorted(passage['notes'])):
            for length, slot in passage['notes'][group].items():
                goal = percent[length] * passage['role_size_count'] // 100
                text = made_up_note(b.by_id[passage['passage_id']], size_rule, goal, 3 * shift)
                table['%s|%s|%s|v1' % (passage['passage_id'], group, length)] = {'http_status': 200, 'model': NAMES['note_writer'], 'content': text}
    path = b.replay('notes_%s' % set_name, table)
    out = b.tool('notes %s: %d made-up notes' % (set_name, len(table)), O, base + ['--max-calls', str(len(table)), '--replay-replies', path], 'ALL_WRITTEN')
    b.check('notes %s: every planned note has a first version' % set_name, out['notes_with_version_1'] == out['notes_planned'] == len(table), out.get('notes_planned'))
    b.tool('support %s: the plan' % set_name, K, ['gemini', '--set', set_name, '--max-calls', '0'], 'STOPPED_CALL_BUDGET')
    state = b.load('support/support_state_%s.json' % set_name)
    replies = [{'http_status': 200, 'model': NAMES['checker'], 'content_json': [{'item': item_id, 'verdict': 'PASS'} for item_id in batch['item_ids']]}
               for one_round in state['rounds'] for batch in one_round['batches'] if batch['status'] == 'PENDING']
    path = b.replay('support_%s' % set_name, replies)
    b.tool('support %s: %d made-up replies' % (set_name, len(replies)), K,
           ['gemini', '--set', set_name, '--max-calls', str(len(replies)), '--replay-replies', path], 'NOTHING_PENDING')
    out = b.tool('support %s: decide' % set_name, K, ['decide', '--set', set_name], 'DECIDED')
    b.check('support %s: every passage is ALL_PASS, judged by one checker' % set_name,
            list(out['passages_by_status']) == ['ALL_PASS'] and out['ready_for_seal_step_4'] is True, out.get('passages_by_status'))


def counts_of(b, set_name):
    counts = b.load('select/selection_%s.json' % set_name)['counts']
    return counts['role_step_tasks'], counts['plain_fact_tasks']


def run_the_tools(b):
    write_fixture(b)
    # practice, 8 settings
    write_questions(b, 'practice')
    solve(b, 'practice')
    b.tool('select practice, 8 settings', S, ['select', '--set', 'practice'], 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING')
    selection = b.load('select/selection_practice.json')
    b.check('with 8 practice settings the made-up set meets both practice floors and misses a reserve target (the case of amendment A8)',
            counts_of(b, 'practice') == EXPECT['practice_8'] and selection['floor']['met'] is True and selection['reserve']['finished'] is False,
            {'counts': counts_of(b, 'practice'), 'floor': selection['floor'], 'reserve': selection['reserve']})
    # the reserve rule: one more practice setting
    nine = ['--practice-settings', '9']
    write_questions(b, 'practice', nine)
    solve(b, 'practice', nine)
    b.tool('select practice, 9 settings', S, ['select', '--set', 'practice'] + nine, 'GO')
    selection = b.load('select/selection_practice.json')
    b.check('with 9 practice settings both reserve targets are met', counts_of(b, 'practice') == EXPECT['practice_9'] and selection['reserve']['finished'] is True,
            {'counts': counts_of(b, 'practice'), 'reserve': selection['reserve']})
    b.work_seal('3A_PRACTICE_QUESTIONS_AND_KEYS', b.set_files('practice', ['questions', 'checks', 'solve', 'select']))
    b.tool('fix the split', S, ['fix-split'], 'SPLIT_FIXED')
    b.work_seal('3B_PRACTICE_SET_FIXED', ['select/split_fixed.json'])
    # practice first: the practice notes, their support check, and the report-only screen, before any final question
    notes_and_support(b, 'practice')
    b.tool('screen practice, report only', N, ['--set', 'practice', '--report-only'], 'REPORT_ONLY')
    b.check('no final question file exists before the practice notes are checked', not b.set_files('final', ['questions', 'checks', 'solve', 'select']))
    # the final set
    write_questions(b, 'final')
    solve(b, 'final')
    b.tool('select final', S, ['select', '--set', 'final'], 'GO')
    b.check('the made-up final set holds the planned tasks', counts_of(b, 'final') == EXPECT['final'], counts_of(b, 'final'))
    b.work_seal('3C_FINAL_QUESTIONS_AND_KEYS', b.set_files('final', ['questions', 'checks', 'solve', 'select']))
    notes_and_support(b, 'final')
    b.work_seal('4_ORDINARY_NOTES', b.set_files('practice', ['notes_ord', 'support']) + b.set_files('final', ['notes_ord', 'support']))
    out = b.tool('screen both sets', N, ['--set', 'both'], 'SCREENED')
    b.check('the answer-leak screen hits no made-up note', all(out['what_is_left'][s]['passages_left'] == n for s, n in (('practice', 12), ('final', 4))), out.get('what_is_left'))
    out = b.tool('assemble', A, [], 'ASSEMBLED')
    final = out['final_counts']
    b.check('the assembled counts are the planned ones', (final['practice_role_step_tasks'], final['practice_plain_fact_tasks']) == EXPECT['practice_9']
            and (final['final_role_step_tasks'], final['final_plain_fact_tasks']) == EXPECT['final'], final)
    b.check('the made-up practice set is large enough for the self-test (FILE_FORMATS.md section 20)',
            PRACTICE_ROLE_STEP_MIN <= final['practice_role_step_tasks'] < PRACTICE_ROLE_STEP_BELOW
            and PRACTICE_PLAIN_FACT_MIN <= final['practice_plain_fact_tasks'] < PRACTICE_PLAIN_FACT_BELOW, final)
    # the made-up answer set DESIGNED of the self-test goes by the places of the sorted role-step task ids
    role = sorted((task['task_id'], task['type']) for task in b.load('select/selection_practice.json')['tasks'] if task['family'] == 'role_step')
    places = {}
    for place, (task_id, name) in enumerate(role):
        places.setdefault(name, [0, 0])[place % 2] += 1
    b.check('the made-up practice set holds PULL-PUSH and HABIT tasks, each type at even and at odd places of the sorted task list',
            sorted(places) == ['HABIT', 'PULL-PUSH'] and all(min(pair) >= 3 for pair in places.values()), places)
    manifest = b.load('assemble/manifest_step5.json')
    names = [Path(ROOT / item['path']).resolve().relative_to(b.work.resolve()).as_posix() for item in manifest['files']]
    b.check('the manifest of the assemble tool marks exactly the six package files', sorted(item['package_path'] for item in manifest['files'] if item['package_path']) == sorted(A.IN_PACKAGE))
    b.work_seal('5_PROMPT_PARTS_AND_REMOVAL_LOG', [name for name in names if not name.startswith('assemble/')])
    return final


# ---------------------------------------------------------------- step 2: the made-up study folder

def lay_out_the_study_folder(b):
    """Copy the made-up files and today's plan, constants, formats, verdict program and job files into the layout of the study folder."""
    C, work_name = b.constants, b.constants['work_folder']
    verdict, plan_file = C['sources']['verdict_program']['path'], C['plan_file']
    job_files = list(C['repairs']['job_programs']['files_that_may_change'])
    b.check('the constants name the five job files under %s/job/' % work_name, len(job_files) == 5 and all(name.startswith(work_name + '/job/') for name in job_files), job_files)
    real = {plan_file: plan_file, work_name + '/PLAN_CONSTANTS.json': 'PLAN_CONSTANTS.json', work_name + '/FILE_FORMATS.md': 'FILE_FORMATS.md',
            verdict: C['seal']['verdict_program_package_path']}
    real.update({name: name[len(work_name) + 1:] for name in job_files})
    for relative in real:
        target = b.project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    pinned = C['sources']['verdict_program']
    data = (b.project / verdict).read_bytes()
    b.check('tools/verdict.py is the pinned frozen file', (len(data), sha(data)) == (pinned['bytes'], pinned['sha256']))
    prefix = b.rel(b.work) + '/'
    seal = b.project / work_name / SEAL_NAME
    rows = [json.loads(line.decode('utf-8')) for line in (b.work / SEAL_NAME).read_bytes().split(b'\n') if line.strip()]
    b.check('the made-up seal file of the work folder holds steps 1 to 5', [row['step'] for row in rows] == list(STEPS[:7]), [row['step'] for row in rows])

    def record(relative, package_path):
        data = (b.project / relative).read_bytes()
        return {'path': relative, 'package_path': package_path, 'bytes': len(data), 'sha256': sha(data)}

    for row in rows:
        records = [record(relative, real[relative]) for relative in real if relative not in job_files] if row['step'] == STEPS[0] else []
        for item in row['files']:
            inner = item['path'][len(prefix):]
            if not item['path'].startswith(prefix):
                raise Halt('SEAL_PATH_OUTSIDE_THE_WORK_FOLDER', item['path'])
            target = b.project / work_name / inner
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(b.work / inner, target)
            made = record(work_name + '/' + inner, inner if inner in A.IN_PACKAGE else None)
            if (made['bytes'], made['sha256']) != (item['bytes'], item['sha256']):
                raise Halt('A_SEALED_MADE_UP_FILE_CHANGED', item['path'])
            records.append(made)
        b.seal_line(seal, row['step'], records)
    b.seal_line(seal, STEPS[7], [record(name, real[name]) for name in job_files])
    # the real seal tool reads the made-up seal file of the made-up study folder: chain, order, and every named file unchanged
    try:
        lines = SEAL.require_steps(b.project, list(STEPS))
    except SEAL.Refused as refusal:
        raise Halt('THE_SEAL_TOOL_REFUSES_THE_MADE_UP_SEAL_FILE', '%s: %s' % (refusal.code, refusal.detail))
    in_force = SEAL.files_in_force(lines)
    packaged = sorted(item['package_path'] for item in in_force.values() if item['package_path'])
    wanted = sorted(list(real.values()) + list(A.IN_PACKAGE))
    b.check('the made-up seal file names the 15 package files of FILE_FORMATS.md section 14 (the seal file itself is the 16th), each once',
            packaged == wanted and len(wanted) == 15, packaged)
    b.check('the made-up seal file ends with the line 6_PROGRAMS and holds no step 7', [line['step'] for line in lines] == list(STEPS))
    return {'seal_file': b.rel(seal), 'seal_sha256': sha(seal.read_bytes()), 'seal_lines': len(lines), 'sealed_files': len(in_force),
            'package_files': {item['package_path']: {'path': path, 'bytes': item['bytes'], 'sha256': item['sha256']}
                              for path, item in sorted(in_force.items()) if item['package_path']}}


# ---------------------------------------------------------------- step 3: the two real builders

def builder_commands(b):
    guest = CONTROLLER / 'worker_v02.py'
    return [[sys.executable, '-B', str(CONTROLLER / 'build_source_zip_b1.py'), '--study-root', str(b.project), '--out', str(b.package), '--guest', str(guest)],
            [sys.executable, '-B', str(CONTROLLER / 'build_contract_b1.py'), '--study-root', str(b.project), '--out', str(b.package), '--stamp-only']]


def run_the_builders(b):
    """The real zip builder, then the real contract builder in its stamp-only form, each as its own process."""
    b.package.mkdir()
    zip_command, stamp_command = builder_commands(b)
    done = subprocess.run(zip_command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    b.steps.append({'label': 'the real zip builder', 'tool': 'optionb/controller_b1_draft/build_source_zip_b1.py', 'argv': zip_command[3:],
                    'exit': done.returncode, 'stop': None if done.returncode == 0 else (done.stderr or done.stdout)[-1500:], 'status': None})
    if done.returncode != 0 or not (b.package / 'source.zip').is_file():
        raise Halt('THE_ZIP_BUILDER_STOPPED', 'build_source_zip_b1.py did not write source.zip. This script does not write a package by itself. Its last words: %s'
                   % (done.stderr or done.stdout)[-1500:])
    receipt = json.loads((b.package / 'SOURCE_ZIP_BUILD_RECEIPT.json').read_text(encoding='utf-8'))
    b.check('the zip builder says: made-up study root, last seal step 6_PROGRAMS, 18 members',
            receipt.get('made_up_study_root_never_for_a_seal_or_the_gpu_job') is True and receipt.get('last_seal_step_in_package') == STEPS[7]
            and receipt.get('members') == 18, {key: receipt.get(key) for key in ('made_up_study_root_never_for_a_seal_or_the_gpu_job', 'last_seal_step_in_package', 'members')})
    # the stamp-only run writes into the guest file of its --out folder; so it gets a copy, never the reviewed draft
    shutil.copyfile(CONTROLLER / 'worker_v02.py', b.package / 'worker_v02.py')
    stamp = subprocess.run(stamp_command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    b.steps.append({'label': 'the real contract builder, stamp only, on a copy of the guest', 'tool': 'optionb/controller_b1_draft/build_contract_b1.py',
                    'argv': stamp_command[3:], 'exit': stamp.returncode, 'stop': None if stamp.returncode == 0 else (stamp.stderr or stamp.stdout)[-1500:], 'status': None})
    return {'source_zip': receipt['source_zip'], 'source_zip_build_receipt': b.rel(b.package / 'SOURCE_ZIP_BUILD_RECEIPT.json'),
            'stamp_only_exit_code': stamp.returncode,
            'stamp_only_note': ('The contract builder stamped a copy of the guest and checked its size limits. No contract was written: a contract needs seal step 7.'
                                if stamp.returncode == 0 else
                                'The contract builder stopped in its stamp-only form. source.zip is not touched by that. The development test needs no contract. '
                                'Its last words: ' + (stamp.stderr or stamp.stdout)[-800:])}


# ---------------------------------------------------------------- the run

def main(argv=None):
    parser = argparse.ArgumentParser(description='Build the made-up package of the development test (amendment A10).')
    parser.add_argument('--folder-name', default='dev_package', help='the output folder under optionb/dry/; it must start with dev_package and must not exist')
    parser.add_argument('--stop-before-the-builders', action='store_true',
                        help='run the laptop tools and lay out the made-up study folder; do not call the two controller builders; print their commands')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    b = None
    try:
        if not re.fullmatch(r'dev_package[A-Za-z0-9_]*', args.folder_name):
            raise Halt('BAD_ARGUMENT', '--folder-name must start with dev_package and hold only letters, digits and underscores.')
        if (OPTIONB / SEAL_NAME).exists():
            raise Halt('THE_REAL_SEAL_FILE_EXISTS', 'optionb/%s exists. The development test can only run before seal step 1. No package is built.' % SEAL_NAME)
        folder = HERE / args.folder_name
        if folder.exists():
            raise Halt('OUTPUT_FOLDER_EXISTS', '%s exists. A package is never overwritten. Give --folder-name for a new one, or remove the old folder on purpose.' % folder)
        b = Build(folder)
        final = run_the_tools(b)
        study = lay_out_the_study_folder(b)
        commands = [' '.join('"%s"' % part if ' ' in part else part for part in command) for command in builder_commands(b)]
        built = None if args.stop_before_the_builders else run_the_builders(b)
        status = 'STUDY_FOLDER_LAID_OUT_BUILDERS_NOT_CALLED' if built is None else 'DEV_PACKAGE_BUILT'
        log = {'schema': SCHEMA + 'dev_package_build_log/v1', 'made_by': b.made_by,
               'note': 'MADE-UP DATA, NOT A RESULT. Made-up passages, label entries, questions, solver answers, notes, verdicts, model names and seal lines. '
                       'No outside call was made. The only real study text is the canon definition lines and the canonical sayings lines (amendment A13), '
                       'copied by the role-note tool from the guide and from the table of the canon file. '
                       'This package is for the development test only. It is never evidence about roles and never the package of a seal step.',
               'status': status, 'folder': b.rel(folder), 'made_up_passages': len(b.people), 'counts': final,
               'plan_files_as_they_stood': {name: study['package_files'][name]['sha256'] for name in (b.constants['plan_file'], 'PLAN_CONSTANTS.json', 'FILE_FORMATS.md')},
               'made_up_study_folder': b.rel(b.project), 'made_up_seal': {key: study[key] for key in ('seal_file', 'seal_sha256', 'seal_lines', 'sealed_files')},
               'package_files': study['package_files'], 'builder_commands': commands, 'builders': built,
               'not_run_by_this_script': ['tools/ob_eligibility.py: it reads the real label files; the made-up eligibility file is written by this script',
                                          'the command of tools/ob_role_notes.py: it refuses a set that is not the real size; its three building functions were called',
                                          'the seal steps of tools/ob_seal.py: they check the real counts and sources; the made-up seal lines are written by this script'],
               'tool_runs': len(b.steps), 'checks': len(b.checks), 'steps': b.steps, 'check_list': b.checks}
        b.write_text(folder / 'BUILD_LOG.json', json.dumps(log, indent=1, ensure_ascii=False) + LF)
        print(json.dumps({key: log[key] for key in ('status', 'folder', 'made_up_passages', 'counts', 'made_up_seal', 'builder_commands', 'builders', 'tool_runs', 'checks')},
                         indent=1, ensure_ascii=False))
        return 0
    except Halt as halt:
        print(json.dumps({'program': PROGRAM, 'status': 'BUILD_STOPPED', 'code': halt.args[0], 'reason': halt.args[1],
                          'tool_runs_so_far': len(b.steps) if b else 0, 'checks_so_far': len(b.checks) if b else 0,
                          'what_is_on_disk': 'A stopped build leaves its folder as it is, for a look at what went wrong. It holds made-up data only. '
                                             'Remove it before the next try.' if b and b.folder.exists() else 'nothing was written'}, indent=1, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
