"""Mechanical checks, shuffle, new ids and the seal for label-agreement attempt 3, version 2.2.

Plan: 09_LABEL_AGREEMENT_PLAN_v2_2.md. Modelled on tools/seal_verdict.py (attempt 1). Plain Python. No model,
no network, no key. It reads no passage for content, and nobody chooses among passages.

MODES
  signing-line   Seals nothing. Prints the line the owner pastes to sign, with the two fingerprints.
  practice       The 30 practice passages. Writes PRACTICE_SET.json ("is_a_seal": false).
  verdict        The 440 verdict passages. Writes SEAL.json ("is_a_seal": true).

WHAT practice AND verdict DO
  1. Mechanical checks. A passage is dropped if it holds a forbidden word, has fewer than 30 or more than 120
     words, or repeats another passage exactly (in this set, or in a set named with --also-not-in; the 428
     old passages and the practice passages are always compared). Drops are listed with their reason.
  2. A fixed-seed shuffle and new ids (practice R01..., verdict W001...).
  3. A passage file with id and text only, and team A chunk files with id and text only. Team A's fixed task
     message (TEAM_A_TASK below) goes to team_a/TASK_MESSAGE.txt. The writer's kinds go to a folder of their
     own beside the output folder, never inside it.
  4. One record with the sha256 of the passages, the guide, the instructions, the checker, the scorer, the plan
     and the attempt-1 program tools/verdict.py (the scorer takes its small-word list and its table of fields
     that must agree from that file); of every file of the scorer's fixture folder (FIXTURE_EXPECTED.json pins
     every number of the measure); of the team B tool, team A's tool, the writer tool, this tool and team A's
     task message; of the Part A builder (tools/build_guide_part_a_v21.py), the canon file it copies from and
     the owner's ruling record; and the owner's sign-off.

IT REFUSES, and writes nothing, when
  - in every mode, signing-line too: the Part A builder's check mode does not print IDENTICAL for the guide.
    Part A of the guide must be the text of the canon file and the owner's sentence, as the script copies them;
  - the output folder already holds a record, a passage file or any label file (labels*);
  - a frozen file is missing, or the writer state is not the finished job list of write_passages_v22.py;
  - tools/verdict.py is not the file attempt 1 sealed (ATTEMPT1_SHA256);
  - the owner sign-off record is not named, is missing or cannot be read, or its two fingerprints are not the
    first 12 characters of the sha256 of the guide and of the plan on disk;
  - the signed numbers are not the numbers the scorer holds (read from the scorer's source, not run);
  - the scorer's fixture mode does not print PASS (this tool runs it: exit code 0, the word PASS, no FAIL);
  - verdict mode: the practice record is missing; or the guide, the plan, the sign-off, the attempt-1 program,
    the canon file, the owner's ruling record or a file of the fixture folder is not the one the practice
    record holds. The guide, the measure and the bars may not change after practice labels exist: that is a
    new version with a new review;
  - verdict mode: a practice receipt does not say "complete": true, or does not name the guide, the
    instructions, the checker and the practice passages about to be sealed (team A: also the task message
    and its tool, tools/team_a_receipt_v22.py; team B: also its tool). After a change to one of those files
    the team labels the 30 practice passages again, under a new file name. A new practice pass with the
    final files, or no seal;
  - verdict mode: the scorer's practice mode, run by this tool on the practice labels with the files about to
    be sealed, does not end with exit code 0 and the line PRACTICE CHECK: PASS.

THE OWNER SIGN-OFF RECORD (a JSON object; the operator writes it from the owner's pasted line)
  {"schema": "casalescence/label-agreement-v22-owner-signoff/1", "utc_recorded": "...",
   "owner_pasted_text_verbatim": "SIGNED: label-agreement v2.2, guide <12>, plan <12>, as proposed.",
   "guide_sha256_first12": "<12>", "plan_sha256_first12": "<12>"}
  The pasted line may end: as proposed except pass mark = 0.75; minimum cases = 60.
  Names: pass mark, presence mark, minimum cases, minimum empty passages. This tool reads the line itself.
  It cannot check that a signature is real. That is the operator's record to keep true.

USAGE
  seal_v22.py signing-line [--guide G] [--plan P]
  seal_v22.py practice --writer-state S --out-dir D --signoff R [options]
  seal_v22.py verdict  --writer-state S --out-dir D --signoff R --practice-set D2/PRACTICE_SET.json
                       --practice-labels-a A [A2 ...] --practice-labels-b B
                       --practice-receipt-a RA --practice-receipt-b RB [options]
  options: --guide --plan --instructions --checker --scorer --team-b-tool --attempt1-program  (see DEFAULTS)
           --fixture-args "--fixture"   how to start the scorer's fixture mode
           --fixture-dir DIR            the fixture folder; it is hashed and handed to the scorer
           --bar-names BAR_E,BAR_KAPPA,MIN_CASES,MIN_ABSENT   the scorer's four constants, in sheet order
           --chunk-size 40   --also-not-in FILE ...   --no-labels-in DIR ...
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
import random
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import write_passages_v22 as writer  # noqa: E402  (the fixed job lists and the forbidden words)
import build_guide_part_a_v21 as part_a  # noqa: E402  (where the canon file and the owner's ruling record are)

DEFAULTS = {'guide': '02_LABELING_GUIDE_v2_2.md', 'plan': '09_LABEL_AGREEMENT_PLAN_v2_2.md',
            'instructions': 'label_v22/LABELER_INSTRUCTIONS.txt', 'checker': 'tools/check_labels_v21.py',
            'scorer': 'tools/verdict_v22.py', 'team_b_tool': 'tools/label_outside_v22.py',
            'attempt1_program': 'tools/verdict.py'}   # the scorer imports it: part of the measure
SEEDS = {'practice': 20261034, 'verdict': 20261033}
IDS = {'practice': 'R%02d', 'verdict': 'W%03d'}
RECORD = {'practice': 'PRACTICE_SET.json', 'verdict': 'SEAL.json'}
PASSAGES = {'practice': 'passages_practice.json', 'verdict': 'passages_sealed.json'}
SCHEMA = {'practice': 'casalescence/label-agreement-v22-practice-set/1', 'verdict': 'casalescence/label-agreement-v22-seal/1'}
SIGNOFF_SCHEMA = 'casalescence/label-agreement-v22-owner-signoff/1'
# The four numbers the owner signs, by their names on the sign-off sheet, with the proposed values.
PROPOSED = {'pass mark': 0.80, 'presence mark': 0.60, 'minimum cases': 50, 'minimum empty passages': 50}
SIGN_LINE = re.compile(r'^SIGNED: label-agreement v2\.2, guide ([0-9a-f]{12,64}), plan ([0-9a-f]{12,64}), as proposed(?: except (.+?))?\.?$')
OLD_PASSAGES = [ROOT / 'verdict' / 'passages_sealed.json',                  # the 428 passages of attempt 1
                ROOT / 'label_v21' / 'verdict' / 'passages_sealed.json',     # the 427 sealed passages of attempt 2
                ROOT / 'label_v21' / 'practice' / 'passages_practice.json']  # the 30 practice passages of attempt 2
ATTEMPT1_SHA256 = 'ee85ccf5a909d0ed252f6b3faa42cdb5f57510613781e89d8d4aaa2d0d52cbbb'   # tools/verdict.py as verdict/SEAL.json of attempt 1 holds it
# Team A's task message: fixed text, as HEAD, ASK and AGAIN are for team B in label_outside_v22.py. The tool
# team_a_receipt_v22.py builds each sub-agent's prompt from this message, the guide and the instructions, and nothing
# else. It fills in the three <...> places and changes no other character. The receipt names the sha256 of this text.
TEAM_A_TASK = (
    'You are a careful labeler. Work only from the labeling guide and the labeler instructions that follow this message. '
    'Never force a label.\n\n'
    'Your passages are in <CHUNK FILE>, a JSON list of {"id", "text"}. Label every passage in it, each on its own.\n'
    'Write your records as ONE JSON list in your working file <WORKING FILE>.\n'
    'Hand the records in with this command and no other: <TAKE COMMAND>\n'
    'The command runs a format checker. It reads form only. Every new or changed record it reads is logged as a try. '
    'You have three tries in all for one passage. If it prints messages, fix what they name in the working file and run '
    'the same command again. Stop when it prints that 0 passages are still open.\n'
    'Never run the checker in any other way, and never import it. Open no file but the two named above: not the '
    'checker, not a labels file, not a try log, not another chunk.\n')
PASS_LINE = 'PRACTICE CHECK: PASS'


def refuse(message):
    raise SystemExit('REFUSED: ' + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    """Write to a .partial file, then rename. LF line ends."""
    partial = Path(path).with_name(Path(path).name + '.partial')
    partial.write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(partial, path)


def load(path, what):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        refuse('cannot read %s (%s): %s' % (what, path, type(error).__name__))


def signing_line(guide, plan):
    return 'SIGNED: label-agreement v2.2, guide %s, plan %s, as proposed.' % (sha(guide)[:12], sha(plan)[:12])


def read_signoff(path, guide, plan):
    """Read the owner's pasted line. Returns the sign-off block for the record, with the four signed numbers."""
    if not path or not Path(path).is_file():
        refuse('name the owner sign-off record with --signoff. Nothing is sealed or labeled before the owner signs.')
    record = load(path, 'the owner sign-off record')
    line = record.get('owner_pasted_text_verbatim') if isinstance(record, dict) else None
    if not isinstance(line, str) or record.get('schema') != SIGNOFF_SCHEMA:
        refuse('the sign-off record needs schema "%s" and "owner_pasted_text_verbatim"' % SIGNOFF_SCHEMA)
    match = SIGN_LINE.match(' '.join(line.split()))
    if not match:
        refuse('the pasted line does not have the form: ' + signing_line(guide, plan))
    for name, path_on_disk, printed, kept in (('guide', guide, match.group(1), record.get('guide_sha256_first12')),
                                              ('plan', plan, match.group(2), record.get('plan_sha256_first12'))):
        real = sha(path_on_disk)
        if not real.startswith(printed) or kept != real[:12]:
            refuse('the sign-off was not made against this %s. On disk: %s. In the pasted line: %s. In the record: %s. '
                   'A %s that changed after the signature needs one new pasted line.' % (name, real[:12], printed[:12], kept, name))
    bars, changed = dict(PROPOSED), {}
    for part in [p.strip() for p in (match.group(3) or '').split(';') if p.strip()]:
        name, _, value = (x.strip() for x in part.partition('='))
        try:
            number = float(value) if name in ('pass mark', 'presence mark') else int(value)
        except ValueError:
            number = None
        if name not in PROPOSED or number is None or number <= 0 or (isinstance(number, float) and number > 1):
            refuse('cannot read the change "%s". Names: %s. A mark is a number above 0 and at most 1; a count is a whole number.' % (part, ', '.join(PROPOSED)))
        bars[name], changed[name] = number, number
    return {'file': Path(path).name, 'sha256': sha(path), 'owner_pasted_text_verbatim': line, 'utc_recorded': record.get('utc_recorded'),
            'signed_against': {'guide_sha256_first12': sha(guide)[:12], 'plan_sha256_first12': sha(plan)[:12]},
            'numbers_signed': bars, 'numbers_changed_by_the_owner': changed, 'numbers_proposed': PROPOSED}


