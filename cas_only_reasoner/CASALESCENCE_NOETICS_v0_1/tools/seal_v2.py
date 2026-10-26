"""Mechanical checks, shuffle, new ids and the seal for label-agreement attempt v2.0.

Plan: 09_LABEL_AGREEMENT_PLAN_v2_0.md. Modelled on tools/seal_verdict.py. Plain Python, no model, no
network, no key. It reads no passage for content, and nobody chooses among passages.

What it does
  1. Mechanical checks. A passage is dropped if it holds a forbidden word, has fewer than 30 or more
     than 120 words, or repeats another passage exactly (in this set, or in an earlier set named with
     --also-not-in). Drops are counted and listed with their reason.
  2. A fixed-seed shuffle and new ids (verdict Y001..., practice pass 1 PA001..., practice pass 2 PB001...).
  3. The team A launch text. This tool writes it, as team_a/TEAM_A_LAUNCH.txt, from fixed words: the
     frame below (TEAM_A_LAUNCH_FRAME) and the recipe the checker holds (its constant TEAM_A_RECIPE).
     So the exact words team A is given are one hashed file. A sub-agent of team A is started with
     that file and one line of the fixed form TEAM_A_START_LINE, and with nothing else.
  4. The sha256 of the passages, the guide, the plan, the checker, the scorer, the hold table, the
     fixture, the labeler instructions, the team A launch text, the team B labeling tool and the
     briefs, written to one record before any label team starts.
  5. The writer's kinds go to a folder of their own (--hidden-dir), never into the folder that holds
     the passages and the team A chunks.

Both records keep "guide", "plan", "checker", "passages", "instructions" and "team_a_launch" at the top,
each with "file" and "sha256". tools/check_labels_v2.py (--export --seal) and tools/verdict_v2.py read
them there.

Verdict mode writes SEAL.json: schema "casalescence/label-agreement-v2-seal/1", "is_a_seal": true,
"owner_signoff", "seal_conditions", "hold_table", "no_label_existed_when_sealed": true.
It REFUSES, and writes nothing, when
  - the folder is already sealed, or already holds output of this tool;
  - any label file exists in the output folder (or in a folder named with --no-labels-in);
  - a frozen file is missing, or the writer state is not the finished 760 of this plan;
  - the owner sign-off is missing, or its pasted line cannot be read, or it was signed against another
    guide or plan than the ones being sealed (see THE OWNER SIGN-OFF);
  - the hold table is not exactly the codes that are still held, each set to "open";
  - a signed value is not the value the scorer and the checker hold (see WHAT IS COMPARED);
  - a seal condition S1 to S5 is not met, or the practice report is not tied to the files being
    sealed (see THE SEAL CONDITIONS).

Practice mode writes PRACTICE_SET.json: schema "casalescence/label-agreement-v2-practice-set/1",
"is_a_seal": false. That record is not a seal, and the scorer refuses it as one. It needs no owner
sign-off, because practice passages are never scored for the verdict. It needs the plan, so that the
plan's hash (and with it the wording of the seal conditions) is on record before any practice label
exists. It needs the guide, the labeler instructions and the checker, so that the practice labels can
be tied to them. Its passage file is passages_practice.json.

Usage
  seal_v2.py verdict  --writer-state S --out-dir D --hold-table H --owner-signoff O
                      --practice-report R --practice-set PRACTICE_SET.json [--s3-reading READING]
                      [--old-dir verdict] [--hidden-dir DIR]
                      [--guide G] [--plan P] [--checker C] [--scorer V] [--fixture F] [--instructions I]
                      [--team-b-tool T] [--signoff-sheet SHEET]
                      [--chunk-size 50] [--also-not-in FILE ...] [--also-hash FILE ...] [--no-labels-in DIR ...]
  seal_v2.py practice --round 1|2 --writer-state S --out-dir D [--hidden-dir DIR]
                      [--plan P] [--guide G] [--checker C] [--instructions I] [--scorer V] [--fixture F]
                      [--team-b-tool T] [--hold-table H] [--chunk-size 40] [--also-not-in FILE ...]
  seal_v2.py signing-line [--guide G] [--plan P] [--signoff-sheet SHEET]
                      Seals nothing. Prints the line the owner pastes to sign, with the two fingerprints.
  Defaults: --guide 02_LABELING_GUIDE_v2_0.md, --plan 09_LABEL_AGREEMENT_PLAN_v2_0.md,
            --checker tools/check_labels_v2.py, --scorer tools/verdict_v2.py, --fixture label_v2/fixture,
            --instructions label_v2/LABELER_INSTRUCTIONS.txt, --team-b-tool tools/label_outside_v2.py,
            --signoff-sheet label_v2/OWNER_SIGNOFF_SHEET.md,
            --old-dir verdict (the first attempt's folder; it is only read),
            --hidden-dir <out-dir>_HIDDEN_FROM_LABELERS (beside the output folder, never inside it).
  The owner's two records (the sign-reading ruling and the direction for this attempt) are hashed too
  when they are there.

THE OWNER SIGN-OFF
  The owner signs by pasting ONE line. `seal_v2.py signing-line` prints it. It has one of two forms:
    SIGNED: label-agreement v2.0, guide <fingerprint>, plan <fingerprint>, all items 1 to 10 as proposed.
    SIGNED: label-agreement v2.0, guide <fingerprint>, plan <fingerprint>, all items as proposed, except item 1 = 0.75; item 9c = struck.
  A fingerprint is the first 12 or more characters of the file's sha256. This tool reads the pasted line
  itself. It refuses when the line has another form, when it names an item that is not on the sheet, or
  when a fingerprint is not that of the guide or the plan being sealed. So a guide or plan that changes
  after the signature needs one new pasted line. That holds for every signature, changed or not.

  The record (the operator writes it; a JSON object)
    schema                      "casalescence/label-agreement-v2-owner-signoff/1"
    utc_recorded                when the operator recorded it
    owner_pasted_text_verbatim  the owner's own pasted line, unchanged
    signoff_sheet               {"file": "OWNER_SIGNOFF_SHEET.md", "sha256": "<of the sheet the owner signed>"}
    changes_applied_in          needed when the owner changed any item but item 10:
                                {"plan_sha256", "guide_sha256", "scorer_sha256", "checker_sha256"}
                                of the files being sealed
    items                       optional. If it is there it must say what the pasted line says: one entry
                                for every item, {"decision": "as_proposed"} or
                                {"decision": "changed", "value": "<the words after '='>"}.
  What the owner may write after '=':
    items 1, 2, 8b, 8d, 8e   one number between 0 and 1
    item 3                   two whole numbers: "60 and 60" (cases and absences)
    items 4a to 4h           "ruled" and the ruling. The hold code is then removed.
    item 6                   "with twins"
    items 8a to 8e           "struck": the seal condition is taken out
    item 10                  "waived"
    items 5, 7a-7i, 9a-9q    "struck", or the other choice in the owner's own words. This tool cannot
                             check such a change against a program. It asks for changes_applied_in and
                             lists the item in SEAL.json under "changed_items_not_checked_by_this_tool".
  The tool cannot check that a signature is real. That is the operator's record to keep true. The
  record's hash and the pasted line are written into SEAL.json.

  What SEAL.json holds under "owner_signoff". tools/verdict_v2.py reads these keys again before it
  scores, so their names are fixed:
    "sha256"                  of the sign-off record
    "items"                   one entry for every sheet item: {"decision": "as_proposed" | "changed",
                              "value": "<the owner's words, when changed>"}. For reading, an entry may
                              also hold "constants" (the values the scorer must hold for the item),
                              "hold_code_removed": true or "seal_condition_removed": true.
    "owner_values"            {item: {SCORER_CONSTANT: value}} for every value the owner changed
    "hold_codes_removed"      the hold codes the owner ruled on
    "conditions_struck"       the seal conditions the owner struck: "S1" to "S5"
    "lines_struck"            the conventions and working lines the owner struck: "7a", "9c", ...
    "changed_items_not_checked_by_this_tool"   items 5, 7a-7i, 9a-9q that the owner changed
    "practiced_files_waiver"  true when the owner signed item 10 as waived
    "owner_pasted_text_verbatim", "signed_against", "changed_items", "sheet", "file", "utc_recorded"

WHAT IS COMPARED WITH THE SIGNED VALUES
  For every item, as proposed or changed: the scorer's constant must equal the signed value. Items 1, 2
  and 3 (bars and minimum counts), 5 (the five outcome words, when as proposed), 6 (the scorer's
  constant for the ^5 bar row; this tool reads either spelling the scorer may use: FIVE_BAR_ROW with
  'without_twins' or 'with_twins', or BAR_ROW_5_WITH_TWINS with False or True), 8b, 8d and 8e (the
  numbers of S2, S4 and S5). For items 4a to 4h: a code signed as proposed must be in HOLD_CODES of the
  scorer and of the checker. A code the owner ruled on must be gone from both, and from the hold table.

THE SEAL CONDITIONS
  S1 is run by this tool itself, on the scorer, the checker and the fixture being sealed: the scorer's
  own commands `fixture --dir F --checker C` and `old --old-dir D --expected F/FIXTURE_EXPECTED.json`
  must both end with exit code 0. S2 to S5 are read from the scorer's practice report
  (--practice-report). S2, S4 and S5 must read PASS. S3 must read PASS, or NEEDS_A_READER together with
  a reading record (--s3-reading), a JSON object:
    schema                  "casalescence/label-agreement-v2-s3-reading/1"
    practice_report_sha256  the sha256 of the practice report that was read
    reports_read            how many guide-problem reports were read (all of them)
    two_rules_that_order_opposite_things_found   false
    read_by                 who read them
    utc_recorded            when
  The practice report must be tied to its files. The scorer writes into its report, under "made_with",
  the sha256 of every file it was run with. This tool reads the sha256 values in that block.
    - The block must name the practice passages of PRACTICE_SET.json. Always.
    - The block must name the guide, the labeler instructions, the checker and the scorer being
      sealed, and the team A launch text must be the one of the practice set. If one of them changed
      after the practice pass, the tool refuses, unless the owner signed item 10 as waived. The
      waiver and the files that differ are written into SEAL.json.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import platform
import random
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # leave no cache folder beside the frozen tools
TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import write_passages_v2 as writer  # noqa: E402  (the briefs, the forbidden words and the job lists live there)

SEAL_SCHEMA = 'casalescence/label-agreement-v2-seal/1'
PRACTICE_SCHEMA = 'casalescence/label-agreement-v2-practice-set/1'
SIGNOFF_SCHEMA = 'casalescence/label-agreement-v2-owner-signoff/1'
READING_SCHEMA = 'casalescence/label-agreement-v2-s3-reading/1'
REPORT_SCHEMA = 'casalescence/label-agreement-v2-report/1'     # written by tools/verdict_v2.py
SHUFFLE_SEEDS = {'verdict': 20261023, 'practice1': 20261021, 'practice2': 20261022}
ID_FORMATS = {'verdict': 'Y%03d', 'practice1': 'PA%03d', 'practice2': 'PB%03d'}
DEFAULT_CHUNK = {'verdict': 50, 'practice1': 40, 'practice2': 40}
MIN_WORDS, MAX_WORDS = 30, 120
FROZEN_ROLES = ('guide', 'plan', 'checker', 'scorer', 'hold_table', 'fixture', 'instructions', 'team_b_tool')
PRACTICE_NEEDS = ('plan', 'guide', 'checker', 'instructions')   # a practice set refuses without these; the others are recorded when there
DEFAULTS = {'guide': PROJECT / '02_LABELING_GUIDE_v2_0.md', 'plan': PROJECT / '09_LABEL_AGREEMENT_PLAN_v2_0.md',
            'checker': TOOLS / 'check_labels_v2.py', 'scorer': TOOLS / 'verdict_v2.py', 'fixture': PROJECT / 'label_v2' / 'fixture',
            'instructions': PROJECT / 'label_v2' / 'LABELER_INSTRUCTIONS.txt', 'team_b_tool': TOOLS / 'label_outside_v2.py'}
ROLE_WORDS = {'hold_table': 'hold table', 'instructions': 'labeler instructions', 'team_a_launch': 'team A launch text',
              'team_b_tool': 'team B labeling tool'}
ALSO_HASH_IF_THERE = (PROJECT / 'OWNER_RULING_SIGN_READING_20261004.json',
                      PROJECT / 'OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json')
PASSAGE_FILE = {'verdict': 'passages_sealed.json', 'practice1': 'passages_practice.json', 'practice2': 'passages_practice.json'}
KINDS_FILE = 'passages_kinds_HIDDEN_FROM_LABELERS.json'
# Every item on label_v2/OWNER_SIGNOFF_SHEET.md.
SIGNOFF_ITEMS = (['1', '2', '3'] + ['4' + c for c in 'abcdefgh'] + ['5', '6'] + ['7' + c for c in 'abcdefghi']
                 + ['8' + c for c in 'abcde'] + ['9' + c for c in 'abcdefghijklmnopq'] + ['10'])
CONDITION_ITEMS = {'S1': '8a', 'S2': '8b', 'S3': '8c', 'S4': '8d', 'S5': '8e'}
HOLD_CODE_ITEMS = {'H2-COMFORT': '4a', 'H3-NOPULL': '4b', 'H3-BORED': '4c', 'H5-ROLE': '4d',
                   'H7-RESULT': '4e', 'H7-NOEFFECT': '4f', 'H7-UNBROKEN': '4g', 'H89-FOLLOWS': '4h'}
# The values printed on the sheet and in the plan, as the scorer's constants. They are proposals until the owner signs them.
PROPOSED_CONSTANTS = {
    '1': {'BAR_ENTRY_AGREEMENT': 0.80},
    '2': {'BAR_KAPPA': 0.60},
    '3': {'MIN_CASES': 50, 'MIN_ABSENCES': 50},
    '5': {'OUTCOME_NOT_ENOUGH': 'NOT_ENOUGH_CASES', 'OUTCOME_NOT_LABELABLE': 'NOT_LABELABLE_UNDER_THIS_METHOD',
          'OUTCOME_WAITING': 'NO_VERDICT_WAITING_ON_OWNER', 'OUTCOME_LABELABLE': 'LABELABLE_UNDER_THIS_METHOD',
          'OUTCOME_NO_BAR': 'REPORTED_ONLY_NO_BAR'},
    '6': {},        # the ^5 bar row: see FIVE_BAR_ROW_FORMS below
    '8b': {'SEAL_S2_MAX_DROPPED_SHARE': 0.05},
    '8d': {'SEAL_S4_KIND': 'K1', 'SEAL_S4_MIN_E': 0.80},
    '8e': {'SEAL_S5_MIN_WHOLE_SHARE': 0.80},
}
# Item 6, the ^5 row that carries the bar: (scorer constant, proposed value, value for "with twins").
# BOTH spellings are read, and neither is preferred: FIVE_BAR_ROW ('without_twins', 'with_twins') and
# BAR_ROW_5_WITH_TWINS (False, True). This tool takes whichever one the scorer being sealed holds.
# The scorer may keep either name. Nothing here needs to change when it does.
FIVE_BAR_ROW_FORMS = (('FIVE_BAR_ROW', 'without_twins', 'with_twins'), ('BAR_ROW_5_WITH_TWINS', False, True))
NUMBER_ITEMS = {'1': 'BAR_ENTRY_AGREEMENT', '2': 'BAR_KAPPA', '8b': 'SEAL_S2_MAX_DROPPED_SHARE',
                '8d': 'SEAL_S4_MIN_E', '8e': 'SEAL_S5_MIN_WHOLE_SHARE'}
PRACTICED_ROLES = ('guide', 'instructions', 'checker', 'scorer')   # item 10: these must be the files the practice pass ran with
S1_TIMEOUT_SECONDS = 900

# The owner's pasted line: the two forms printed on the sign-off sheet.
SIGNED_LINE = re.compile(r'^SIGNED: label-agreement v2\.0, guide ([0-9a-f]{12,64}), plan ([0-9a-f]{12,64}), '
                         r'all items (?:1 to 10 as proposed|as proposed, except (.+))$')
ONE_CHANGE = re.compile(r'^item ([0-9]{1,2}[a-z]?) = (\S.*)$')
SHARE = re.compile(r'^(?:0(?:\.[0-9]+)?|1(?:\.0+)?|\.[0-9]+)$')
TWO_COUNTS = re.compile(r'^([0-9]+) and ([0-9]+)$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')

# ----------------------------------------------------------------------------------------------------
# The exact words team A is given. Fixed here, and hashed with this tool. The recipe is added from the
# checker (its constant TEAM_A_RECIPE), word for word. Nothing else is said to a team A sub-agent
# but one start line of the form TEAM_A_START_LINE.
# ----------------------------------------------------------------------------------------------------
TEAM_A_LAUNCH_FILE = 'TEAM_A_LAUNCH.txt'
TEAM_A_START_LINE = ('Read the launch text <TEAM_A_LAUNCH.txt> and do what it says. Guide: <the labeling guide>. '
                     'Instructions: <the labeler instructions>. Passages: <your chunk file>. Work folder: <your work folder>. '
                     'Try log: <your try log>.')
TEAM_A_LAUNCH_FRAME = """LAUNCH TEXT FOR A LABELER WHO WORKS WITH FILES
Fixed text. A program writes it. Nobody edits it.

