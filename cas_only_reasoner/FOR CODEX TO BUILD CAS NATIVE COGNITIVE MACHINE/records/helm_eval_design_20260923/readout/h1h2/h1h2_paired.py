"""H1/H2 paired no-regression reader, one seed pair at a time (EVALUATION_DESIGN_v0_4 s7.2, amendment A2.6).

WHAT IT ANSWERS. For one seed pair (a repaired run and its unchanged control) and each historical gate set, at the
fixed final endpoint (checkpoint 10 = final.pt after 1,470 main updates, A2.5):
  H1 = G_LEARN_population (18 questions), H2 = G_LEARN_all_kinds (45 questions);
  b' = questions only the repaired run gets right (gains); c' = questions only the unchanged run gets right (losses).
A gate is FLAGGED as a regression iff c' > b' and the exact one-sided p(c', b' + c') <= 1/100.
The smallest flaggable result is 7 losses with no gains (p = 1/128). Six losses with no gains give p = 1/64 and are
NOT flagged; that sensitivity is printed with every reading.

WHAT IT ALWAYS PRINTS (A2.6). Every gain, loss and tie, by question id and kind; both accuracies; the difference; the
exact p-value; and every old-gate crossing (a historical gate one arm passes and the other fails), read from the
pinned grader's own readings. When no gate is flagged, the caption is exactly:
    no regression detected by the listed paired tests
Never write "no ability lost", "preserved performance" or "noninferior" from this reader: failing to reject is not
proof of preservation.

THE UNIT is the frozen grader's (records/typed_pointer_001/evaluate_gates.py, LF sha256 d3e0ea97...,
`question_outcomes` and `scoring_rows`): a question is right iff every one of its held records is right, and the
checkpoint-10 table merges every `<prefix>_p10_scoring.json` that the job's own manifest lists. The held panel (50
questions, 127 records) is read from `heldback_p02_scoring.json`. Measured on 2026-09-24: this unit reproduces the
frozen Helm 2.0 reading's population and all-kinds counts at every checkpoint (0, 1, 2, 4, 6, 8, 10) of all three
seeds. Every file read is checked against the sha256 and byte count in the job's own manifest.json. That shows the
receipt matches itself; it is not independent custody.

READING ORDER (prereg A5.1/A5.3). H1 and H2 each hold the 5 analogy questions. On a repaired arm, the registered
view may be opened only after ITEM2_PASS and the matched-start check (A5.5). Before that, only the non-analogy view
(--mask-analogy: 13 and 40 questions) may be printed, and it is labelled exploratory (claude-0024 Q-J default). The
program refuses to run without an explicit view flag, so the analogy-inclusive view is never a default. The
non-analogy view shows no old-gate crossings, because every historical gate is computed over sets that include
analogy questions.

SCOPE. H1 and H2 only. The V gate (HSET-2 cells that can carry a claim) belongs to the E1 scorer, and the output
lists it as not covered. Pure Python: it reads small JSON files only. No torch, no course load, no network.

Usage:
  python -B h1h2_paired.py --seed 20260917 --repaired <receipt dir> --unchanged <receipt dir> \
      --unchanged-gate-reading <.../typed_pointer_001/admission_001/gate_reading.json> \
      (--mask-analogy | --registered-view) [--repaired-gate-reading <gate_reading.json of the repaired study>]
A receipt dir holds collected/results/artifacts/. Output: one JSON document on stdout.
Exit 0: a reading was printed, flagged or not. Exit 1: TOOL_STOP, nothing was read (the reason is printed as JSON).
Exit 2: usage refused.

Label: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from fractions import Fraction
from math import comb
from pathlib import Path

READER = 'h1h2-paired/1.0'
CAPTION = 'no regression detected by the listed paired tests'
FORBIDDEN_WORDING = ('no ability lost', 'preserved performance', 'noninferior')
ALPHA = Fraction(1, 100)
FINAL_CHECKPOINT = 10
PANEL_FILE = 'heldback_p02_scoring.json'
PANEL_PHASE = 'heldback_p02'
ANALOGY = 'analogy'
GATE_READING_SCHEMA = 'cncm.typed-pointer-gate-reading/0.1'
PINNED_GRADER = 'records/typed_pointer_001/evaluate_gates.py LF sha256 d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d'
SCORING_NAME = re.compile(r'^(?P<prefix>[A-Za-z0-9_]+)_p(?P<number>\d{2})_scoring\.json$')
GATES = (('H1', 'G_LEARN_population'), ('H2', 'G_LEARN_all_kinds'))
NOT_COVERED = ['V: every v0.4 HSET-2 cell with can_carry_a_claim true (read by the E1 scorer, not by this reader)']

# PINS, measured 2026-09-24 from the committed Helm 2.0 reading records/typed_pointer_001/admission_001/
# gate_reading.json (sha256 52877c1670132c70..., git blob 0bdb520e) and the heldback_p02 panel of receipt_20260917,
# _20260918 and _20260919 (identical in all three). ids_sha256 = sha256 of the sorted question ids joined by "\n".
# The panel digest is over the sorted "query_id<TAB>record_id" lines. A gate set or panel that does not reproduce
# its pin is a TOOL_STOP: the question sets are fixed by design s7.2 and may not drift.
PINS = {
    'H1': (18, '8c74e3df62df224b9b0cb1372033c52d04d7b04b13d5051daeb45db5c16fa9fc'),
    'H2': (45, 'e0d967b81c83a85f1e63ab3e250b97b0cb5124f6950e2605237532eefc0f1007'),
    'H1_non_analogy': (13, '073e91a30fc7692a429f34f10cf799c4c0b86d4611e57f2c8c158e5e1ae2c003'),
    'H2_non_analogy': (40, 'dbca8eda9f820644bd88fe6dabd9893b1c919c65e2a495b4f41b45d1312c847a'),
}
PANEL_PIN = (50, 127, 'f7ad026c9a8a451264c7e4ff0d2b34bcdc8dbfa6c69e528fb57927c813dfdc30')


class Stop(Exception):
    """TOOL_STOP: the inputs cannot give a trustworthy reading, so no reading is printed."""


def upper_tail(k, n):
    """Exact one-sided P(X >= k | n, 1/2); 1 when n == 0 (the frozen grader's binomial_upper_tail)."""
    if n == 0:
        return Fraction(1)
    return Fraction(sum(comb(n, i) for i in range(k, n + 1)), 2 ** n)


def is_regression(b_prime, c_prime, alpha=ALPHA):
    """Design s7.2: a regression iff c' > b' and the exact one-sided p(c', b' + c') <= alpha."""
    return c_prime > b_prime and upper_tail(c_prime, b_prime + c_prime) <= alpha


def smallest_detectable_regression(alpha=ALPHA):
    """The smallest c' with b' = 0 that is flagged (7 at alpha = 1/100)."""
    c_prime = 1
    while not is_regression(0, c_prime, alpha):
        c_prime += 1
    return c_prime


def ids_digest(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode('utf-8')).hexdigest()


def paired_regression(unchanged, repaired, keys, kind_of):
    """One gate's paired comparison. `unchanged` and `repaired` map question id -> right (bool)."""
    keys = sorted(keys)
    gains = [k for k in keys if repaired[k] and not unchanged[k]]
    losses = [k for k in keys if unchanged[k] and not repaired[k]]
    both_right = [k for k in keys if unchanged[k] and repaired[k]]
    both_wrong = [k for k in keys if not unchanged[k] and not repaired[k]]
    b_prime, c_prime, n = len(gains), len(losses), len(keys)
    u_right, r_right = sum(unchanged[k] for k in keys), sum(repaired[k] for k in keys)
    if r_right - u_right != b_prime - c_prime or b_prime + c_prime + len(both_right) + len(both_wrong) != n:
        raise Stop('INTERNAL_COUNT_MISMATCH')
    p = upper_tail(c_prime, b_prime + c_prime)

    def rows(ids):
        return [{'query_id': k, 'kind': kind_of[k]} for k in ids]

    return {
        'questions': n,
        'unchanged_correct': u_right, 'repaired_correct': r_right,
        'unchanged_accuracy': '%d/%d' % (u_right, n), 'repaired_accuracy': '%d/%d' % (r_right, n),
        'difference_correct_repaired_minus_unchanged': r_right - u_right,
        'difference_accuracy_repaired_minus_unchanged': str(Fraction(r_right - u_right, n)) if n else '0',
        'b_prime_gains': b_prime, 'c_prime_losses': c_prime,
        'ties': len(both_right) + len(both_wrong),
        'ties_both_right': len(both_right), 'ties_both_wrong': len(both_wrong),
        'p_one_sided': str(p), 'p_float': float(p),
        'regression_flagged': is_regression(b_prime, c_prime),
        'gains': rows(gains), 'losses': rows(losses),
        'ties_both_right_ids': rows(both_right), 'ties_both_wrong_ids': rows(both_wrong),
    }


def read_receipt(receipt, seed):
    """The held panel, question kinds and checkpoint-10 question outcomes of one receipt, hash-checked."""
    art = Path(receipt) / 'collected' / 'results' / 'artifacts'
    try:
        manifest = {row['name']: row for row in json.loads((art / 'manifest.json').read_bytes())['artifacts']}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Stop('MANIFEST_UNREADABLE:%s:%s' % (type(error).__name__, receipt))
    files = {}

    def load(name):
        entry = manifest.get(name)
        if entry is None:
            raise Stop('NOT_IN_MANIFEST:%s' % name)
        try:
            data = (art / name).read_bytes()
        except OSError:
            raise Stop('MISSING_FILE:%s' % name)
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.get('sha256') or len(data) != entry.get('bytes'):
            raise Stop('HASH_MISMATCH:%s' % name)
        files[name] = digest
        try:
            return json.loads(data)
        except ValueError:
            raise Stop('UNREADABLE_JSON:%s' % name)

    report = load('worker_report.json')
    if not isinstance(report, dict):
        raise Stop('WORKER_REPORT_MALFORMED')
    if report.get('model_seed') != seed:
        raise Stop('SEED_MISMATCH:%s!=%s' % (report.get('model_seed'), seed))
    numbered = {}
    for name in manifest:
        match = SCORING_NAME.match(name)
        if match:
            numbered.setdefault(int(match.group('number')), []).append(name)
    if not numbered or max(numbered) != FINAL_CHECKPOINT:
        raise Stop('FINAL_CHECKPOINT_IS_NOT_%d:%s' % (FINAL_CHECKPOINT, max(numbered) if numbered else None))

    panel, kind_of, record_kind = {}, {}, {}
    try:
        doc = load(PANEL_FILE)
        if doc.get('phase') != PANEL_PHASE:
            raise Stop('PHASE_FIELD:%s' % PANEL_FILE)
        for row in doc['rows']:
            question, record = row['query_id'], row['record_id']
            if kind_of.setdefault(question, row['kind']) != row['kind'] or record in record_kind:
                raise Stop('PANEL_INCONSISTENT:%s' % question)
            record_kind[record] = row['kind']
            panel.setdefault(question, []).append(record)
    except (KeyError, TypeError):
        raise Stop('PANEL_ROWS_MALFORMED')
    panel = {question: sorted(records) for question, records in panel.items()}
    lines = sorted('%s\t%s' % (question, record) for question, records in panel.items() for record in records)
    if (len(panel), len(lines), hashlib.sha256('\n'.join(lines).encode('utf-8')).hexdigest()) != PANEL_PIN:
        raise Stop('PANEL_IS_NOT_THE_PINNED_HISTORICAL_HELD_PANEL')

    final = {}
    for name in sorted(numbered[FINAL_CHECKPOINT]):
        doc = load(name)
        if doc.get('phase') != name[:-len('_scoring.json')]:
            raise Stop('PHASE_FIELD:%s' % name)
        try:
            for row in doc['rows']:
                record, right = row['record_id'], bool(row['correct'])
                if record in final and final[record] != right:
                    raise Stop('SCORING_CONFLICT:%d:%s' % (FINAL_CHECKPOINT, record))
                if record in record_kind and row['kind'] != record_kind[record]:
                    raise Stop('KIND_DIFFERS_FROM_PANEL:%s' % record)
                final[record] = right
        except (KeyError, TypeError):
            raise Stop('SCORING_ROWS_MALFORMED:%s' % name)
    missing = sorted(record for records in panel.values() for record in records if record not in final)
    if missing:
        raise Stop('FINAL_INCOMPLETE:%d_HELD_RECORDS_UNSCORED' % len(missing))
    outcome = {question: all(final[record] for record in records) for question, records in panel.items()}
    identity = {key: report.get(key) for key in
                ('model_seed', 'job', 'source_sha', 'claim_bearing', 'schedule_plan_mode', 'status')}
    return {'panel': panel, 'kind_of': kind_of, 'outcome': outcome,
            'identity': identity, 'path': str(receipt), 'files_read_sha256': files}


def read_gate_reading(path, seed):
    """A pinned-grader reading: its H1 list, its shortcut ids and this seed's historical gate booleans."""
    try:
        data = Path(path).read_bytes()
        reading = json.loads(data)
    except (OSError, ValueError) as error:
        raise Stop('GATE_READING_UNREADABLE:%s:%s' % (type(error).__name__, path))
    try:
        if reading.get('schema') != GATE_READING_SCHEMA:
            raise Stop('GATE_READING_SCHEMA:%s' % reading.get('schema'))
        if (reading.get('label') == 'VOID' or reading.get('void_paths_taken')
                or reading['gates']['integrity']['pass'] is not True):
            raise Stop('GATE_READING_NOT_VALID:%s' % path)
        population = reading['population']
        h1, shortcut = list(population['question_ids']), list(population['shortcut_question_ids'])
        entry = reading['seeds'].get(str(seed))
        if not isinstance(entry, dict):
            raise Stop('GATE_READING_HAS_NO_SEED:%s' % seed)
        old = {name: value['passed'] for name, value in entry.items()
               if isinstance(value, dict) and isinstance(value.get('passed'), bool)}
    except (KeyError, TypeError, AttributeError):
        raise Stop('GATE_READING_MALFORMED:%s' % path)
    for _, historical in GATES:
        if historical not in old:
            raise Stop('GATE_READING_LACKS:%s' % historical)
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'label': reading.get('label'),
            'h1': h1, 'shortcut': shortcut, 'old_gates': old}