def scorer_numbers(path):
    """Every top-level NAME = number (also NAME, NAME = number, number) in the scorer, read without running it."""
    found = {}
    for node in ast.parse(Path(path).read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
            both = isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple)
            for name, number in (zip(target.elts, value.elts) if both else [(target, value)]):
                if isinstance(name, ast.Name) and isinstance(number, ast.Constant) and type(number.value) in (int, float):
                    found[name.id] = number.value
    return found


def check_bars(signed, scorer, bar_names):
    """The scorer must hold the four signed numbers. Returns {sheet name: [scorer constant, value]}."""
    names = [n.strip() for n in bar_names.split(',')]
    if len(names) != len(PROPOSED):
        refuse('--bar-names needs four names, in this order: ' + ', '.join(PROPOSED))
    held, out, wrong = scorer_numbers(scorer), {}, []
    for item, constant in zip(PROPOSED, names):
        out[item] = [constant, held.get(constant)]
        if constant not in held or abs(held[constant] - signed[item]) > 1e-9:
            wrong.append('%s: signed %s, scorer %s = %s' % (item, signed[item], constant, held.get(constant, 'not found')))
    if wrong:
        refuse('the scorer does not hold the signed numbers (%s). Put the signed numbers in the scorer, or name its four '
               'constants with --bar-names.' % '; '.join(wrong))
    return out