You are a careful labeler. Work only from the labeling guide and the labeler instructions. Never force a label.

WHAT YOU WERE GIVEN
The line that started you names six things and nothing else:
  1. this launch text;
  2. the labeling guide ({guide});
  3. the labeler instructions ({instructions});
  4. your passage file;
  5. your work folder;
  6. your try log.
Read the labeling guide and the labeler instructions in full before you label anything.
Open no other file. You may read only those six things and your own records.
You may write only the records you save in your work folder. The checker writes your try log. You never edit it.
You run the checker program that the recipe below names. You do not open its source.

YOUR PASSAGES
Your passage file holds your passages and nothing else. Each passage has an id and a text.
Label every passage in the file. Label each passage on its own. One passage must not change how you label another.

YOUR RECORDS
Write one record for each passage, as the labeler instructions say. Save each record in your work folder.
Then check it with the recipe below. In the recipe, PASSAGES.json stands for your passage file, the folder
work/ stands for your work folder, and work/tries_NAME.json stands for your try log.

"""


def team_a_launch_text(guide_name, instructions_name, recipe):
    return TEAM_A_LAUNCH_FRAME.format(guide=guide_name, instructions=instructions_name) + recipe.strip() + chr(10)


def refuse(code, detail):
    raise SystemExit('REFUSED: %s: %s Nothing was written.' % (code, detail))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_of(path):
    """A file: its sha256. A folder: the sha256 of every file in it, and one hash over that list."""
    path = Path(path)
    if path.is_file():
        return {'file': path.name, 'sha256': sha(path)}
    files = sorted(p for p in path.rglob('*') if p.is_file())
    listing = [{'file': p.relative_to(path).as_posix(), 'sha256': sha(p)} for p in files]
    joined = ''.join('%s %s\n' % (row['sha256'], row['file']) for row in listing)
    return {'folder': path.name, 'files': listing, 'sha256': hashlib.sha256(joined.encode('utf-8')).hexdigest()}


def dump(path, value):
    """Write to a .partial file, then rename. LF line ends."""
    path = Path(path)
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(partial, path)


def load_json(path, code):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        refuse(code, '%s cannot be read as JSON (%s).' % (path, type(error).__name__))


def label_files(folder):
    """Files or folders under `folder` whose name says they hold labels. 'labelers' (people) does not count."""
    folder = Path(folder)
    found = []
    if folder.is_dir():
        for path in folder.rglob('*'):
            for part in path.relative_to(folder).parts:
                low = part.lower()
                if 'label' in low and 'labeler' not in low and 'labeller' not in low:
                    found.append(path.relative_to(folder).as_posix())
                    break
    return sorted(set(found))


def texts_of(value):
    """Passage texts in an earlier passage file (a list of rows) or an earlier writer state."""
    if isinstance(value, dict) and isinstance(value.get('chunks'), dict):
        value = [row for rows in value['chunks'].values() for row in rows]
    return {row['text'].strip() for row in value if isinstance(row, dict) and isinstance(row.get('text'), str)}


def read_writer_state(path, name):
    state = load_json(path, 'WRITER_STATE_NOT_READABLE')
    if not isinstance(state, dict) or state.get('schema') != writer.STATE_SCHEMA or state.get('plan') != name:
        refuse('WRITER_STATE_NOT_FROM_THIS_PLAN', 'The state file is not a %s state of write_passages_v2.py.' % name)
    if state.get('provider') != writer.PROVIDER or state.get('model') != writer.MODEL:
        refuse('WRONG_WRITER', 'The plan names %s %s as the blind writer.' % (writer.PROVIDER, writer.MODEL))
    if state.get('jobs_sha256') != writer.jobs_sha256(name) or state.get('briefs_sha256') != writer.briefs_sha256(name):
        refuse('WRITER_STATE_NOT_FROM_THIS_PLAN', 'The job list or the briefs changed after the passages were written.')
    rows = [row for start in sorted(state.get('chunks', {}), key=int) for row in state['chunks'][start]]
    jobs = writer.jobs(name)
    if len(rows) != len(jobs):
        refuse('WRITER_NOT_FINISHED', '%d of %d passages are written.' % (len(rows), len(jobs)))
    if [(row.get('setting'), row.get('kind')) for row in rows] != [tuple(job) for job in jobs]:
        refuse('WRITER_STATE_NOT_FROM_THIS_PLAN', 'The settings and kinds in the state file are not the job list, in order.')
    return state, rows


def load_program(path, name, code):
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as error:      # a program that cannot even be loaded cannot be sealed
        refuse(code, '%s cannot be loaded (%s).' % (path, type(error).__name__))
    return module


# ----------------------------------------------------------------------------------------------------
# the owner's signature
# ----------------------------------------------------------------------------------------------------
def parse_signed_line(text):
    """The owner's pasted line -> ({'guide', 'plan', 'changes'}, problems). Only the two forms on the sheet are read."""
    line = ' '.join(text.split()).strip('`"\' ')
    if line.endswith('.'):
        line = line[:-1].rstrip()
    found = SIGNED_LINE.match(line)
    if not found:
        return None, ['owner_pasted_text_verbatim is not one of the two forms printed on the sign-off sheet '
                      '("SIGNED: label-agreement v2.0, guide <fingerprint>, plan <fingerprint>, all items 1 to 10 as proposed" '
                      'or "..., all items as proposed, except item N = value; item M = value")']
    changes, problems = {}, []
    if found.group(3) is not None:
        for part in found.group(3).split(';'):
            one = ONE_CHANGE.match(part.strip())
            if not one:
                problems.append('the pasted line has a change this tool cannot read: "%s" (write: item N = value)' % part.strip()[:80])
            elif one.group(1) not in SIGNOFF_ITEMS:
                problems.append('the pasted line names item %s, which is not on the sheet' % one.group(1))
            elif one.group(1) in changes:
                problems.append('the pasted line names item %s twice' % one.group(1))
            else:
                changes[one.group(1)] = one.group(2).strip()
    return {'guide': found.group(1), 'plan': found.group(2), 'changes': changes}, problems


