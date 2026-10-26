"""Known-example check for scorer_v0_1. Status: NOT RUN. Runs on AWS as a software test; loads no model.

Every expected category in scorer_examples_v0_1.json was decided by hand from the written rules.
"""
import json
import unittest
from pathlib import Path

import scorer_v0_1 as scorer

EXAMPLES = json.loads((Path(__file__).resolve().parent.parent / 'scorer_examples_v0_1.json').read_text(encoding='utf-8'))['examples']


class KnownExamples(unittest.TestCase):
    def test_exactly_thirty_examples(self):
        self.assertEqual(len(EXAMPLES), 30)
        self.assertEqual(len({row['id'] for row in EXAMPLES}), 30)

    def test_every_example_gets_its_hand_decided_category(self):
        wrong = [(row['id'], row['expected'], scorer.categorize(row['raw_text'], row['task_answer'], row['cut_off']))
                 for row in EXAMPLES
                 if scorer.categorize(row['raw_text'], row['task_answer'], row['cut_off']) != row['expected']]
        self.assertEqual(wrong, [])

    def test_every_category_is_exercised(self):
        self.assertEqual({row['expected'] for row in EXAMPLES}, set(scorer.CATEGORIES))

    def test_primary_score_is_one_only_for_correct(self):
        for row in EXAMPLES:
            self.assertEqual(scorer.primary_score(row['raw_text'], row['task_answer'], row['cut_off']),
                             1 if row['expected'] == 'CORRECT' else 0, row['id'])

    def test_true_is_not_a_whole_number(self):
        self.assertEqual(scorer.categorize('{"answer": true}', 1), 'FORMAT_FAIL')

    def test_secondary_view_changes_only_type_mismatches(self):
        for row in EXAMPLES:
            first = scorer.categorize(row['raw_text'], row['task_answer'], row['cut_off'])
            second = scorer.secondary_category(row['raw_text'], row['task_answer'], row['cut_off'])
            if first != 'TYPE_MISMATCH':
                self.assertEqual(first, second, row['id'])
        self.assertEqual(scorer.secondary_category('{"answer": "4"}', 4), 'CORRECT')
        self.assertEqual(scorer.secondary_category('{"answer": "5"}', 4), 'WRONG')
        self.assertEqual(scorer.secondary_category('{"answer": "piano"}', ['piano']), 'TYPE_MISMATCH')

    def test_tally_adds_up(self):
        counts = scorer.tally((row['raw_text'], row['task_answer'], row['cut_off']) for row in EXAMPLES)
        self.assertEqual(sum(counts.values()), 30)


if __name__ == '__main__':
    unittest.main()