def run_scorer(scorer, arguments, what):
    """Run one mode of the scorer (or of another tool) as its own process. Returns (the finished process, the command as text)."""
    command = [sys.executable, '-B', str(scorer)] + [str(a) for a in arguments]
    try:
        return subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=600, cwd=str(ROOT)), ' '.join(command[1:])
    except (OSError, subprocess.TimeoutExpired) as error:
        refuse('the %s could not be run: %s' % (what, type(error).__name__))


def run_part_a_check(tool, guide):
    """Part A of the guide must be what the builder cuts out of the canon file and the owner's ruling record now: its
    check mode must end with exit code 0 and print IDENTICAL, and nothing else. It refuses a canon file that is not the pinned one."""
    done, command = run_scorer(tool, ['check', guide], 'Part A check')
    if done.returncode != 0 or done.stdout.strip() != 'IDENTICAL':
        refuse('Part A of the guide is not the canon text as the script copies it (exit code %d). The check printed: %s'
               % (done.returncode, (done.stdout + done.stderr).strip()[-400:]))
    return {'command': command, 'exit_code': 0, 'printed': 'IDENTICAL', 'canon_sha256_pinned_in_the_builder': part_a.CANON_SHA256}


def run_fixture(scorer, fixture_args, folder):
    """Run the scorer's fixture mode on the fixture folder. It must end with exit code 0 and print the word PASS and
    no FAIL. Also returns the sha256 of every file of that folder: FIXTURE_EXPECTED.json pins the measure."""
    if not (Path(folder) / 'FIXTURE_EXPECTED.json').is_file():
        refuse('the fixture folder %s holds no FIXTURE_EXPECTED.json' % folder)
    done, command = run_scorer(scorer, shlex.split(fixture_args) + ['--fixture-dir', folder], 'scorer\'s fixture mode')
    lines = [line.strip() for line in done.stdout.splitlines() if re.search(r'\bPASS\b', line)]
    if done.returncode != 0 or not lines or re.search(r'\bFAIL', done.stdout):
        refuse('the scorer\'s fixture mode did not print PASS (exit code %d). Last output: %s'
               % (done.returncode, (done.stdout + done.stderr).strip()[-300:]))
    return {'command': command, 'exit_code': 0, 'pass_line': lines[-1][:200],
            'stdout_sha256': hashlib.sha256(done.stdout.encode('utf-8')).hexdigest(),
            'files_sha256': {p.name: sha(p) for p in sorted(Path(folder).iterdir()) if p.is_file()}}