def five_bar_row_form(scorer):
    """(constant, proposed value, value for "with twins") as the scorer being sealed names the ^5 bar row."""
    for form in FIVE_BAR_ROW_FORMS:
        if hasattr(scorer, form[0]):
            return form
    return FIVE_BAR_ROW_FORMS[0]


def read_decisions(changes, six=FIVE_BAR_ROW_FORMS[0]):
    """What each changed item means for this tool: (facts, problems)."""
    facts = {'owner_values': {}, 'conditions_struck': [], 'hold_codes_removed': [], 'lines_struck': [],
             'practiced_files_waiver': False, 'not_checked_by_this_tool': []}
    problems = []
    code_of = {item: code for code, item in HOLD_CODE_ITEMS.items()}
    condition_of = {item: condition for condition, item in CONDITION_ITEMS.items()}
    for item in SIGNOFF_ITEMS:
        if item not in changes:
            continue
        value = changes[item]
        low = value.lower()
        if item in condition_of and low == 'struck':
            facts['conditions_struck'].append(condition_of[item])
        elif item in NUMBER_ITEMS:
            if SHARE.match(value):
                facts['owner_values'][item] = {NUMBER_ITEMS[item]: float(value)}
            else:
                problems.append('item %s needs one number between 0 and 1%s, not "%s"'
                                % (item, ', or the word struck' if item in condition_of else '', value[:60]))
        elif item == '3':
            two = TWO_COUNTS.match(value)
            if two:
                facts['owner_values'][item] = {'MIN_CASES': int(two.group(1)), 'MIN_ABSENCES': int(two.group(2))}
            else:
                problems.append('item 3 needs two whole numbers, like "60 and 60", not "%s"' % value[:60])
        elif item in code_of:
            if low.startswith('ruled'):
                facts['hold_codes_removed'].append(code_of[item])
            else:
                problems.append('item %s can only be changed by a ruling: write "ruled" and the ruling, not "%s"' % (item, value[:60]))
        elif item == '6':
            if low == 'with twins':
                facts['owner_values'][item] = {six[0]: six[2]}
            else:
                problems.append('item 6 can only be changed to "with twins", not "%s"' % value[:60])
        elif item == '10':
            if low == 'waived':
                facts['practiced_files_waiver'] = True
            else:
                problems.append('item 10 can only be changed to "waived", not "%s"' % value[:60])
        elif item in condition_of:      # 8a and 8c hold no number
            problems.append('item %s can only be struck, not changed to "%s"' % (item, value[:60]))
        else:                           # 5, 7a to 7i, 9a to 9q: the owner's own words, or struck
            facts['not_checked_by_this_tool'].append(item)
            if low == 'struck':
                facts['lines_struck'].append(item)
    return facts, problems