def _pass_word(value):
    return None if value is None else ('PASS' if value else 'FAIL')


def old_gate_crossings(unchanged_gate, repaired_gate):
    names = sorted(set(unchanged_gate['old_gates']) | set(repaired_gate['old_gates']))
    rows, crossings = [], []
    for name in names:
        u_pass, r_pass = unchanged_gate['old_gates'].get(name), repaired_gate['old_gates'].get(name)
        crossing = u_pass is not None and r_pass is not None and u_pass != r_pass
        rows.append({'gate': name, 'unchanged': _pass_word(u_pass), 'repaired': _pass_word(r_pass),
                     'crossing': crossing})
        if crossing:
            crossings.append('%s: unchanged %s, repaired %s' % (name, _pass_word(u_pass), _pass_word(r_pass)))
    return {'status': 'READ', 'per_gate': rows, 'crossings': crossings, 'information_only': True}


def parse(argv):
    parser = argparse.ArgumentParser(description='H1/H2 paired no-regression reader (design v0.4 s7.2, A2.6).')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--repaired', required=True, help='repaired receipt dir')
    parser.add_argument('--unchanged', required=True, help='unchanged receipt dir')
    parser.add_argument('--unchanged-gate-reading', required=True,
                        help='pinned-grader reading for the unchanged arm (gives the H1 list and old gates)')
    parser.add_argument('--repaired-gate-reading', help='pinned-grader reading of the repaired study')
    view = parser.add_mutually_exclusive_group(required=True)
    view.add_argument('--mask-analogy', action='store_true',
                      help='non-analogy view (13 and 40 questions); the only view allowed before ITEM2_PASS')
    view.add_argument('--registered-view', action='store_true',
                      help='registered H1/H2 (18 and 45, analogy included); repaired arm: only after ITEM2_PASS')
    args = parser.parse_args(argv)
    if args.mask_analogy and args.repaired_gate_reading:
        parser.error('--repaired-gate-reading is not read in the non-analogy view (every historical gate '
                     'includes analogy questions, A5.1)')
    return args


