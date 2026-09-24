"""Acceptance tests for h1h2_paired.py (readout plan item 3). Pure Python, no torch; run once with
    python -B test_h1h2_paired.py
Reads the committed Helm 2.0 receipts read-only. Planted receipts are written to a system temp folder only.

Acceptance (plan item 3):
  * self-pair on Helm 2.0 seed 17 gives 12/18 and 33/45 with b' = c' = 0;
  * a planted case with 7 losses and 0 gains is flagged;
  * a planted case with 6 losses is not flagged (p = 1/64).
"""
import hashlib
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import h1h2_paired as H  # noqa: E402

TP = HERE.parents[2] / 'typed_pointer_001'
GATE_READING = TP / 'admission_001' / 'gate_reading.json'
SEED = 20260917
RECEIPT = TP / ('receipt_%d' % SEED)
FILES = ('manifest.json', 'worker_report.json', 'heldback_p02_scoring.json',
         'course_p10_scoring.json', 'development_p10_scoring.json')


def run(repaired, unchanged, view='--registered-view', seed=SEED, extra=()):
    return H.run(['--seed', str(seed), '--repaired', str(repaired), '--unchanged', str(unchanged),
                  '--unchanged-gate-reading', str(GATE_READING), view, *extra])


def gate(document, name):
    return [row for row in document['gates'] if row['gate'] == name][0]


def seed17_state():
    """(panel, kind_of, outcome) of the committed seed-17 receipt, via the reader itself."""
    arm = H.read_receipt(RECEIPT, SEED)
    return arm['panel'], arm['kind_of'], arm['outcome']


def planted_receipt(root, flips):
    """A copy of seed 17's needed files with the listed questions' records set to the given value at p10.
    The copied manifest is rewritten with the new hashes, as an honest job would have written them."""
    panel, _, _ = seed17_state()
    target = {record: value for question, value in flips.items() for record in panel[question]}
    src = RECEIPT / 'collected' / 'results' / 'artifacts'
    art = Path(root) / 'collected' / 'results' / 'artifacts'
    art.mkdir(parents=True)
    manifest = json.loads((src / 'manifest.json').read_bytes())
    by_name = {row['name']: row for row in manifest['artifacts']}
    for name in FILES[1:]:
        data = (src / name).read_bytes()
        if name == 'course_p10_scoring.json' and target:
            doc = json.loads(data)
            hit = 0
            for row in doc['rows']:
                if row['record_id'] in target:
                    row['correct'] = target[row['record_id']]
                    hit += 1
            assert hit == len(target), 'every planted record must be in course_p10'
            data = json.dumps(doc).encode('utf-8')
        (art / name).write_bytes(data)
        by_name[name]['sha256'] = hashlib.sha256(data).hexdigest()
        by_name[name]['bytes'] = len(data)
    (art / 'manifest.json').write_bytes(json.dumps(manifest).encode('utf-8'))
    return Path(root)


class PureRule(unittest.TestCase):
    def test_tail_and_thresholds(self):
        self.assertEqual(H.upper_tail(7, 7), Fraction(1, 128))
        self.assertEqual(H.upper_tail(6, 6), Fraction(1, 64))
        self.assertEqual(H.smallest_detectable_regression(), 7)
        self.assertTrue(H.is_regression(0, 7))
        self.assertFalse(H.is_regression(0, 6))
        self.assertFalse(H.is_regression(1, 7))  # p = 9/256: more losses than gains is not enough
        self.assertEqual(H.upper_tail(7, 8), Fraction(9, 256))
        self.assertFalse(H.is_regression(7, 0))  # gains are never a regression
        self.assertEqual(H.upper_tail(0, 0), Fraction(1))