def read_signoff(path, sheet_path, sealed, six=FIVE_BAR_ROW_FORMS[0]):
    """The owner sign-off record. `sealed`: the sha256 of the guide, plan, scorer and checker being sealed.
    `six`: how the scorer being sealed names the ^5 bar row (five_bar_row_form)."""
    if not path:
        refuse('OWNER_SIGNOFF_MISSING', 'Name the owner sign-off record with --owner-signoff.')
    if not Path(path).is_file():
        refuse('OWNER_SIGNOFF_MISSING', 'The owner sign-off record %s does not exist.' % path)
    if not Path(sheet_path).is_file():
        refuse('OWNER_SIGNOFF_NOT_VALID', 'The sign-off sheet %s does not exist.' % sheet_path)
    record = load_json(path, 'OWNER_SIGNOFF_NOT_VALID')
    problems = []
    if not isinstance(record, dict):
        refuse('OWNER_SIGNOFF_NOT_VALID', 'The record is not a JSON object.')
    if record.get('schema') != SIGNOFF_SCHEMA:
        problems.append('schema is not ' + SIGNOFF_SCHEMA)
    if not record.get('utc_recorded'):
        problems.append('utc_recorded is missing')
    sheet = record.get('signoff_sheet') if isinstance(record.get('signoff_sheet'), dict) else {}
    sheet_sha = sha(sheet_path)
    if sheet.get('sha256') != sheet_sha:
        problems.append('the sheet on disk is not the sheet that was signed (sha256 differs)')
    text = record.get('owner_pasted_text_verbatim')
    parsed = None
    if not (isinstance(text, str) and text.strip()):
        problems.append('owner_pasted_text_verbatim is empty')
    else:
        parsed, found = parse_signed_line(text)
        problems += found
    changes = parsed['changes'] if parsed else {}
    if parsed:
        for role in ('guide', 'plan'):
            if not sealed[role].startswith(parsed[role]):
                problems.append('the owner signed against %s %s, but the %s being sealed has sha256 %s; a %s that changed '
                                'after the signature needs one new pasted line' % (role, parsed[role], role, sealed[role], role))
    facts, found = read_decisions(changes, six)
    problems += found
    decisions = {item: ({'decision': 'changed', 'value': changes[item]} if item in changes else {'decision': 'as_proposed'})
                 for item in SIGNOFF_ITEMS}
    items = record.get('items')
    if items is not None and parsed:        # the operator's own list of decisions must say what the pasted line says
        if not isinstance(items, dict):
            problems.append('items is not an object')
        else:
            for item in SIGNOFF_ITEMS:
                entry = items.get(item) if isinstance(items.get(item), dict) else {}
                said = {'decision': entry.get('decision')}
                if entry.get('decision') == 'changed':
                    said['value'] = entry.get('value').strip() if isinstance(entry.get('value'), str) else entry.get('value')
                if said != decisions[item]:
                    problems.append('item %s: the record says %s, but the pasted line says %s'
                                    % (item, json.dumps(said), json.dumps(decisions[item])))
            unknown = sorted(set(items) - set(SIGNOFF_ITEMS))
            if unknown:
                problems.append('unknown items in the record: ' + ', '.join(unknown))
    changed = [item for item in SIGNOFF_ITEMS if item in changes]
    if any(item != '10' for item in changed):
        applied = record.get('changes_applied_in') if isinstance(record.get('changes_applied_in'), dict) else {}
        missing = [role for role in ('plan', 'guide', 'scorer', 'checker') if applied.get(role + '_sha256') != sealed[role]]
        if missing:
            problems.append('items %s were changed by the owner, and changes_applied_in does not name the %s being sealed'
                            % (', '.join(changed), ', '.join(missing)))
    if problems:
        refuse('OWNER_SIGNOFF_NOT_VALID', '; '.join(problems) + '.')

    # What the seal holds for each item, for a reader. The scorer reads "decision" here, and the lists below.
    code_of = {item: code for code, item in HOLD_CODE_ITEMS.items()}
    condition_of = {item: condition for condition, item in CONDITION_ITEMS.items()}
    for item in SIGNOFF_ITEMS:
        if condition_of.get(item) in facts['conditions_struck']:
            decisions[item]['seal_condition_removed'] = True
        elif code_of.get(item) in facts['hold_codes_removed']:
            decisions[item]['hold_code_removed'] = True
        elif item in PROPOSED_CONSTANTS and item not in facts['not_checked_by_this_tool']:
            constants = {six[0]: six[1]} if item == '6' else dict(PROPOSED_CONSTANTS[item])
            constants.update(facts['owner_values'].get(item, {}))
            decisions[item]['constants'] = constants
    result = {'file': Path(path).name, 'sha256': sha(path), 'utc_recorded': record.get('utc_recorded'),
              'sheet': {'file': Path(sheet_path).name, 'sha256': sheet_sha},
              'owner_pasted_text_verbatim': text,
              'signed_against': {'guide_fingerprint_in_the_pasted_line': parsed['guide'], 'guide_sha256': sealed['guide'],
                                 'plan_fingerprint_in_the_pasted_line': parsed['plan'], 'plan_sha256': sealed['plan']},
              'items': decisions, 'changed_items': changed,
              'changed_items_not_checked_by_this_tool': facts['not_checked_by_this_tool']}
    result.update({key: facts[key] for key in ('owner_values', 'conditions_struck', 'hold_codes_removed', 'lines_struck',
                                               'practiced_files_waiver')})
    return result