def run_practice_check(args, frozen, hashes, passages):
    """Verdict mode only. The practice labels must have been made with the files about to be sealed (both receipts
    say so), and the scorer's practice mode, run here with those files, must print PRACTICE CHECK: PASS."""
    given = {key: getattr(args, 'practice_' + key) for key in ('labels_a', 'labels_b', 'receipt_a', 'receipt_b')}
    if not all(given.values()):
        refuse('verdict mode needs --practice-labels-a, --practice-labels-b, --practice-receipt-a and --practice-receipt-b. '
               'The 440 are sealed only after the practice tool check has passed with the final files.')
    want = dict({role + '_sha256': hashes[role] for role in ('guide', 'instructions', 'checker')}, passages_sha256=sha(passages), complete=True)
    own = {'a': {'task_message_sha256': hashlib.sha256(TEAM_A_TASK.encode('utf-8')).hexdigest(), 'tool_sha256': hashes['team_a_tool']},
           'b': {'tool_sha256': hashes['team_b_tool']}}
    wrong = []
    for team in 'ab':
        receipt = load(given['receipt_' + team], 'the practice receipt of team ' + team.upper())
        wrong += ['team %s: %s' % (team.upper(), key) for key, value in dict(want, **own[team]).items()
                  if not isinstance(receipt, dict) or receipt.get(key) != value]
    if wrong:
        refuse('the practice labels are not complete, or were not made with the files about to be sealed (%s). After a change to '
               'the instructions, the checker, a team\'s tool or team A\'s task message, the team labels the 30 practice passages '
               'again under a new file name. A new practice pass with the final files, or no seal.' % '; '.join(wrong))
    done, command = run_scorer(frozen['scorer'], ['practice', '--passages', passages, '--labels-a'] + given['labels_a'] + ['--labels-b']
                               + given['labels_b'] + ['--guide', frozen['guide'], '--instructions', frozen['instructions'],
                                                      '--receipt-a', given['receipt_a'], '--receipt-b', given['receipt_b']], 'scorer\'s practice mode')
    if done.returncode != 0 or PASS_LINE not in done.stdout:
        refuse('the practice tool check did not pass with the files about to be sealed (exit code %d). Nothing is sealed. Last '
               'output: %s' % (done.returncode, (done.stdout + done.stderr).strip()[-300:]))
    return {'command': command, 'exit_code': 0, 'pass_line': PASS_LINE, 'stdout_sha256': hashlib.sha256(done.stdout.encode('utf-8')).hexdigest(),
            'files_sha256': {'%s: %s' % (key, Path(p).name): sha(p) for key in sorted(given)
                             for p in ([given[key]] if isinstance(given[key], str) else given[key])}}