class Acceptance(unittest.TestCase):
    def test_inputs_are_the_committed_ones(self):
        self.assertTrue(GATE_READING.is_file() and RECEIPT.is_dir(), 'committed Helm 2.0 receipts must be on disk')

    def test_self_pair_seed17_registered(self):
        code, doc = run(RECEIPT, RECEIPT)
        self.assertEqual(code, 0, doc)
        h1, h2 = gate(doc, 'H1'), gate(doc, 'H2')
        self.assertEqual((h1['unchanged_accuracy'], h1['repaired_accuracy']), ('12/18', '12/18'))
        self.assertEqual((h2['unchanged_accuracy'], h2['repaired_accuracy']), ('33/45', '33/45'))
        for row in (h1, h2):
            self.assertEqual((row['b_prime_gains'], row['c_prime_losses']), (0, 0))
            self.assertEqual(row['ties'], row['questions'])
            self.assertEqual(row['p_one_sided'], '1')
            self.assertFalse(row['regression_flagged'])
        self.assertEqual((h1['ties_both_right'], h1['ties_both_wrong']), (12, 6))
        self.assertEqual(doc['result'], 'NO_REGRESSION_DETECTED')
        self.assertEqual(doc['caption'], 'no regression detected by the listed paired tests')
        self.assertTrue(doc['self_pair'] and doc['claim_bearing_inputs'])
        self.assertEqual(doc['smallest_detectable_regression'], {'c_prime': 7, 'b_prime': 0, 'p': '1/128'})
        self.assertEqual((doc['six_loss_sensitivity']['p'], doc['six_loss_sensitivity']['flagged']), ('1/64', False))
        # no repaired gate reading given: the crossings are named as missing, never silently skipped
        self.assertEqual(doc['old_gate_crossings']['status'], 'NOT_READ')
        self.assertEqual(doc['status'], 'READ_REPORT_INCOMPLETE')
        self.assertEqual(doc['report_incomplete_reasons'], ['OLD_GATE_CROSSINGS_NOT_READ'])

    def test_self_pair_with_both_gate_readings_has_no_crossings(self):
        code, doc = run(RECEIPT, RECEIPT, extra=('--repaired-gate-reading', str(GATE_READING)))
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc['status'], 'READ')
        crossings = doc['old_gate_crossings']
        self.assertEqual((crossings['status'], crossings['crossings']), ('READ', []))
        names = {row['gate']: row for row in crossings['per_gate']}
        self.assertEqual(names['G_LEARN_population']['unchanged'], 'PASS')  # Helm 2.0 seed 17: 11/1, p = 13/4096

    def test_other_seeds_reproduce_the_frozen_reading(self):
        frozen = json.loads(GATE_READING.read_bytes())['seeds']
        for seed, h1_right, h2_right in ((20260918, 12, 35), (20260919, 10, 32)):
            receipt = TP / ('receipt_%d' % seed)
            code, doc = run(receipt, receipt, seed=seed)
            self.assertEqual(code, 0, doc)
            self.assertEqual(gate(doc, 'H1')['unchanged_correct'], h1_right)
            self.assertEqual(gate(doc, 'H2')['unchanged_correct'], h2_right)
            self.assertEqual(frozen[str(seed)]['population_questions_correct']['10'], h1_right)
            self.assertEqual(frozen[str(seed)]['eligible_questions_correct']['10'], h2_right)

    def test_self_pair_seed17_non_analogy_view(self):
        code, doc = run(RECEIPT, RECEIPT, view='--mask-analogy')
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc['view'], 'NON_ANALOGY_VIEW_EXPLORATORY')
        h1, h2 = gate(doc, 'H1'), gate(doc, 'H2')
        self.assertEqual((h1['questions'], h2['questions']), (13, 40))
        self.assertEqual((h1['unchanged_accuracy'], h2['unchanged_accuracy']), ('12/13', '33/40'))
        listed = [item for row in (h1, h2) for key in ('gains', 'losses', 'ties_both_right_ids', 'ties_both_wrong_ids')
                  for item in row[key]]
        self.assertTrue(listed and all(item['kind'] != 'analogy' for item in listed))
        self.assertEqual(doc['old_gate_crossings']['status'], 'NOT_SHOWN_IN_NON_ANALOGY_VIEW')

    def _right_h1_non_analogy(self):
        _, kind_of, outcome = seed17_state()
        h1 = json.loads(GATE_READING.read_bytes())['population']['question_ids']
        return sorted(q for q in h1 if outcome[q] and kind_of[q] != 'analogy')

    def test_planted_seven_losses_is_flagged(self):
        losers = self._right_h1_non_analogy()[:7]
        with tempfile.TemporaryDirectory() as tmp:
            code, doc = run(planted_receipt(tmp, {q: False for q in losers}), RECEIPT)
            self.assertEqual(code, 0, doc)
            for name in ('H1', 'H2'):
                row = gate(doc, name)
                self.assertEqual((row['b_prime_gains'], row['c_prime_losses']), (0, 7))
                self.assertEqual(row['p_one_sided'], '1/128')
                self.assertTrue(row['regression_flagged'])
                self.assertEqual(sorted(item['query_id'] for item in row['losses']), losers)
            self.assertEqual(gate(doc, 'H1')['repaired_accuracy'], '5/18')
            self.assertEqual(gate(doc, 'H1')['difference_accuracy_repaired_minus_unchanged'], '-7/18')
            self.assertEqual(doc['result'], 'REGRESSION_DETECTED:H1,H2')
            self.assertIsNone(doc['caption'])
            code, masked = run(Path(tmp), RECEIPT, view='--mask-analogy')
            self.assertEqual(code, 0, masked)
            self.assertTrue(gate(masked, 'H1')['regression_flagged'])

    def test_planted_six_losses_is_not_flagged(self):
        losers = self._right_h1_non_analogy()[:6]
        with tempfile.TemporaryDirectory() as tmp:
            code, doc = run(planted_receipt(tmp, {q: False for q in losers}), RECEIPT)
            self.assertEqual(code, 0, doc)
            for name in ('H1', 'H2'):
                row = gate(doc, name)
                self.assertEqual((row['b_prime_gains'], row['c_prime_losses']), (0, 6))
                self.assertEqual(row['p_one_sided'], '1/64')
                self.assertFalse(row['regression_flagged'])
            self.assertEqual(doc['result'], 'NO_REGRESSION_DETECTED')
            self.assertEqual(doc['caption'], 'no regression detected by the listed paired tests')

    def test_planted_seven_gains_is_not_a_regression(self):
        _, kind_of, outcome = seed17_state()
        wrong = sorted(q for q in outcome if not outcome[q] and kind_of[q] != 'analogy')
        shortcut = set(json.loads(GATE_READING.read_bytes())['population']['shortcut_question_ids'])
        winners = [q for q in wrong if q not in shortcut][:7]
        self.assertEqual(len(winners), 7)
        with tempfile.TemporaryDirectory() as tmp:
            code, doc = run(planted_receipt(tmp, {q: True for q in winners}), RECEIPT)
            self.assertEqual(code, 0, doc)
            row = gate(doc, 'H2')
            self.assertEqual((row['b_prime_gains'], row['c_prime_losses'], row['regression_flagged']), (7, 0, False))