def reading(args):
    unchanged_gate = read_gate_reading(args.unchanged_gate_reading, args.seed)
    repaired_gate = (read_gate_reading(args.repaired_gate_reading, args.seed)
                     if args.repaired_gate_reading else None)
    if repaired_gate is not None and (sorted(repaired_gate['h1']) != sorted(unchanged_gate['h1'])
                                      or sorted(repaired_gate['shortcut']) != sorted(unchanged_gate['shortcut'])):
        raise Stop('GATE_READINGS_DISAGREE_ON_THE_QUESTION_SETS')
    repaired = read_receipt(args.repaired, args.seed)
    unchanged = read_receipt(args.unchanged, args.seed)
    if repaired['panel'] != unchanged['panel'] or repaired['kind_of'] != unchanged['kind_of']:
        raise Stop('ARMS_HAVE_DIFFERENT_HELD_PANELS')
    kind_of = unchanged['kind_of']
    sets = {'H1': sorted(unchanged_gate['h1']),
            'H2': sorted(set(unchanged['panel']) - set(unchanged_gate['shortcut']))}
    if not set(sets['H1']) <= set(sets['H2']):
        raise Stop('H1_NOT_INSIDE_H2')
    masked = bool(args.mask_analogy)
    if masked:
        sets = {gate: [q for q in ids if kind_of[q] != ANALOGY] for gate, ids in sets.items()}
    gates, flagged = [], []
    for gate, historical in GATES:
        pin_name = gate + ('_non_analogy' if masked else '')
        if (len(sets[gate]), ids_digest(sets[gate])) != PINS[pin_name]:
            raise Stop('GATE_SET_NOT_PINNED:%s' % pin_name)
        result = paired_regression(unchanged['outcome'], repaired['outcome'], sets[gate], kind_of)
        result.update(gate=gate, historical_gate=historical, question_set=pin_name, ids_sha256=ids_digest(sets[gate]))
        gates.append(result)
        if result['regression_flagged']:
            flagged.append(gate)

    incomplete = []
    if masked:
        crossings = {'status': 'NOT_SHOWN_IN_NON_ANALOGY_VIEW',
                     'reason': 'every historical gate is computed over sets that include the 5 analogy questions '
                               '(A5.1); crossings are printed in the registered view'}
    elif repaired_gate is None:
        crossings = {'status': 'NOT_READ',
                     'reason': 'pass --repaired-gate-reading: the reading of the repaired study by ' + PINNED_GRADER}
        incomplete.append('OLD_GATE_CROSSINGS_NOT_READ')
    else:
        crossings = old_gate_crossings(unchanged_gate, repaired_gate)

    self_pair = Path(args.repaired).resolve() == Path(args.unchanged).resolve()
    claim_bearing = all(arm['identity']['claim_bearing'] is True and arm['identity']['schedule_plan_mode'] == 'REGISTERED'
                        for arm in (repaired, unchanged))
    smallest = smallest_detectable_regression()
    own = Path(__file__).read_bytes().replace(b'\r\n', b'\n')
    return {
        'reader': READER, 'reader_sha256_lf': hashlib.sha256(own).hexdigest(),
        'design': 'EVALUATION_DESIGN_v0_4 s7.2 (gate set H1, H2) and amendment A2.6 (reporting and wording)',
        'status': 'READ' if not incomplete else 'READ_REPORT_INCOMPLETE',
        'view': 'NON_ANALOGY_VIEW_EXPLORATORY' if masked else 'REGISTERED_H1_H2',
        'view_rule': ('exploratory only; not condition 4 of REPAIR_IMPROVES_ANALOGY_6 (prereg A5.1/A5.3; '
                      'claude-0024 Q-J default)') if masked else
                     ('registered sets, analogy included; on a repaired arm allowed only after ITEM2_PASS and the '
                      'A5.5 matched-start check; covers the H1/H2 part of condition 4 only'),
        'seed': args.seed, 'self_pair': self_pair,
        'self_pair_note': 'sanity check only: both arms are the same receipt' if self_pair else None,
        'claim_bearing_inputs': claim_bearing,
        'inputs': {
            'repaired': {'receipt': repaired['path'], 'identity': repaired['identity'],
                         'files_read_sha256': repaired['files_read_sha256']},
            'unchanged': {'receipt': unchanged['path'], 'identity': unchanged['identity'],
                          'files_read_sha256': unchanged['files_read_sha256']},
            'unchanged_gate_reading': {k: unchanged_gate[k] for k in ('path', 'sha256', 'label')},
            'repaired_gate_reading': ({k: repaired_gate[k] for k in ('path', 'sha256', 'label')}
                                      if repaired_gate else None),
            'hash_check': "each file read matches the job's own manifest.json (not independent custody)",
        },
        'endpoint': 'checkpoint %d: every <prefix>_p%02d_scoring.json in the manifest (final.pt, 1,470 main updates)'
                    % (FINAL_CHECKPOINT, FINAL_CHECKPOINT),
        'unit': 'a question is right iff every one of its held records is right (%s)' % PINNED_GRADER,
        'rule': "regression iff c_prime > b_prime and exact one-sided P(X >= c_prime | b_prime + c_prime, 1/2) <= 1/100",
        'alpha': str(ALPHA),
        'smallest_detectable_regression': {'c_prime': smallest, 'b_prime': 0,
                                           'p': str(upper_tail(smallest, smallest))},
        'six_loss_sensitivity': {'c_prime': 6, 'b_prime': 0, 'p': str(upper_tail(6, 6)),
                                 'flagged': is_regression(0, 6),
                                 'note': 'six losses and no gains are NOT flagged at 1/100'},
        'gates': gates,
        'regression_flagged_gates': flagged,
        'result': ('REGRESSION_DETECTED:' + ','.join(flagged)) if flagged else 'NO_REGRESSION_DETECTED',
        'caption': None if flagged else CAPTION,
        'old_gate_crossings': crossings,
        'report_incomplete_reasons': incomplete,
        'covers': [gate for gate, _ in GATES], 'not_covered': NOT_COVERED,
        'forbidden_wording': list(FORBIDDEN_WORDING),
        'labels': ['CLAUDE_BUILT_CLAUDE_CHECKED', 'EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT'],
    }


def run(argv):
    """(exit code, document). argparse refusals raise SystemExit(2)."""
    args = parse(argv)
    try:
        return 0, reading(args)
    except Stop as stop:
        return 1, {'reader': READER, 'status': 'TOOL_STOP', 'reason': str(stop)}


def main(argv=None):
    code, document = run(sys.argv[1:] if argv is None else argv)
    sys.stdout.write(json.dumps(document, indent=1, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    sys.exit(main())