def read_writer_state(path, mode):
    """The written passages, in the order of the fixed job list. Refuses an unfinished or foreign state file."""
    state = load(path, 'the writer state')
    if state.get('plan') != mode or state.get('jobs_sha256') != writer.jobs_sha256(mode) or state.get('briefs_sha256') != writer.briefs_sha256(mode):
        refuse('the writer state is not the %s job list of write_passages_v22.py' % mode)
    rows = [row for start in sorted(state.get('chunks', {}), key=int) for row in state['chunks'][start]]
    if len(rows) != writer.TOTALS[mode] or [(r['setting'], r['kind']) for r in rows] != [tuple(j) for j in writer.jobs(mode)]:
        refuse('the writer state holds %d of %d passages, or not in the order of the job list' % (len(rows), writer.TOTALS[mode]))
    models = sorted({str(entry.get('reply_model')) for entry in state.get('log', []) if entry.get('ok')})
    return rows, {'provider': state.get('provider'), 'model_asked_for': state.get('model'), 'models_that_answered': models,
                  'jobs_sha256': state['jobs_sha256'], 'briefs_sha256': state['briefs_sha256'], 'state_sha256': sha(path)}


def mechanical(rows, earlier):
    """Drop by rule only: a forbidden word, the length, an exact repeat. Returns (kept, dropped)."""
    kept, dropped, seen = [], [], set(earlier)
    for row in rows:
        text = row['text'].strip()
        words, reason = len(text.split()), None
        if any(re.search(r'\b' + w + r'\w*\b', text, flags=re.I) for w in writer.FORBIDDEN):
            reason = 'forbidden word'
        elif words < 30 or words > 120:
            reason = 'length %d words' % words
        elif text in seen:
            reason = 'exact repeat'
        if reason:
            dropped.append({'kind': row['kind'], 'reason': reason})
        else:
            seen.add(text)
            kept.append({'kind': row['kind'], 'setting': row['setting'], 'text': text})
    return kept, dropped