class Refusals(unittest.TestCase):
    def test_edited_file_without_manifest_is_a_tool_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = planted_receipt(tmp, {})
            path = receipt / 'collected' / 'results' / 'artifacts' / 'course_p10_scoring.json'
            path.write_bytes(path.read_bytes() + b' ')
            code, doc = run(receipt, RECEIPT)
            self.assertEqual((code, doc['status']), (1, 'TOOL_STOP'))
            self.assertEqual(doc['reason'], 'HASH_MISMATCH:course_p10_scoring.json')

    def test_wrong_seed_pair_is_a_tool_stop(self):
        code, doc = run(RECEIPT, TP / 'receipt_20260918')
        self.assertEqual((code, doc['reason']), (1, 'SEED_MISMATCH:20260918!=20260917'))

    def test_a_view_flag_is_required(self):
        with self.assertRaises(SystemExit) as raised:
            H.run(['--seed', str(SEED), '--repaired', str(RECEIPT), '--unchanged', str(RECEIPT),
                   '--unchanged-gate-reading', str(GATE_READING)])
        self.assertEqual(raised.exception.code, 2)

    def test_masked_view_refuses_a_repaired_gate_reading(self):
        with self.assertRaises(SystemExit) as raised:
            run(RECEIPT, RECEIPT, view='--mask-analogy', extra=('--repaired-gate-reading', str(GATE_READING)))
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