def read_hold_table(path, signoff):
    """The hold table for the verdict run: the codes that are still held, each set to "open"."""
    table = load_json(path, 'HOLD_TABLE_NOT_VALID')
    if not isinstance(table, dict):
        refuse('HOLD_TABLE_NOT_VALID', 'The hold table is not a JSON object of code: "open".')
    expected = {code for code in HOLD_CODE_ITEMS if code not in signoff['hold_codes_removed']}
    problems = []
    if set(table) != expected:
        problems.append('the codes must be exactly: ' + ', '.join(sorted(expected)))
    not_open = sorted(code for code, value in table.items() if value != 'open')
    if not_open:
        problems.append('a verdict run needs "open" for every code; not open: ' + ', '.join(not_open))
    if problems:
        refuse('HOLD_TABLE_NOT_VALID', '; '.join(problems) + '.')


def same_value(held, value):
    """True and 1 are not the same value here. Numbers are compared as numbers."""
    if isinstance(held, bool) or isinstance(value, bool):
        return isinstance(held, bool) and isinstance(value, bool) and held == value
    if isinstance(value, (int, float)):
        return isinstance(held, (int, float)) and abs(held - value) < 1e-9
    return held == value


def check_programs(scorer, checker, signoff):
    """Every signed value this tool can read must be the value the programs being sealed hold.

    Signed as proposed: the proposed value (the one on the sheet and in the plan). Changed by the owner:
    the owner's value, read from the pasted line. A hold code the owner ruled on must be gone from the
    scorer and from the checker. A hold code signed as proposed must be in both.
    """
    missing = object()
    problems = []
    for item in SIGNOFF_ITEMS:
        entry = signoff['items'][item]
        owner = signoff['owner_values'].get(item, {})
        for constant, value in (entry.get('constants') or {}).items():
            held = getattr(scorer, constant, missing)
            if held is missing or not same_value(held, value):
                problems.append('item %s is %s (%s = %r), but the scorer holds %s'
                                % (item, 'changed by the owner' if constant in owner else 'signed as proposed', constant, value,
                                   'no such constant' if held is missing else repr(held)))
    for code, item in HOLD_CODE_ITEMS.items():
        removed = code in signoff['hold_codes_removed']
        for name, program in (('scorer', scorer), ('checker', checker)):
            codes = getattr(program, 'HOLD_CODES', missing)
            there = codes is not missing and code in codes
            if removed and there:
                problems.append('item %s: the owner ruled on %s, but the %s still holds that code' % (item, code, name))
            elif not removed and not there:
                problems.append('item %s is signed as proposed, but the %s has no hold code %s' % (item, name, code))
    if problems:
        refuse('PROGRAMS_DO_NOT_MATCH_THE_SIGNED_VALUES', '; '.join(problems) + '.')


# ----------------------------------------------------------------------------------------------------
# the seal conditions
# ----------------------------------------------------------------------------------------------------
def sha256_values_in(value, found=None):
    """Every sha256 value a JSON value holds, wherever it sits."""
    found = set() if found is None else found
    if isinstance(value, dict):
        for inner in value.values():
            sha256_values_in(inner, found)
    elif isinstance(value, list):
        for inner in value:
            sha256_values_in(inner, found)
    elif isinstance(value, str) and HEX64.match(value.lower()):
        found.add(value.lower())
    return found