def main(argv=None):
    parser = argparse.ArgumentParser(description='Seal tool for label-agreement attempt 3, version 2.2.')
    parser.add_argument('mode', choices=['signing-line', 'practice', 'verdict'])
    for name in ('writer-state', 'out-dir', 'signoff', 'practice-set', 'practice-receipt-a', 'practice-receipt-b'):
        parser.add_argument('--' + name, default='')
    for name, default in DEFAULTS.items():
        parser.add_argument('--' + name.replace('_', '-'), default=str(ROOT / default))
    parser.add_argument('--fixture-args', default='--fixture')
    parser.add_argument('--fixture-dir', default=str(ROOT / 'label_v21' / 'fixture'))
    parser.add_argument('--bar-names', default='BAR_E,BAR_KAPPA,MIN_CASES,MIN_ABSENT')
    parser.add_argument('--chunk-size', type=int, default=40)
    for name in ('also-not-in', 'no-labels-in', 'practice-labels-a', 'practice-labels-b'):
        parser.add_argument('--' + name, nargs='*', default=[])
    args = parser.parse_args(argv)
    mode = args.mode
    frozen = {role: Path(getattr(args, role)) for role in DEFAULTS}
    frozen.update(writer_tool=HERE / 'write_passages_v22.py', seal_tool=Path(__file__).resolve(), team_a_tool=HERE / 'team_a_receipt_v22.py',
                  part_a_tool=Path(part_a.__file__).resolve(), canon=Path(part_a.CANON), owner_ruling=Path(part_a.RULING),
                  owner_answers=ROOT / 'label_v22_draft' / 'OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json',
                  team_a_wrapper=ROOT / 'label_v22' / 'TEAM_A_WRAPPER.txt',
                  flag_gate=HERE / 'flag_gate_v22.py')   # not options: the check reads these very files
    missing = [role for role, path in frozen.items() if not path.is_file()
               and (mode != 'signing-line' or role in ('guide', 'plan', 'part_a_tool', 'canon', 'owner_ruling'))]
    if missing:
        refuse('missing file for: %s' % ', '.join('%s (%s)' % (role, frozen[role]) for role in missing))
    part_a_check = run_part_a_check(frozen['part_a_tool'], frozen['guide'])
    if mode == 'signing-line':
        print(signing_line(frozen['guide'], frozen['plan']))
        print(json.dumps({'schema': SIGNOFF_SCHEMA, 'utc_recorded': '<when>', 'owner_pasted_text_verbatim': '<the owner\'s pasted line, unchanged>',
                          'guide_sha256_first12': sha(frozen['guide'])[:12], 'plan_sha256_first12': sha(frozen['plan'])[:12]}, indent=1))
        return 0
    if not args.writer_state or not args.out_dir:
        refuse('name --writer-state and --out-dir')
    out = Path(args.out_dir)
    hidden = out.parent / (out.name + '_HIDDEN_FROM_LABELERS')
    for folder in [out, hidden] + [Path(d) for d in args.no_labels_in]:
        found = sorted(p.name for p in folder.rglob('*') if p.is_file() and (p.name.startswith('labels') or p.name in (RECORD[mode], PASSAGES[mode]))) if folder.is_dir() else []
        if found:
            refuse('%s already holds %s. A set is sealed once, before any label exists.' % (folder, ', '.join(found[:5])))

    # every check comes before the first file is written
    signoff = read_signoff(args.signoff, frozen['guide'], frozen['plan'])
    scorer_constants = check_bars(signoff['numbers_signed'], frozen['scorer'], args.bar_names)
    fixture = run_fixture(frozen['scorer'], args.fixture_args, args.fixture_dir)
    hashes = {role: sha(path) for role, path in frozen.items()}
    if hashes['attempt1_program'] != ATTEMPT1_SHA256:
        refuse('%s is not the attempt-1 program as it was sealed in attempt 1 (found %s)' % (frozen['attempt1_program'], hashes['attempt1_program'][:12]))
    gone = [str(p) for p in OLD_PASSAGES if not p.is_file()]
    if gone:
        refuse('an earlier passage set to compare against is missing: %s' % ', '.join(gone))
    not_in, practice_block = [Path(p) for p in args.also_not_in] + list(OLD_PASSAGES), None
    if mode == 'verdict':
        if not args.practice_set or not Path(args.practice_set).is_file():
            refuse('verdict mode needs --practice-set: the record of the practice tool check')
        practice = load(args.practice_set, 'the practice record')
        if not isinstance(practice, dict) or practice.get('schema') != SCHEMA['practice'] or practice.get('is_a_seal') is not False:
            refuse('%s is not a practice record of this tool' % args.practice_set)
        moved = [role for role in ('guide', 'plan', 'attempt1_program', 'canon', 'owner_ruling', 'owner_answers', 'team_a_wrapper', 'flag_gate') if (practice.get(role) or {}).get('sha256') != hashes[role]]
        if practice['owner_signoff']['sha256'] != signoff['sha256']:
            moved.append('owner sign-off')
        then, now = (practice.get('scorer_fixture') or {}).get('files_sha256') or {}, fixture['files_sha256']
        moved += ['the measure (fixture file %s)' % name for name in sorted(set(then) | set(now)) if then.get(name) != now.get(name)]
        if moved:
            refuse('changed since the practice record was written: %s. The guide, the measure and the bars may not change after '
                   'practice labels exist. That is a new version with a new review.' % ', '.join(moved))
        practice_passages = Path(args.practice_set).parent / practice['passages']['file']
        if not practice_passages.is_file() or sha(practice_passages) != practice['passages']['sha256']:
            refuse('%s is not the passage file the practice record holds' % practice_passages)
        not_in.append(practice_passages)
        practice_block = {'file': Path(args.practice_set).name, 'sha256': sha(args.practice_set), 'guide_measure_and_signoff_unchanged': True,
                          'practice_check_run_by_this_tool': run_practice_check(args, frozen, hashes, practice_passages),
                          'tool_files_changed_since_practice': {role: {'at_practice': practice[role]['sha256'], 'now': hashes[role]}
                                                                for role in ('instructions', 'checker', 'scorer', 'team_a_tool', 'team_b_tool', 'writer_tool',
                                                                             'seal_tool', 'part_a_tool') if practice[role]['sha256'] != hashes[role]}}
    earlier = [p['text'].strip() for path in not_in for p in load(path, 'an earlier passage file')]
    rows, writer_block = read_writer_state(args.writer_state, mode)
    kept, dropped = mechanical(rows, earlier)
    random.Random(SEEDS[mode]).shuffle(kept)
    for index, row in enumerate(kept, 1):
        row['id'] = IDS[mode] % index

    # all checks passed: write
    (out / 'team_a').mkdir(parents=True, exist_ok=True)
    hidden.mkdir(parents=True, exist_ok=True)
    plain = [{'id': r['id'], 'text': r['text']} for r in kept]
    dump(out / PASSAGES[mode], plain)
    chunks = []
    for number, start in enumerate(range(0, len(plain), max(1, args.chunk_size)), 1):
        part = plain[start:start + max(1, args.chunk_size)]
        dump(out / 'team_a' / ('chunk_%02d.json' % number), part)
        chunks.append({'file': 'chunk_%02d.json' % number, 'first': part[0]['id'], 'last': part[-1]['id'], 'passages': len(part)})
    task_file = out / 'team_a' / 'TASK_MESSAGE.txt'
    task_file.write_bytes(TEAM_A_TASK.encode('utf-8'))
    kinds = {}
    for r in kept:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    dump(hidden / 'passages_kinds.json', {'kept_by_writer_kind': dict(sorted(kinds.items())), 'dropped': dropped,
                                          'passages': [{'id': r['id'], 'kind': r['kind'], 'setting': r['setting'], 'text': r['text']} for r in kept]})
    hashes.update(passages=sha(out / PASSAGES[mode]), team_a_task_message=sha(task_file))
    record = {'schema': SCHEMA[mode], 'is_a_seal': mode == 'verdict', 'mode': mode,
              'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'writer': writer_block,
              'passages_written': len(rows), 'passages_dropped': [d['reason'] for d in dropped], 'passages_kept': len(kept),
              'passages_sealed_sha256': hashes['passages'], 'sha256': dict(sorted(hashes.items()))}
    names = dict(frozen, passages=out / PASSAGES[mode], team_a_task_message=task_file)
    record.update({role: {'file': names[role].name, 'sha256': hashes[role]} for role in sorted(hashes)})
    record.update(owner_signoff=signoff, scorer_constants_compared=scorer_constants, scorer_fixture=fixture, part_a_check=part_a_check,
                  team_a_chunks=chunks, shuffle_seed=SEEDS[mode], compared_for_exact_repeats=[os.path.relpath(p, ROOT).replace(os.sep, '/') for p in not_in],
                  hidden_kinds={'folder': hidden.name, 'file': 'passages_kinds.json', 'sha256': sha(hidden / 'passages_kinds.json')},
                  no_label_existed_when_sealed=True)
    if practice_block:
        record['practice_set'] = practice_block
    dump(out / RECORD[mode], record)
    print(json.dumps({'written': str(out / RECORD[mode]), 'is_a_seal': record['is_a_seal'], 'passages_written': len(rows),
                      'passages_kept': len(kept), 'dropped': record['passages_dropped'], 'chunks': len(chunks),
                      'passages_sha256': hashes['passages'], 'numbers_signed': signoff['numbers_signed'],
                      'fixture': fixture['pass_line'], 'record_sha256': sha(out / RECORD[mode])}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