def run_scorer(scorer_path, command):
    done = subprocess.run([sys.executable, '-B', str(scorer_path)] + command, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=S1_TIMEOUT_SECONDS)
    return done.returncode, (done.stdout or '')


def run_s1(scorer_path, checker_path, fixture_path, old_dir):
    """S1, run here on the scorer, the checker and the fixture being sealed. Both commands must end with exit code 0."""
    if not old_dir or not Path(old_dir).is_dir():
        refuse('SEAL_CONDITIONS_NOT_MET', 'S1 is run by the seal tool itself. Name the folder of the first attempt '
                                          '(passages and old labels) with --old-dir.')
    fixture_command = ['fixture', '--dir', str(fixture_path)]
    runs, failed = {}, []
    try:
        if '--checker' in run_scorer(scorer_path, ['fixture', '--help'])[1]:
            fixture_command += ['--checker', str(checker_path)]
    except (OSError, subprocess.SubprocessError):
        pass
    commands = (('fixture', fixture_command),
                ('old_labels', ['old', '--old-dir', str(old_dir), '--expected', str(Path(fixture_path) / 'FIXTURE_EXPECTED.json')]))
    for name, command in commands:
        try:
            code, text = run_scorer(scorer_path, command)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            summary = [line[:200] for line in lines if line.startswith('PROGRAM CHECK')] or [line[:200] for line in lines[-1:]]
            runs[name] = {'command': ' '.join(command[:1] + [part for part in command[1:] if part.startswith('--')]),
                          'exit_code': code, 'summary': summary}
        except (OSError, subprocess.SubprocessError) as error:
            runs[name] = {'exit_code': None, 'summary': ['could not be run (%s)' % type(error).__name__]}
        if runs[name]['exit_code'] != 0:
            failed.append('%s: exit code %s: %s' % (name, runs[name]['exit_code'], ' | '.join(runs[name]['summary'])))
    if failed:
        refuse('SEAL_CONDITIONS_NOT_MET', 'S1, run on the scorer, the checker and the fixture being sealed, did not pass: '
               + '; '.join(failed) + '.')
    return runs


def read_conditions(args, signoff, frozen, launch_sha):
    """S1 is run here. S2 to S5 are read from the scorer's own practice report. Only PASS is a pass."""
    struck = signoff['conditions_struck']
    if not args.practice_set or not Path(args.practice_set).is_file():
        refuse('SEAL_CONDITIONS_NOT_MET', 'Name PRACTICE_SET.json of the practice pass with --practice-set.')
    practice = load_json(args.practice_set, 'SEAL_CONDITIONS_NOT_MET')
    is_practice = isinstance(practice, dict) and practice.get('schema') == PRACTICE_SCHEMA and practice.get('is_a_seal') is False
    node = practice.get('passages') if is_practice else None
    passages_sha = node.get('sha256') if isinstance(node, dict) else None
    if not (isinstance(passages_sha, str) and HEX64.match(passages_sha)):
        refuse('SEAL_CONDITIONS_NOT_MET', '%s is not a practice-set record of this tool.' % args.practice_set)
    if not args.practice_report or not Path(args.practice_report).is_file():
        refuse('SEAL_CONDITIONS_NOT_MET', 'Name the scorer\'s practice report with --practice-report.')
    report = load_json(args.practice_report, 'SEAL_CONDITIONS_NOT_MET')
    if not isinstance(report, dict) or report.get('schema') != REPORT_SCHEMA or report.get('mode') != 'practice':
        refuse('SEAL_CONDITIONS_NOT_MET', 'The file is not a practice report of tools/verdict_v2.py.')

    # The report must be tied to its files: the scorer's "made_with" block names the sha256 of each.
    named = sha256_values_in(report.get('made_with'))
    if passages_sha not in named:
        refuse('PRACTICE_REPORT_NOT_TIED_TO_ITS_FILES',
               'Under "made_with", the practice report does not name the practice passages of %s (sha256 %s). The scorer must '
               'write into its practice report the sha256 of every file it was run with.' % (Path(args.practice_set).name, passages_sha))
    not_practiced = [role for role in PRACTICED_ROLES if frozen[role]['sha256'] not in named]
    practice_launch = practice.get('team_a_launch') if isinstance(practice.get('team_a_launch'), dict) else {}
    if practice_launch.get('sha256') != launch_sha:
        not_practiced.append('team_a_launch')
    if not_practiced and not signoff['practiced_files_waiver']:
        refuse('PRACTICED_FILES_ARE_NOT_THE_SEALED_FILES',
               'These files being sealed are not the ones the practice pass ran with, or the practice report does not name '
               'them: %s. Run a practice pass with the files being sealed (two passes at most), or the owner signs item 10 as '
               'waived.' % ', '.join(ROLE_WORDS.get(role, role) for role in not_practiced))

    nodes = report.get('seal_conditions') if isinstance(report.get('seal_conditions'), dict) else {}
    report_sha = sha(args.practice_report)
    seen, problems = {}, []
    for condition in CONDITION_ITEMS:
        node = nodes.get(condition) if isinstance(nodes.get(condition), dict) else {}
        status = node.get('status')
        seen[condition] = {'status': status}
        if condition in struck:
            seen[condition]['removed_by_owner'] = True
        elif condition == 'S1':
            seen[condition] = {'status': 'PASS',
                               'run_by_the_seal_tool_on_the_files_being_sealed': run_s1(args.scorer, args.checker, args.fixture, args.old_dir),
                               'status_in_the_practice_report': status}
        elif status == 'PASS':
            pass
        elif condition == 'S3' and status == 'NEEDS_A_READER':
            reports = node.get('reports') if isinstance(node.get('reports'), list) else []
            reading_path = args.s3_reading
            reading = load_json(reading_path, 'SEAL_CONDITIONS_NOT_MET') if reading_path and Path(reading_path).is_file() else None
            if not isinstance(reading, dict):
                problems.append('S3 needs a reader: name the reading record with --s3-reading')
            elif (reading.get('schema') != READING_SCHEMA or reading.get('practice_report_sha256') != report_sha
                  or reading.get('reports_read') != len(reports)
                  or reading.get('two_rules_that_order_opposite_things_found') is not False
                  or not (isinstance(reading.get('read_by'), str) and reading['read_by'].strip())
                  or not reading.get('utc_recorded')):
                problems.append('the S3 reading record is not complete, is for another report, does not cover all %d reports, '
                                'or found two rules that order opposite things' % len(reports))
            else:
                seen[condition]['reading'] = {'file': Path(reading_path).name, 'sha256': sha(reading_path),
                                              'read_by': reading['read_by'], 'reports_read': len(reports)}
        else:
            problems.append('%s reads %s in the practice report' % (condition, status))
    if problems:
        refuse('SEAL_CONDITIONS_NOT_MET', '; '.join(problems) + '.')
    return {'practice_report': {'file': Path(args.practice_report).name, 'sha256': report_sha},
            'practice_set': {'file': Path(args.practice_set).name, 'sha256': sha(args.practice_set),
                             'practice_passages_sha256': passages_sha},
            'practiced_files': {'must_be_the_sealed_files': list(PRACTICED_ROLES) + ['team_a_launch'],
                                'not_the_files_of_the_practice_pass': not_practiced,
                                'owner_waiver_item_10': signoff['practiced_files_waiver']},
            'conditions': seen}


def signing_line(args):
    """Print the line the owner pastes. Nothing is sealed and nothing is written."""
    for role in ('guide', 'plan'):
        if not Path(getattr(args, role)).is_file():
            raise SystemExit('REFUSED: the %s (%s) does not exist.' % (role, getattr(args, role)))
    guide, plan = sha(args.guide), sha(args.plan)
    head = 'SIGNED: label-agreement v2.0, guide %s, plan %s, ' % (guide[:12], plan[:12])
    print('guide  %s  sha256 %s' % (Path(args.guide).name, guide))
    print('plan   %s  sha256 %s' % (Path(args.plan).name, plan))
    if Path(args.signoff_sheet).is_file():
        print('sheet  %s  sha256 %s' % (Path(args.signoff_sheet).name, sha(args.signoff_sheet)))
    print()
    print('To sign everything as proposed, the owner pastes:')
    print(head + 'all items 1 to 10 as proposed.')
    print()
    print('To sign with changes, the owner pastes a line like this one, with the owner\'s own items and values:')
    print(head + 'all items as proposed, except item 1 = 0.75; item 9c = struck.')
    print()
    print('If the guide or the plan changes after the owner pastes the line, the line no longer opens the seal.')
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description='Mechanical checks, shuffle, ids and seal for label-agreement attempt v2.0.')
    parser.add_argument('mode', choices=['practice', 'verdict', 'signing-line'])
    parser.add_argument('--round', type=int, default=1, choices=[1, 2])
    parser.add_argument('--writer-state')
    parser.add_argument('--out-dir')
    for role in FROZEN_ROLES:
        parser.add_argument('--' + role.replace('_', '-'), default=str(DEFAULTS[role]) if role in DEFAULTS else None)
    parser.add_argument('--hidden-dir', help='folder for the writer\'s kinds; never inside --out-dir; default <out-dir>_HIDDEN_FROM_LABELERS')
    parser.add_argument('--owner-signoff')
    parser.add_argument('--signoff-sheet', default=str(PROJECT / 'label_v2' / 'OWNER_SIGNOFF_SHEET.md'))
    parser.add_argument('--practice-report', help='the scorer\'s practice report; it holds S2 to S5')
    parser.add_argument('--practice-set', help='PRACTICE_SET.json of the practice pass; the report must name its passages')
    parser.add_argument('--s3-reading', help='the reading record for S3, when the report says NEEDS_A_READER')
    parser.add_argument('--old-dir', default=str(PROJECT / 'verdict'), help='the first attempt\'s folder; S1 part 1 reads it')
    parser.add_argument('--chunk-size', type=int)
    parser.add_argument('--also-not-in', action='append', default=[], help='an earlier passage file; exact repeats of it are dropped')
    parser.add_argument('--also-hash', action='append', default=[], help='another file to hash into the record')
    parser.add_argument('--no-labels-in', action='append', default=[], help='another folder that must hold no label file')
    args = parser.parse_args(argv)

    if args.mode == 'signing-line':
        return signing_line(args)
    if not args.writer_state or not args.out_dir:
        raise SystemExit('REFUSED: name --writer-state and --out-dir.')

    writer.self_check()
    name = writer.plan_name(args.mode, args.round)
    verdict = name == 'verdict'
    out = Path(args.out_dir)
    hidden = Path(args.hidden_dir) if args.hidden_dir else out.parent / (out.name + '_HIDDEN_FROM_LABELERS')
    record_name = 'SEAL.json' if verdict else 'PRACTICE_SET.json'
    passage_file = PASSAGE_FILE[name]

    # 1. Refusals that depend on the output folders.
    if (out / record_name).exists():
        refuse('ALREADY_SEALED', '%s already exists in %s.' % (record_name, out))
    left = [n for n in (passage_file, KINDS_FILE, 'team_a') if (out / n).exists()]
    if left:
        refuse('OUTPUT_EXISTS', '%s already holds %s. Use an empty folder.' % (out, ', '.join(left)))
    out_full, hidden_full = out.resolve(), hidden.resolve()
    if hidden_full == out_full or out_full in hidden_full.parents or hidden_full in out_full.parents:
        refuse('HIDDEN_FOLDER_NOT_APART', 'The folder for the writer\'s kinds (%s) must not be the output folder, inside it, or '
                                          'around it. Team A is pointed at the output folder.' % hidden)
    if (hidden / KINDS_FILE).exists():
        refuse('OUTPUT_EXISTS', '%s already holds %s. Use an empty folder.' % (hidden, KINDS_FILE))
    for folder in [out] + [Path(p) for p in args.no_labels_in]:
        found = label_files(folder)
        if found:
            refuse('LABELS_ALREADY_EXIST', '%s holds label files (%s).' % (folder, ', '.join(found[:5])))

    # 2. The writer's output must be the finished job list of this plan.
    state, rows = read_writer_state(args.writer_state, name)

    # 3. The frozen files. All are needed for a seal. A practice set needs the plan (so that the seal
    #    conditions are on record before any practice label exists) and the guide, the labeler instructions
    #    and the checker (so that the practice labels can be tied to them). It records the others that are there.
    frozen = {}
    needed = FROZEN_ROLES if verdict else PRACTICE_NEEDS
    for role in FROZEN_ROLES:
        path = getattr(args, role)
        if path and Path(path).exists():
            frozen[role] = sha_of(path)
        elif role in needed or (path and path != str(DEFAULTS.get(role))):
            refuse('FROZEN_FILE_MISSING', 'The %s (%s) is not named or does not exist.' % (ROLE_WORDS.get(role, role), path))
    frozen['briefs'] = {'file': 'write_passages_v2.py', 'sha256': sha(TOOLS / 'write_passages_v2.py'),
                        'briefs_sha256': writer.briefs_sha256(name), 'jobs_sha256': writer.jobs_sha256(name)}

    # 4. The team A launch text: the fixed frame of this tool and the checker's own recipe, word for word.
    checker = load_program(args.checker, 'checker_being_sealed', 'CHECKER_NOT_READABLE')
    recipe = getattr(checker, 'TEAM_A_RECIPE', None)
    if not (isinstance(recipe, str) and recipe.strip()):
        refuse('CHECKER_HOLDS_NO_RECIPE', 'The checker %s has no TEAM_A_RECIPE text. The team A launch text is built from it.' % args.checker)
    launch_bytes = team_a_launch_text(Path(args.guide).name, Path(args.instructions).name, recipe).encode('utf-8')
    launch_sha = hashlib.sha256(launch_bytes).hexdigest()
    frozen['team_a_launch'] = {'file': TEAM_A_LAUNCH_FILE, 'sha256': launch_sha, 'written_into': 'team_a', 'written_by': 'seal_v2.py',
                               'start_line_form': TEAM_A_START_LINE}

    # 5. The owner's signature, the hold table, the signed values and the seal conditions. Only a seal needs them.
    signoff = conditions = None
    if verdict:
        scorer = load_program(args.scorer, 'scorer_being_sealed', 'SCORER_NOT_READABLE')
        signoff = read_signoff(args.owner_signoff, args.signoff_sheet,
                               {role: frozen[role]['sha256'] for role in ('guide', 'plan', 'scorer', 'checker')},
                               five_bar_row_form(scorer))
        read_hold_table(args.hold_table, signoff)
        check_programs(scorer, checker, signoff)
        conditions = read_conditions(args, signoff, frozen, launch_sha)

    # 6. Mechanical checks. No passage is read for content.
    earlier, earlier_files = set(), []
    for path in args.also_not_in:
        texts = texts_of(load_json(path, 'EARLIER_SET_NOT_READABLE'))
        earlier |= texts
        earlier_files.append({'file': Path(path).name, 'sha256': sha(path), 'passages': len(texts)})
    kept, dropped, seen = [], [], set()
    for row in rows:
        text = row['text'].strip()
        words = len(text.split())
        reason = None
        if any(re.search(r'\b' + w + r'\w*\b', text, flags=re.I) for w in writer.FORBIDDEN):
            reason = 'forbidden word'
        elif words < MIN_WORDS or words > MAX_WORDS:
            reason = 'length %d words' % words
        elif text in seen:
            reason = 'exact repeat'
        elif text in earlier:
            reason = 'exact repeat of an earlier set'
        if reason:
            dropped.append({'kind': row['kind'], 'reason': reason})
        else:
            seen.add(text)
            kept.append({'kind': row['kind'], 'setting': row['setting'], 'text': text})
    if not kept:
        refuse('NO_PASSAGE_KEPT', 'Every passage failed a mechanical check.')

    # 7. Fixed-seed shuffle and new ids.
    random.Random(SHUFFLE_SEEDS[name]).shuffle(kept)
    for index, row in enumerate(kept, 1):
        row['id'] = ID_FORMATS[name] % index

    # 8. Write the passage files and the launch text, then the record last. The kinds go to their own folder.
    out.mkdir(parents=True, exist_ok=True)
    hidden.mkdir(parents=True, exist_ok=True)
    dump(out / passage_file, [{'id': r['id'], 'text': r['text']} for r in kept])
    dump(hidden / KINDS_FILE, [{'id': r['id'], 'kind': r['kind'], 'setting': r['setting'], 'text': r['text']} for r in kept])
    team = out / 'team_a'
    team.mkdir(exist_ok=True)
    partial = team / (TEAM_A_LAUNCH_FILE + '.partial')
    partial.write_bytes(launch_bytes)
    os.replace(partial, team / TEAM_A_LAUNCH_FILE)
    size = args.chunk_size or DEFAULT_CHUNK[name]
    chunks = []
    for number, start in enumerate(range(0, len(kept), size), 1):
        part = kept[start:start + size]
        file_name = 'chunk_%02d.json' % number
        dump(team / file_name, [{'id': r['id'], 'text': r['text']} for r in part])
        chunks.append({'file': file_name, 'first': part[0]['id'], 'last': part[-1]['id'], 'passages': len(part)})
    kinds, settings = {}, {}
    for r in kept:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
        settings[r['setting']] = settings.get(r['setting'], 0) + 1
    tool_now = sha(TOOLS / 'write_passages_v2.py')
    passages_sha = sha(out / passage_file)
    also = ([Path(p) for p in args.also_hash] + [p for p in ALSO_HASH_IF_THERE if p.is_file()]
            + [Path(getattr(args, role)) for role in ('instructions', 'team_b_tool') if role in frozen])
    record = {
        'schema': SEAL_SCHEMA if verdict else PRACTICE_SCHEMA,
        'is_a_seal': verdict,
        'note': ('Sealed before any label team started.' if verdict else
                 'Practice set. Not a seal. Practice passages are never scored for the verdict.'),
        'plan_name': name,
        ('sealed_utc' if verdict else 'written_utc'): datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    record.update(frozen)          # "guide", "plan", "checker", "scorer", "hold_table", "fixture", "instructions", ... at the top
    record.update({
        'passages': {'file': passage_file, 'sha256': passages_sha},
        'passages_kinds_hidden': {'file': KINDS_FILE, 'sha256': sha(hidden / KINDS_FILE),
                                  'note': 'Kept in a folder of its own, apart from the passages and the team A chunks.'},
        'frozen_roles_in_this_record': sorted(frozen) + ['passages'],
        'writer': {'provider': state.get('provider'), 'model': state.get('model'), 'state_file': Path(args.writer_state).name,
                   'state_sha256': sha(args.writer_state), 'tool_sha256_at_start': state.get('tool_sha256_at_start'),
                   'tool_sha256_now': tool_now, 'writer_tool_unchanged_since_writing': state.get('tool_sha256_at_start') == tool_now},
        'passages_written': len(rows), 'passages_dropped': dropped, 'passages_kept': len(kept),
        'kept_by_writer_kind': dict(sorted(kinds.items())),
        'kept_by_setting': dict(sorted(settings.items())),
        'ids': {'first': kept[0]['id'], 'last': kept[-1]['id']},
        'shuffle_seed': SHUFFLE_SEEDS[name], 'python': platform.python_version(),
        'tools_sha256': {'write_passages_v2.py': tool_now, 'seal_v2.py': sha(Path(__file__).resolve())},
        'also_hashed': [{'file': p.name, 'sha256': sha(p)} for p in also],
        'earlier_sets_checked_for_exact_repeats': earlier_files,
        'owner_signoff': signoff, 'seal_conditions': conditions,
        'team_a_chunks': chunks,
        'no_label_existed_when_sealed': True,
    })
    if verdict:
        record['passages_sealed_sha256'] = passages_sha
    dump(out / record_name, record)
    reasons = {}
    for d in dropped:
        key = d['reason'].split(' ')[0] if d['reason'].startswith('length') else d['reason']
        reasons[key] = reasons.get(key, 0) + 1
    print(json.dumps({'status': 'SEALED' if verdict else 'PRACTICE_SET_WRITTEN', 'record': record_name,
                      'passages_written': len(rows), 'passages_kept': len(kept), 'dropped': len(dropped), 'dropped_by_reason': reasons,
                      'kept_by_writer_kind': record['kept_by_writer_kind'], 'ids': record['ids'], 'team_a_chunks': len(chunks),
                      'passages_file': passage_file, 'passages_sha256': passages_sha, 'kinds_folder': str(hidden),
                      'team_a_launch_text': 'team_a/' + TEAM_A_LAUNCH_FILE, 'team_a_launch_sha256': launch_sha,
                      'frozen': record['frozen_roles_in_this_record'],
                      'owner_changed_items': signoff['changed_items'] if signoff else None,
                      'owner_changed_items_not_checked_by_this_tool': signoff['changed_items_not_checked_by_this_tool'] if signoff else None,
                      'practiced_files_waiver': signoff['practiced_files_waiver'] if signoff else None}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
